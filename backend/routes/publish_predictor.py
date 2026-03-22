"""
Publish-probability predictor.

Trains a CalibratedRandomForestClassifier from DB data on first request (or loads
cached weights from disk).  Exposes /options and /predict for the
front-end "Publish Oracle" game.

Fixes applied:
- Removed polynomial features (harmful to tree-based models, near-zero values)
- Added max_depth=20, min_samples_split=20, min_samples_leaf=10 to prevent overfitting
- Raised n_estimators to 300 for smoother vote boundary and less volatility
- Wrapped model in CalibratedClassifierCV (isotonic) for better probability calibration
- Replaced manual tree vote loop with predict_proba
- Added max_upload_to_create_days (95th percentile) to options for dynamic JSX cap
"""

import logging
import math
import pathlib
from typing import Any

import joblib
import numpy as np
import pandas as pd
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
import shap

from backend.db.pool import query
from backend.middleware.auth import AuthContext, require_auth

logger = logging.getLogger(__name__)
router = APIRouter()

MODEL_DIR = pathlib.Path(__file__).resolve().parent.parent / "models"
MODEL_PATH = MODEL_DIR / "publish_predictor.pkl"
META_PATH  = MODEL_DIR / "publish_predictor_meta.pkl"

_model: CalibratedClassifierCV | None = None
_meta:  dict[str, Any] | None         = None


# ── helpers ───────────────────────────────────────────────────────────────────

def _build_option_scope_maps(df: pd.DataFrame, clients: list[str]) -> dict[str, dict[str, Any]]:
    """Build per-client option maps used to scope non-admin responses."""
    scope_maps: dict[str, dict[str, Any]] = {
        "input_types_by_client":             {},
        "languages_by_client":               {},
        "output_types_by_client":            {},
        "max_uploaded_duration_by_client":   {},
        "max_created_duration_by_client":    {},
        "max_upload_to_create_days_by_client": {},
    }

    for client in clients:
        client_df = df.loc[df["Client_Name"] == client]
        scope_maps["input_types_by_client"][client] = sorted(
            client_df["Input_Type"].dropna().unique().tolist()
        )
        scope_maps["languages_by_client"][client] = sorted(
            client_df["Language"].dropna().unique().tolist()
        )
        scope_maps["output_types_by_client"][client] = sorted(
            client_df["Output_Type"].dropna().unique().tolist()
        )
        scope_maps["max_uploaded_duration_by_client"][client] = int(
            client_df["Uploaded_Duration"].dropna().max() or 15000
        )
        scope_maps["max_created_duration_by_client"][client] = int(
            client_df["Created_Duration"].dropna().max() or 10000
        )
        # Use 95th percentile so one outlier doesn't collapse the slider range
        p95_days = client_df["Upload_to_Create_Days"].dropna().quantile(0.95)
        scope_maps["max_upload_to_create_days_by_client"][client] = int(p95_days or 30)

    return scope_maps


def _base_feature_name(feature_name: str) -> str:
    """Collapse one-hot encoded columns back to their parent feature name."""
    categorical_prefixes = (
        "Client_Name",
        "Assigned_Channel",
        "Input_Type",
        "Language",
        "Output_Type",
    )
    for prefix in categorical_prefixes:
        if feature_name.startswith(f"{prefix}_"):
            return prefix
    return feature_name


def _sigmoid(value: float) -> float:
    return 1.0 / (1.0 + math.exp(-value))


def _load_training_data() -> pd.DataFrame:
    """Replicate the notebook's master-df from the live database."""
    result = query("""
        SELECT
            u."Client_Name",
            rvc."Channel_Name"   AS "Assigned_Channel",
            rv."Input_Type",
            rv."Language",
            rv."Uploaded_Duration",
            rv."Upload_Date",
            ca."Output_Type",
            ca."Created_Duration",
            ca."Create_Date",
            pd."Published_URL"
        FROM raw_videos rv
        LEFT JOIN users             u   ON rv."User_ID"  = u."User_ID"
        LEFT JOIN raw_video_channel rvc ON rv."Video_ID" = rvc."Video_ID"
        LEFT JOIN created_assets    ca  ON rv."Video_ID" = ca."Video_ID"
        LEFT JOIN published_posts   pp  ON ca."Asset_ID" = pp."Asset_ID"
        LEFT JOIN post_distribution pd  ON pp."Post_ID"  = pd."Post_ID"
    """)
    return pd.DataFrame(result.rows)


def _train_and_save() -> None:
    global _model, _meta

    logger.info("publish_predictor: training model from DB …")
    df = _load_training_data()

    # ── Feature engineering ────────────────────────────────────────────────
    for col in ("Upload_Date", "Create_Date"):
        df[col] = pd.to_datetime(df[col], errors="coerce")

    # Target variable: binary flag — was this asset published?
    df["Is_Published"] = df["Published_URL"].notna().astype(int)

    # Derived temporal feature
    df["Upload_to_Create_Days"] = (
        (df["Create_Date"] - df["Upload_Date"]).dt.total_seconds() / 86400
    )

    # Filter to asset-level records (must have been through editing stage)
    df = df.dropna(subset=["Created_Duration"]).copy()

    # Handle missing values
    df["Upload_to_Create_Days"] = df["Upload_to_Create_Days"].fillna(0)
    df["Output_Type"]           = df["Output_Type"].fillna("None")

    # Drop identifier and leakage columns
    drop_cols = ["Published_URL", "Create_Date", "Upload_Date"]
    df = df.drop(columns=[c for c in drop_cols if c in df.columns])

    # Extract dynamic frontend options before dummying
    # Use 95th percentile for days cap — prevents a single outlier from
    # making the slider useless in the UI.
    p95_days = int(df["Upload_to_Create_Days"].dropna().quantile(0.95) or 30)

    options: dict[str, Any] = {
        "clients":      sorted(df["Client_Name"].dropna().unique().tolist()),
        "channels":     sorted(df["Assigned_Channel"].dropna().unique().tolist()),
        "input_types":  sorted(df["Input_Type"].dropna().unique().tolist()),
        "languages":    sorted(df["Language"].dropna().unique().tolist()),
        "output_types": sorted(df["Output_Type"].dropna().unique().tolist()),
        "max_uploaded_duration":      int(df["Uploaded_Duration"].dropna().max() or 15000),
        "max_created_duration":       int(df["Created_Duration"].dropna().max() or 10000),
        "max_upload_to_create_days":  p95_days,
        "channel_by_client": {},
    }
    for client in options["clients"]:
        options["channel_by_client"][client] = sorted(
            df.loc[df["Client_Name"] == client, "Assigned_Channel"]
            .dropna().unique().tolist()
        )
    options.update(_build_option_scope_maps(df, options["clients"]))

    # ── Prepare X and y ───────────────────────────────────────────────────
    y = df["Is_Published"]
    X = df.drop(columns=["Is_Published"])

    # Fill remaining NaN in numeric cols
    X["Uploaded_Duration"]     = X["Uploaded_Duration"].fillna(0)
    X["Created_Duration"]      = X["Created_Duration"].fillna(0)
    X["Upload_to_Create_Days"] = X["Upload_to_Create_Days"].fillna(0)

    # Strip and clean string cols before one-hot encoding
    for col in X.select_dtypes(include="object").columns:
        X[col] = X[col].apply(lambda x: x.strip() if isinstance(x, str) else x)
        X[col] = X[col].fillna("Unknown")

    # NOTE: Polynomial features deliberately removed.
    # RandomForest is a tree-based model — it splits on thresholds, not
    # polynomial curves.  High-power features (^7, ^9, ^11) on normalised
    # [0,1] inputs collapse to near-zero for virtually all real values,
    # adding noisy near-identical columns that destabilise the vote boundary.

    # Convert to dummies
    X = pd.get_dummies(X, drop_first=True)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # ── Model — tuned for stability and calibration ───────────────────────
    # max_depth=20          — prevents full memorisation of training data
    # min_samples_split=20  — requires meaningful evidence before splitting
    # min_samples_leaf=10   — each leaf must represent real signal
    # n_estimators=300      — smoother vote boundary; each tree = 0.33% not 1%
    # CalibratedClassifierCV — isotonic regression maps raw RF votes to
    #                          true probabilities, widening the 0–100 range
    base_rf = RandomForestClassifier(
        n_estimators=300,
        max_depth=20,
        min_samples_split=20,
        min_samples_leaf=10,
        max_features="sqrt",
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )

    model = CalibratedClassifierCV(base_rf, method="isotonic", cv=5)
    model.fit(X_train, y_train)

    accuracy = float(model.score(X_test, y_test))
    logger.info("publish_predictor: accuracy=%.4f", accuracy)

    sample_counts = df["Is_Published"].value_counts().to_dict()

    meta = {
        "training_columns": list(X_train.columns),
        "options":          options,
        "accuracy":         round(accuracy, 4),
        "classes":          [0, 1],
        "sample_counts":    sample_counts,
        "total_samples":    len(df),
    }

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    joblib.dump(meta,  META_PATH)
    _model, _meta = model, meta


def _ensure_model(auth: AuthContext | None = None) -> str | None:
    """Load or train the model. Returns an error string if unavailable."""
    global _model, _meta
    if _model is not None:
        return None
    if MODEL_PATH.exists() and META_PATH.exists():
        logger.info("publish_predictor: loading cached model from disk")
        _model = joblib.load(MODEL_PATH)
        _meta  = joblib.load(META_PATH)
        return None

    if auth is None or auth.role != "website_admin":
        return "Model not trained yet. Please ask a Frammer admin to log in first to initialize the model."
    _train_and_save()
    return None


# ── request schema ────────────────────────────────────────────────────────────

class PredictRequest(BaseModel):
    client_name:           str
    assigned_channel:      str
    input_type:            str
    language:              str
    output_type:           str
    uploaded_duration:     float
    created_duration:      float
    upload_to_create_days: float


# ── auth helpers ──────────────────────────────────────────────────────────────

def _allowed_clients(auth: AuthContext) -> list[str] | None:
    if auth.role == "website_admin":
        return None          # None == all clients allowed
    return [auth.client_name] if auth.client_name else []


def _scope_options(opts: dict, auth: AuthContext) -> dict:
    allowed = _allowed_clients(auth)
    if allowed is None:
        return opts          # admin sees everything

    scoped = {**opts}
    scoped["clients"] = [c for c in opts.get("clients", []) if c in allowed]

    cbc = opts.get("channel_by_client", {})
    scoped["channel_by_client"] = {c: cbc[c] for c in allowed if c in cbc}
    scoped["channels"] = sorted(ch for c in allowed for ch in cbc.get(c, []))

    input_types_by_client              = opts.get("input_types_by_client", {})
    languages_by_client                = opts.get("languages_by_client", {})
    output_types_by_client             = opts.get("output_types_by_client", {})
    max_uploaded_by_client             = opts.get("max_uploaded_duration_by_client", {})
    max_created_by_client              = opts.get("max_created_duration_by_client", {})
    max_upload_to_create_days_by_client = opts.get("max_upload_to_create_days_by_client", {})

    scoped["input_types"] = sorted(list(set(
        it for c in allowed for it in input_types_by_client.get(c, [])
    ))) or []
    scoped["languages"] = sorted(list(set(
        lang for c in allowed for lang in languages_by_client.get(c, [])
    ))) or []
    scoped["output_types"] = sorted(list(set(
        ot for c in allowed for ot in output_types_by_client.get(c, [])
    ))) or []
    scoped["max_uploaded_duration"] = max(
        [int(max_uploaded_by_client.get(c, 0) or 0) for c in allowed] or [0]
    ) or int(opts.get("max_uploaded_duration") or 15000)
    scoped["max_created_duration"] = max(
        [int(max_created_by_client.get(c, 0) or 0) for c in allowed] or [0]
    ) or int(opts.get("max_created_duration") or 10000)
    scoped["max_upload_to_create_days"] = max(
        [int(max_upload_to_create_days_by_client.get(c, 0) or 0) for c in allowed] or [0]
    ) or int(opts.get("max_upload_to_create_days") or 30)

    return scoped


def _validate_client(auth: AuthContext, requested_client: str) -> str | None:
    allowed = _allowed_clients(auth)
    if allowed is None:
        return None
    if not allowed:
        return "Access denied: no client scope found for your account"
    if requested_client not in allowed:
        return f"Access denied: you may only use client(s) {', '.join(allowed)}"
    return None


def _validate_channel(requested_client: str, requested_channel: str) -> str | None:
    channel_map      = (_meta or {}).get("options", {}).get("channel_by_client", {})
    allowed_channels = set(channel_map.get(requested_client, []))
    if requested_channel not in allowed_channels:
        return (
            f"Access denied: channel '{requested_channel}' is not available "
            f"for client '{requested_client}'"
        )
    return None


# ── endpoints ─────────────────────────────────────────────────────────────────

@router.get("/options")
def predictor_options(auth: AuthContext = Depends(require_auth)):
    try:
        model_err = _ensure_model(auth)
        if model_err:
            return JSONResponse({"error": model_err}, status_code=503)
        scoped  = _scope_options(_meta["options"], auth)
        payload = {**scoped}
        if auth.role == "website_admin":
            payload.update({
                "accuracy":      _meta["accuracy"],
                "classes":       _meta["classes"],
                "total_samples": _meta.get("total_samples", 0),
            })
        return payload
    except Exception as exc:
        logger.exception("predictor options failed")
        return JSONResponse({"error": str(exc)}, status_code=500)


@router.post("/predict")
def predictor_predict(req: PredictRequest, auth: AuthContext = Depends(require_auth)):
    try:
        err = _validate_client(auth, req.client_name)
        if err:
            return JSONResponse({"error": err}, status_code=403)

        model_err = _ensure_model(auth)
        if model_err:
            return JSONResponse({"error": model_err}, status_code=503)

        if auth.role != "website_admin":
            channel_err = _validate_channel(req.client_name, req.assigned_channel)
            if channel_err:
                return JSONResponse({"error": channel_err}, status_code=403)

        # 1. Clamp inputs to observed training ranges
        max_up_dur   = float((_meta or {}).get("options", {}).get("max_uploaded_duration", 15000) or 15000)
        max_cr_dur   = float((_meta or {}).get("options", {}).get("max_created_duration", 10000)  or 10000)
        max_days     = float((_meta or {}).get("options", {}).get("max_upload_to_create_days", 30) or 30)

        uploaded_duration     = max(0.0, min(float(req.uploaded_duration),     max_up_dur))
        created_duration      = max(0.0, min(float(req.created_duration),      max_cr_dur))
        upload_to_create_days = max(0.0, min(float(req.upload_to_create_days), max_days))

        # 2. Build sample DataFrame matching training schema (no polynomial features)
        sample = pd.DataFrame([{
            "Client_Name":           req.client_name,
            "Assigned_Channel":      req.assigned_channel,
            "Input_Type":            req.input_type,
            "Language":              req.language,
            "Output_Type":           req.output_type,
            "Uploaded_Duration":     uploaded_duration,
            "Created_Duration":      created_duration,
            "Upload_to_Create_Days": upload_to_create_days,
        }])

        # 3. Dummy encoding and feature alignment
        sample_enc   = pd.get_dummies(sample)
        sample_final = sample_enc.reindex(
            columns=_meta["training_columns"], fill_value=0
        )

        # 4. Calibrated probability via predict_proba
        #    CalibratedClassifierCV.predict_proba returns true probability
        #    estimates (not raw vote fractions), giving a wider, more
        #    realistic 0–100 output range.
        proba       = _model.predict_proba(sample_final.values)[0]
        classes     = list(_model.classes_)
        publish_idx = classes.index(1) if 1 in classes else -1

        if publish_idx == -1:
            probability = 0.0
        else:
            probability = float(proba[publish_idx] * 100)

        # Reconstruct vote counts as approximate integers for display
        n_estimators = getattr(
            getattr(_model, "estimator", None), "n_estimators", 300
        )
        yes_votes     = int(round(probability * n_estimators / 100))
        no_votes      = n_estimators - yes_votes
        predicted_class = "1" if probability >= 50 else "0"

        # 5. SHAP — use the base RandomForest inside the calibrated wrapper
        raw_top_impacts: list[dict] = []
        grouped_top_impacts: list[dict] = []
        try:
            # CalibratedClassifierCV stores base estimators in .calibrated_classifiers_
            # Each has a .estimator attribute pointing to the fitted RF.
            base_rf = _model.calibrated_classifiers_[0].estimator
            explainer   = shap.TreeExplainer(base_rf)
            shap_values = explainer.shap_values(sample_final)

            # Extract class-1 (Is_Published = True) SHAP values
            if isinstance(shap_values, list):
                vals = shap_values[1][0]
            elif len(shap_values.shape) == 3:
                vals = shap_values[0, :, 1]
            else:
                vals = shap_values[0]

            features = list(sample_final.columns)
            expected_value = explainer.expected_value
            if isinstance(expected_value, list):
                base_log_odds = float(expected_value[1] if len(expected_value) > 1 else expected_value[0])
            elif hasattr(expected_value, "shape"):
                flat = np.ravel(expected_value)
                base_log_odds = float(flat[1] if flat.size > 1 else flat[0])
            else:
                base_log_odds = float(expected_value)

            base_probability = _sigmoid(base_log_odds)

            impacts  = []
            for feature_name, shap_value in zip(features, vals):
                shap_impact = float(shap_value)
                if abs(shap_impact) <= 0:
                    continue
                marginal_probability = _sigmoid(base_log_odds + shap_impact)
                probability_contribution = float(marginal_probability - base_probability)
                impacts.append({
                    "feature": str(feature_name),
                    "impact": shap_impact,
                    "probability_contribution": probability_contribution,
                })

            impacts.sort(
                key=lambda x: abs(x.get("probability_contribution", 0.0)),
                reverse=True,
            )
            raw_top_impacts = impacts[:10]

            grouped: dict[str, dict[str, float]] = {}
            for item in impacts:
                base_name = _base_feature_name(item["feature"])
                if base_name not in grouped:
                    grouped[base_name] = {
                        "impact": 0.0,
                        "probability_contribution": 0.0,
                    }
                grouped[base_name]["impact"] += float(item["impact"])
                grouped[base_name]["probability_contribution"] += float(
                    item.get("probability_contribution", 0.0)
                )

            grouped_top_impacts = [
                {
                    "feature": feature,
                    "impact": values["impact"],
                    "probability_contribution": values["probability_contribution"],
                }
                for feature, values in grouped.items()
                if abs(values["impact"]) > 0
            ]
            grouped_top_impacts.sort(
                key=lambda x: abs(x.get("probability_contribution", 0.0)),
                reverse=True,
            )
            grouped_top_impacts = grouped_top_impacts[:10]
        except Exception as e:
            logger.warning("SHAP RCA failed: %s", e)

        return {
            "publish_probability": float(round(probability, 2)),
            "yes_votes":           int(yes_votes),
            "no_votes":            int(no_votes),
            "predicted_class":     str(predicted_class),
            "shap_impacts":        grouped_top_impacts,
            "grouped_shap_impacts": grouped_top_impacts,
            "raw_shap_impacts":    raw_top_impacts,
        }
    except Exception as exc:
        logger.exception("prediction failed")
        return JSONResponse({"error": str(exc)}, status_code=500)


@router.post("/retrain")
def predictor_retrain(auth: AuthContext = Depends(require_auth)):
    if auth.role != "website_admin":
        return JSONResponse({"error": "Admin access required"}, status_code=403)
    global _model, _meta
    try:
        _model, _meta = None, None
        for p in (MODEL_PATH, META_PATH):
            if p.exists():
                p.unlink()
        _train_and_save()
        return {"status": "ok", "accuracy": _meta["accuracy"]}
    except Exception as exc:
        logger.exception("retrain failed")
        return JSONResponse({"error": str(exc)}, status_code=500)
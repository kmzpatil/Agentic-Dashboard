"""
Publish-probability predictor.

Trains a RandomForestClassifier from DB data on first request (or loads
cached weights from disk).  Exposes /options and /predict for the
front-end "Publish Oracle" game.
"""

import logging
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

from backend.db.pool import query
from backend.middleware.auth import AuthContext, require_auth

logger = logging.getLogger(__name__)
router = APIRouter()

MODEL_DIR = pathlib.Path(__file__).resolve().parent.parent / "models"
MODEL_PATH = MODEL_DIR / "publish_predictor.pkl"
META_PATH = MODEL_DIR / "publish_predictor_meta.pkl"

_model: RandomForestClassifier | None = None
_meta: dict[str, Any] | None = None


# ── helpers ───────────────────────────────────────────────────────────────────

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
            pp."Publish_Date"
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

    # ── feature engineering (mirrors the notebook exactly) ────────────────
    for col in ("Upload_Date", "Create_Date", "Publish_Date"):
        df[col] = pd.to_datetime(df[col], errors="coerce")

    df["Upload_to_Create_Days"] = (
        (df["Create_Date"] - df["Upload_Date"]).dt.total_seconds() / 86400
    )
    df["Days_to_Publish"] = (
        (df["Publish_Date"] - df["Create_Date"]).dt.total_seconds() / 86400
    )
    df["Is_Published"] = df["Publish_Date"].notna()

    # target
    def _timeframe(row):
        if not row["Is_Published"]:
            return "0_Never"
        d = row["Days_to_Publish"]
        if d <= 1:
            return "1_Within_1_Day"
        if d <= 2:
            return "2_Within_2_Days"
        if d <= 3:
            return "3_Within_3_Days"
        return "4_More_than_3_Days"

    df["Publish_Timeframe"] = df.apply(_timeframe, axis=1)

    # dropdown options (before dropping columns)
    options: dict[str, Any] = {
        "clients":      sorted(df["Client_Name"].dropna().unique().tolist()),
        "channels":     sorted(df["Assigned_Channel"].dropna().unique().tolist()),
        "input_types":  sorted(df["Input_Type"].dropna().unique().tolist()),
        "languages":    sorted(df["Language"].dropna().unique().tolist()),
        "output_types": sorted(df["Output_Type"].dropna().unique().tolist()),
        "max_uploaded_duration": int(df["Uploaded_Duration"].dropna().max() or 15000),
        "max_created_duration":  int(df["Created_Duration"].dropna().max() or 10000),
        "channel_by_client": {},
    }
    for client in options["clients"]:
        options["channel_by_client"][client] = sorted(
            df.loc[df["Client_Name"] == client, "Assigned_Channel"]
            .dropna().unique().tolist()
        )

    # ── features / target ─────────────────────────────────────────────────
    drop = [
        "Publish_Timeframe", "Is_Published", "Publish_Date",
        "Days_to_Publish", "Create_Date", "Upload_Date",
    ]
    X = df.drop(columns=[c for c in drop if c in df.columns])

    # fill NaN in numeric cols
    X["Uploaded_Duration"] = X["Uploaded_Duration"].fillna(0)
    X["Created_Duration"] = X["Created_Duration"].fillna(0)
    X["Upload_to_Create_Days"] = X["Upload_to_Create_Days"].fillna(0)

    # fill NaN in string cols before one-hot encoding
    for col in X.select_dtypes(include="object").columns:
        X[col] = X[col].fillna("Unknown")

    X = pd.get_dummies(X, drop_first=True)
    y = df["Publish_Timeframe"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    base_rf = RandomForestClassifier(
        n_estimators=100,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )
    # Wrap with isotonic calibration → continuous probabilities (not 1/100 steps)
    model = CalibratedClassifierCV(base_rf, method="isotonic", cv=3)
    model.fit(X_train, y_train)
    accuracy = float(model.score(X_test, y_test))
    logger.info("publish_predictor: accuracy=%.4f  classes=%s", accuracy, model.classes_)

    sample_counts = df["Publish_Timeframe"].value_counts().to_dict()

    meta = {
        "training_columns": list(X_train.columns),
        "options": options,
        "accuracy": round(accuracy, 4),
        "classes": list(model.classes_),
        "sample_counts": sample_counts,
        "total_samples": len(df),
    }

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    joblib.dump(meta, META_PATH)
    _model, _meta = model, meta


def _ensure_model(auth: AuthContext | None = None) -> str | None:
    """Load or train the model. Returns an error string if unavailable."""
    global _model, _meta
    if _model is not None:
        return None
    if MODEL_PATH.exists() and META_PATH.exists():
        logger.info("publish_predictor: loading cached model from disk")
        _model = joblib.load(MODEL_PATH)
        _meta = joblib.load(META_PATH)
        return None
    # Model not on disk — only website_admin may trigger first-time training
    if auth is None or auth.role != "website_admin":
        return "Model not trained yet. Please ask a Frammer admin to log in first to initialize the model."
    _train_and_save()
    return None


# ── request schema ────────────────────────────────────────────────────────────

class PredictRequest(BaseModel):
    client_name: str
    assigned_channel: str
    input_type: str
    language: str
    output_type: str
    uploaded_duration: float
    created_duration: float
    upload_to_create_days: float


# ── auth helpers ──────────────────────────────────────────────────────────────

def _allowed_clients(auth: AuthContext) -> list[str] | None:
    """Return the list of clients the user may access, or None for admins."""
    if auth.role == "website_admin":
        return None  # no restriction
    # client_admin and user are scoped to their own client
    return [auth.client_name] if auth.client_name else []


def _scope_options(opts: dict, auth: AuthContext) -> dict:
    """Filter dropdown options to only what the user is allowed to see."""
    allowed = _allowed_clients(auth)
    if allowed is None:
        return opts  # admin sees everything

    scoped = {**opts}
    scoped["clients"] = [c for c in opts.get("clients", []) if c in allowed]
    # Only keep channels belonging to allowed clients
    cbc = opts.get("channel_by_client", {})
    scoped["channel_by_client"] = {c: cbc[c] for c in allowed if c in cbc}
    scoped["channels"] = sorted(
        ch for c in allowed for ch in cbc.get(c, [])
    )
    return scoped


def _validate_client(auth: AuthContext, requested_client: str) -> str | None:
    """Return an error message if the user is not allowed to use this client."""
    allowed = _allowed_clients(auth)
    if allowed is None:
        return None
    if requested_client not in allowed:
        return f"Access denied: you may only use client(s) {', '.join(allowed)}"
    return None


# ── endpoints ─────────────────────────────────────────────────────────────────

@router.get("/options")
def predictor_options(auth: AuthContext = Depends(require_auth)):
    try:
        model_err = _ensure_model(auth)
        if model_err:
            return JSONResponse({"error": model_err}, status_code=503)
        scoped = _scope_options(_meta["options"], auth)
        return {
            **scoped,
            "accuracy": _meta["accuracy"],
            "classes": _meta["classes"],
            "total_samples": _meta.get("total_samples", 0),
        }
    except Exception as exc:
        logger.exception("predictor options failed")
        return JSONResponse({"error": str(exc)}, status_code=500)


@router.post("/predict")
def predictor_predict(req: PredictRequest, auth: AuthContext = Depends(require_auth)):
    try:
        # Enforce client scope
        err = _validate_client(auth, req.client_name)
        if err:
            return JSONResponse({"error": err}, status_code=403)

        model_err = _ensure_model(auth)
        if model_err:
            return JSONResponse({"error": model_err}, status_code=503)

        sample = pd.DataFrame([{
            "Client_Name":           req.client_name,
            "Assigned_Channel":      req.assigned_channel,
            "Input_Type":            req.input_type,
            "Language":              req.language,
            "Output_Type":           req.output_type,
            "Uploaded_Duration":     req.uploaded_duration,
            "Created_Duration":      req.created_duration,
            "Upload_to_Create_Days": req.upload_to_create_days,
        }])

        sample_enc = pd.get_dummies(sample)
        sample_final = sample_enc.reindex(
            columns=_meta["training_columns"], fill_value=0
        )

        probs = _model.predict_proba(sample_final)[0]
        classes = _model.classes_
        prob_map = {str(c): round(float(p) * 100, 2) for c, p in zip(classes, probs)}

        never = prob_map.get("0_Never", 0)
        p1 = prob_map.get("1_Within_1_Day", 0)
        p2 = prob_map.get("2_Within_2_Days", 0)
        p3 = prob_map.get("3_Within_3_Days", 0)
        p4 = prob_map.get("4_More_than_3_Days", 0)

        return {
            "publish_probability": round(100 - never, 2),
            "class_probabilities": prob_map,
            "cumulative": {
                "within_1_day":  round(p1, 2),
                "within_2_days": round(p1 + p2, 2),
                "within_3_days": round(p1 + p2 + p3, 2),
                "eventually":    round(p1 + p2 + p3 + p4, 2),
            },
            "never": round(never, 2),
            "predicted_class": str(_model.predict(sample_final)[0]),
        }
    except Exception as exc:
        logger.exception("prediction failed")
        return JSONResponse({"error": str(exc)}, status_code=500)


@router.post("/retrain")
def predictor_retrain(auth: AuthContext = Depends(require_auth)):
    """Force retrain from current DB data. Admin only."""
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

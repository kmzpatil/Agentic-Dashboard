from __future__ import annotations

import importlib
import os
from typing import List, Optional

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query

from backend.middleware.auth import require_auth


router = APIRouter(
    prefix="/v1/filters",
    dependencies=[Depends(require_auth)],
    tags=["Filters"],
)


DATABASE_URL: str = (
    os.getenv("DATABASE_URL")
    or os.getenv("POSTGRES_URL")
    or (
        f"postgresql://{os.getenv('POSTGRES_USER', 'postgres')}:"
        f"{os.getenv('POSTGRES_PASSWORD', '')}@"
        f"{os.getenv('POSTGRES_HOST', 'localhost')}:"
        f"{os.getenv('POSTGRES_PORT', '5432')}/"
        f"{os.getenv('POSTGRES_DB', 'frammer_database')}"
    )
)

_ENGINE = None


def _get_engine():
    global _ENGINE
    if _ENGINE is None:
        try:
            sqlalchemy = importlib.import_module("sqlalchemy")
        except ImportError as exc:
            raise RuntimeError(
                "sqlalchemy is required - install from backend/requirements.txt"
            ) from exc
        _ENGINE = sqlalchemy.create_engine(DATABASE_URL)
    return _ENGINE


# -- Small helpers -----------------------------------------------------------------

def _sorted_unique(series: pd.Series) -> List[str]:
    """Return sorted unique non-null string values, prefixed with 'All'."""
    values = sorted(series.dropna().astype(str).unique().tolist())
    return ["All"] + values


def _read(query: str) -> pd.DataFrame:
    return pd.read_sql(query, _get_engine())


def _read_optional(query: str, columns: List[str]) -> pd.DataFrame:
    try:
        return pd.read_sql(query, _get_engine())
    except Exception:
        return pd.DataFrame(columns=columns)


def _is_all(value: Optional[str]) -> bool:
    if value is None:
        return True
    return value.strip().lower() in {"all", ""}


def _filter_videos_by_channel(videos: pd.DataFrame, channel: Optional[str]) -> pd.DataFrame:
    if _is_all(channel):
        return videos
    rvc = _read_optional(
        "SELECT \"Video_ID\", \"Channel_Name\" FROM \"raw_video_channel\"",
        ["Video_ID", "Channel_Name"],
    )
    if rvc.empty:
        return videos
    channel_video_ids = rvc.loc[rvc["Channel_Name"] == channel, "Video_ID"]
    return videos[videos["Video_ID"].isin(channel_video_ids)]


# -- /v1/filters/date-range ---------------------------------------------------------

@router.get("/date-range")
def get_date_range():
    """
    Returns the earliest and latest upload dates available in the dataset.
    The frontend uses this to initialize and constrain the date-range picker.
    """
    try:
        df = _read(
            "SELECT MIN(\"Upload_Date\") AS min_date, MAX(\"Upload_Date\") AS max_date FROM \"raw_videos\""
        )
        row = df.iloc[0]
        min_date = pd.Timestamp(row["min_date"])
        max_date = pd.Timestamp(row["max_date"])
        return {
            "status": "success",
            "min_date": min_date.strftime("%Y-%m-%d"),
            "max_date": max_date.strftime("%Y-%m-%d"),
            "label": f"{min_date.strftime('%b %Y')} - {max_date.strftime('%b %Y')}",
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# -- /v1/filters/options/company ----------------------------------------------------

@router.get("/options/company")
def get_company_options(auth: AuthContext = Depends(require_auth)):
    """All unique company (Client_Name) values."""
    try:
        if auth.role == "client_admin":
            return {
                "status": "success",
                "filter": "company",
                "options": ["All", auth.client_name] if auth.client_name else ["All"],
            }
        df = _read("SELECT DISTINCT \"Client_Name\" FROM \"users\" WHERE \"Client_Name\" IS NOT NULL")
        return {
            "status": "success",
            "filter": "company",
            "options": _sorted_unique(df["Client_Name"]),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# -- /v1/filters/options/channel ----------------------------------------------------

@router.get("/options/channel")
def get_channel_options(
    company: Optional[str] = Query(None, description="Scope to a specific company"),
    auth: AuthContext = Depends(require_auth),
):
    """
    All unique channel names.
    Pass ?company=Acme Corp to restrict to that company's posts.
    """
    try:
        if auth.role == "client_admin":
            company = auth.client_name

        rvc = _read_optional(
            "SELECT \"Video_ID\", \"Channel_Name\" FROM \"raw_video_channel\" WHERE \"Channel_Name\" IS NOT NULL",
            ["Video_ID", "Channel_Name"],
        )

        if company and not _is_all(company):
            videos = _read("SELECT \"Video_ID\", \"User_ID\" FROM \"raw_videos\"")
            users = _read("SELECT \"User_ID\", \"Client_Name\" FROM \"users\"")

            company_user_ids = users.loc[users["Client_Name"] == company, "User_ID"]
            videos = videos[videos["User_ID"].isin(company_user_ids)]

            if not rvc.empty:
                rvc = rvc[rvc["Video_ID"].isin(videos["Video_ID"])]

        return {
            "status": "success",
            "filter": "channel",
            "options": _sorted_unique(rvc["Channel_Name"]),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# -- /v1/filters/options/user -------------------------------------------------------

@router.get("/options/user")
def get_user_options(
    company: Optional[str] = Query(None, description="Scope to a specific company"),
    channel: Optional[str] = Query(None, description="Scope to a specific channel"),
    auth: AuthContext = Depends(require_auth),
):
    """
    All unique usernames / user identifiers.
    Pass ?company=Acme Corp to restrict to that company's users.
    """
    try:
        if auth.role == "client_admin":
            company = auth.client_name

        users = _read("SELECT \"User_ID\", \"User_Name\", \"Client_Name\" FROM \"users\"")
        videos = _read("SELECT \"Video_ID\", \"User_ID\" FROM \"raw_videos\"")

        if company and not _is_all(company):
            users = users[users["Client_Name"] == company]
            videos = videos[videos["User_ID"].isin(users["User_ID"])]

        if channel and not _is_all(channel):
            videos = _filter_videos_by_channel(videos, channel)

        scoped_users = users[users["User_ID"].isin(videos["User_ID"])]

        name_col = "User_Name" if "User_Name" in scoped_users.columns else "User_ID"
        return {
            "status": "success",
            "filter": "user",
            "options": _sorted_unique(scoped_users[name_col]),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# -- /v1/filters/options/language ---------------------------------------------------

@router.get("/options/language")
def get_language_options(
    company: Optional[str] = Query(None, description="Scope to a specific company"),
    auth: AuthContext = Depends(require_auth),
):
    """
    All unique languages present in raw_videos.
    Pass ?company=Acme Corp to restrict to that company's uploads.
    """
    try:
        if auth.role == "client_admin":
            company = auth.client_name

        videos = _read(
            "SELECT \"Video_ID\", \"User_ID\", \"Language\" FROM \"raw_videos\" WHERE \"Language\" IS NOT NULL"
        )

        if company and not _is_all(company):
            users = _read("SELECT \"User_ID\", \"Client_Name\" FROM \"users\"")
            company_user_ids = users.loc[users["Client_Name"] == company, "User_ID"]
            videos = videos[videos["User_ID"].isin(company_user_ids)]

        return {
            "status": "success",
            "filter": "language",
            "options": _sorted_unique(videos["Language"]),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# -- /v1/filters/options/input-type -------------------------------------------------

@router.get("/options/input-type")
def get_input_type_options(
    company: Optional[str] = Query(None, description="Scope to a specific company"),
    auth: AuthContext = Depends(require_auth),
):
    """
    All unique input types from raw_videos.
    Pass ?company=Acme Corp to restrict results.
    """
    try:
        if auth.role == "client_admin":
            company = auth.client_name

        videos = _read(
            "SELECT \"Video_ID\", \"User_ID\", \"Input_Type\" FROM \"raw_videos\" WHERE \"Input_Type\" IS NOT NULL"
        )

        if company and not _is_all(company):
            users = _read("SELECT \"User_ID\", \"Client_Name\" FROM \"users\"")
            company_user_ids = users.loc[users["Client_Name"] == company, "User_ID"]
            videos = videos[videos["User_ID"].isin(company_user_ids)]

        return {
            "status": "success",
            "filter": "input_type",
            "options": _sorted_unique(videos["Input_Type"]),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# -- /v1/filters/options/output-type ------------------------------------------------

@router.get("/options/output-type")
def get_output_type_options(
    company: Optional[str] = Query(None, description="Scope to a specific company"),
    auth: AuthContext = Depends(require_auth),
):
    """
    All unique output types from created_assets.
    Pass ?company=Acme Corp to restrict results.
    """
    try:
        if auth.role == "client_admin":
            company = auth.client_name

        assets = _read(
            "SELECT \"Asset_ID\", \"Video_ID\", \"Output_Type\" FROM \"created_assets\" WHERE \"Output_Type\" IS NOT NULL"
        )
        videos = _read("SELECT \"Video_ID\", \"User_ID\" FROM \"raw_videos\"")
        merged = assets.merge(videos, on="Video_ID", how="inner")

        if company and not _is_all(company):
            users = _read("SELECT \"User_ID\", \"Client_Name\" FROM \"users\"")
            company_user_ids = users.loc[users["Client_Name"] == company, "User_ID"]
            merged = merged[merged["User_ID"].isin(company_user_ids)]

        return {
            "status": "success",
            "filter": "output_type",
            "options": _sorted_unique(merged["Output_Type"]),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# -- /v1/filters/options (all-in-one) ----------------------------------------------

@router.get("/options")
def get_all_filter_options(
    company: Optional[str] = Query(None, description="Scope all dimension filters to this company"),
    channel: Optional[str] = Query(None, description="Scope all dimension filters to this channel"),
    auth: AuthContext = Depends(require_auth),
):
    """
    Fetches every filter dimension in a single round-trip.
    Equivalent to calling all individual /options/* endpoints at once.
    """
    try:
        if auth.role == "client_admin":
            company = auth.client_name

        engine = _get_engine()

        videos = pd.read_sql(
            "SELECT \"Video_ID\", \"User_ID\", \"Input_Type\", \"Language\", \"Upload_Date\" FROM \"raw_videos\"",
            engine,
        )
        assets = pd.read_sql("SELECT \"Asset_ID\", \"Video_ID\", \"Output_Type\" FROM \"created_assets\"", engine)
        posts = pd.read_sql("SELECT \"Post_ID\", \"Asset_ID\" FROM \"published_posts\"", engine)
        users = pd.read_sql("SELECT \"User_ID\", \"Client_Name\", \"User_Name\" FROM \"users\"", engine)

        rvc = _read_optional(
            "SELECT \"Video_ID\", \"Channel_Name\" FROM \"raw_video_channel\"",
            ["Video_ID", "Channel_Name"],
        )

        videos["Upload_Date"] = pd.to_datetime(videos["Upload_Date"])
        min_date = videos["Upload_Date"].min()
        max_date = videos["Upload_Date"].max()
        date_range = {
            "min_date": min_date.strftime("%Y-%m-%d"),
            "max_date": max_date.strftime("%Y-%m-%d"),
            "label": f"{min_date.strftime('%b %Y')} - {max_date.strftime('%b %Y')}",
        }

        scoped_videos = videos.copy()
        scoped_users = users.copy()

        if company and not _is_all(company):
            company_user_ids = users.loc[users["Client_Name"] == company, "User_ID"]
            scoped_videos = videos[videos["User_ID"].isin(company_user_ids)]
            scoped_users = users[users["Client_Name"] == company]

        if channel and not _is_all(channel):
            scoped_videos = _filter_videos_by_channel(scoped_videos, channel)
            scoped_users = scoped_users[scoped_users["User_ID"].isin(scoped_videos["User_ID"])]

        scoped_assets = assets[assets["Video_ID"].isin(scoped_videos["Video_ID"])]
        scoped_posts = posts[posts["Asset_ID"].isin(scoped_assets["Asset_ID"])]
        scoped_rvc = (
            rvc[rvc["Video_ID"].isin(scoped_videos["Video_ID"])] if not rvc.empty else rvc
        )

        name_col = "User_Name" if "User_Name" in scoped_users.columns else "User_ID"

        company_options = _sorted_unique(users["Client_Name"])
        if auth.role == "client_admin":
            company_options = ["All", auth.client_name] if auth.client_name else ["All"]

        return {
            "status": "success",
            "date_range": date_range,
            "filters": {
                "company": company_options,
                "channel": _sorted_unique(scoped_rvc["Channel_Name"]),
                "user": _sorted_unique(scoped_users[name_col]),
                "language": _sorted_unique(scoped_videos["Language"].dropna()),
                "input_type": _sorted_unique(scoped_videos["Input_Type"].dropna()),
                "output_type": _sorted_unique(scoped_assets["Output_Type"].dropna()),
            },
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# -- /v1/filters/validate -----------------------------------------------------------

@router.get("/validate")
def validate_filter_combination(
    company: Optional[List[str]] = Query(None),
    channel: Optional[List[str]] = Query(None),
    user: Optional[List[str]] = Query(None),
    language: Optional[List[str]] = Query(None),
    input_type: Optional[List[str]] = Query(None),
    output_type: Optional[List[str]] = Query(None),
    date_from: Optional[str] = Query(None, description="YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="YYYY-MM-DD"),
    auth: AuthContext = Depends(require_auth),
):
    """
    Validates that the given filter combination returns at least one row.
    Useful for the frontend to warn users about empty result sets before
    triggering expensive downstream queries.
    """
    def _is_all(value: Optional[str | List[str]]) -> bool:
        if value is None:
            return True
        if isinstance(value, list):
            return not value or any(v.strip().lower() in {"all", ""} for v in value)
        return value.strip().lower() in {"all", ""}

    def _to_list(value: str | List[str]) -> List[str]:
        if isinstance(value, list):
            return value
        return [value]

    try:
        if auth.role == "client_admin":
            company = [auth.client_name]

        engine = _get_engine()
        videos = pd.read_sql(
            "SELECT \"Video_ID\", \"User_ID\", \"Input_Type\", \"Language\", \"Upload_Date\" FROM \"raw_videos\"",
            engine,
        )
        assets = pd.read_sql("SELECT \"Asset_ID\", \"Video_ID\", \"Output_Type\" FROM \"created_assets\"", engine)
        posts = pd.read_sql("SELECT \"Post_ID\", \"Asset_ID\" FROM \"published_posts\"", engine)
        users = pd.read_sql("SELECT \"User_ID\", \"Client_Name\", \"User_Name\" FROM \"users\"", engine)
        rvc = _read_optional(
            "SELECT \"Video_ID\", \"Channel_Name\" FROM \"raw_video_channel\"",
            ["Video_ID", "Channel_Name"],
        )

        videos["Upload_Date"] = pd.to_datetime(videos["Upload_Date"])

        if company and not _is_all(company):
            company_list = _to_list(company)
            company_user_ids = users.loc[users["Client_Name"].isin(company_list), "User_ID"]
            videos = videos[videos["User_ID"].isin(company_user_ids)]

        if user and not _is_all(user):
            name_col = "User_Name" if "User_Name" in users.columns else "User_ID"
            user_list = _to_list(user)
            user_ids = users.loc[users[name_col].isin(user_list), "User_ID"]
            videos = videos[videos["User_ID"].isin(user_ids)]

        if language and not _is_all(language):
            videos = videos[videos["Language"].isin(_to_list(language))]

        if input_type and not _is_all(input_type):
            videos = videos[videos["Input_Type"].isin(_to_list(input_type))]

        if date_from:
            videos = videos[videos["Upload_Date"] >= pd.Timestamp(date_from)]
        if date_to:
            videos = videos[videos["Upload_Date"] <= pd.Timestamp(date_to)]

        if channel and not _is_all(channel):
            if not rvc.empty:
                channel_list = _to_list(channel)
                channel_video_ids = rvc.loc[rvc["Channel_Name"].isin(channel_list), "Video_ID"]
                videos = videos[videos["Video_ID"].isin(channel_video_ids)]

        scoped_assets = assets[assets["Video_ID"].isin(videos["Video_ID"])]

        if output_type and not _is_all(output_type):
            scoped_assets = scoped_assets[scoped_assets["Output_Type"].isin(_to_list(output_type))]

        scoped_posts = posts[posts["Asset_ID"].isin(scoped_assets["Asset_ID"])]

        row_count = len(videos)

        return {
            "status": "success",
            "has_data": row_count > 0,
            "row_count": row_count,
            "post_count": len(scoped_posts),
            "asset_count": len(scoped_assets),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

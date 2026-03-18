from fastapi import APIRouter, Depends, HTTPException, Query
import pandas as pd
import numpy as np
import importlib
from urllib.parse import quote_plus
from typing import Optional, List

from backend.analytics.trends_service import get_trends_snapshot
from backend.config.env import get_config
from backend.routes.filters import router as filters_router
from backend.middleware.auth import AuthContext, require_auth

router = APIRouter(dependencies=[Depends(require_auth)])
router.include_router(filters_router)

def _database_url_from_config() -> str:
    db = get_config().db
    user = quote_plus(db.user)
    password = quote_plus(db.password) if db.password else ""

    if db.host.startswith("/"):
        auth = f"{user}:{password}@" if password else f"{user}@"
        host = quote_plus(db.host)
        return f"postgresql://{auth}/{db.database}?host={host}&port={db.port}"

    auth = f"{user}:{password}@" if password else f"{user}@"
    return f"postgresql://{auth}{db.host}:{db.port}/{db.database}"


DATABASE_URL = _database_url_from_config()
_ENGINE = None


@router.get("")
def deprecated_trends_alias(
    metric: str = Query("uploaded_count"),
    granularity: str = Query("month"),
    auth: AuthContext = Depends(require_auth),
):
    snapshot = get_trends_snapshot(auth, metric=metric, granularity=granularity)
    return {"deprecated": True, "redirect": "/api/trends", **snapshot}


def _create_db_engine(db_url: str):
    try:
        sqlalchemy = importlib.import_module("sqlalchemy")
    except ImportError as exc:
        raise RuntimeError(
            "sqlalchemy is required. Install dependencies from backend/requirements.txt"
        ) from exc
    return sqlalchemy.create_engine(db_url)


def _get_engine():
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = _create_db_engine(DATABASE_URL)
    return _ENGINE


def _build_master_df() -> pd.DataFrame:
    """Builds the base daily master dataframe from the database."""
    engine = _get_engine()
    raw = pd.read_sql("SELECT * FROM \"raw_videos\"", engine)
    raw["Upload_Date"] = pd.to_datetime(raw["Upload_Date"])

    assets = pd.read_sql("SELECT * FROM \"created_assets\"", engine)
    assets["Create_Date"] = pd.to_datetime(assets["Create_Date"])

    posts = pd.read_sql("SELECT * FROM \"published_posts\"", engine)
    posts["Publish_Date"] = pd.to_datetime(posts["Publish_Date"])

    raw = raw.merge(
        pd.read_sql("SELECT * FROM \"users\"", engine)[["User_ID", "Team_Name", "Client_Name"]],
        on="User_ID",
        how="left",
    )

    daily_upload = (
        raw.groupby(['Upload_Date', 'Client_Name'])
        .agg(
            Upload_Count=('Video_ID', 'count'),
            Upload_Duration=('Uploaded_Duration', 'sum')
        )
        .reset_index()
        .rename(columns={'Upload_Date': 'Date'})
    )

    daily_assets = (
        assets.merge(raw[['Video_ID', 'Client_Name']], on='Video_ID', how='left')
        .groupby(['Create_Date', 'Client_Name'])
        .agg(
            Assets_Created=('Asset_ID', 'count'),
            Assets_Duration=('Created_Duration', 'sum')
        )
        .reset_index()
        .rename(columns={'Create_Date': 'Date'})
    )

    # Compute avg_days_to_publish per client per publish date
    post_full = (
        posts.merge(assets[['Asset_ID', 'Video_ID']], on='Asset_ID', how='left')
             .merge(raw[['Video_ID', 'Upload_Date', 'Client_Name']], on='Video_ID', how='left')
    )
    post_full['Days_to_Publish'] = (
        post_full['Publish_Date'] - post_full['Upload_Date']
    ).dt.days
    valid_posts = post_full[post_full['Days_to_Publish'] >= 0]

    daily_publish = (
        valid_posts.groupby(['Publish_Date', 'Client_Name'])
        .agg(
            Posts_Published=('Post_ID', 'count'),
            Published_Duration=('Published_Duration', 'sum'),
            Avg_Days_to_Publish=('Days_to_Publish', 'mean')
        )
        .reset_index()
        .rename(columns={'Publish_Date': 'Date'})
    )

    master_df = (
        daily_upload
        .merge(daily_assets, on=['Date', 'Client_Name'], how='outer')
        .merge(daily_publish, on=['Date', 'Client_Name'], how='outer')
    )
    master_df['Date'] = pd.to_datetime(master_df['Date'])
    master_df = master_df.sort_values(['Client_Name', 'Date'])
    master_df['Avg_Days_to_Publish'] = master_df['Avg_Days_to_Publish'].fillna(0)
    master_df.fillna(0, inplace=True)

    return master_df


def _build_master_df_from_frames(
    raw: pd.DataFrame,
    assets: pd.DataFrame,
    posts: pd.DataFrame,
    users: pd.DataFrame,
) -> pd.DataFrame:
    """Builds the base daily master dataframe from filtered dataframes."""
    raw = raw.copy()
    assets = assets.copy()
    posts = posts.copy()

    raw["Upload_Date"] = pd.to_datetime(raw["Upload_Date"])
    assets["Create_Date"] = pd.to_datetime(assets["Create_Date"])
    posts["Publish_Date"] = pd.to_datetime(posts["Publish_Date"])

    raw = raw.merge(
        users[["User_ID", "Team_Name", "Client_Name"]],
        on="User_ID",
        how="left",
    )

    daily_upload = (
        raw.groupby(["Upload_Date", "Client_Name"])
        .agg(
            Upload_Count=("Video_ID", "count"),
            Upload_Duration=("Uploaded_Duration", "sum"),
        )
        .reset_index()
        .rename(columns={"Upload_Date": "Date"})
    )

    daily_assets = (
        assets.merge(raw[["Video_ID", "Client_Name"]], on="Video_ID", how="left")
        .groupby(["Create_Date", "Client_Name"])
        .agg(
            Assets_Created=("Asset_ID", "count"),
            Assets_Duration=("Created_Duration", "sum"),
        )
        .reset_index()
        .rename(columns={"Create_Date": "Date"})
    )

    post_full = (
        posts.merge(assets[["Asset_ID", "Video_ID"]], on="Asset_ID", how="left")
        .merge(raw[["Video_ID", "Upload_Date", "Client_Name"]], on="Video_ID", how="left")
    )
    post_full["Days_to_Publish"] = (
        post_full["Publish_Date"] - post_full["Upload_Date"]
    ).dt.days
    valid_posts = post_full[post_full["Days_to_Publish"] >= 0]

    daily_publish = (
        valid_posts.groupby(["Publish_Date", "Client_Name"])
        .agg(
            Posts_Published=("Post_ID", "count"),
            Published_Duration=("Published_Duration", "sum"),
            Avg_Days_to_Publish=("Days_to_Publish", "mean"),
        )
        .reset_index()
        .rename(columns={"Publish_Date": "Date"})
    )

    master_df = (
        daily_upload
        .merge(daily_assets, on=["Date", "Client_Name"], how="outer")
        .merge(daily_publish, on=["Date", "Client_Name"], how="outer")
    )
    master_df["Date"] = pd.to_datetime(master_df["Date"])
    master_df = master_df.sort_values(["Client_Name", "Date"])
    master_df["Avg_Days_to_Publish"] = master_df["Avg_Days_to_Publish"].fillna(0)
    master_df.fillna(0, inplace=True)

    return master_df


def _resample_dataframe(df: pd.DataFrame, granularity: str) -> pd.DataFrame:
    """Resamples the daily dataframe based on requested granularity and calculates all metrics."""
    # Map API granularity to Pandas offset strings
    freq_map = {'day': 'D', 'week': 'W-MON', 'month': 'MS', 'quarter': 'QS'}
    freq = freq_map.get(granularity, 'MS')

    # Aggregate base metrics
    agg_funcs = {
        'Upload_Count': 'sum',
        'Upload_Duration': 'sum',
        'Assets_Created': 'sum',
        'Assets_Duration': 'sum',
        'Posts_Published': 'sum',
        'Published_Duration': 'sum'
    }

    resampled = df.groupby(['Client_Name', pd.Grouper(key='Date', freq=freq)]).agg(agg_funcs).reset_index()

    # Map to expected metric names
    resampled['uploaded_count'] = resampled['Upload_Count']
    resampled['created_count'] = resampled['Assets_Created']
    resampled['published_count'] = resampled['Posts_Published']
    resampled['uploaded_duration'] = resampled['Upload_Duration']
    resampled['created_duration'] = resampled['Assets_Duration']
    resampled['published_duration'] = resampled['Published_Duration']

    # Calculate derived rates (matching the JS logic exactly)
    resampled['publish_conversion_rate'] = np.where(
        resampled['created_count'] == 0, 0,
        (resampled['published_count'] / resampled['created_count']) * 100
    )
    resampled['creation_rate'] = np.where(
        resampled['uploaded_count'] == 0, 0,
        (resampled['created_count'] / resampled['uploaded_count']) * 100
    )
    resampled['processing_efficiency'] = np.where(
        resampled['created_duration'] == 0, 0,
        (resampled['published_duration'] / resampled['created_duration']) * 100
    )

    # Waste Index: Avg Created Duration - Avg Published Duration
    avg_created = np.where(resampled['created_count'] == 0, 0, resampled['created_duration'] / resampled['created_count'])
    avg_published = np.where(resampled['published_count'] == 0, 0, resampled['published_duration'] / resampled['published_count'])
    resampled['waste_index'] = avg_created - avg_published

    # Turnaround time (weighted mean of avg_days_to_publish)
    if 'Avg_Days_to_Publish' in df.columns:
        resampled2 = df.groupby(['Client_Name', pd.Grouper(key='Date', freq=freq)]).agg(
            Avg_Days_to_Publish=('Avg_Days_to_Publish', 'mean')
        ).reset_index()
        resampled = resampled.merge(resampled2, on=['Client_Name', 'Date'], how='left')
        resampled['turnaround_time'] = resampled['Avg_Days_to_Publish'].fillna(0)
    else:
        resampled['turnaround_time'] = 0

    # Rolling backlog and yield (cumulative per client)
    result_parts = []
    for _, cdf in resampled.groupby('Client_Name', sort=False):
        cdf = cdf.sort_values('Date').copy()
        cdf['running_publish_backlog'] = (
            cdf['created_count'].cumsum() - cdf['published_count'].cumsum()
        ).clip(lower=0)
        cdf['rolling_7d_yield'] = (
            cdf['created_count'].rolling(7, min_periods=1).sum() /
            cdf['uploaded_count'].rolling(7, min_periods=1).sum().replace(0, np.nan)
        ).fillna(0)
        result_parts.append(cdf)

    resampled = pd.concat(result_parts).sort_values(['Client_Name', 'Date']).reset_index(drop=True)
    resampled.fillna(0, inplace=True)
    return resampled


def _apply_usage_filters(
    videos: pd.DataFrame,
    assets: pd.DataFrame,
    posts: pd.DataFrame,
    users: pd.DataFrame,
    dist: Optional[pd.DataFrame],
    rvc: Optional[pd.DataFrame],
    *,
    company: Optional[str] = None,
    channel: Optional[str] = None,
    user: Optional[str] = None,
    language: Optional[str] = None,
    input_type: Optional[str] = None,
    output_type: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    force_user_id: Optional[int] = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, Optional[pd.DataFrame]]:
    """Apply filter parameters consistently across usage-trends datasets."""
    if force_user_id is not None:
        videos = videos[videos["User_ID"] == force_user_id]
        users = users[users["User_ID"] == force_user_id]
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

    if company and not _is_all(company):
        company_list = _to_list(company)
        company_user_ids = users.loc[users["Client_Name"].isin(company_list), "User_ID"]
        videos = videos[videos["User_ID"].isin(company_user_ids)]
        users = users[users["Client_Name"].isin(company_list)]

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
        channel_list = _to_list(channel)
        if rvc is not None and not rvc.empty and "Channel_Name" in rvc.columns:
            channel_video_ids = rvc.loc[rvc["Channel_Name"].isin(channel_list), "Video_ID"]
            videos = videos[videos["Video_ID"].isin(channel_video_ids)]
        elif dist is not None and not dist.empty and "Channel_Name" in dist.columns:
            channel_post_ids = dist.loc[dist["Channel_Name"].isin(channel_list), "Post_ID"]
            posts = posts[posts["Post_ID"].isin(channel_post_ids)]

    assets = assets[assets["Video_ID"].isin(videos["Video_ID"])]

    if output_type and not _is_all(output_type):
        assets = assets[assets["Output_Type"].isin(_to_list(output_type))]

    posts = posts[posts["Asset_ID"].isin(assets["Asset_ID"])]

    if dist is not None and not dist.empty:
        dist = dist[dist["Post_ID"].isin(posts["Post_ID"])]

    return videos, assets, posts, users, dist


# ---------------------------------------------------------------------------
# Incomplete-tail removal
# ---------------------------------------------------------------------------

# Pandas period aliases differ from resample freq aliases
_FREQ_TO_PERIOD = {
    'D':     'D',
    'W-MON': 'W',
    'MS':    'M',
    'QS':    'Q',
}

_GRANULARITY_TO_FREQ = {
    'day':     'D',
    'week':    'W-MON',
    'month':   'MS',
    'quarter': 'QS',
}


def _drop_incomplete_tail(df: pd.DataFrame, granularity: str) -> pd.DataFrame:
    """
    Removes the last period bucket(s) that are still in-progress (i.e. the
    period that contains today has not yet closed).

    This eliminates the trailing-zero artefact visible on line charts when the
    current week / month / quarter is only partially complete.

    Turnaround-time / avg_days_to_publish are *not* volume metrics and are
    excluded from the "zero" check — they can legitimately be 0.

    The filter is applied per-Client_Name so every client's tail is handled
    independently.
    """
    if df.empty:
        return df

    today = pd.Timestamp.now().normalize()
    freq = _GRANULARITY_TO_FREQ.get(granularity, 'MS')
    period_alias = _FREQ_TO_PERIOD.get(freq, 'M')

    # Start-of-the-period that contains today
    current_period_start = today.to_period(period_alias).to_timestamp()

    has_client = 'Client_Name' in df.columns

    def _trim(cdf: pd.DataFrame) -> pd.DataFrame:
        cdf = cdf.sort_values('Date').copy()
        # Keep only rows whose period-start is strictly before today's period
        mask = pd.to_datetime(cdf['Date']) < current_period_start
        return cdf[mask] if mask.any() else cdf

    if has_client:
        parts = [_trim(cdf) for _, cdf in df.groupby('Client_Name', sort=False)]
        return (
            pd.concat(parts)
            .sort_values(['Client_Name', 'Date'])
            .reset_index(drop=True)
        )

    return _trim(df).reset_index(drop=True)


def _drop_trailing_zeros(df: pd.DataFrame, metric: str) -> pd.DataFrame:
    """
    Removes trailing rows from a dataframe where the specified metric is zero or null.
    This ensures that forecasts start immediately after the last "real" data point,
    aligning with the visual "Auto cutoff" on the frontend.
    """
    if df.empty or metric not in df.columns:
        return df

    # Find the index of the last non-zero/non-null value
    non_zero_indices = df.index[df[metric] > 0]
    if non_zero_indices.empty:
        return df.iloc[:0]  # Or return empty if everything is zero

    last_idx = non_zero_indices[-1]
    return df.loc[:last_idx].copy()


# ── Chronos singleton ─────────────────────────────────────────────────────
import threading

_CHRONOS_PIPELINE = None
_CHRONOS_LOCK = threading.Lock()


def _get_chronos_pipeline():
    """Lazy-load the Chronos T5-small model once and cache it in a thread-safe way."""
    global _CHRONOS_PIPELINE
    if _CHRONOS_PIPELINE is None:
        with _CHRONOS_LOCK:
            if _CHRONOS_PIPELINE is None:
                import torch
                from chronos import ChronosPipeline
                _CHRONOS_PIPELINE = ChronosPipeline.from_pretrained(
                    "amazon/chronos-t5-small",
                    device_map="cpu",
                    torch_dtype=torch.float32,
                )
    return _CHRONOS_PIPELINE


def _chronos_predict_uploads(target_series: np.ndarray, prediction_length: int) -> np.ndarray:
    import torch
    pipeline = _get_chronos_pipeline()

    context = torch.tensor(target_series, dtype=torch.float32)
    forecast = pipeline.predict(context, prediction_length)
    forecast_array = np.asarray(forecast)

    if forecast_array.ndim == 3:
        return np.median(forecast_array[0], axis=0)
    if forecast_array.ndim == 2:
        return np.median(forecast_array, axis=0)
    return forecast_array.reshape(-1)


def _naive_forecast(target_series: np.ndarray, prediction_length: int, seed: int) -> np.ndarray:
    np.random.seed(seed)
    base_level = np.mean(target_series[-30:]) if len(target_series) >= 30 else np.mean(target_series)
    forecast_path = base_level + np.random.normal(0, 3, prediction_length)
    return np.maximum(forecast_path, 0)


def get_client_master_timeline(
    client_name: str,
    videos_df: pd.DataFrame,
    assets_df: pd.DataFrame,
    posts_df: pd.DataFrame,
    dist_df: Optional[pd.DataFrame],
    users_df: pd.DataFrame,
) -> pd.DataFrame:
    """Full client timeline with volume, duration, turnaround, proportions, backlog, and rolling yield."""
    client_users = users_df[users_df['Client_Name'] == client_name]['User_ID']
    client_vids = videos_df[videos_df['User_ID'].isin(client_users)].copy()

    client_assets = assets_df[assets_df['Video_ID'].isin(client_vids['Video_ID'])].copy()
    client_assets = client_assets.merge(
        client_vids[['Video_ID', 'Upload_Date', 'Input_Type']], on='Video_ID', how='left'
    )

    client_posts = posts_df[posts_df['Asset_ID'].isin(client_assets['Asset_ID'])].copy()
    client_posts = client_posts.merge(client_assets[['Asset_ID', 'Upload_Date']], on='Asset_ID', how='left')

    # A. Daily uploads
    daily_uploads = client_vids.groupby('Upload_Date').agg(
        uploads_count=('Video_ID', 'count'),
        uploads_duration_sec=('Uploaded_Duration', 'sum')
    ).reset_index().rename(columns={'Upload_Date': 'Date'})
    daily_uploads['Date'] = pd.to_datetime(daily_uploads['Date'])

    # B. Daily assets + turnaround to create
    client_assets['Create_Date'] = pd.to_datetime(client_assets['Create_Date'])
    client_assets['Upload_Date'] = pd.to_datetime(client_assets['Upload_Date'])
    client_assets['Days_to_Create'] = (client_assets['Create_Date'] - client_assets['Upload_Date']).dt.days

    daily_assets = client_assets[client_assets['Days_to_Create'] >= 0].groupby('Create_Date').agg(
        assets_created_count=('Asset_ID', 'count'),
        assets_duration_sec=('Created_Duration', 'sum'),
        avg_days_to_create=('Days_to_Create', 'mean')
    ).reset_index().rename(columns={'Create_Date': 'Date'})

    # B.2 Output type proportions
    if 'Output_Type' in client_assets.columns:
        daily_output_mix = pd.crosstab(
            client_assets['Create_Date'], client_assets['Output_Type']
        ).reset_index().rename(columns={'Create_Date': 'Date'})
        out_cols = [c for c in daily_output_mix.columns if c != 'Date']
        daily_output_mix.columns = ['Date'] + [f"count_out_{c.replace(' ', '_')}" for c in out_cols]
        clean_out_cols = [c for c in daily_output_mix.columns if c != 'Date']
    else:
        daily_output_mix = None
        clean_out_cols = []

    # B.3 Input type proportions
    input_col = 'Input_Type'
    if input_col in client_assets.columns:
        daily_input_mix = pd.crosstab(
            client_assets['Create_Date'], client_assets[input_col]
        ).reset_index().rename(columns={'Create_Date': 'Date'})
        in_cols = [c for c in daily_input_mix.columns if c != 'Date']
        daily_input_mix.columns = ['Date'] + [
            f"count_in_{c.replace(' ', '_').replace('-', '_')}" for c in in_cols
        ]
        clean_in_cols = [c for c in daily_input_mix.columns if c != 'Date']
    else:
        daily_input_mix = None
        clean_in_cols = []

    # C. Daily posts + turnaround to publish
    client_posts['Publish_Date'] = pd.to_datetime(client_posts['Publish_Date'])
    client_posts['Upload_Date'] = pd.to_datetime(client_posts['Upload_Date'])
    client_posts['Days_to_Publish'] = (client_posts['Publish_Date'] - client_posts['Upload_Date']).dt.days

    daily_posts = client_posts[client_posts['Days_to_Publish'] >= 0].groupby('Publish_Date').agg(
        posts_published_count=('Post_ID', 'count'),
        posts_duration_sec=('Published_Duration', 'sum'),
        avg_days_to_publish=('Days_to_Publish', 'mean')
    ).reset_index().rename(columns={'Publish_Date': 'Date'})

    # C.2 Platform mix from post_distribution
    if dist_df is not None and not dist_df.empty and 'Published_Platform' in dist_df.columns:
        client_dist = dist_df[dist_df['Post_ID'].isin(client_posts['Post_ID'])].copy()
        client_dist = client_dist.merge(client_posts[['Post_ID', 'Publish_Date']], on='Post_ID', how='inner')
        daily_plat_mix = pd.crosstab(
            client_dist['Publish_Date'], client_dist['Published_Platform']
        ).reset_index().rename(columns={'Publish_Date': 'Date'})
        plat_cols = [c for c in daily_plat_mix.columns if c != 'Date']
        daily_plat_mix.columns = ['Date'] + [f"count_plat_{c.replace(' ', '_')}" for c in plat_cols]
        clean_plat_cols = [c for c in daily_plat_mix.columns if c != 'Date']
    else:
        daily_plat_mix = None
        clean_plat_cols = []

    # Merge all
    date_series = [s for s in [
        daily_uploads['Date'] if not daily_uploads.empty else None,
        daily_assets['Date'] if not daily_assets.empty else None,
        daily_posts['Date'] if not daily_posts.empty else None,
    ] if s is not None]

    if not date_series:
        return pd.DataFrame(columns=['Date', 'uploads_count', 'assets_created_count', 'posts_published_count', 'client_name'])

    all_dates = pd.DataFrame({'Date': pd.concat(date_series).dropna().unique()})
    master_df = all_dates.merge(daily_uploads, on='Date', how='left')
    master_df = master_df.merge(daily_assets, on='Date', how='left')
    if daily_output_mix is not None:
        master_df = master_df.merge(daily_output_mix, on='Date', how='left')
    if daily_input_mix is not None:
        master_df = master_df.merge(daily_input_mix, on='Date', how='left')
    master_df = master_df.merge(daily_posts, on='Date', how='left')
    if daily_plat_mix is not None:
        master_df = master_df.merge(daily_plat_mix, on='Date', how='left')

    master_df = master_df.sort_values('Date').reset_index(drop=True)

    fill_0 = (['uploads_count', 'uploads_duration_sec', 'assets_created_count',
                'assets_duration_sec', 'posts_published_count', 'posts_duration_sec']
               + clean_out_cols + clean_in_cols + clean_plat_cols)
    master_df[fill_0] = master_df[fill_0].fillna(0)
    master_df['avg_days_to_create'] = master_df.get('avg_days_to_create', pd.Series(0, index=master_df.index)).fillna(0)
    master_df['avg_days_to_publish'] = master_df.get('avg_days_to_publish', pd.Series(0, index=master_df.index)).fillna(0)

    # Health metrics
    master_df['creation_rate'] = (
        master_df['assets_created_count'] / master_df['uploads_count'].replace(0, np.nan)
    ).fillna(0)
    master_df['publish_conversion_rate'] = (
        master_df['posts_published_count'] / master_df['assets_created_count'].replace(0, np.nan)
    ).fillna(0)
    master_df['processing_efficiency'] = (
        master_df['posts_duration_sec'] / master_df['uploads_duration_sec'].replace(0, np.nan)
    ).fillna(0)

    # Proportions
    for col in clean_out_cols:
        master_df[col.replace('count_out_', 'pct_out_')] = (
            master_df[col] / master_df['assets_created_count'].replace(0, np.nan)
        ).fillna(0)
    for col in clean_in_cols:
        master_df[col.replace('count_in_', 'pct_in_')] = (
            master_df[col] / master_df['assets_created_count'].replace(0, np.nan)
        ).fillna(0)
    for col in clean_plat_cols:
        master_df[col.replace('count_plat_', 'pct_plat_')] = (
            master_df[col] / master_df['posts_published_count'].replace(0, np.nan)
        ).fillna(0)

    # Backlog and rolling yield
    master_df['running_publish_backlog'] = (
        master_df['assets_created_count'].cumsum() - master_df['posts_published_count'].cumsum()
    ).clip(lower=0)
    master_df['rolling_7d_yield'] = (
        master_df['assets_created_count'].rolling(7, min_periods=1).sum() /
        master_df['uploads_count'].rolling(7, min_periods=1).sum().replace(0, np.nan)
    ).fillna(0)

    master_df['client_name'] = client_name
    return master_df


def _resample_client_timeline(df: pd.DataFrame, granularity: str) -> pd.DataFrame:
    freq_map = {'day': 'D', 'week': 'W-MON', 'month': 'MS', 'quarter': 'QS'}
    freq = freq_map.get(granularity, 'D')

    if granularity == 'day':
        return df.sort_values('Date').reset_index(drop=True)

    sum_cols = [c for c in df.columns if c.startswith(('uploads_', 'assets_', 'posts_', 'count_out_', 'count_in_', 'count_plat_'))]
    mean_cols = ['avg_days_to_create', 'avg_days_to_publish']
    mean_cols = [c for c in mean_cols if c in df.columns]

    agg_dict = {c: 'sum' for c in sum_cols if c in df.columns}
    agg_dict.update({c: 'mean' for c in mean_cols})
    if 'client_name' in df.columns:
        agg_dict['client_name'] = 'first'

    grouped = (
        df.groupby(pd.Grouper(key='Date', freq=freq))
        .agg(agg_dict)
        .reset_index()
    )

    # Recalculate derived metrics
    grouped['creation_rate'] = (
        grouped['assets_created_count'] / grouped['uploads_count'].replace(0, np.nan)
    ).fillna(0)
    grouped['publish_conversion_rate'] = (
        grouped['posts_published_count'] / grouped['assets_created_count'].replace(0, np.nan)
    ).fillna(0)
    grouped['processing_efficiency'] = (
        grouped['posts_duration_sec'] / grouped['uploads_duration_sec'].replace(0, np.nan)
    ).fillna(0)

    # Recalculate proportions from summed counts
    for col in [c for c in grouped.columns if c.startswith('count_out_')]:
        grouped[col.replace('count_out_', 'pct_out_')] = (
            grouped[col] / grouped['assets_created_count'].replace(0, np.nan)
        ).fillna(0)
    for col in [c for c in grouped.columns if c.startswith('count_in_')]:
        grouped[col.replace('count_in_', 'pct_in_')] = (
            grouped[col] / grouped['assets_created_count'].replace(0, np.nan)
        ).fillna(0)
    for col in [c for c in grouped.columns if c.startswith('count_plat_')]:
        grouped[col.replace('count_plat_', 'pct_plat_')] = (
            grouped[col] / grouped['posts_published_count'].replace(0, np.nan)
        ).fillna(0)

    grouped['running_publish_backlog'] = (
        grouped['assets_created_count'].cumsum() - grouped['posts_published_count'].cumsum()
    ).clip(lower=0)
    grouped['rolling_7d_yield'] = (
        grouped['assets_created_count'].rolling(7, min_periods=1).sum() /
        grouped['uploads_count'].rolling(7, min_periods=1).sum().replace(0, np.nan)
    ).fillna(0)

    grouped.fillna(0, inplace=True)
    return grouped.sort_values('Date').reset_index(drop=True)


# ---------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------

@router.get("/v1/pipeline-metrics")
def get_pipeline_metrics(
    granularity: str = Query("day", description="day, week, month, or quarter"),
    company: Optional[List[str]] = Query(None),
    channel: Optional[List[str]] = Query(None),
    user: Optional[List[str]] = Query(None),
    language: Optional[List[str]] = Query(None),
    input_type: Optional[List[str]] = Query(None),
    output_type: Optional[List[str]] = Query(None),
    date_from: Optional[str] = Query(None, description="YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="YYYY-MM-DD"),
    auth_context: AuthContext = Depends(require_auth),
):
    try:
        engine = _get_engine()
        videos_df = pd.read_sql("SELECT * FROM \"raw_videos\"", engine)
        assets_df = pd.read_sql("SELECT * FROM \"created_assets\"", engine)
        posts_df = pd.read_sql("SELECT * FROM \"published_posts\"", engine)
        users_df = pd.read_sql("SELECT * FROM \"users\"", engine)
        try:
            dist_df = pd.read_sql("SELECT * FROM \"post_distribution\"", engine)
        except Exception:
            dist_df = None
        try:
            rvc_df = pd.read_sql("SELECT * FROM \"raw_video_channel\"", engine)
        except Exception:
            rvc_df = None

        videos_df["Upload_Date"] = pd.to_datetime(videos_df["Upload_Date"])
        assets_df["Create_Date"] = pd.to_datetime(assets_df["Create_Date"])
        posts_df["Publish_Date"] = pd.to_datetime(posts_df["Publish_Date"])

        if auth_context.role == "client_admin":
            company = [auth_context.client_name]
        elif auth_context.role == "user":
            company = [auth_context.client_name]
            # user = [auth_context.username]  <-- [FIX] This login ID doesn't match display name

        videos_df, assets_df, posts_df, users_df, dist_df = _apply_usage_filters(
            videos_df,
            assets_df,
            posts_df,
            users_df,
            dist_df,
            rvc_df,
            company=company,
            channel=channel,
            user=user,
            language=language,
            input_type=input_type,
            output_type=output_type,
            date_from=date_from,
            date_to=date_to,
            force_user_id=auth_context.user_id if auth_context.role == "user" else None,
        )

        if videos_df.empty:
            return {"status": "success", "granularity": granularity, "row_count": 0, "data": []}

        master_df = _build_master_df_from_frames(videos_df, assets_df, posts_df, users_df)
        resampled_df = _resample_dataframe(master_df, granularity)

        # Remove the current incomplete period so charts don't drop to zero at the tail
        resampled_df = _drop_incomplete_tail(resampled_df, granularity)

        resampled_df['Date'] = resampled_df['Date'].astype(str)
        result_dict = resampled_df.to_dict(orient='records')

        return {"status": "success", "granularity": granularity, "row_count": len(resampled_df), "data": result_dict}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/v1/client-master-timeline")
def get_client_master_timeline_endpoint(
    client_name: str = Query(..., description="Exact client name"),
    granularity: str = Query("day", description="day, week, month, or quarter"),
    company: Optional[List[str]] = Query(None),
    channel: Optional[List[str]] = Query(None),
    user: Optional[List[str]] = Query(None),
    language: Optional[List[str]] = Query(None),
    input_type: Optional[List[str]] = Query(None),
    output_type: Optional[List[str]] = Query(None),
    date_from: Optional[str] = Query(None, description="YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="YYYY-MM-DD"),
    auth_context: AuthContext = Depends(require_auth),
):
    try:
        safe_granularity = granularity if granularity in {'day', 'week', 'month', 'quarter'} else 'day'

        engine = _get_engine()
        videos_df = pd.read_sql("SELECT * FROM \"raw_videos\"", engine)
        assets_df = pd.read_sql("SELECT * FROM \"created_assets\"", engine)
        posts_df = pd.read_sql("SELECT * FROM \"published_posts\"", engine)
        users_df = pd.read_sql("SELECT * FROM \"users\"", engine)
        try:
            dist_df = pd.read_sql("SELECT * FROM \"post_distribution\"", engine)
        except Exception:
            dist_df = None
        try:
            rvc_df = pd.read_sql("SELECT * FROM \"raw_video_channel\"", engine)
        except Exception:
            rvc_df = None

        videos_df["Upload_Date"] = pd.to_datetime(videos_df["Upload_Date"])
        assets_df["Create_Date"] = pd.to_datetime(assets_df["Create_Date"])
        posts_df["Publish_Date"] = pd.to_datetime(posts_df["Publish_Date"])

        if auth_context.role == "client_admin":
            client_name = auth_context.client_name
            company = [auth_context.client_name]
        elif auth_context.role == "user":
            client_name = auth_context.client_name
            company = [auth_context.client_name]
            # [FIX] Do not filter by auth_context.username here either.

        videos_df, assets_df, posts_df, users_df, dist_df = _apply_usage_filters(
            videos_df,
            assets_df,
            posts_df,
            users_df,
            dist_df,
            rvc_df,
            company=company,
            channel=channel,
            user=user,
            language=language,
            input_type=input_type,
            output_type=output_type,
            date_from=date_from,
            date_to=date_to,
            force_user_id=auth_context.user_id if auth_context.role == "user" else None,
        )

        timeline_df = get_client_master_timeline(
            client_name=client_name,
            videos_df=videos_df,
            assets_df=assets_df,
            posts_df=posts_df,
            dist_df=dist_df,
            users_df=users_df,
        )

        if timeline_df.empty:
            raise HTTPException(status_code=404, detail=f"No timeline data found for client '{client_name}'")

        timeline_df = _resample_client_timeline(timeline_df, safe_granularity)

        # Remove the current incomplete period so charts don't drop to zero at the tail
        timeline_df = _drop_incomplete_tail(timeline_df, safe_granularity)

        timeline_df['Date'] = timeline_df['Date'].astype(str)

        return {
            "status": "success",
            "client": client_name,
            "granularity": safe_granularity,
            "row_count": len(timeline_df),
            "data": timeline_df.to_dict(orient='records'),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/v1/clients")
def list_clients():
    """Return all unique client names from the pipeline data."""
    try:
        master_df = _build_master_df()
        clients = sorted(master_df["Client_Name"].dropna().unique().tolist())
        return {"status": "success", "clients": clients}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


_MULTIDIM_ANALYSIS_COLS = {
    "volume_dynamics": ["uploaded_count", "created_count", "published_count"],
    "duration_dynamics": ["uploaded_duration", "created_duration", "published_duration"],
    "success_scores": ["creation_rate", "publish_conversion_rate", "processing_efficiency", "waste_index"],
}


@router.get("/v1/multi-dim")
def get_multi_dim(
    analysis: str = Query(..., description="volume_dynamics | duration_dynamics | success_scores | output_type | input_type_proportion"),
    granularity: str = Query("month", description="day, week, month, or quarter"),
    company: Optional[List[str]] = Query(None),
    channel: Optional[List[str]] = Query(None),
    user: Optional[List[str]] = Query(None),
    language: Optional[List[str]] = Query(None),
    input_type: Optional[List[str]] = Query(None),
    output_type_filter: Optional[List[str]] = Query(None, alias="output_type"),
    date_from: Optional[str] = Query(None, description="YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="YYYY-MM-DD"),
    auth_context: AuthContext = Depends(require_auth),
):
    """Multi-dimensional analysis endpoint returning time series for multiple keys."""
    try:
        safe_granularity = granularity if granularity in {'day', 'week', 'month', 'quarter'} else 'month'

        if analysis in ('output_type', 'input_type_proportion'):
            engine = _get_engine()
            assets_df = pd.read_sql("SELECT * FROM \"created_assets\"", engine)
            videos_df = pd.read_sql("SELECT * FROM \"raw_videos\"", engine)
            users_df = pd.read_sql("SELECT * FROM \"users\"", engine)

            videos_df["Upload_Date"] = pd.to_datetime(videos_df["Upload_Date"])
            assets_df["Create_Date"] = pd.to_datetime(assets_df["Create_Date"])

            rvc_df = None
            try:
                rvc_df = pd.read_sql("SELECT * FROM \"raw_video_channel\"", engine)
            except Exception:
                rvc_df = None

            if auth_context.role == "client_admin":
                company = [auth_context.client_name]
            elif auth_context.role == "user":
                company = [auth_context.client_name]
                # [FIX] Do not filter by auth_context.username (the login ID).
                # The numeric user filtering happens via force_user_id below.

            videos_df, assets_df, _, users_df, _ = _apply_usage_filters(
                videos_df,
                assets_df,
                pd.DataFrame(columns=["Post_ID", "Asset_ID"]),
                users_df,
                None,
                rvc_df,
                company=company,
                channel=channel,
                user=user,
                language=language,
                input_type=input_type,
                output_type=output_type_filter,
                date_from=date_from,
                date_to=date_to,
                force_user_id=auth_context.user_id if auth_context.role == "user" else None,
            )

            # Attach client name via users
            vids = videos_df.merge(
                users_df[['User_ID', 'Client_Name']], on='User_ID', how='left'
            )
            merged = assets_df.merge(vids[['Video_ID', 'Client_Name', 'Input_Type']], on='Video_ID', how='left')


            if merged.empty:
                raise HTTPException(status_code=404, detail="No data found for the selected filters")

            type_col = 'Output_Type' if analysis == 'output_type' else 'Input_Type'
            if type_col not in merged.columns:
                raise HTTPException(status_code=404, detail=f"Column '{type_col}' not found in assets table")

            merged = merged.dropna(subset=[type_col])
            if merged.empty:
                raise HTTPException(status_code=404, detail=f"No '{type_col}' data available")

            # Build date-indexed crosstab
            # to_period() requires period-compatible aliases (Q not QS)
            period_freq_map = {'day': 'D', 'week': 'W', 'month': 'M', 'quarter': 'Q'}
            period_freq = period_freq_map.get(safe_granularity, 'M')
            merged['Period'] = merged['Create_Date'].dt.to_period(period_freq).dt.to_timestamp()

            # Drop the current incomplete period before building the crosstab
            today = pd.Timestamp.now().normalize()
            current_period_start = today.to_period(period_freq).to_timestamp()
            merged = merged[merged['Period'] < current_period_start]
            if merged.empty:
                raise HTTPException(status_code=404, detail="No complete period data available yet")

            crosstab = pd.crosstab(merged['Period'], merged[type_col]).reset_index()
            type_cols = [c for c in crosstab.columns if c != 'Period']

            totals = crosstab[type_cols].sum(axis=1).replace(0, np.nan)
            for col in type_cols:
                safe_key = f"pct_{col.replace(' ', '_').replace('-', '_')}"
                crosstab[safe_key] = (crosstab[col] / totals).fillna(0)

            prefix = 'pct_'
            series_keys = [c for c in crosstab.columns if c.startswith(prefix)]
            crosstab['Date'] = crosstab['Period'].astype(str)
            labels = {k: k[len(prefix):].replace('_', ' ').title() for k in series_keys}
            return {
                "status": "success",
                "analysis": analysis,
                "granularity": safe_granularity,
                "series_keys": series_keys,
                "labels": labels,
                "data": crosstab[['Date'] + series_keys].to_dict(orient='records'),
            }

        # volume_dynamics / duration_dynamics / success_scores
        if analysis not in _MULTIDIM_ANALYSIS_COLS:
            raise HTTPException(status_code=400, detail=f"Unknown analysis '{analysis}'")

        if auth_context.role == "client_admin":
            company = [auth_context.client_name]
        elif auth_context.role == "user":
            company = [auth_context.client_name]
            # user = [auth_context.username]

        if any([company, channel, user, language, input_type, output_type_filter, date_from, date_to]) or auth_context.role == "user":
            engine = _get_engine()
            videos_df = pd.read_sql("SELECT * FROM \"raw_videos\"", engine)
            assets_df = pd.read_sql("SELECT * FROM \"created_assets\"", engine)
            posts_df = pd.read_sql("SELECT * FROM \"published_posts\"", engine)
            users_df = pd.read_sql("SELECT * FROM \"users\"", engine)
            try:
                dist_df = pd.read_sql("SELECT * FROM \"post_distribution\"", engine)
            except Exception:
                dist_df = None
            try:
                rvc_df = pd.read_sql("SELECT * FROM \"raw_video_channel\"", engine)
            except Exception:
                rvc_df = None

            videos_df["Upload_Date"] = pd.to_datetime(videos_df["Upload_Date"])
            assets_df["Create_Date"] = pd.to_datetime(assets_df["Create_Date"])
            posts_df["Publish_Date"] = pd.to_datetime(posts_df["Publish_Date"])

            videos_df, assets_df, posts_df, users_df, dist_df = _apply_usage_filters(
                videos_df,
                assets_df,
                posts_df,
                users_df,
                dist_df,
                rvc_df,
                company=company,
                channel=channel,
                user=user,
                language=language,
                input_type=input_type,
                output_type=output_type_filter,
                date_from=date_from,
                date_to=date_to,
                force_user_id=auth_context.user_id if auth_context.role == "user" else None,
            )

            master_df = _build_master_df_from_frames(videos_df, assets_df, posts_df, users_df)
        else:
            master_df = _build_master_df()

        resampled = _resample_dataframe(master_df, safe_granularity)

        # Remove current incomplete period
        resampled = _drop_incomplete_tail(resampled, safe_granularity)

        series_keys = _MULTIDIM_ANALYSIS_COLS[analysis]
        agg = (
            resampled.groupby('Date')[series_keys]
            .sum()
            .reset_index()
        )
        agg['Date'] = agg['Date'].astype(str)
        labels = {k: k.replace('_', ' ').title() for k in series_keys}
        return {
            "status": "success",
            "analysis": analysis,
            "granularity": safe_granularity,
            "series_keys": series_keys,
            "labels": labels,
            "data": agg.to_dict(orient='records'),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/v1/forecast/client-chronos")
def forecast_client_chronos(
    client_name: str = "Client 1",
    prediction_length: int = 30,
    metric: str = Query("uploaded_count", description="Metric to forecast (e.g., uploaded_count, creation_rate)"),
    granularity: str = Query("day", description="day, week, month, or quarter"),
    cutoff_date: Optional[str] = Query(
        None,
        description=(
            "ISO date (YYYY-MM-DD) after which the forecast begins. "
            "History is trimmed to this date and prediction starts from the next period. "
            "Defaults to the last complete period in the data."
        ),
    ),
    company: Optional[List[str]] = Query(None),
    channel: Optional[List[str]] = Query(None),
    user: Optional[List[str]] = Query(None),
    language: Optional[List[str]] = Query(None),
    input_type: Optional[List[str]] = Query(None),
    output_type_filter: Optional[List[str]] = Query(None, alias="output_type"),
    date_from: Optional[str] = Query(None, description="YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="YYYY-MM-DD"),
    auth_context: AuthContext = Depends(require_auth),
):
    """
    Forecast a single client metric using Chronos.

    Pass `cutoff_date` to pin exactly where the forecast horizon starts —
    useful for back-testing or for starting predictions from a specific date
    instead of the latest available data point.
    """
    try:
        if auth_context.role == "client_admin":
            company = [auth_context.client_name]
            client_name = auth_context.client_name
        elif auth_context.role == "user":
            company = [auth_context.client_name]
            user = [auth_context.username]
            client_name = auth_context.client_name

        if any([company, channel, user, language, input_type, output_type_filter, date_from, date_to]) or auth_context.role == "user":
            engine = _get_engine()
            videos_df = pd.read_sql("SELECT * FROM \"raw_videos\"", engine)
            assets_df = pd.read_sql("SELECT * FROM \"created_assets\"", engine)
            posts_df = pd.read_sql("SELECT * FROM \"published_posts\"", engine)
            users_df = pd.read_sql("SELECT * FROM \"users\"", engine)
            try:
                dist_df = pd.read_sql("SELECT * FROM \"post_distribution\"", engine)
            except Exception:
                dist_df = None
            try:
                rvc_df = pd.read_sql("SELECT * FROM \"raw_video_channel\"", engine)
            except Exception:
                rvc_df = None

            videos_df["Upload_Date"] = pd.to_datetime(videos_df["Upload_Date"])
            assets_df["Create_Date"] = pd.to_datetime(assets_df["Create_Date"])
            posts_df["Publish_Date"] = pd.to_datetime(posts_df["Publish_Date"])

            videos_df, assets_df, posts_df, users_df, dist_df = _apply_usage_filters(
                videos_df,
                assets_df,
                posts_df,
                users_df,
                dist_df,
                rvc_df,
                company=company,
                channel=channel,
                user=user,
                language=language,
                input_type=input_type,
                output_type=output_type_filter,
                date_from=date_from,
                date_to=date_to,
            )

            master_df = _build_master_df_from_frames(videos_df, assets_df, posts_df, users_df)
        else:
            master_df = _build_master_df()

        resampled_df = _resample_dataframe(master_df, granularity)

        # Always strip the current incomplete period first
        resampled_df = _drop_incomplete_tail(resampled_df, granularity)

        client_df = resampled_df[resampled_df['Client_Name'] == client_name].copy()
        if client_df.empty:
            raise HTTPException(status_code=404, detail=f"Client '{client_name}' not found")
        if metric not in client_df.columns:
            raise HTTPException(status_code=400, detail=f"Invalid metric '{metric}'")

        client_df = client_df.sort_values('Date')

        # [FIX] Align Auto cutoff with the last data point showing in plot
        client_df = _drop_trailing_zeros(client_df, metric)

        # ── Apply cutoff_date filter ──────────────────────────────────────
        if cutoff_date is not None:
            try:
                cutoff_ts = pd.Timestamp(cutoff_date).normalize()
            except Exception:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid cutoff_date '{cutoff_date}'. Use ISO format YYYY-MM-DD."
                )
            client_df = client_df[pd.to_datetime(client_df['Date']) <= cutoff_ts]
            if client_df.empty:
                raise HTTPException(
                    status_code=400,
                    detail=f"No data available on or before cutoff_date '{cutoff_date}' for client '{client_name}'."
                )

        target_series = client_df[metric].astype(float).values

        prediction = _chronos_predict_uploads(target_series, prediction_length)

        # Generate future dates starting from the day after the last history point
        freq_map = {'day': 'D', 'week': 'W-MON', 'month': 'MS', 'quarter': 'QS'}
        last_date = client_df['Date'].max()
        forecast_dates = pd.date_range(
            start=last_date,
            periods=prediction_length + 1,
            freq=freq_map.get(granularity, 'D')
        )[1:]  # Drop the first date (= last known date)

        result = pd.DataFrame({
            "Date": forecast_dates.astype(str),
            "Client_Name": client_name,
            f"Forecast_{metric}": prediction.astype(float),
        })

        return {
            "status": "success",
            "client": client_name,
            "metric": metric,
            "granularity": granularity,
            "prediction_length": prediction_length,
            "history_cutoff": str(last_date),
            "forecast": result.to_dict(orient="records"),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/v1/forecast/all-clients")
def forecast_all_clients(
    prediction_length: int = 30,
    client_name: Optional[str] = None,
    metric: str = Query("uploaded_count", description="Metric to forecast"),
    granularity: str = Query("day", description="day, week, month, or quarter"),
    cutoff_date: Optional[str] = Query(
        None,
        description=(
            "ISO date (YYYY-MM-DD) after which the forecast begins. "
            "History is trimmed to this date and prediction starts from the next period. "
            "Defaults to the last complete period in the data."
        ),
    ),
    company: Optional[List[str]] = Query(None),
    channel: Optional[List[str]] = Query(None),
    user: Optional[List[str]] = Query(None),
    language: Optional[List[str]] = Query(None),
    input_type: Optional[List[str]] = Query(None),
    output_type_filter: Optional[List[str]] = Query(None, alias="output_type"),
    date_from: Optional[str] = Query(None, description="YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="YYYY-MM-DD"),
    auth_context: AuthContext = Depends(require_auth),
):
    """
    Forecast a metric for all (or one) clients using Chronos.

    Pass `cutoff_date` to pin exactly where the forecast horizon starts.
    All clients share the same cutoff so comparisons remain aligned.
    """
    try:
        if auth_context.role == "client_admin":
            company = [auth_context.client_name]
            client_name = auth_context.client_name

        if any([company, channel, user, language, input_type, output_type_filter, date_from, date_to]) or auth_context.role == "user":
            engine = _get_engine()
            videos_df = pd.read_sql("SELECT * FROM \"raw_videos\"", engine)
            assets_df = pd.read_sql("SELECT * FROM \"created_assets\"", engine)
            posts_df = pd.read_sql("SELECT * FROM \"published_posts\"", engine)
            users_df = pd.read_sql("SELECT * FROM \"users\"", engine)
            try:
                dist_df = pd.read_sql("SELECT * FROM \"post_distribution\"", engine)
            except Exception:
                dist_df = None
            try:
                rvc_df = pd.read_sql("SELECT * FROM \"raw_video_channel\"", engine)
            except Exception:
                rvc_df = None

            videos_df["Upload_Date"] = pd.to_datetime(videos_df["Upload_Date"])
            assets_df["Create_Date"] = pd.to_datetime(assets_df["Create_Date"])
            posts_df["Publish_Date"] = pd.to_datetime(posts_df["Publish_Date"])

            videos_df, assets_df, posts_df, users_df, dist_df = _apply_usage_filters(
                videos_df,
                assets_df,
                posts_df,
                users_df,
                dist_df,
                rvc_df,
                company=company,
                channel=channel,
                user=user,
                language=language,
                input_type=input_type,
                output_type=output_type_filter,
                date_from=date_from,
                date_to=date_to,
                force_user_id=auth_context.user_id if auth_context.role == "user" else None,
            )

            master_df = _build_master_df_from_frames(videos_df, assets_df, posts_df, users_df)
        else:
            master_df = _build_master_df()

        resampled_df = _resample_dataframe(master_df, granularity)

        # Always strip the current incomplete period first
        resampled_df = _drop_incomplete_tail(resampled_df, granularity)

        clients = resampled_df['Client_Name'].dropna().unique().tolist()

        if client_name is not None:
            client_name = client_name.strip()
            if not client_name:
                raise HTTPException(status_code=400, detail="client_name cannot be empty")
            if client_name not in clients:
                raise HTTPException(status_code=404, detail=f"Client '{client_name}' not found")
            clients = [client_name]

        # Validate cutoff_date once up front
        cutoff_ts: Optional[pd.Timestamp] = None
        if cutoff_date is not None:
            try:
                cutoff_ts = pd.Timestamp(cutoff_date).normalize()
            except Exception:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid cutoff_date '{cutoff_date}'. Use ISO format YYYY-MM-DD."
                )

        all_client_forecasts = {}
        freq_map = {'day': 'D', 'week': 'W-MON', 'month': 'MS', 'quarter': 'QS'}

        for client in clients:
            client_df = resampled_df[resampled_df['Client_Name'] == client].copy()
            if metric not in client_df.columns:
                raise HTTPException(status_code=400, detail=f"Invalid metric '{metric}'")

            client_df = client_df.sort_values('Date')

            # [FIX] Align Auto cutoff with the last data point showing in plot
            client_df = _drop_trailing_zeros(client_df, metric)

            # ── Apply cutoff_date filter ──────────────────────────────────
            if cutoff_ts is not None:
                client_df = client_df[pd.to_datetime(client_df['Date']) <= cutoff_ts]
                if client_df.empty:
                    # Skip clients that have no data before the cutoff instead of
                    # crashing the whole request
                    all_client_forecasts[client] = {
                        'history': [],
                        'forecast': [],
                        'warning': f"No data on or before cutoff_date '{cutoff_date}'",
                    }
                    continue

            last_date = client_df['Date'].max()
            forecast_dates = pd.date_range(
                start=last_date,
                periods=prediction_length + 1,
                freq=freq_map.get(granularity, 'D')
            )[1:]

            target_series = client_df[metric].astype(float).values
            forecast_path = _chronos_predict_uploads(target_series, prediction_length)

            history = client_df[['Date', metric]].copy()
            history['Date'] = history['Date'].astype(str)

            forecast_rows = pd.DataFrame({
                'Date': forecast_dates.astype(str),
                f'Forecast_{metric}': forecast_path.astype(float),
            })

            all_client_forecasts[client] = {
                'history_cutoff': str(last_date),
                'history': history.to_dict(orient='records'),
                'forecast': forecast_rows.to_dict(orient='records'),
            }

        return {
            'status': 'success',
            'metric': metric,
            'granularity': granularity,
            'prediction_length': prediction_length,
            'clients': all_client_forecasts,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
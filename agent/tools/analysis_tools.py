"""Pandas / NumPy helpers for the deep-path analytics agent."""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger("agent.analysis_tools")


def rows_to_dataframe(columns: list[str], rows: list[list]) -> pd.DataFrame:
    """Convert raw query result into a DataFrame."""
    return pd.DataFrame(rows, columns=columns)


def compute_trend(df: pd.DataFrame, date_col: str, value_col: str) -> dict[str, Any]:
    """Compute linear trend direction and slope over a time series."""
    if df.empty or date_col not in df.columns or value_col not in df.columns:
        return {"direction": "unknown", "slope": 0.0}
    series = pd.to_numeric(df[value_col], errors="coerce").dropna()
    if len(series) < 2:
        return {"direction": "flat", "slope": 0.0}
    x = np.arange(len(series), dtype=float)
    slope = float(np.polyfit(x, series.values, 1)[0])
    direction = "up" if slope > 0.01 else ("down" if slope < -0.01 else "flat")
    return {"direction": direction, "slope": round(slope, 4), "points": len(series)}


def compute_period_comparison(df1: pd.DataFrame, df2: pd.DataFrame, value_col: str) -> dict[str, Any]:
    """Compare aggregate values between two period DataFrames."""
    s1 = pd.to_numeric(df1[value_col], errors="coerce").sum() if value_col in df1.columns else 0
    s2 = pd.to_numeric(df2[value_col], errors="coerce").sum() if value_col in df2.columns else 0
    delta = float(s2 - s1)
    pct = round(delta / s1 * 100, 2) if s1 else 0.0
    return {"previous": float(s1), "current": float(s2), "delta": delta, "pct_change": pct}


def detect_anomalies(df: pd.DataFrame, col: str, z_threshold: float = 2.0) -> list[dict]:
    """Simple Z-score anomaly detection on a numeric column."""
    if col not in df.columns or df.empty:
        return []
    vals = pd.to_numeric(df[col], errors="coerce").dropna()
    if vals.std() == 0:
        return []
    z_scores = (vals - vals.mean()) / vals.std()
    anomalies: list[dict] = []
    for idx in z_scores[z_scores.abs() > z_threshold].index:
        anomalies.append({
            "index": int(idx),
            "value": float(vals.loc[idx]),
            "z_score": round(float(z_scores.loc[idx]), 2),
        })
    return anomalies


def compute_correlation(df: pd.DataFrame) -> dict[str, Any]:
    """Compute correlation matrix for all numeric columns."""
    numeric = df.select_dtypes(include=[np.number])
    if numeric.shape[1] < 2:
        return {"matrix": {}}
    corr = numeric.corr().round(3)
    return {"matrix": corr.to_dict()}


def compute_growth_rate(values: list[float]) -> float:
    """Compound growth rate over a list of values."""
    if len(values) < 2 or values[0] == 0:
        return 0.0
    return round((values[-1] / values[0]) ** (1.0 / (len(values) - 1)) - 1, 4)

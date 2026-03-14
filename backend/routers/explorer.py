"""
explorer.py — Explorer / multidim routes.
Port of backend_legacy/routes/explorer.js.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.engine import Connection

from ..dependencies import AuthUser, get_db, require_admin, require_auth
from ..queries.analytics_shared import (
    DATE_FIELD_MAP,
    DIMENSION_MAP,
    MEASURE_MAP,
    build_access_filter,
    build_where,
)
from ..queries.explorer import (
    TABLE_COLUMNS_QUERY,
    TABLE_EXISTS_QUERY,
    TABLES_QUERY,
    count_chart_query,
    matrix_query,
    sum_chart_query,
    table_data_query,
    time_series_query,
)

router = APIRouter(prefix="/api/explorer", tags=["explorer"])

VALID_TIME_GRAINS = {"none", "day", "week", "month"}


@router.get("/dimensions")
def dimensions():
    return {
        "dimensions": [
            {"key": "channel",            "label": "Channel"},
            {"key": "language",           "label": "Language"},
            {"key": "input_type",         "label": "Input Type"},
            {"key": "output_type",        "label": "Output Type"},
            {"key": "user",               "label": "User"},
            {"key": "client",             "label": "Client"},
            {"key": "published_platform", "label": "Published Platform"},
        ],
        "measures": [
            {"key": "uploaded_videos", "label": "Uploaded Videos (distinct)"},
            {"key": "created_assets",  "label": "Created Assets (distinct)"},
            {"key": "published_posts", "label": "Published Posts (distinct)"},
        ],
        "dateFields": [
            {"key": "upload_date",  "label": "Upload Date"},
            {"key": "create_date",  "label": "Create Date"},
            {"key": "publish_date", "label": "Publish Date"},
        ],
    }


@router.get("/multidim")
def multidim(
    dim1: str = Query("channel"),
    dim2: str = Query("language"),
    measure: str = Query("uploaded_videos"),
    timeGrain: str = Query("none"),
    dateField: str = Query("upload_date"),
    dim1Value: str = Query(""),
    auth: AuthUser = Depends(require_auth),
    conn: Connection = Depends(get_db),
):
    if dim1 not in DIMENSION_MAP:
        dim1 = "channel"
    if dim2 not in DIMENSION_MAP:
        dim2 = "language"
    if measure not in MEASURE_MAP:
        measure = "uploaded_videos"
    if timeGrain not in VALID_TIME_GRAINS:
        timeGrain = "none"
    if dateField not in DATE_FIELD_MAP:
        dateField = "upload_date"

    dim1_expr = DIMENSION_MAP[dim1]
    dim2_expr = DIMENSION_MAP[dim2]
    measure_expr = MEASURE_MAP[measure]
    date_expr = DATE_FIELD_MAP[dateField]

    # Matrix query
    m_af = build_access_filter(auth, "rv")
    m_preds = list(m_af.predicates)
    m_params = dict(m_af.params)

    if dim1Value:
        m_params["m_dim1val"] = dim1Value
        m_preds.append(f"{dim1_expr}::text = :m_dim1val")

    m_where = build_where(m_preds)
    m_sql = matrix_query(dim1_expr, dim2_expr, measure_expr, m_af.join, m_where)
    m_rows = conn.execute(text(m_sql), m_params).mappings().all()
    matrix_rows = [{"dim1": r["dim1"], "dim2": r["dim2"], "value": float(r.get("value", 0))} for r in m_rows]

    dim1_values = list(dict.fromkeys(r["dim1"] for r in matrix_rows))[:60]
    dim2_values = list(dict.fromkeys(r["dim2"] for r in matrix_rows))[:30]

    ts_rows_out = []
    if timeGrain != "none":
        ts_af = build_access_filter(auth, "rv")
        ts_params = {"ts_grain": timeGrain, **ts_af.params}
        ts_where = list(ts_af.predicates) + [f"{date_expr} IS NOT NULL"]

        if dim1Value:
            ts_params["ts_dim1val"] = dim1Value
            ts_where.append(f"{dim1_expr}::text = :ts_dim1val")

        ts_sql = time_series_query(date_expr, dim2_expr, measure_expr, ts_af.join, ts_where)
        ts_rows = conn.execute(text(ts_sql), ts_params).mappings().all()
        ts_rows_out = [{"period": str(r["period"]), "dim2": r["dim2"], "value": float(r.get("value", 0))} for r in ts_rows]

    return {
        "dim1": dim1, "dim2": dim2, "measure": measure,
        "timeGrain": timeGrain, "dateField": dateField,
        "dim1Value": dim1Value or None,
        "matrixRows": matrix_rows, "dim1Values": dim1_values, "dim2Values": dim2_values,
        "timeSeriesRows": ts_rows_out,
    }


@router.get("/tables")
def tables(auth: AuthUser = Depends(require_admin), conn: Connection = Depends(get_db)):
    rows = conn.execute(text(TABLES_QUERY)).mappings().all()
    return {"tables": [r["tablename"] for r in rows]}


@router.get("/table/{table_name}")
def table_detail(
    table_name: str,
    limit: int = Query(100, le=500),
    auth: AuthUser = Depends(require_admin),
    conn: Connection = Depends(get_db),
):
    exists = conn.execute(text(TABLE_EXISTS_QUERY), {"tbl": table_name}).mappings().first()
    if not exists:
        raise HTTPException(404, "Table not found")

    cols = conn.execute(text(TABLE_COLUMNS_QUERY), {"tbl": table_name}).mappings().all()
    data = conn.execute(text(table_data_query(table_name, limit))).mappings().all()

    return {
        "table": table_name,
        "columns": [r["column_name"] for r in cols],
        "rows": [dict(r) for r in data],
    }


@router.get("/chart")
def chart(
    table: str = Query(...),
    x: str = Query(...),
    y: str | None = Query(None),
    aggregation: str = Query("count"),
    auth: AuthUser = Depends(require_admin),
    conn: Connection = Depends(get_db),
):
    exists = conn.execute(text(TABLE_EXISTS_QUERY), {"tbl": table}).mappings().first()
    if not exists:
        raise HTTPException(404, "Invalid table")

    cols = conn.execute(text(TABLE_COLUMNS_QUERY), {"tbl": table}).mappings().all()
    valid_cols = {r["column_name"] for r in cols}

    if x not in valid_cols:
        raise HTTPException(400, "Invalid x column")

    if aggregation == "sum":
        if not y or y not in valid_cols:
            raise HTTPException(400, "Valid numeric y column required for sum aggregation")
        rows = conn.execute(text(sum_chart_query(table, x, y))).mappings().all()
    else:
        rows = conn.execute(text(count_chart_query(table, x))).mappings().all()

    return {"rows": [dict(r) for r in rows]}

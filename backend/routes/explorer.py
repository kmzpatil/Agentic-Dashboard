from fastapi import APIRouter, Depends, Path, Query
from fastapi.responses import JSONResponse

from backend.db.pool import query
from backend.middleware.auth import AuthContext, require_auth
from backend.queries.analytics_shared import (
    DATE_FIELD_MAP,
    DIMENSION_MAP,
    MEASURE_MAP,
    build_access_filter,
    build_where_clause,
)
from backend.queries.explorer_queries import (
    TABLE_COLUMNS_QUERY,
    TABLE_EXISTS_QUERY,
    TABLES_QUERY,
    get_count_chart_query,
    get_matrix_query,
    get_sum_chart_query,
    get_table_data_query,
    get_time_series_query,
)


router = APIRouter()


@router.get("/dimensions")
def get_dimensions(_auth: AuthContext = Depends(require_auth)):
    return {
        "dimensions": [
            {"key": "channel", "label": "Channel"},
            {"key": "language", "label": "Language"},
            {"key": "input_type", "label": "Input Type"},
            {"key": "output_type", "label": "Output Type"},
            {"key": "user", "label": "User"},
            {"key": "client", "label": "Client"},
            {"key": "published_platform", "label": "Published Platform"},
            {"key": "Team_Name", "label": "Team Name"},
        ],
        "measures": [
            {"key": "uploaded_videos", "label": "Uploaded Videos (distinct)"},
            {"key": "created_assets", "label": "Created Assets (distinct)"},
            {"key": "published_posts", "label": "Published Posts (distinct)"},
        ],
        "dateFields": [
            {"key": "upload_date", "label": "Upload Date"},
            {"key": "create_date", "label": "Create Date"},
            {"key": "publish_date", "label": "Publish Date"},
        ],
    }


@router.get("/channels")
def get_channels(auth: AuthContext = Depends(require_auth)):
    try:
        if auth.role == "website_admin":
            result = query("""
                SELECT DISTINCT "Channel_Name"
                FROM channels
                WHERE "Channel_Name" IS NOT NULL
                ORDER BY "Channel_Name"
            """)
        else:
            # client_admin and user: only channels belonging to their client
            result = query("""
                SELECT DISTINCT "Channel_Name"
                FROM channels
                WHERE "Channel_Name" IS NOT NULL
                  AND "Client_Name" = $1
                ORDER BY "Channel_Name"
            """, [auth.client_name])
        return {"channels": [row["Channel_Name"] for row in result.rows]}
    except Exception as error:
        return JSONResponse(status_code=500, content={"error": str(error)})


@router.get("/multidim")
def get_multidim(
    auth: AuthContext = Depends(require_auth),
    dim1: str = Query(default="channel"),
    dim2: str = Query(default="language"),
    measure: str = Query(default="uploaded_videos"),
    timeGrain: str = Query(default="none"),
    dateField: str = Query(default="upload_date"),
    dim1Value: str = Query(default=""),
    channels: str | None = Query(default=None),
    startDate: str | None = Query(default=None),
    endDate: str | None = Query(default=None),
):
    safe_dim1 = dim1 if dim1 in DIMENSION_MAP else "channel"
    safe_dim2 = dim2 if dim2 in DIMENSION_MAP else "language"
    safe_measure = measure if measure in MEASURE_MAP else "uploaded_videos"
    safe_time_grain = timeGrain if timeGrain in {"none", "day", "week", "month"} else "none"
    safe_date_field = dateField if dateField in DATE_FIELD_MAP else "upload_date"

    dim1_expr = DIMENSION_MAP[safe_dim1]
    dim2_expr = DIMENSION_MAP[safe_dim2]
    measure_expr = MEASURE_MAP[safe_measure]
    date_expr = DATE_FIELD_MAP[safe_date_field]

    try:
        matrix_scope = build_access_filter(auth, 1, "rv")
        matrix_params = [*matrix_scope["params"]]
        matrix_where = [*matrix_scope["predicates"]]

        if dim1Value:
            matrix_params.append(dim1Value)
            matrix_where.append(f"{dim1_expr}::text = ${len(matrix_params)}")

        # Apply Global Date Filters to Matrix Query
        if startDate:
            matrix_params.append(startDate)
            matrix_where.append(f"{date_expr} >= ${len(matrix_params)}::date")
        
        if endDate:
            matrix_params.append(endDate)
            matrix_where.append(f"{date_expr} <= ${len(matrix_params)}::date")

        # Add the dynamic IN clause for the Matrix Query (Channels)
        if channels and channels != "all":
            selected_channels = channels.split(",")
            placeholders = []
            for ch in selected_channels:
                matrix_params.append(ch)
                placeholders.append(f"${len(matrix_params)}")
            matrix_where.append(f'ch."Channel_Name" IN ({", ".join(placeholders)})')

        matrix_where_clause = build_where_clause(matrix_where)
        matrix_sql = get_matrix_query(dim1_expr, dim2_expr, measure_expr, matrix_scope["join"], matrix_where_clause)

        matrix_rows = [
            {
                "dim1": row["dim1"],
                "dim2": row["dim2"],
                "value": float(row.get("value") or 0),
            }
            for row in query(matrix_sql, matrix_params).rows
        ]

        dim1_values = list(dict.fromkeys(row["dim1"] for row in matrix_rows))[:60]
        dim2_values = list(dict.fromkeys(row["dim2"] for row in matrix_rows))[:30]

        time_series_rows = []
        if safe_time_grain != "none":
            ts_scope = build_access_filter(auth, 2, "rv")
            ts_params = [safe_time_grain, *ts_scope["params"]]
            ts_where = [*ts_scope["predicates"], f"{date_expr} IS NOT NULL"]

            # Apply Date Filters to Time Series
            if startDate:
                ts_params.append(startDate)
                ts_where.append(f"{date_expr} >= ${len(ts_params)}::date")
            
            if endDate:
                ts_params.append(endDate)
                ts_where.append(f"{date_expr} <= ${len(ts_params)}::date")

            if dim1Value:
                ts_params.append(dim1Value)
                ts_where.append(f"{dim1_expr}::text = ${len(ts_params)}")
            
            # Apply Channel Filters to Time Series
            if channels and channels != "all":
                selected_channels = channels.split(",")
                placeholders = []
                for ch in selected_channels:
                    ts_params.append(ch)
                    placeholders.append(f"${len(ts_params)}")
                ts_where.append(f'ch."Channel_Name" IN ({", ".join(placeholders)})')

            ts_sql = get_time_series_query(date_expr, dim2_expr, measure_expr, ts_scope["join"], " AND ".join(ts_where))
            time_series_rows = [
                {
                    "period": row["period"],
                    "dim2": row["dim2"],
                    "value": float(row.get("value") or 0),
                }
                for row in query(ts_sql, ts_params).rows
            ]

        return {
            "dim1": safe_dim1,
            "dim2": safe_dim2,
            "measure": safe_measure,
            "timeGrain": safe_time_grain,
            "dateField": safe_date_field,
            "dim1Value": dim1Value or None,
            "matrixRows": matrix_rows,
            "dim1Values": dim1_values,
            "dim2Values": dim2_values,
            "timeSeriesRows": time_series_rows,
        }
    except Exception as error:
        return JSONResponse(status_code=500, content={"error": str(error)})


@router.get("/tables")
def get_tables(auth: AuthContext = Depends(require_auth)):
    if auth.role != "website_admin":
        return JSONResponse(status_code=403, content={"error": "Forbidden"})

    try:
        rows = query(TABLES_QUERY).rows
        return {"tables": [row["tablename"] for row in rows]}
    except Exception as error:
        return JSONResponse(status_code=500, content={"error": str(error)})


@router.get("/table/{table_name}")
def get_table(
    table_name: str = Path(...),
    limit: int = Query(default=100),
    auth: AuthContext = Depends(require_auth),
):
    if auth.role != "website_admin":
        return JSONResponse(status_code=403, content={"error": "Forbidden"})

    safe_limit = min(int(limit or 100), 500)

    try:
        table_check = query(TABLE_EXISTS_QUERY, [table_name])
        if table_check.row_count == 0:
            return JSONResponse(status_code=404, content={"error": "Table not found"})

        columns_result = query(TABLE_COLUMNS_QUERY, [table_name])
        data_result = query(get_table_data_query(table_name, safe_limit))

        return {
            "table": table_name,
            "columns": [row["column_name"] for row in columns_result.rows],
            "rows": data_result.rows,
        }
    except Exception as error:
        return JSONResponse(status_code=500, content={"error": str(error)})


@router.get("/chart")
def get_chart(
    auth: AuthContext = Depends(require_auth),
    table: str | None = Query(default=None),
    x: str | None = Query(default=None),
    y: str | None = Query(default=None),
    aggregation: str = Query(default="count"),
):
    if auth.role != "website_admin":
        return JSONResponse(status_code=403, content={"error": "Forbidden"})

    if not table or not x:
        return JSONResponse(status_code=400, content={"error": "table and x are required"})

    try:
        table_check = query(TABLE_EXISTS_QUERY, [table])
        if table_check.row_count == 0:
            return JSONResponse(status_code=404, content={"error": "Invalid table"})

        columns_result = query(TABLE_COLUMNS_QUERY, [table])
        valid_columns = {row["column_name"] for row in columns_result.rows}

        if x not in valid_columns:
            return JSONResponse(status_code=400, content={"error": "Invalid x column"})

        if aggregation == "sum":
            if not y or y not in valid_columns:
                return JSONResponse(
                    status_code=400,
                    content={"error": "Valid numeric y column required for sum aggregation"},
                )
            rows = query(get_sum_chart_query(table, x, y)).rows
            return {"rows": rows}

        rows = query(get_count_chart_query(table, x)).rows
        return {"rows": rows}
    except Exception as error:
        return JSONResponse(status_code=500, content={"error": str(error)})
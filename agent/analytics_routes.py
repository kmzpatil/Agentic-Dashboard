import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Query
from mcp_server.config import ServerSettings
from mcp_server.database import DatabaseClient

logger = logging.getLogger(__name__)

router = APIRouter()

_settings = ServerSettings.from_env()
_db_client = DatabaseClient(
    database_url=_settings.database_url,
    default_schema=_settings.default_schema,
)

def run_query(sql: str, params: tuple = ()) -> List[dict]:
    import sqlite3
    db_path = _settings.database_url.replace("sqlite:///", "")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        rows = cur.fetchall()
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"SQL Error: {e} | Query: {sql} | Params: {params}")
        raise e
    finally:
        conn.close()

@router.get("/overview")
async def get_overview():
    try:
        # KPI calculations from raw_videos, created_assets, published_posts
        kpi_sql = """
        SELECT 
            (SELECT COUNT(*) FROM raw_videos) AS uploaded_count,
            (SELECT SUM(Uploaded_Duration) FROM raw_videos) AS uploaded_duration,
            (SELECT COUNT(*) FROM created_assets) as processed_count,
            (SELECT COUNT(*) FROM created_assets) AS created_count,
            (SELECT SUM(Created_Duration) FROM created_assets) AS created_duration,
            (SELECT COUNT(*) FROM published_posts) AS published_count,
            (SELECT SUM(Published_Duration) FROM published_posts) AS published_duration,
            
            CASE WHEN (SELECT COUNT(*) FROM created_assets) = 0 THEN 0 
                 ELSE (CAST((SELECT COUNT(*) FROM published_posts) AS REAL) / (SELECT COUNT(*) FROM created_assets)) * 100 END AS publish_conversion_rate,
                 
            CASE WHEN (SELECT SUM(Created_Duration) FROM created_assets) = 0 THEN 0 
                 ELSE ((SELECT SUM(Published_Duration) FROM published_posts) / (SELECT SUM(Created_Duration) FROM created_assets)) * 100 END AS processing_efficiency,
                 
            CASE WHEN (SELECT COUNT(*) FROM raw_videos) = 0 THEN 0 
                 ELSE (CAST((SELECT COUNT(*) FROM created_assets) AS REAL) / (SELECT COUNT(*) FROM raw_videos)) * 100 END AS creation_rate,
                 
            IFNULL((SELECT SUM(Created_Duration) FROM created_assets), 0) - IFNULL((SELECT SUM(Published_Duration) FROM published_posts), 0) AS waste_index;
        """
        
        input_sql = """
        SELECT r.Input_Type AS label,
               COUNT(c.Asset_ID) AS created_count,
               COUNT(p.Post_ID) AS published_count,
               CASE WHEN COUNT(c.Asset_ID) = 0 THEN 0 
                    ELSE (CAST(COUNT(p.Post_ID) AS REAL) / COUNT(c.Asset_ID)) * 100 END AS conversion
        FROM raw_videos r
        LEFT JOIN created_assets c ON r.Video_ID = c.Video_ID
        LEFT JOIN published_posts p ON c.Asset_ID = p.Asset_ID
        GROUP BY r.Input_Type
        ORDER BY conversion DESC, published_count DESC
        LIMIT 1;
        """
        
        output_sql = """
        SELECT c.Output_Type AS label,
               COUNT(c.Asset_ID) AS created_count,
               COUNT(p.Post_ID) AS published_count,
               CASE WHEN COUNT(c.Asset_ID) = 0 THEN 0 
                    ELSE (CAST(COUNT(p.Post_ID) AS REAL) / COUNT(c.Asset_ID)) * 100 END AS conversion
        FROM created_assets c
        LEFT JOIN published_posts p ON c.Asset_ID = p.Asset_ID
        GROUP BY c.Output_Type
        ORDER BY conversion DESC, published_count DESC
        LIMIT 1;
        """
        
        lang_sql = """
        SELECT r.Language AS label,
               COUNT(c.Asset_ID) AS created_count,
               COUNT(p.Post_ID) AS published_count,
               CASE WHEN COUNT(c.Asset_ID) = 0 THEN 0 
                    ELSE (CAST(COUNT(p.Post_ID) AS REAL) / COUNT(c.Asset_ID)) * 100 END AS conversion
        FROM raw_videos r
        LEFT JOIN created_assets c ON r.Video_ID = c.Video_ID
        LEFT JOIN published_posts p ON c.Asset_ID = p.Asset_ID
        GROUP BY r.Language
        ORDER BY conversion DESC, published_count DESC
        LIMIT 1;
        """
        
        alert_sql = """
        SELECT r.Input_Type AS channel_name,
               COUNT(c.Asset_ID) AS created_count,
               COUNT(p.Post_ID) AS published_count,
               CASE WHEN COUNT(c.Asset_ID) = 0 THEN 0 
                    ELSE (CAST(COUNT(p.Post_ID) AS REAL) / COUNT(c.Asset_ID)) * 100 END AS conversion
        FROM raw_videos r
        LEFT JOIN created_assets c ON r.Video_ID = c.Video_ID
        LEFT JOIN published_posts p ON c.Asset_ID = p.Asset_ID
        GROUP BY r.Input_Type
        HAVING COUNT(c.Asset_ID) > 5
        ORDER BY conversion ASC, created_count DESC
        LIMIT 5;
        """
        
        kpis = run_query(kpi_sql)[0] if run_query(kpi_sql) else {}
        in_res = run_query(input_sql)
        out_res = run_query(output_sql)
        lang_res = run_query(lang_sql)
        al_res = run_query(alert_sql)

        topPerformers = []
        if in_res and in_res[0].get("label"): topPerformers.append({"dimension": "Input Type", **in_res[0]})
        if out_res and out_res[0].get("label"): topPerformers.append({"dimension": "Output Type", **out_res[0]})
        if lang_res and lang_res[0].get("label"): topPerformers.append({"dimension": "Language", **lang_res[0]})

        alerts = []
        for row in al_res:
            conv = row.get("conversion", 0)
            alerts.append({
                "title": f"{row.get('channel_name')}: {conv:.2f}% conversion",
                "subtitle": f"{row.get('created_count')} created, {row.get('published_count')} published",
                "severity": "critical" if conv < 50 else "warning"
            })

        return {"kpis": kpis, "topPerformers": topPerformers, "alerts": alerts}
    except Exception as e:
        logger.error(f"Error in /overview: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/usage-trends")
async def get_usage_trends(metric: str = "uploaded_count", granularity: str = "month"):
    # Generate common YYYY-MM periods from all date columns
    sql = """
        WITH periods AS (
            SELECT strftime('%Y-%m', Upload_Date) AS period FROM raw_videos WHERE Upload_Date IS NOT NULL
            UNION
            SELECT strftime('%Y-%m', Create_Date) AS period FROM created_assets WHERE Create_Date IS NOT NULL
            UNION
            SELECT strftime('%Y-%m', Publish_Date) AS period FROM published_posts WHERE Publish_Date IS NOT NULL
        )
        SELECT p.period, 
               (SELECT COUNT(*) FROM raw_videos r WHERE strftime('%Y-%m', r.Upload_Date) = p.period) AS total_uploaded,
               (SELECT COUNT(*) FROM created_assets c WHERE strftime('%Y-%m', c.Create_Date) = p.period) AS total_created,
               (SELECT COUNT(*) FROM published_posts pu WHERE strftime('%Y-%m', pu.Publish_Date) = p.period) AS total_published,
               (SELECT SUM(Uploaded_Duration) FROM raw_videos r WHERE strftime('%Y-%m', r.Upload_Date) = p.period) AS total_uploaded_duration,
               (SELECT SUM(Created_Duration) FROM created_assets c WHERE strftime('%Y-%m', c.Create_Date) = p.period) AS total_created_duration,
               (SELECT SUM(Published_Duration) FROM published_posts pu WHERE strftime('%Y-%m', pu.Publish_Date) = p.period) AS total_published_duration
        FROM periods p
        ORDER BY p.period ASC
    """
    rows = run_query(sql)
    points = []
    
    for r in rows:
        val = 0
        if metric == "uploaded_count": val = r["total_uploaded"]
        elif metric == "created_count": val = r["total_created"]
        elif metric == "published_count": val = r["total_published"]
        elif metric == "uploaded_duration": val = r["total_uploaded_duration"]
        elif metric == "created_duration": val = r["total_created_duration"]
        elif metric == "published_duration": val = r["total_published_duration"]
        
        points.append({"period": r["period"], "value": float(val or 0)})
        
    latest = points[-1] if points else None
    previous = points[-2] if len(points) > 1 else None
    
    delta = None
    if latest and previous and previous["value"] > 0:
        delta = ((latest["value"] - previous["value"]) / previous["value"]) * 100

    return {
        "metric": metric,
        "granularity": "month",
        "series": points,
        "summary": {
            "latestValue": round(latest["value"], 2) if latest else 0,
            "latestPeriod": latest["period"] if latest else None,
            "deltaVsPreviousPct": round(delta, 2) if delta is not None else None
        },
        "anomalies": []
    }

@router.get("/explorer/dimensions")
async def get_dimensions():
    return {
        "dimensions": [
            { "key": 'Channel_Name', "label": 'Channel' },
            { "key": 'Language', "label": 'Language' },
            { "key": 'Input_Type', "label": 'Input Type' },
            { "key": 'Output_Type', "label": 'Output Type' }
        ],
        "measures": [
            { "key": 'uploaded_count', "label": 'Uploaded Count' },
            { "key": 'created_count', "label": 'Created Count' },
            { "key": 'published_count', "label": 'Published Count' }
        ],
        "dateFields": [
            { "key": 'period', "label": 'Month' }
        ]
    }

@router.get("/explorer/tables")
async def get_explorer_tables():
    return {"tables": ["raw_videos", "created_assets", "published_posts", "channels", "users", "clients", "post_distribution", "raw_video_channel"]}

@router.get("/explorer/table/{name}")
async def get_explorer_table_data(name: str):
    sql = f"SELECT * FROM {name} LIMIT 100"
    rows = run_query(sql)
    cols = list(rows[0].keys()) if rows else []
    return {"columns": cols, "rows": rows}

@router.get("/explorer/chart")
async def get_explorer_chart(table: str, x: str, aggregation: str = "sum", y: str = None):
    # Using real tables
    if y:
        sql = f"SELECT {x} AS label, SUM({y}) AS value FROM {table} GROUP BY {x} ORDER BY value DESC LIMIT 30"
    else:
        sql = f"SELECT {x} AS label, COUNT(*) AS value FROM {table} GROUP BY {x} ORDER BY value DESC LIMIT 30"
    try:
        rows = run_query(sql)
        return {"rows": rows}
    except:
        return {"rows": []}

@router.get("/multidim")
@router.get("/explorer/multidim")
async def get_multidim(dim1: str = "Language", dim2: str = "Output_Type", measure: str = "uploaded_count"):
    
    if measure == "uploaded_count": 
        sql = f"""
            SELECT r.Input_Type AS dim1, c.Output_Type AS dim2, COUNT(DISTINCT r.Video_ID) AS value
            FROM raw_videos r
            LEFT JOIN created_assets c ON r.Video_ID = c.Video_ID
            GROUP BY 1, 2 ORDER BY value DESC LIMIT 100
        """
    else:
        # Fallback to single dim from appropriate table
        sql = f"SELECT Language AS dim1, 'All' AS dim2, COUNT(*) AS value FROM raw_videos GROUP BY Language"

    try:
        rows = run_query(sql)
        return {"matrixRows": rows}
    except:
        return {"matrixRows": []}

@router.get("/funnel")
async def get_funnel(breakdown: str = "Input_Type"):
    sql_stage = """
        SELECT 
            (SELECT COUNT(*) FROM raw_videos) AS uploaded_count,
            (SELECT COUNT(*) FROM created_assets) AS processed_count,
            (SELECT COUNT(*) FROM created_assets) AS created_count,
            (SELECT COUNT(*) FROM published_posts) AS published_count
    """
    stage_counts = run_query(sql_stage)[0]
    
    if breakdown == "Channel":
        sql_breakdown = "SELECT Channel_Name AS label, COUNT(*) AS uploaded_count, 0 AS created_count, 0 AS published_count, 0 AS conversion FROM raw_video_channel GROUP BY Channel_Name"
    elif breakdown == "Language":
        sql_breakdown = """
            SELECT r.Language AS label, 
                   COUNT(DISTINCT r.Video_ID) AS uploaded_count, 
                   COUNT(DISTINCT c.Asset_ID) AS created_count, 
                   COUNT(DISTINCT p.Post_ID) AS published_count, 
                   CASE WHEN COUNT(DISTINCT c.Asset_ID)=0 THEN 0 ELSE (CAST(COUNT(DISTINCT p.Post_ID) AS REAL)/COUNT(DISTINCT c.Asset_ID))*100 END AS conversion 
            FROM raw_videos r
            LEFT JOIN created_assets c ON r.Video_ID = c.Video_ID
            LEFT JOIN published_posts p ON c.Asset_ID = p.Asset_ID
            GROUP BY r.Language
        """
    elif breakdown == "Output_Type":
        sql_breakdown = """
            SELECT c.Output_Type AS label, 
                   COUNT(DISTINCT c.Video_ID) AS uploaded_count, 
                   COUNT(DISTINCT c.Asset_ID) AS created_count, 
                   COUNT(DISTINCT p.Post_ID) AS published_count, 
                   CASE WHEN COUNT(DISTINCT c.Asset_ID)=0 THEN 0 ELSE (CAST(COUNT(DISTINCT p.Post_ID) AS REAL)/COUNT(DISTINCT c.Asset_ID))*100 END AS conversion 
            FROM created_assets c
            LEFT JOIN published_posts p ON c.Asset_ID = p.Asset_ID
            GROUP BY c.Output_Type
        """
    else:
        sql_breakdown = f"""
            SELECT r.Input_Type AS label,
                COUNT(DISTINCT r.Video_ID) AS uploaded_count,
                COUNT(DISTINCT c.Asset_ID) AS created_count,
                COUNT(DISTINCT p.Post_ID) AS published_count,
                CASE WHEN COUNT(DISTINCT c.Asset_ID) = 0 THEN 0 ELSE (CAST(COUNT(DISTINCT p.Post_ID) AS REAL) / COUNT(DISTINCT c.Asset_ID)) * 100 END AS conversion
            FROM raw_videos r
            LEFT JOIN created_assets c ON r.Video_ID = c.Video_ID
            LEFT JOIN published_posts p ON c.Asset_ID = p.Asset_ID
            GROUP BY r.Input_Type
            ORDER BY conversion DESC, uploaded_count DESC LIMIT 30
        """
    
    try:
        bd_rows = run_query(sql_breakdown)
    except:
        bd_rows = []
    
    return {
        "stageCounts": stage_counts,
        "sankeyLinks": [
            {"from": "Uploaded", "to": "Processed", "flow": stage_counts["processed_count"]},
            {"from": "Processed", "to": "Created", "flow": stage_counts["created_count"]},
            {"from": "Created", "to": "Published", "flow": stage_counts["published_count"]}
        ],
        "compositionLinks": [],
        "breakdownDimension": breakdown,
        "breakdown": bd_rows,
        "journeyVideos": []
    }

"""
Tool: retrieve_metric_definitions
Simulates a semantic/vector search layer over business metric definitions.
Used to look up exact formulas, table names, and column names before
the LLM generates SQL so it targets the correct transactional schema.
"""

# ── Actual transactional schema (frammer_database.sql) ───────────────────────
METRIC_DICTIONARY: dict[str, str] = {
    "upload": 'uploads: raw_videos. count=COUNT(DISTINCT rv."Video_ID")',
    "channel": 'channel: raw_video_channel maps Video_ID->Channel_Name. channels maps Channel_Name->Client_Name.',
    "client": 'client: JOIN users u ON u."User_ID"=rv."User_ID" WHERE u."Client_Name"=\'...\'',
    "user": 'user: raw_videos."User_ID"=users."User_ID"',
    "asset": 'assets: created_assets. count=COUNT(DISTINCT ca."Asset_ID"), duration=SUM("Created_Duration").',
    "output": 'output type: created_assets."Output_Type"',
    "publish": 'publish: published_posts. count=COUNT(DISTINCT pp."Asset_ID"), duration=SUM("Published_Duration"). IMPORTANT: Do not count Post_ID for published volume, use Asset_ID.',
    "conversion": 'conversion: (COUNT(DISTINCT pp."Asset_ID")::NUMERIC / NULLIF(COUNT(DISTINCT ca."Asset_ID"), 0)) * 100. IMPORTANT: When grouping conversion by channel or user, you MUST join created_assets to raw_videos (Video_ID), then to users (User_ID) and raw_video_channel (Video_ID) to get the grouping columns (User_Name, Channel_Name). DO NOT group by post_distribution.Channel_Name because unpublished assets will drop out of the denominator.',
    "creation_rate": 'creation rate: (COUNT(DISTINCT ca."Asset_ID")::NUMERIC / NULLIF(COUNT(DISTINCT rv."Video_ID"), 0)) * 100',
    "funnel": 'funnel: raw_videos -> raw_video_channel -> channels -> created_assets -> published_posts -> post_distribution',
    "language": 'language: raw_videos."Language"',
    "input_type": 'input_type: lower(raw_videos."Input_Type")',
    "platform": 'platform: post_distribution."Published_Platform"',
    "duration": 'durations: Uploaded_Duration(rv), Created_Duration(ca), Published_Duration(pp)',
    "trend": "trend: date_trunc('month', to_date(col, 'YYYY-MM-DD'))::date",
    "correlation": 'correlation: Use PostgreSQL CORR(x, y) for Pearson correlation between two numeric columns. Returns -1 to 1. Example: SELECT CORR("Uploaded_Duration"::numeric, asset_count::numeric) AS correlation_value FROM ...',
    "heatmap": 'heatmap: SQL must return exactly 3 columns — two categorical dimensions and one numeric value. Example: SELECT lower(rv."Input_Type") AS x_dim, rv."Language" AS y_dim, COUNT(*) AS value FROM raw_videos rv GROUP BY 1, 2',
}


def retrieve_metric_definitions(search_term: str) -> str:
    """Return matching brief metric definitions, or a super concise fallback."""
    term = search_term.lower()
    results = [desc for key, desc in METRIC_DICTIONARY.items() if key in term or term in key]
    if results:
        return " | ".join(results)

    return (
        "dataset overview: raw_videos (uploads) -> created_assets (processed) -> published_posts (published).\n"
        "path: raw_videos rv JOIN created_assets ca ON ca.\"Video_ID\"=rv.\"Video_ID\" JOIN published_posts pp ON pp.\"Asset_ID\"=ca.\"Asset_ID\"\n"
        "rules: NO CARTESIAN PRODUCTS. lower(rv.\"Input_Type\"). pd=\"post_distribution\", pp=\"published_posts\"."
    )

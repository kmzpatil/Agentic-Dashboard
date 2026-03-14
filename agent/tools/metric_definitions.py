"""
Tool: retrieve_metric_definitions
Simulates a semantic/vector search layer over business metric definitions.
Used to look up exact formulas, table names, and column names before
the LLM generates SQL so it targets the correct transactional schema.
"""

# ── Actual transactional schema (frammer_database.sql) ───────────────────────
METRIC_DICTIONARY: dict[str, str] = {
    "upload": (
        "Raw video uploads live in `raw_videos` (columns: Video_ID, User_ID, "
        "Input_Type, Language, Upload_Date TEXT 'YYYY-MM-DD', Uploaded_Duration INTEGER seconds). "
        "Channel mapping: `raw_video_channel` (Video_ID, Channel_Name). "
        "uploaded_count = COUNT(*) FROM raw_videos. "
        "uploaded_duration = SUM(\"Uploaded_Duration\") FROM raw_videos."
    ),
    "channel": (
        "`raw_video_channel` maps Video_ID → Channel_Name. "
        "`channels` maps Channel_Name → Client_Name. "
        "To count uploads per channel: JOIN raw_videos rv ON rvc.Video_ID = rv.Video_ID "
        "GROUP BY rvc.Channel_Name."
    ),
    "client": (
        "`clients` (Client_Name TEXT PK). "
        "`users` (User_ID, User_Name, Team_Name, Client_Name) links users to clients. "
        "To scope by client: JOIN users u ON u.User_ID = rv.User_ID WHERE u.Client_Name = '...'."
    ),
    "user": (
        "`users` columns: User_ID INTEGER, User_Name TEXT, Team_Name TEXT, Client_Name TEXT. "
        "Join to raw_videos via: raw_videos.User_ID = users.User_ID."
    ),
    "asset": (
        "Created content assets live in `created_assets` "
        "(Asset_ID, Video_ID FK→raw_videos, Output_Type TEXT, Create_Date TEXT 'YYYY-MM-DD', "
        "Created_Duration INTEGER seconds). "
        "Output_Type values include: 'Full package', 'Chapters', 'Summary', 'Key moments', 'My Key moments'. "
        "created_count = COUNT(*) FROM created_assets. "
        "created_duration = SUM(\"Created_Duration\") FROM created_assets."
    ),
    "output": (
        "Output types are stored in `created_assets`.Output_Type. "
        "Values: 'Full package', 'Chapters', 'Summary', 'Key moments', 'My Key moments'. "
        "To analyse by output type: GROUP BY ca.\"Output_Type\"."
    ),
    "publish": (
        "Published posts live in `published_posts` "
        "(Post_ID, Asset_ID FK→created_assets, Publish_Date TEXT 'YYYY-MM-DD', Published_Duration INTEGER seconds). "
        "Platform distribution: `post_distribution` (Post_ID, Channel_Name, Published_Platform, Published_URL). "
        "published_count = COUNT(*) FROM published_posts. "
        "published_duration = SUM(\"Published_Duration\") FROM published_posts."
    ),
    "conversion": (
        "publish_conversion_rate = (COUNT published_posts / COUNT created_assets) * 100. "
        "Join path: raw_videos → created_assets (Video_ID) → published_posts (Asset_ID). "
        "Example SQL: "
        "SELECT CASE WHEN COUNT(ca.Asset_ID) = 0 THEN 0 "
        "ELSE COUNT(pp.Post_ID)::float8 / COUNT(ca.Asset_ID) * 100 END AS conversion_rate "
        "FROM created_assets ca LEFT JOIN published_posts pp ON pp.Asset_ID = ca.Asset_ID."
    ),
    "creation_rate": (
        "creation_rate = (COUNT created_assets / COUNT raw_videos) * 100. "
        "Join path: raw_videos → created_assets via Video_ID."
    ),
    "funnel": (
        "Full pipeline: raw_videos → raw_video_channel → channels → created_assets → published_posts → post_distribution. "
        "Stage counts: uploaded (raw_videos), processed (videos with ≥1 asset), "
        "created (total assets), published (total posts)."
    ),
    "language": (
        "Video language is stored in `raw_videos`.Language (TEXT). "
        "To analyse by language: GROUP BY rv.\"Language\"."
    ),
    "input_type": (
        "Video input type is stored in `raw_videos`.Input_Type (TEXT). "
        "To analyse by input type: GROUP BY rv.\"Input_Type\"."
    ),
    "platform": (
        "Published platform is stored in `post_distribution`.Published_Platform (TEXT). "
        "Join: published_posts → post_distribution via Post_ID. "
        "To count by platform: GROUP BY pd.\"Published_Platform\"."
    ),
    "duration": (
        "Three duration columns exist: "
        "raw_videos.Uploaded_Duration (seconds uploaded), "
        "created_assets.Created_Duration (seconds of created content), "
        "published_posts.Published_Duration (seconds published). "
        "waste_index = AVG(Created_Duration) - AVG(Published_Duration). "
        "processing_efficiency = SUM(Published_Duration) / SUM(Created_Duration) * 100."
    ),
    "trend": (
        "All dates are stored as TEXT in 'YYYY-MM-DD' format. "
        "Convert with: to_date(column, 'YYYY-MM-DD'). "
        "Truncate to month/week/day with: date_trunc('month', to_date(column, 'YYYY-MM-DD'))::date. "
        "Example monthly trend: "
        "SELECT date_trunc('month', to_date(\"Upload_Date\", 'YYYY-MM-DD'))::date AS period, COUNT(*) AS uploads "
        "FROM raw_videos GROUP BY 1 ORDER BY 1."
    ),
}


def retrieve_metric_definitions(search_term: str) -> str:
    """
    Return matching business metric definitions for the given search term.

    Args:
        search_term: A natural-language keyword or phrase (e.g. 'conversion rate', 'published').

    Returns:
        A pipe-separated string of matched definitions, or a schema summary if no match.
    """
    term = search_term.lower()
    results = [
        desc
        for key, desc in METRIC_DICTIONARY.items()
        if key in term or term in key
    ]
    if results:
        return " | ".join(results)

    # Fallback: return full schema summary so the LLM knows what tables to use.
    return (
        "No specific metric matched. "
        "Available tables: raw_videos (Video_ID, User_ID, Input_Type, Language, Upload_Date, Uploaded_Duration), "
        "raw_video_channel (Video_ID, Channel_Name), "
        "channels (Channel_Name, Client_Name), "
        "clients (Client_Name), "
        "users (User_ID, User_Name, Team_Name, Client_Name), "
        "created_assets (Asset_ID, Video_ID, Output_Type, Create_Date, Created_Duration), "
        "published_posts (Post_ID, Asset_ID, Publish_Date, Published_Duration), "
        "post_distribution (Post_ID, Channel_Name, Published_Platform, Published_URL). "
        "All date columns are TEXT in YYYY-MM-DD format — use to_date(col, 'YYYY-MM-DD') to cast."
    )

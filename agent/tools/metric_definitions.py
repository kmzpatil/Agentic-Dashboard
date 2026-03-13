"""
Tool: retrieve_metric_definitions
Retrieves business metric definitions by matching user queries against
known table/domain terms using word-overlap scoring.
"""

METRIC_DICTIONARY: dict[str, str] = {
    "channel_metrics": "Table `channel_metrics`. Columns: channel_name, facebook, instagram, linkedin, reels, shorts, x, youtube, threads. Sample: {'channel_name': 'c4_channel_3', 'facebook': 42}",
    "input_type_metrics": "Table `input_type_metrics`. Columns: input_type, count, total_duration. Sample: {'input_type': 'special reports', 'count': 1501}",
    "monthly_counts_duration": "Table `monthly_counts_duration`. Columns: month, total_uploaded, total_created, total_published, total_uploaded_duration, total_created_duration, total_published_duration. Sample: {'month': '2025-12', 'total_uploaded': 854}",
    "output_type_statistics": "Table `output_type_statistics`. Columns: output_type, count, total_duration. Sample: {'output_type': 'key moments', 'count': 10720}",
    "raw_videos": "Core table `raw_videos`. Columns: video_id, user_id, headline, source_url, upload_date, input_type, language, uploaded_duration. NOTE: `upload_date` is VARCHAR. Use `strftime(TRY_CAST(upload_date AS DATE), '%Y-%m')` for monthly trends.",
    "created_assets": "Table `created_assets`. Columns: asset_id, video_id, output_type, create_date, created_duration. NOTE: `create_date` is VARCHAR. Use `strftime(TRY_CAST(create_date AS DATE), '%Y-%m')` for monthly trends.",
    "published_posts": "Table `published_posts`. Columns: post_id, asset_id, publish_date, published_duration. NOTE: `publish_date` is VARCHAR. Use `strftime(TRY_CAST(publish_date AS DATE), '%Y-%m')` for monthly trends.",
    "post_distribution": "Table `post_distribution`. Columns: post_id, channel_name, published_platform, published_url. Sample: {'published_platform': 'reels', 'channel_name': 'c2_channel_10'}",
    "SQL_RULES": "CRITICAL: DuckDB date columns are stored as VARCHAR. You MUST use `TRY_CAST(col AS DATE)` before passing to `strftime`. Example: `strftime(TRY_CAST(publish_date AS DATE), '%Y-%m')`."
}

# Expanded keyword aliases to improve matching
_KEYWORD_ALIASES: dict[str, list[str]] = {
    "channel_metrics": ["channel", "channels", "platform", "facebook", "instagram", "youtube", "linkedin", "reels", "shorts", "threads", "social", "media", "posts"],
    "input_type_metrics": ["input", "type", "upload", "create", "publish"],
    "language_statistics": ["language", "languages", "hindi", "english", "marathi", "telugu"],
    "monthly_counts_duration": ["month", "monthly", "trend", "time", "duration", "count", "total", "uploaded", "created", "published"],
    "output_type_statistics": ["output", "type", "format"],
    "video_list_data": ["video", "videos", "team", "headline", "source", "uploaded_by", "platform", "url"],
}


def retrieve_metric_definitions(search_term: str) -> str:
    """
    Return matching business metric definitions using word-overlap scoring.

    Args:
        search_term: A natural-language keyword or phrase.

    Returns:
        A pipe-separated string of matched definitions, or a fallback message.
    """
    query_words = set(search_term.lower().replace("_", " ").split())

    scores: list[tuple[float, str]] = []
    for table_key, description in METRIC_DICTIONARY.items():
        # Score by overlap with both the table key and alias keywords
        key_words = set(table_key.replace("_", " ").split())
        alias_words = set(_KEYWORD_ALIASES.get(table_key, []))
        all_match_words = key_words | alias_words

        overlap = query_words & all_match_words
        if overlap:
            score = len(overlap) / max(len(query_words), 1)
            scores.append((score, description))

    if scores:
        # Return all matches above 0.1 threshold, best first
        scores.sort(key=lambda x: x[0], reverse=True)
        matched = [desc for score, desc in scores if score >= 0.1]
        if matched:
            return " | ".join(matched)

    return (
        "No specific metric matched exactly. Available domains are: "
        "channel_metrics, input_type_metrics, language_statistics, "
        "monthly_counts_duration, output_type_statistics, video_list_data. "
        "Use standard SQL counting/summing."
    )

"""
Tool: retrieve_metric_definitions
Retrieves business metric definitions by matching user queries against
known table/domain terms using word-overlap scoring.
"""

METRIC_DICTIONARY: dict[str, str] = {
    "channel_metrics": "Table `channel_metrics` contains metrics across columns: channels, facebook, instagram, linkedin, reels, shorts, x, youtube, threads, facebook_duration, instagram_duration, linkedin_duration, reels_duration, shorts_duration, x_duration, youtube_duration, threads_duration",
    "input_type_metrics": "Table `input_type_metrics` contains metrics across columns: input_type, uploaded_count, created_count, published_count, uploaded_duration, created_duration, published_duration",
    "language_statistics": "Table `language_statistics` contains metrics across columns: language, uploaded_count, created_count, published_count, uploaded_duration, created_duration, published_duration",
    "monthly_counts_duration": "Table `monthly_counts_duration` contains metrics across columns: month, total_uploaded, total_created, total_published, total_uploaded_duration, total_created_duration, total_published_duration",
    "output_type_statistics": "Table `output_type_statistics` contains metrics across columns: output_type, uploaded_count, created_count, published_count, uploaded_duration, created_duration, published_duration",
    "video_list_data": "Table `video_list_data` contains metrics across columns: headline, source, published, team_name, type, uploaded_by, video_id, published_platform, published_url",
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

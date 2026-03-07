"""
Tool: retrieve_metric_definitions
Simulates a semantic/vector search layer over business metric definitions.
Used to look up exact formulas and definitions before generating SQL.
"""


# In production, replace this dict with a ChromaDB / FAISS vector search query.
METRIC_DICTIONARY: dict[str, str] = {
    "conversion": (
        "Publish Conversion Rate = (COUNT(published_url) / COUNT(video_id)) * 100"
    ),
    "drop-off": (
        "Processed vs Published Gap = "
        "Count of processed_at IS NOT NULL minus Count of published_flag = 1"
    ),
    "usage": "Usage Hours = SUM(duration) / 60 for a given dimension",
    "gap": (
        "Look at the difference between uploaded, processed, and published counts."
    ),
}


def retrieve_metric_definitions(search_term: str) -> str:
    """
    Return matching business metric definitions for the given search term.

    Args:
        search_term: A natural-language keyword or phrase (e.g. 'conversion rate').

    Returns:
        A pipe-separated string of matched definitions, or a fallback message.
    """
    results = [
        desc
        for term, desc in METRIC_DICTIONARY.items()
        if term in search_term.lower()
    ]
    if results:
        return " | ".join(results)
    return "No specific metric definition found. Use standard SQL counting/summing."

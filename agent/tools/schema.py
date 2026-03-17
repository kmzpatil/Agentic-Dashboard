"""
Tool: get_frammer_schema
Retrieves the live database schema (tables + columns) via the shared MCP
DatabaseClient.  Works with any SQLAlchemy-supported backend.
Always call this before writing SQL to ensure table and column names are correct.
"""

from tools._db import get_db, get_default_schema


def get_frammer_schema() -> str:
    """
    Inspect the database and return a human-readable schema string.

    Uses the shared MCP DatabaseClient so it stays in sync with all
    other tools and benefits from connection pooling.

    Returns:
        A multi-line string listing every table and its columns (with types),
        or an error message if the database cannot be opened.
    """
    try:
        db = get_db()
        schema = get_default_schema()
        tables = db.list_tables(schema=schema)

        if not tables:
            return "No tables found in the database."

        schema_info = "Frammer AI Database Schema:\n"
        for tbl in tables:
            name = tbl["name"]
            try:
                details = db.describe_table(name, schema=schema)
                col_parts = []
                for col in details.get("columns", []):
                    nullable_tag = "" if col.get("nullable", True) else " NOT NULL"
                    col_parts.append(f"{col['name']} ({col['type']}{nullable_tag})")
                schema_info += f"\nTable: {name}\nColumns: {', '.join(col_parts)}\n"
            except Exception:
                schema_info += f"\nTable: {name}\nColumns: (could not inspect)\n"

        schema_info += "\n--- CRITICAL DATASET RELATIONSHIP RULES ---\n"
        schema_info += "1. The content pipeline is: raw_videos -> created_assets -> published_posts\n"
        schema_info += "2. created_assets maps to raw_videos via 'Video_ID'. published_posts maps to created_assets via 'Asset_ID'.\n"
        schema_info += "3. IMPORTANT FOR CONVERSION/RETENTION: To group by 'Channel_Name' or 'User_Name' for assets, you MUST NOT group by post_distribution.'Channel_Name'. This drops unpublished assets. You MUST join created_assets ca to raw_videos rv (ca.\"Video_ID\"=rv.\"Video_ID\"), then to raw_video_channel rvc (rvc.\"Video_ID\"=rv.\"Video_ID\") and use rvc.\"Channel_Name\" or users.\"User_Name\".\n"
        schema_info += "4. CARDINALITY RULE: Multiple assets can be bundled into a single published post. To count 'published volume' correctly, ALWAYS use COUNT(DISTINCT pp.\"Asset_ID\") instead of Post_ID. Counting Post_ID will result in deflated conversion rates (e.g. 2% instead of 100%).\n"
        return schema_info

    except Exception as exc:
        return f"Error retrieving schema: {exc}"

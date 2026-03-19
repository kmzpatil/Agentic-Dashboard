"""
Tool: get_frammer_schema
Retrieves the live database schema (tables + columns) via the shared MCP
DatabaseClient.  Works with any SQLAlchemy-supported backend.
Always call this before writing SQL to ensure table and column names are correct.
"""

import json
import logging
from ._db import get_db, get_default_schema

logger = logging.getLogger("frammer.tools.schema")

def get_frammer_schema() -> str:
    """
    Inspect the database and return a human-readable schema string.
    Uses a highly optimized single-query approach for PostgreSQL.
    """
    try:
        db = get_db()
        schema = get_default_schema() or "public"
        
        # Optimized for performance: retrieve all columns in one go if possible
        # Otherwise fall back to the slower per-table inspection
        
        schema_info = "Frammer AI Database Schema:\n"
        
        try:
            # Try optimized PostgreSQL query
            sql = f"""
            SELECT table_name, column_name, data_type 
            FROM information_schema.columns 
            WHERE table_schema = '{schema}'
            AND table_name NOT LIKE 'pg_%'
            AND table_name NOT LIKE 'sql_%'
            ORDER BY table_name, ordinal_position;
            """
            from sqlalchemy import text
            with db.engine.connect() as conn:
                res = conn.execute(text(sql))
                rows = res.fetchall()
            
            if rows:
                current_table = None
                for row in rows:
                    t_name, c_name, d_type = row
                    if t_name != current_table:
                        if current_table:
                            schema_info += "\n"
                        schema_info += f"\nTable: {t_name}\nColumns: "
                        current_table = t_name
                        schema_info += f"{c_name} ({d_type})"
                    else:
                        schema_info += f", {c_name} ({d_type})"
                schema_info += "\n"
            else:
                # Fallback to standard inspection if no rows (e.g. not Postgres or empty)
                return _get_schema_fallback(db, schema)
                
        except Exception as e:
            logger.warning("Optimized schema fetch failed: %s. Falling back.", e)
            return _get_schema_fallback(db, schema)

        schema_info += "\n--- CRITICAL DATASET RELATIONSHIP RULES ---\n"
        schema_info += "1. The content pipeline is: raw_videos -> created_assets -> published_posts\n"
        schema_info += "2. created_assets maps to raw_videos via 'Video_ID'. published_posts maps to created_assets via 'Asset_ID'.\n"
        schema_info += "3. IMPORTANT FOR CONVERSION/RETENTION: To group by 'Channel_Name' or 'User_Name' for assets, you MUST NOT group by post_distribution.'Channel_Name'. This drops unpublished assets. You MUST join created_assets ca to raw_videos rv (ca.\"Video_ID\"=rv.\"Video_ID\"), then to raw_video_channel rvc (rvc.\"Video_ID\"=rv.\"Video_ID\") and use rvc.\"Channel_Name\" or users.\"User_Name\".\n"
        schema_info += "4. CARDINALITY RULE: Multiple assets can be bundled into a single published post. To count 'published volume' correctly, ALWAYS use COUNT(DISTINCT pp.\"Asset_ID\") instead of Post_ID. Counting Post_ID will result in deflated conversion rates (e.g. 2% instead of 100%).\n"

        # Append sample values from cached profile (built once at MCP init)
        try:
            profile = db.get_schema_profile(schema=schema)
            value_lines = []
            for table_name, cols in profile.items():
                for col_name, info in cols.items():
                    vals = info.get("values")
                    if vals:
                        value_lines.append(f"  {table_name}.{col_name}: {vals}")
            if value_lines:
                schema_info += "\n--- TEXT COLUMN SAMPLE VALUES ---\n"
                schema_info += "(Exact strings stored in the DB — always use these when filtering by text)\n"
                schema_info += "\n".join(value_lines) + "\n"
        except Exception as e:
            logger.warning("Could not append sample values to schema: %s", e)

        return schema_info

    except Exception as exc:
        return f"Error retrieving schema: {exc}"

def _get_schema_fallback(db, schema) -> str:
    tables = db.list_tables(schema=schema)
    if not tables:
        return "No tables found in the database."

    schema_info = "Frammer AI Database Schema (Fallback):\n"
    for tbl in tables:
        name = tbl["name"]
        try:
            details = db.describe_table(name, schema=schema)
            col_parts = []
            for col in details.get("columns", []):
                col_parts.append(f"{col['name']} ({col['type']})")
            schema_info += f"\nTable: {name}\nColumns: {', '.join(col_parts)}\n"
        except Exception:
            schema_info += f"\nTable: {name}\nColumns: (could not inspect)\n"
    return schema_info

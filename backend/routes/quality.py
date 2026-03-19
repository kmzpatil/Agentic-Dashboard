"""Data Quality & Governance API endpoints.

Runs live quality checks against the Postgres database and returns
results for the frontend Data Quality dashboard.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from backend.db.pool import query
from backend.middleware.auth import AuthContext, require_auth

router = APIRouter()

# ── Schema definitions (mirrored from database/simulator/quality.py) ──

REQUIRED_COLUMNS: dict[str, list[str]] = {
    "raw_videos": ["Video_ID"],
    "users": ["User_ID"],
    "created_assets": ["Asset_ID"],
    "published_posts": ["Post_ID"],
    "post_distribution": ["Post_ID"],
    "channels": ["Channel_Name"],
    "raw_video_channel": ["Video_ID", "Channel_Name"],
}

PRIMARY_KEYS: dict[str, list[str]] = {
    "raw_videos": ["Video_ID"],
    "users": ["User_ID"],
    "created_assets": ["Asset_ID"],
    "published_posts": ["Post_ID"],
    "post_distribution": ["Post_ID"],
    "channels": ["Channel_Name"],
    "clients": ["Client_Name"],
    "raw_video_channel": ["Video_ID", "Channel_Name"],
}

FOREIGN_KEYS: list[tuple[str, str, str, str]] = [
    ("raw_videos", "User_ID", "users", "User_ID"),
    ("created_assets", "Video_ID", "raw_videos", "Video_ID"),
    ("published_posts", "Asset_ID", "created_assets", "Asset_ID"),
    ("post_distribution", "Post_ID", "published_posts", "Post_ID"),
    ("raw_video_channel", "Video_ID", "raw_videos", "Video_ID"),
    ("raw_video_channel", "Channel_Name", "channels", "Channel_Name"),
]

NON_NEGATIVE_COLUMNS: dict[str, list[str]] = {
    "raw_videos": ["Uploaded_Duration"],
    "created_assets": ["Created_Duration"],
    "published_posts": ["Published_Duration"],
}

DATE_COLUMNS: dict[str, list[str]] = {
    "raw_videos": ["Upload_Date"],
    "created_assets": ["Create_Date"],
    "published_posts": ["Publish_Date"],
}

DIMENSION_COLUMNS: dict[str, list[str]] = {
    "raw_videos": ["Input_Type", "Language"],
    "users": ["Team_Name"],
    "post_distribution": ["Published_Platform"],
}

ALL_TABLES = list(PRIMARY_KEYS.keys())


def _table_exists(table: str) -> bool:
    result = query(
        "SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = %s",
        [table],
    )
    return result.row_count > 0


def _row_count(table: str) -> int:
    result = query(f'SELECT COUNT(*) AS cnt FROM "{table}"')
    return int(result.rows[0]["cnt"]) if result.rows else 0


# ── Endpoint: Overview (health score, KPIs, heatmap, orphan flow, dead ends, suspicious users) ──

@router.get("", include_in_schema=False)
@router.get("/")
def get_quality_overview(auth: AuthContext = Depends(require_auth)):
    try:
        issues: list[dict] = []
        table_row_counts: dict[str, int] = {}

        # Collect row counts
        for table in ALL_TABLES:
            if _table_exists(table):
                table_row_counts[table] = _row_count(table)
            else:
                table_row_counts[table] = 0

        # 1. NULL violations
        null_issues = _check_nulls()
        issues.extend(null_issues)

        # 2. Duplicate PKs
        dup_issues = _check_duplicate_pks()
        issues.extend(dup_issues)

        # 3. FK violations (orphans)
        fk_issues = _check_fk_violations()
        issues.extend(fk_issues)

        # 4. Negative values
        neg_issues = _check_negative_values()
        issues.extend(neg_issues)

        # 5. Invalid dates
        date_issues = _check_invalid_dates()
        issues.extend(date_issues)

        # 6. Unknown/contamination values
        unknown_issues = _check_unknown_values()
        issues.extend(unknown_issues)

        # Per-table health scores
        table_scores: dict[str, dict] = {}
        for table in ALL_TABLES:
            t_issues = [i for i in issues if i["table"] == table]
            rc = table_row_counts.get(table, 0)
            score = max(0.0, 1.0 - len(t_issues) / max(rc, 1)) * 100
            table_scores[table] = {
                "row_count": rc,
                "issue_count": len(t_issues),
                "score": round(score, 1),
            }

        # Overall health score
        total_issues = len(issues)
        total_rows = sum(table_row_counts.values())
        overall_score = max(0.0, 1.0 - total_issues / max(total_rows, 1)) * 100

        # Count by check type
        check_counts: dict[str, int] = {}
        for issue in issues:
            check_counts[issue["check"]] = check_counts.get(issue["check"], 0) + 1

        # Orphan counts per FK link
        orphan_links = _get_orphan_link_counts()

        # Contamination heatmap
        heatmap = _get_contamination_heatmap()

        # Dead ends
        dead_ends = _get_dead_ends()

        # Suspicious users
        suspicious_users = _get_suspicious_users()

        return {
            "overall_score": round(overall_score, 1),
            "total_issues": total_issues,
            "total_rows": total_rows,
            "check_counts": check_counts,
            "table_scores": table_scores,
            "orphan_links": orphan_links,
            "heatmap": heatmap,
            "dead_ends": dead_ends,
            "suspicious_users": suspicious_users,
        }
    except Exception as error:
        return JSONResponse(status_code=500, content={"error": str(error)})


# ── Endpoint: Issues list (paginated) ──

@router.get("/issues")
def get_quality_issues(
    table: Optional[str] = None,
    check_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    auth: AuthContext = Depends(require_auth),
):
    try:
        all_issues: list[dict] = []
        all_issues.extend(_check_nulls())
        all_issues.extend(_check_duplicate_pks())
        all_issues.extend(_check_fk_violations())
        all_issues.extend(_check_negative_values())
        all_issues.extend(_check_invalid_dates())
        all_issues.extend(_check_unknown_values())

        # Filter
        if table:
            all_issues = [i for i in all_issues if i["table"] == table]
        if check_type:
            all_issues = [i for i in all_issues if i["check"] == check_type]

        # Assign severity
        for issue in all_issues:
            issue["severity"] = _classify_severity(issue)

        total = len(all_issues)
        page = all_issues[offset : offset + limit]

        return {
            "issues": page,
            "total": total,
            "limit": limit,
            "offset": offset,
        }
    except Exception as error:
        return JSONResponse(status_code=500, content={"error": str(error)})


# ── Check functions ──

def _check_nulls() -> list[dict]:
    issues: list[dict] = []
    for table, cols in REQUIRED_COLUMNS.items():
        if not _table_exists(table):
            continue
        for col in cols:
            result = query(
                f'SELECT COUNT(*) AS cnt FROM "{table}" WHERE "{col}" IS NULL'
            )
            cnt = int(result.rows[0]["cnt"]) if result.rows else 0
            if cnt > 0:
                issues.append({
                    "table": table,
                    "check": "NULL_VIOLATION",
                    "column": col,
                    "count": cnt,
                    "message": f"Required column '{col}' is NULL in {cnt} rows",
                })
    return issues


def _check_duplicate_pks() -> list[dict]:
    issues: list[dict] = []
    for table, pk_cols in PRIMARY_KEYS.items():
        if not _table_exists(table):
            continue
        cols_sql = ", ".join(f'"{c}"' for c in pk_cols)
        result = query(
            f'SELECT {cols_sql}, COUNT(*) AS cnt FROM "{table}" '
            f"GROUP BY {cols_sql} HAVING COUNT(*) > 1"
        )
        for row in result.rows:
            cnt = int(row["cnt"])
            pk_vals = {c: row[c] for c in pk_cols}
            issues.append({
                "table": table,
                "check": "DUPLICATE_PK",
                "column": ", ".join(pk_cols),
                "value": str(pk_vals),
                "count": cnt,
                "message": f"Duplicate PK {pk_vals} appears {cnt} times",
            })
    return issues


def _check_fk_violations() -> list[dict]:
    issues: list[dict] = []
    for child_tbl, child_col, parent_tbl, parent_col in FOREIGN_KEYS:
        if not _table_exists(child_tbl) or not _table_exists(parent_tbl):
            continue
        result = query(
            f'SELECT COUNT(*) AS cnt FROM "{child_tbl}" c '
            f'LEFT JOIN "{parent_tbl}" p ON c."{child_col}" = p."{parent_col}" '
            f'WHERE p."{parent_col}" IS NULL AND c."{child_col}" IS NOT NULL'
        )
        cnt = int(result.rows[0]["cnt"]) if result.rows else 0
        if cnt > 0:
            issues.append({
                "table": child_tbl,
                "check": "FK_VIOLATION",
                "column": child_col,
                "count": cnt,
                "references": f"{parent_tbl}.{parent_col}",
                "message": f"Orphan FK: {cnt} rows in {child_tbl}.{child_col} not found in {parent_tbl}.{parent_col}",
            })
    return issues


def _check_negative_values() -> list[dict]:
    issues: list[dict] = []
    for table, cols in NON_NEGATIVE_COLUMNS.items():
        if not _table_exists(table):
            continue
        for col in cols:
            result = query(
                f'SELECT COUNT(*) AS cnt FROM "{table}" WHERE "{col}" < 0'
            )
            cnt = int(result.rows[0]["cnt"]) if result.rows else 0
            if cnt > 0:
                issues.append({
                    "table": table,
                    "check": "NEGATIVE_VALUE",
                    "column": col,
                    "count": cnt,
                    "message": f"Negative value in {table}.{col} for {cnt} rows",
                })
    return issues


def _check_invalid_dates() -> list[dict]:
    issues: list[dict] = []
    for table, cols in DATE_COLUMNS.items():
        if not _table_exists(table):
            continue
        for col in cols:
            # Check for values that don't match YYYY-MM-DD pattern
            result = query(
                f"""SELECT COUNT(*) AS cnt FROM "{table}"
                    WHERE "{col}" IS NOT NULL
                    AND "{col}" !~ '^[0-9]{{4}}-[0-9]{{2}}-[0-9]{{2}}$'"""
            )
            cnt = int(result.rows[0]["cnt"]) if result.rows else 0
            if cnt > 0:
                issues.append({
                    "table": table,
                    "check": "INVALID_DATE",
                    "column": col,
                    "count": cnt,
                    "message": f"Invalid date format in {table}.{col} for {cnt} rows (expected YYYY-MM-DD)",
                })
    return issues


def _check_unknown_values() -> list[dict]:
    issues: list[dict] = []
    for table, cols in DIMENSION_COLUMNS.items():
        if not _table_exists(table):
            continue
        for col in cols:
            result = query(
                f"""SELECT COUNT(*) AS cnt FROM "{table}"
                    WHERE LOWER(CAST("{col}" AS TEXT)) IN ('unknown', 'n/a', 'none', '')
                    OR "{col}" IS NULL"""
            )
            cnt = int(result.rows[0]["cnt"]) if result.rows else 0
            if cnt > 0:
                issues.append({
                    "table": table,
                    "check": "UNKNOWN_VALUE",
                    "column": col,
                    "count": cnt,
                    "message": f"Unknown/empty value in {table}.{col} for {cnt} rows",
                })
    return issues


# ── Helper: orphan link counts for the Broken Reference Chains diagram ──

def _get_orphan_link_counts() -> list[dict]:
    links = []
    for child_tbl, child_col, parent_tbl, parent_col in FOREIGN_KEYS:
        if not _table_exists(child_tbl) or not _table_exists(parent_tbl):
            links.append({
                "from": parent_tbl, "to": child_tbl,
                "child_col": child_col, "parent_col": parent_col,
                "orphans": 0,
            })
            continue
        result = query(
            f'SELECT COUNT(*) AS cnt FROM "{child_tbl}" c '
            f'LEFT JOIN "{parent_tbl}" p ON c."{child_col}" = p."{parent_col}" '
            f'WHERE p."{parent_col}" IS NULL AND c."{child_col}" IS NOT NULL'
        )
        cnt = int(result.rows[0]["cnt"]) if result.rows else 0
        links.append({
            "from": parent_tbl, "to": child_tbl,
            "child_col": child_col, "parent_col": parent_col,
            "orphans": cnt,
        })
    return links


# ── Helper: contamination heatmap ──

def _get_contamination_heatmap() -> list[dict]:
    """For each table, compute % of NULL or 'Unknown' in dimension columns."""
    all_dim_cols = ["Input_Type", "Language", "Team_Name", "Channel_Name", "Published_Platform"]

    # Map which columns belong to which tables
    table_dim_map = {
        "raw_videos": ["Input_Type", "Language"],
        "created_assets": [],
        "published_posts": [],
        "post_distribution": ["Published_Platform"],
        "users": ["Team_Name"],
        "channels": ["Channel_Name"],
        "raw_video_channel": ["Channel_Name"],
        "clients": [],
    }

    rows_out = []
    for table in ALL_TABLES:
        if not _table_exists(table):
            continue
        rc = _row_count(table)
        row = {"table": table}
        available_cols = table_dim_map.get(table, [])
        for col in all_dim_cols:
            if col not in available_cols or rc == 0:
                row[col] = None
                continue
            result = query(
                f"""SELECT COUNT(*) AS cnt FROM "{table}"
                    WHERE "{col}" IS NULL
                    OR LOWER(CAST("{col}" AS TEXT)) IN ('unknown', 'n/a', 'none', '')"""
            )
            cnt = int(result.rows[0]["cnt"]) if result.rows else 0
            row[col] = round((cnt / rc) * 100, 1)
        rows_out.append(row)
    return rows_out


# ── Helper: dead ends ──

def _get_dead_ends() -> list[dict]:
    """Find dimension values with uploads but zero publishes."""
    dead_ends = []

    # By Language
    result = query("""
        SELECT rv."Language" AS name, COUNT(DISTINCT rv."Video_ID") AS uploads
        FROM raw_videos rv
        WHERE rv."Language" IS NOT NULL
        GROUP BY rv."Language"
        HAVING COUNT(DISTINCT rv."Video_ID") > 0
    """)
    for row in result.rows:
        lang = row["name"]
        # Check if any published posts exist for this language
        pub = query("""
            SELECT COUNT(DISTINCT pp."Post_ID") AS cnt
            FROM raw_videos rv
            JOIN created_assets ca ON ca."Video_ID" = rv."Video_ID"
            JOIN published_posts pp ON pp."Asset_ID" = ca."Asset_ID"
            WHERE rv."Language" = %s
        """, [lang])
        pub_cnt = int(pub.rows[0]["cnt"]) if pub.rows else 0
        if pub_cnt == 0:
            dead_ends.append({
                "category": "Languages",
                "name": lang,
                "uploads": int(row["uploads"]),
                "published": 0,
            })

    # By Input_Type
    result = query("""
        SELECT rv."Input_Type" AS name, COUNT(DISTINCT rv."Video_ID") AS uploads
        FROM raw_videos rv
        WHERE rv."Input_Type" IS NOT NULL
        GROUP BY rv."Input_Type"
        HAVING COUNT(DISTINCT rv."Video_ID") > 0
    """)
    for row in result.rows:
        itype = row["name"]
        pub = query("""
            SELECT COUNT(DISTINCT pp."Post_ID") AS cnt
            FROM raw_videos rv
            JOIN created_assets ca ON ca."Video_ID" = rv."Video_ID"
            JOIN published_posts pp ON pp."Asset_ID" = ca."Asset_ID"
            WHERE rv."Input_Type" = %s
        """, [itype])
        pub_cnt = int(pub.rows[0]["cnt"]) if pub.rows else 0
        if pub_cnt == 0:
            dead_ends.append({
                "category": "Input Types",
                "name": itype,
                "uploads": int(row["uploads"]),
                "published": 0,
            })

    # By Channel
    result = query("""
        SELECT rvc."Channel_Name" AS name, COUNT(DISTINCT rvc."Video_ID") AS uploads
        FROM raw_video_channel rvc
        GROUP BY rvc."Channel_Name"
        HAVING COUNT(DISTINCT rvc."Video_ID") > 0
    """)
    for row in result.rows:
        ch = row["name"]
        pub = query("""
            SELECT COUNT(DISTINCT pp."Post_ID") AS cnt
            FROM raw_video_channel rvc
            JOIN raw_videos rv ON rv."Video_ID" = rvc."Video_ID"
            JOIN created_assets ca ON ca."Video_ID" = rv."Video_ID"
            JOIN published_posts pp ON pp."Asset_ID" = ca."Asset_ID"
            JOIN post_distribution pd ON pd."Post_ID" = pp."Post_ID"
            WHERE rvc."Channel_Name" = %s
        """, [ch])
        pub_cnt = int(pub.rows[0]["cnt"]) if pub.rows else 0
        if pub_cnt == 0:
            dead_ends.append({
                "category": "Channels",
                "name": ch,
                "uploads": int(row["uploads"]),
                "published": 0,
            })

    # By Platform
    result = query("""
        SELECT pd."Published_Platform" AS name, COUNT(DISTINCT pd."Post_ID") AS uploads
        FROM post_distribution pd
        WHERE pd."Published_Platform" IS NOT NULL
        GROUP BY pd."Published_Platform"
        HAVING COUNT(DISTINCT pd."Post_ID") > 0
    """)
    # For platforms, "dead end" means the platform exists in distribution but with 0
    # valid published_posts backing it. Since post_distribution already implies publish,
    # we check for platforms that exist but have NULL/broken URLs.
    # Actually for platforms — they all have publishes by definition (they're in post_distribution).
    # So instead, check platforms with 0 published_posts linked.
    result = query("""
        SELECT pd."Published_Platform" AS name, COUNT(*) AS total,
               COUNT(pp."Post_ID") AS valid_posts
        FROM post_distribution pd
        LEFT JOIN published_posts pp ON pd."Post_ID" = pp."Post_ID"
        WHERE pd."Published_Platform" IS NOT NULL
        GROUP BY pd."Published_Platform"
    """)
    for row in result.rows:
        valid = int(row["valid_posts"]) if row["valid_posts"] else 0
        total = int(row["total"])
        if valid == 0 and total > 0:
            dead_ends.append({
                "category": "Platforms",
                "name": row["name"],
                "uploads": total,
                "published": 0,
            })

    return dead_ends


# ── Helper: suspicious users ──

def _get_suspicious_users() -> list[dict]:
    suspects = []

    # 1. Test/mock/QA accounts
    result = query("""
        SELECT u."User_ID", u."User_Name", u."Team_Name",
               COUNT(DISTINCT rv."Video_ID") AS uploads
        FROM users u
        LEFT JOIN raw_videos rv ON rv."User_ID" = u."User_ID"
        WHERE LOWER(u."User_Name") SIMILAR TO '%%(test|delete|mock|qa|dummy|deleteme)%%'
        GROUP BY u."User_ID", u."User_Name", u."Team_Name"
    """)
    for row in result.rows:
        # Get created & published counts
        counts = _get_user_pipeline_counts(row["User_ID"])
        suspects.append({
            "name": row["User_Name"],
            "reason": "Test/QA account in production data",
            "uploads": int(row["uploads"] or 0),
            "created": counts["created"],
            "published": counts["published"],
            "severity": "Critical",
        })

    # 2. Users where created > uploaded (impossible anomaly)
    result = query("""
        SELECT u."User_ID", u."User_Name",
               COUNT(DISTINCT rv."Video_ID") AS uploads,
               COUNT(DISTINCT ca."Asset_ID") AS created
        FROM users u
        LEFT JOIN raw_videos rv ON rv."User_ID" = u."User_ID"
        LEFT JOIN created_assets ca ON ca."Video_ID" = rv."Video_ID"
        GROUP BY u."User_ID", u."User_Name"
        HAVING COUNT(DISTINCT ca."Asset_ID") > COUNT(DISTINCT rv."Video_ID")
            AND COUNT(DISTINCT rv."Video_ID") > 0
    """)
    existing_names = {s["name"] for s in suspects}
    for row in result.rows:
        if row["User_Name"] in existing_names:
            continue
        counts = _get_user_pipeline_counts(row["User_ID"])
        suspects.append({
            "name": row["User_Name"],
            "reason": f"Anomaly: created ({int(row['created'])}) > uploaded ({int(row['uploads'])})",
            "uploads": int(row["uploads"] or 0),
            "created": counts["created"],
            "published": counts["published"],
            "severity": "Warning",
        })

    # 3. High volume, zero output
    result = query("""
        SELECT u."User_ID", u."User_Name",
               COUNT(DISTINCT rv."Video_ID") AS uploads
        FROM users u
        JOIN raw_videos rv ON rv."User_ID" = u."User_ID"
        GROUP BY u."User_ID", u."User_Name"
        HAVING COUNT(DISTINCT rv."Video_ID") > 20
    """)
    for row in result.rows:
        if row["User_Name"] in existing_names:
            continue
        counts = _get_user_pipeline_counts(row["User_ID"])
        if counts["published"] == 0:
            suspects.append({
                "name": row["User_Name"],
                "reason": f"High volume ({int(row['uploads'])} uploads) with 0 publishes",
                "uploads": int(row["uploads"] or 0),
                "created": counts["created"],
                "published": 0,
                "severity": "Warning",
            })
            existing_names.add(row["User_Name"])

    return suspects


def _get_user_pipeline_counts(user_id: int) -> dict:
    result = query("""
        SELECT COUNT(DISTINCT ca."Asset_ID") AS created,
               COUNT(DISTINCT pp."Post_ID") AS published
        FROM raw_videos rv
        LEFT JOIN created_assets ca ON ca."Video_ID" = rv."Video_ID"
        LEFT JOIN published_posts pp ON pp."Asset_ID" = ca."Asset_ID"
        WHERE rv."User_ID" = %s
    """, [user_id])
    if result.rows:
        return {
            "created": int(result.rows[0]["created"] or 0),
            "published": int(result.rows[0]["published"] or 0),
        }
    return {"created": 0, "published": 0}


def _classify_severity(issue: dict) -> str:
    check = issue.get("check", "")
    count = issue.get("count", 0)
    if check == "DUPLICATE_PK":
        return "Critical"
    if check == "FK_VIOLATION" and issue.get("table") == "published_posts":
        return "Critical"
    if check == "NULL_VIOLATION":
        return "Critical" if count > 10 else "Warning"
    if check == "NEGATIVE_VALUE":
        return "Warning"
    if check == "INVALID_DATE":
        return "Warning" if count > 5 else "Info"
    if check == "UNKNOWN_VALUE":
        return "Info"
    return "Info"

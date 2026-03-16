
import json
import os
from datetime import date, datetime, time
from decimal import Decimal
from pathlib import Path

import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv

load_dotenv()


def _serialise(obj):
    """JSON serialiser for postgres types that aren't natively JSON-serialisable."""
    if isinstance(obj, (datetime, date, time)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, memoryview):
        return "<binary>"
    raise TypeError(f"Not serialisable: {type(obj)}")


def main():
    try:
        conn = psycopg2.connect(
            host=os.getenv("POSTGRES_HOST", "127.0.0.1"),
            port=int(os.getenv("POSTGRES_PORT", 5432)),
            dbname=os.getenv("POSTGRES_DB", "frammer_database"),
            user=os.getenv("POSTGRES_USER", "postgres"),
            password=os.getenv("POSTGRES_PASSWORD", "1234567890"),
            connect_timeout=5,
        )
    except Exception as e:
        print(json.dumps({"error": str(e)}, indent=2))
        return

    cur = conn.cursor()

    # 1. List all base tables in public schema
    cur.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_type = 'BASE TABLE'
        ORDER BY table_name;
    """)
    tables = [row[0] for row in cur.fetchall()]

    output = {
        "database": os.getenv("POSTGRES_DB", "frammer_database"),
        "extracted_at": datetime.now().isoformat(),
        "table_count": len(tables),
        "tables": {},
    }

    for table in tables:
        # 2. Column info
        cur.execute("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_name = %s
              AND table_schema = 'public'
            ORDER BY ordinal_position;
        """, (table,))
        cols = cur.fetchall()
        col_names = [c[0] for c in cols]
        columns = [
            {
                "name": c[0],
                "type": c[1],
                "nullable": c[2] == "YES",
                "default": c[3],
            }
            for c in cols
        ]

        # 3. Row count
        try:
            cur.execute(sql.SQL("SELECT COUNT(*) FROM {}").format(sql.Identifier(table)))
            row_count = cur.fetchone()[0]
        except Exception:
            conn.rollback()
            cur = conn.cursor()
            row_count = None

        # 4. Sample rows (1 row)
        sample = []
        try:
            cur.execute(sql.SQL("SELECT * FROM {} LIMIT 1").format(sql.Identifier(table)))
            rows = cur.fetchall()
            for row in rows:
                sample.append(dict(zip(col_names, row)))
        except Exception as e:
            conn.rollback()
            cur = conn.cursor()
            sample = [{"error": str(e)}]

        # 5. Unique values per column
        for col in columns:
            col_name = col["name"]
            try:
                cur.execute(
                    sql.SQL("SELECT COUNT(DISTINCT {}) FROM {}").format(
                        sql.Identifier(col_name), sql.Identifier(table)
                    )
                )
                unique_count = cur.fetchone()[0]
                col["unique_count"] = unique_count

                if unique_count is not None and 0 < unique_count < 20:
                    cur.execute(
                        sql.SQL("SELECT DISTINCT {} FROM {} WHERE {} IS NOT NULL").format(
                            sql.Identifier(col_name), sql.Identifier(table), sql.Identifier(col_name)
                        )
                    )
                    col["unique_values"] = [r[0] for r in cur.fetchall()]
            except Exception:
                conn.rollback()
                cur = conn.cursor()

        output["tables"][table] = {
            "row_count": row_count,
            "columns": columns,
            "sample": sample,
        }

    cur.close()
    conn.close()

    # Write to schema_data/schema.json
    out_dir = Path(__file__).parent / "schema_data"
    out_dir.mkdir(exist_ok=True)
    out_file = out_dir / "schema.json"
    out_file.write_text(json.dumps(output, indent=2, default=_serialise), encoding="utf-8")
    print(f"✓ Written to {out_file}")
    print(f"  Tables: {len(tables)}")
    for tbl, info in output["tables"].items():
        print(f"  {tbl}: {info['row_count']} rows, {len(info['columns'])} columns")


if __name__ == "__main__":
    main()

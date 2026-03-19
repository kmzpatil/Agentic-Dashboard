"""
Integration tests for the Database Simulator (Postgres-backed).
"""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from sqlalchemy import text
from database.simulator.engine import SimulatorEngine


def _has_pg_env() -> bool:
    return bool(os.getenv("PGHOST") and os.getenv("PGPORT") and os.getenv("PGUSER") and os.getenv("PGDATABASE"))


@unittest.skipUnless(_has_pg_env(), "Postgres env not configured")
class TestSchemaCreation(unittest.TestCase):
    def setUp(self):
        self.engine = SimulatorEngine()

    def test_tables_exist(self):
        tables = self.engine.get_tables()
        table_names = {t["name"] for t in tables}
        expected = {
            "clients",
            "users",
            "channels",
            "raw_videos",
            "raw_video_channel",
            "created_assets",
            "published_posts",
            "post_distribution",
        }
        self.assertTrue(expected.issubset(table_names))


@unittest.skipUnless(_has_pg_env(), "Postgres env not configured")
class TestSeeding(unittest.TestCase):
    def setUp(self):
        self.engine = SimulatorEngine()
        self.engine.reset()
        self.engine.seed(count=3)

    def tearDown(self):
        self.engine.reset()

    def test_tables_have_rows(self):
        state = self.engine.get_state()
        for table, count in state["tables"].items():
            if table in ("clients", "channels", "users"):
                self.assertGreaterEqual(count, 1, f"{table} should have seeded rows")


@unittest.skipUnless(_has_pg_env(), "Postgres env not configured")
class TestInsertLogging(unittest.TestCase):
    def setUp(self):
        self.engine = SimulatorEngine()
        self.engine.reset()

    def tearDown(self):
        self.engine.reset()

    def test_insert_is_logged(self):
        self.engine.seed(count=1)
        logs = self.engine.get_logs(limit=50)
        insert_logs = [l for l in logs if l["operation"] == "INSERT"]
        self.assertGreater(len(insert_logs), 0)
        successes = [l for l in insert_logs if l["status"] == "SUCCESS"]
        self.assertGreater(len(successes), 0)


@unittest.skipUnless(_has_pg_env(), "Postgres env not configured")
class TestQualityChecks(unittest.TestCase):
    def setUp(self):
        self.engine = SimulatorEngine()
        self.engine.reset()
        self.engine.seed(count=2)

    def tearDown(self):
        self.engine.reset()

    def test_invalid_date_detected(self):
        # Resolve engine for the test
        from database.bootstrap_postgres import resolve_postgres_engine
        pg_engine = resolve_postgres_engine()
        
        with pg_engine.connect() as conn:
            conn.execute(text(
                "INSERT INTO raw_videos (Video_ID, User_ID, Headline, Source_URL, Upload_Date, Input_Type, Language, Uploaded_Duration) "
                "VALUES (:vid, :uid, :head, :url, :date, :type, :lang, :dur)"
            ), {
                "vid": 999999,
                "uid": 1,
                "head": "SIM: BadDate",
                "url": "http://x.com",
                "date": "not-a-date",
                "type": "Uploaded",
                "lang": "English",
                "dur": 100
            })
            conn.commit()

        report = self.engine.get_quality_report()
        raw_video_issues = report["tables"].get("raw_videos", {}).get("issues", [])
        date_issues = [i for i in raw_video_issues if i["check"] == "INVALID_DATE"]
        self.assertGreater(len(date_issues), 0)


if __name__ == "__main__":
    unittest.main()

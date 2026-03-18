import json
import unittest
from unittest.mock import patch

from backend.middleware.auth import AuthContext
from backend.queries.analytics_shared import build_access_filter
from backend.queries.funnel_queries import (
    get_breakdown_query,
    get_client_outcome_platform_sankey_query,
    get_filter_options_channels_query,
    get_heatmap_query,
    get_publish_by_client_query,
)
from backend.routes import funnel as funnel_routes


class _MockResult:
    def __init__(self, rows):
        self.rows = rows
        self.row_count = len(rows)


class FunnelHardeningTests(unittest.TestCase):
    def test_breakdown_client_uses_channel_fallback_and_channel_join(self):
        filter_data = {"join": "", "where": "", "predicates": [], "next_index": 1}
        sql = get_breakdown_query(filter_data, "client")

        self.assertIn('COALESCE(ch."Client_Name", u."Client_Name")', sql)
        self.assertIn("'Unknown'", sql)
        self.assertIn('LEFT JOIN channels ch ON ch."Channel_Name" = rvc."Channel_Name"', sql)

    def test_client_aggregates_use_consistent_client_fallback(self):
        filter_data = {"join": "", "where": "", "predicates": [], "next_index": 1}

        heatmap_sql = get_heatmap_query(filter_data)
        publish_by_client_sql = get_publish_by_client_query(filter_data)
        sankey_sql = get_client_outcome_platform_sankey_query(filter_data)

        for sql in (heatmap_sql, publish_by_client_sql, sankey_sql):
            self.assertIn('COALESCE(ch."Client_Name", u."Client_Name")', sql)
            self.assertIn('MIN(COALESCE', sql)
            self.assertIn("AS client_name", sql)

    def test_filter_options_channels_keeps_user_scope_on_rv_alias(self):
        auth = AuthContext(
            auth_user_id="auth-1",
            username="test-user",
            role="user",
            client_name=None,
            user_id=123,
        )
        access_filter = build_access_filter(auth, 1, "rv")

        sql = get_filter_options_channels_query(access_filter)

        self.assertIn('rv."User_ID" = $1', sql)
        self.assertNotIn('rvc."User_ID" = $1', sql)

    def test_filter_options_redacts_internal_errors(self):
        auth = AuthContext(
            auth_user_id="auth-1",
            username="admin",
            role="website_admin",
            client_name=None,
            user_id=None,
        )

        with patch.object(funnel_routes, "query", side_effect=RuntimeError("db internals should not leak")):
            response = funnel_routes.get_filter_options(auth=auth)

        self.assertEqual(response.status_code, 500)
        payload = json.loads(response.body.decode("utf-8"))
        self.assertEqual(payload["error"], "Failed to load funnel filter options")
        self.assertNotIn("db internals", response.body.decode("utf-8"))

    def test_funnel_masks_client_name_for_non_admin_in_absolute_waste(self):
        auth = AuthContext(
            auth_user_id="auth-2",
            username="scoped-user",
            role="user",
            client_name=None,
            user_id=77,
        )

        def query_side_effect(sql, _params):
            rows_by_sql = {
                "STAGE": [{"uploaded_count": 5, "processed_count": 5, "created_count": 4, "published_count": 2}],
                "PIPE": [{
                    "uploads": 5,
                    "assets_created": 4,
                    "posts_published": 2,
                    "platform_posts": 3,
                    "assets_multiplier": 0.8,
                    "not_published_pct": 50,
                    "platform_multiplier": 1.5,
                }],
                "KPI": [{
                    "publish_conversion_pct": 50,
                    "avg_assets_per_upload": 0.8,
                    "upload_failure_rate": 20,
                    "waste_index_seconds": 12,
                    "avg_lag_days": 3,
                }],
                "BREAK": [{"label": "A", "uploaded_count": 5, "created_count": 4, "published_count": 2, "conversion": 50}],
                "COMP": [],
                "CHAN": [{"channel_name": "Channel A", "client_name": "Sensitive Client", "videos_assigned": 5, "yield_pct": 40}],
                "WASTE": [{"channel_name": "Channel A", "client_name": "Sensitive Client", "videos_assigned": 5, "yield_pct": 40, "waste_slots": 3}],
                "LAG": [],
                "TEAM_EFF": [],
                "TEAM_VOL": [],
                "TEAM_WASTE": [],
                "OUT_SURV": [],
                "PUB_CLIENT": [],
                "HEAT": [],
                "JOURNEY": [],
                "MIX": [],
            }
            if sql not in rows_by_sql:
                raise AssertionError(f"Unexpected SQL key in test: {sql}")
            return _MockResult(rows_by_sql[sql])

        with (
            patch.object(funnel_routes, "get_stage_counts_query", return_value="STAGE"),
            patch.object(funnel_routes, "get_pipeline_strip_query", return_value="PIPE"),
            patch.object(funnel_routes, "get_kpis_query", return_value="KPI"),
            patch.object(funnel_routes, "get_breakdown_query", return_value="BREAK"),
            patch.object(funnel_routes, "get_client_outcome_platform_sankey_query", return_value="COMP"),
            patch.object(funnel_routes, "get_channel_efficiency_query", return_value="CHAN"),
            patch.object(funnel_routes, "get_absolute_waste_query", return_value="WASTE"),
            patch.object(funnel_routes, "get_publish_lag_distribution_query", return_value="LAG"),
            patch.object(funnel_routes, "get_team_efficiency_query", return_value="TEAM_EFF"),
            patch.object(funnel_routes, "get_team_volume_yield_query", return_value="TEAM_VOL"),
            patch.object(funnel_routes, "get_team_absolute_waste_query", return_value="TEAM_WASTE"),
            patch.object(funnel_routes, "get_output_type_survival_query", return_value="OUT_SURV"),
            patch.object(funnel_routes, "get_publish_by_client_query", return_value="PUB_CLIENT"),
            patch.object(funnel_routes, "get_heatmap_query", return_value="HEAT"),
            patch.object(funnel_routes, "get_journey_query", return_value="JOURNEY"),
            patch.object(funnel_routes, "get_mix_query", return_value="MIX"),
            patch.object(funnel_routes, "query", side_effect=query_side_effect),
        ):
            payload = funnel_routes.get_funnel(auth=auth, breakdown="channel")

        self.assertEqual(payload["channelEfficiency"][0]["client_name"], None)
        self.assertEqual(payload["absoluteWasteTopChannels"][0]["client_name"], None)


if __name__ == "__main__":
    unittest.main()
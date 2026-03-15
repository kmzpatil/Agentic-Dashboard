import unittest

from backend.analytics.artifacts import build_assistant_artifacts, build_dataset


class ArtifactPlannerTests(unittest.TestCase):
    def test_build_dataset_infers_schema(self):
        dataset = build_dataset(
            "uploaded_count_month",
            "Uploads",
            [{"period": "2026-01-01", "value": 12}, {"period": "2026-02-01", "value": 16}],
        )

        self.assertEqual(dataset.id, "uploaded_count_month")
        self.assertEqual([column.key for column in dataset.columns], ["period", "value"])
        self.assertEqual(dataset.columns[0].type, "date")
        self.assertEqual(dataset.columns[1].type, "number")

    def test_build_assistant_artifacts_creates_chart_and_table(self):
        datasets, artifacts = build_assistant_artifacts(
            [{"channel": "YouTube", "published_count": 32}, {"channel": "LinkedIn", "published_count": 18}],
            sql="SELECT channel, published_count FROM metrics",
            title="Publishing",
        )

        self.assertEqual(len(datasets), 1)
        self.assertGreaterEqual(len(artifacts), 2)
        self.assertEqual(artifacts[0].kind, "chart")
        self.assertEqual(artifacts[-1].kind, "table")


if __name__ == "__main__":
    unittest.main()

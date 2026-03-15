import os
import unittest
from unittest.mock import patch

from backend.config.env import get_config


class EnvConfigTests(unittest.TestCase):
    def tearDown(self):
        get_config.cache_clear()

    def test_config_reads_shared_env_groups(self):
        with patch.dict(
            os.environ,
            {
                "PORT": "4100",
                "PGHOST": "localhost",
                "PGPORT": "5433",
                "PGUSER": "postgres",
                "PGDATABASE": "frammer_database",
                "PGPASSWORD": "",
                "FEATURE_MCP_ENABLED": "true",
                "FEATURE_LABS_ENABLED": "false",
                "AZURE_OPENAI_ENDPOINT": "https://example.openai.azure.com/",
                "AZURE_OPENAI_API_KEY": "test-key",
                "AZURE_DEPLOYMENT": "o4-mini",
            },
            clear=True,
        ):
            get_config.cache_clear()
            config = get_config()

        self.assertEqual(config.port, 4100)
        self.assertEqual(config.db.port, 5433)
        self.assertTrue(config.features.mcp_enabled)
        self.assertFalse(config.features.labs_enabled)
        self.assertTrue(config.ai.configured)


if __name__ == "__main__":
    unittest.main()

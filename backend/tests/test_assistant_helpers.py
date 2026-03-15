import unittest

from backend.assistant.service import _extract_rows, _normalise_filter_prompt


class AssistantHelperTests(unittest.TestCase):
    def test_filter_prompt_ignores_empty_values(self):
        prompt = _normalise_filter_prompt({"client": "Acme", "channel": "", "language": "All"})
        self.assertEqual(prompt, "[Filters: client=Acme] ")

    def test_extract_rows_uses_first_dataset_list(self):
        rows = _extract_rows({"query_result": [{"value": 1}], "other": []})
        self.assertEqual(rows, [{"value": 1}])


if __name__ == "__main__":
    unittest.main()

import sys
import os
from pathlib import Path
import json

# Add agent dir to path
AGENT_DIR = Path("c:/Users/kmzpa/Desktop/asdfghjkl/gcdata/agent")
sys.path.insert(0, str(AGENT_DIR))

# Mock LLM and database to avoid external calls if possible
# But we mostly want to see if the functions can even run.

def test_classify():
    try:
        from agent import _classify
        # We need _fast_client to exist.
        print("Import _classify successful")
        # result = _classify("Hello") # This will likely fail if no API key
    except Exception as e:
        import traceback
        traceback.print_exc()

def test_format_bug():
    try:
        template = "Schema: {schema_block}, Plan: {plan_block}, Memory: {memory_block}, Metrics: {metrics_block}"
        res = template.format(
            schema_block="Tables { 'rv' }",
            plan_block="Step 1",
            memory_block="...",
            metrics_block="..."
        )
        print("Format successful")
    except KeyError as e:
        print(f"Format failed with KeyError: {e}")

if __name__ == "__main__":
    test_classify()
    test_format_bug()

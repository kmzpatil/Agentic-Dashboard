import sys
import os
from pathlib import Path

# Add agent dir to path
AGENT_DIR = Path("c:/Users/kmzpa/Desktop/asdfghjkl/gcdata/agent")
sys.path.insert(0, str(AGENT_DIR))

def trace_import(module_name):
    print(f"Trimming import: {module_name}...")
    try:
        __import__(module_name)
        print(f"DONE: {module_name}")
    except Exception as e:
        print(f"FAILED: {module_name}: {e}")

print("--- STARTING TRACE ---")
trace_import("dotenv")
trace_import("json")
trace_import("logging")
trace_import("pathlib")
trace_import("typing")
trace_import("re")
trace_import("google.genai")
trace_import("uuid")
trace_import("client")
trace_import("mcp_server.config")
trace_import("mcp_server.database")
trace_import("tools.metric_definitions")
trace_import("tools.chart")
trace_import("tools")
trace_import("tools.sql_query")
print("--- END TRACE ---")

import sys
import os
from pathlib import Path

print("Trace: Initializing...")
# Add agent dir to path
AGENT_DIR = Path("c:/Users/kmzpa/Desktop/asdfghjkl/gcdata/agent")
sys.path.insert(0, str(AGENT_DIR))

print("Trace: Importing agent...")
try:
    import agent
    print("Trace: Agent imported successfully.")
except Exception as e:
    print(f"Trace: Import failed with error: {e}")
    import traceback
    traceback.print_exc()

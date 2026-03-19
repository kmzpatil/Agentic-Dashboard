# This file intentionally left minimal.
# When api_server.py runs from agent/ directory, Python uses agent.py as
# the "agent" module (via `from agent import run_agent`).
# This __init__.py exists only so that pytest can collect from agent/tests/.

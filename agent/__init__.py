import sys
from pathlib import Path

# Frammer Agent Package

# Ensure the agent directory is in path so top-level imports works for submodules
_agent_dir = Path(__file__).resolve().parent
if str(_agent_dir) not in sys.path:
    sys.path.insert(0, str(_agent_dir))

async def run_agent(*args, **kwargs):
    """Lazy import of the real run_agent to avoid circular import issues."""
    from .agent import run_agent as _run_agent
    return await _run_agent(*args, **kwargs)


async def run_agent_stream(*args, **kwargs):
    """Lazy import of the streaming run_agent_stream."""
    from .agent import run_agent_stream as _run_agent_stream
    async for event in _run_agent_stream(*args, **kwargs):
        yield event

import asyncio
import logging
import sys
import os

# Add agent dir to path
sys.path.append(os.path.join(os.getcwd(), "agent"))

from agent.agent import run_agent
from agent.logger_setup import setup_logging

async def test():
    setup_logging()
    logger = logging.getLogger("test_logger")
    logger.info("Starting logging test...")
    
    # Test a simple query
    try:
        await run_agent("hi")
    except Exception as e:
        logger.error(f"Test failed: {e}")

if __name__ == "__main__":
    asyncio.run(test())

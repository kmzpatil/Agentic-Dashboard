import asyncio
import sys
import os
import logging
from pathlib import Path

# Add agent dir to path
AGENT_DIR = Path("c:/Users/kmzpa/Desktop/asdfghjkl/gcdata/agent")
sys.path.insert(0, str(AGENT_DIR))

# Configure logging to see agent output
logging.basicConfig(level=logging.INFO)

async def test():
    print("0. Starting debug script...")
    try:
        print("1. Importing run_agent...")
        from agent import run_agent
        print("2. Import successful.")
        
        print("3. Calling run_agent...")
        task = asyncio.create_task(run_agent("How many Hindi videos?"))
        
        while not task.done():
            print("...waiting for task...")
            await asyncio.sleep(2)
            
        result = await task
        print("4. run_agent finished.")
        print(f"Result intent: {result.intent}")
        print(f"Result response: {result.response[:100]}...")
    except Exception as e:
        print("ERROR ENCOUNTERED:")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())

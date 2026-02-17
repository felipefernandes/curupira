
import asyncio
import pytest
import sys
import os
import logging
from unittest.mock import MagicMock

# Adjust path to import from parent directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import config
from core.agent import AgentBrain

# Mock configuration — IMPORTANT: mutate in-place, do NOT reassign,
# otherwise skills that imported MCP_SERVERS will hold a stale reference.
config.MCP_SERVERS.clear()
config.MCP_SERVERS.update({
    "dummy": {
        "command": sys.executable,
        "args": ["tests/dummy_mcp_server.py"],
        "env": {"PYTHONUNBUFFERED": "1"}
    }
})
config.AI_PROVIDER = "groq" # Mock provider
config.GROQ_API_KEY = "mock_key"

@pytest.mark.skip(reason="Hangs on Windows CI/local due to subprocess pipe issues")
@pytest.mark.asyncio
async def test_mcp_integration():
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("TestMCP")
    
    logger.info("Initializing AgentBrain...")
    brain = AgentBrain("groq", "mock_key", "mock_model")
    
    # Mock the LLM client to avoid real API calls
    brain.client = MagicMock()
    brain.client.chat.completions.create = MagicMock()
    
    logger.info("Starting MCP Clients...")
    await brain.start_mcp_clients()
    
    # Verify tools registered
    tools = brain.skills
    logger.info(f"Registered skills: {list(tools.keys())}")
    
    if "dummy_echo" in tools and "dummy_add" in tools:
        logger.info("SUCCESS: Dummy tools found!")
    else:
        logger.error("FAILURE: Dummy tools NOT found!")
        await brain.shutdown()
        return

    # Verify Tool Execution
    logger.info("Testing dummy_add execution...")
    context = {}
    
    # Direct execution of the skill
    add_skill = tools["dummy_add"]
    result = await asyncio.wait_for(add_skill.execute(context, a=10, b=5), timeout=5.0)
    
    logger.info(f"Result of dummy_add(10, 5): {result}")
    
    # MCP returns content list, let's parse it
    # Expecting: {'content': [{'type': 'text', 'text': '15'}]}
    # Wrapper might return the raw dict or just the text depending on implementation.
    # checking mcp_client.py: return result (the whole dict from result key)
    
    # Actually mcp_client.call_tool returns result.get("result") which is the content dict.
    
    if isinstance(result, dict) and "content" in result:
        text = result["content"][0]["text"]
        if text == "15":
            logger.info("SUCCESS: dummy_add returned correct result!")
        else:
            logger.error(f"FAILURE: dummy_add returned wrong result: {text}")
    else:
        logger.error(f"FAILURE: Unexpected result format: {result}")

    logger.info("Shutting down...")
    await brain.shutdown()

if __name__ == "__main__":
    asyncio.run(test_mcp_integration())

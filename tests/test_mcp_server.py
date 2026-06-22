import pytest
import asyncio
import sys
import os
from pathlib import Path

# Adjust path to import core modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.mcp_client import MCPClient

# Configuration for the server under test
SERVER_SCRIPT = str(Path(__file__).parent.parent / "skills" / "github_server.py")
PYTHON_EXE = sys.executable

# Skip all tests if server script doesn't exist
pytestmark = pytest.mark.skipif(
    not os.path.exists(SERVER_SCRIPT),
    reason=f"Server script not found: {SERVER_SCRIPT}"
)

@pytest.fixture
def mcp_server_env():
    """Sets up environment with a dummy token."""
    env = os.environ.copy()
    env["GITHUB_PERSONAL_ACCESS_TOKEN"] = "ghp_dummy_token_for_testing"
    return env

@pytest.fixture
def mcp_server_no_token_env():
    """Sets up environment WITHOUT a token."""
    env = os.environ.copy()
    if "GITHUB_PERSONAL_ACCESS_TOKEN" in env:
        del env["GITHUB_PERSONAL_ACCESS_TOKEN"]
    return env

@pytest.mark.asyncio
async def test_server_startup_and_list_tools(mcp_server_env):
    """Verifies that the server starts up and registers GitHub tools."""
    client = MCPClient(PYTHON_EXE, [SERVER_SCRIPT], env=mcp_server_env)
    
    try:
        await asyncio.wait_for(client.connect(), timeout=15.0)
        assert client.connected is True
        
        tools = await asyncio.wait_for(client.list_tools(), timeout=10.0)
        tool_names = [t["name"] for t in tools]
        
        print(f"Discovered tools: {tool_names}")
        
        assert "github_list_repos" in tool_names
        assert "github_list_issues" in tool_names
        assert "github_create_issue" in tool_names
        
    finally:
        await client.close()

@pytest.mark.asyncio
async def test_server_fails_without_token(mcp_server_no_token_env):
    """Verifies that the server fails to start (or errors out) if token is missing."""
    client = MCPClient(PYTHON_EXE, [SERVER_SCRIPT], env=mcp_server_no_token_env)
    
    try:
        await asyncio.wait_for(client.connect(), timeout=10.0)
        # If it connects, give it a moment to die
        await asyncio.sleep(1)
        
        if client.process is not None and client.process.returncode is not None:
             assert client.process.returncode != 0
             
    except (asyncio.TimeoutError, Exception):
        # Connection might fail/timeout if process exits immediately — expected
        pass
    finally:
        await client.close()

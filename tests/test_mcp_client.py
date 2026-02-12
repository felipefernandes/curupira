import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
import sys
import os

# Add parent directory to path to import core
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.mcp_client import MCPClient

@pytest.fixture
def mcp_client():
    return MCPClient("python", ["script.py"], {})

@pytest.mark.asyncio
async def test_mcp_client_init(mcp_client):
    assert mcp_client.command == "python"
    assert mcp_client.args == ["script.py"]
    # assert mcp_client.session is None # attribute does not exist

@pytest.mark.asyncio
async def test_connect_failure(mcp_client):
    """Test connection failure handling"""
    # Mock subprocess creation to raise an exception
    with patch("asyncio.create_subprocess_exec", side_effect=OSError("Exec failed")):
        with pytest.raises(OSError, match="Exec failed"):
            await mcp_client.connect()
        assert mcp_client.connected is False # Should remain false (or be set to true then failed? Code sets it true early)
        # Actually in code: self.connected = True is line 37, before try.
        # But if it raises, we might want to check if it cleans up? 
        # The code doesn't reset connected=False in except block. 
        # So we just check exception propagation.

@pytest.mark.asyncio
async def test_list_tools_not_connected(mcp_client):
    """Test list_tools when not connected"""
    with pytest.raises(RuntimeError, match="not connected"):
        await mcp_client.list_tools()

@pytest.mark.asyncio
async def test_call_tool_not_connected(mcp_client):
    """Test call_tool when not connected"""
    with pytest.raises(RuntimeError, match="not connected"):
        await mcp_client.call_tool("some_tool", {})

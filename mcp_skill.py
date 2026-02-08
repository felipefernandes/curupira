
from typing import Any, Dict
from skills.base import BaseSkill
from mcp_client import MCPClient

class MCPSkill(BaseSkill):
    """
    Adapter bridging a remote MCP Tool to the internal Curupira BaseSkill interface.
    """

    def __init__(self, client: MCPClient, tool_def: Dict[str, Any]):
        """
        Initialize the MCPSkill.

        Args:
            client: The connected MCPClient instance that provides this tool.
            tool_def: The tool definition dictionary from MCP 'list_tools'.
                      Expected format: {
                          "name": "tool_name",
                          "description": "...",
                          "inputSchema": {...} 
                      }
        """
        self.client = client
        self._tool_def = tool_def

    @property
    def name(self) -> str:
        return self._tool_def.get("name", "unknown_mcp_tool")

    @property
    def description(self) -> str:
        return self._tool_def.get("description", "No description provided.")

    @property
    def parameters(self) -> Dict[str, Any]:
        """
        Returns the JSON Schema for the tool's parameters.
        MCP uses 'inputSchema', which aligns with OpenAI/Gemini expectations.
        """
        return self._tool_def.get("inputSchema", {"type": "object", "properties": {}})

    async def execute(self, context: Dict[str, Any], **kwargs) -> Any:
        """
        Executes the MCP tool via the client.
        """
        # Context is currently not passed to MCP tools (state is managed by the server or client session)
        # We forward the arguments directly.
        return await self.client.call_tool(self.name, kwargs)

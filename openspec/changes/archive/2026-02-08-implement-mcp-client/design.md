# Design: MCP Integration

## Architecture
The MCP Client will be integrated into `AgentBrain` as a new capability provider. Instead of hardcoding interactions with specific APIs, the AgentBrain will communicate with local MCP Servers via Stdio transport.

### Components

1.  **`MCPClient` Class:**
    - Handles connection to an MCP Server process (Stdio).
    - Implements JSON-RPC 2.0 communication.
    - Methods: `connect()`, `list_tools()`, `call_tool()`, `close()`.

2.  **`MCPSkill` Wrapper (extends `BaseSkill`):**
    - Adapts an MCP Tool definition to the `BaseSkill` interface used by `AgentBrain`.
    - `name`: Cleaned tool name from MCP.
    - `description`: Tool description from MCP.
    - `parameters`: Tool input schema from MCP (needs conversion to OpenAI/Gemini format if not already compatible).
    - `execute`: Delegates execution to `MCPClient.call_tool()`.

3.  **`AgentBrain` Enhancements:**
    - Load MCP Servers configuration on init.
    - Initialize `MCPClient` instances.
    - Fetch tools and register them as `MCPSkill`s.

## Configuration
MCP Servers will be configured in `config.py` (loaded from JSON/Env).
Structure:
```json
{
  "mcp_servers": {
    "filesystem": {
      "command": "python",
      "args": ["-m", "mcp_server_filesystem", "."]
    }
  }
}
```

## Data Flow
1.  **Startup:** `AgentBrain` reads config -> Starts MCP Servers -> Lists Tools -> Registers `MCPSkill`s.
2.  **Interaction:** User Query -> LLM (calls tool) -> `AgentBrain` (finds `MCPSkill`) -> `MCPSkill.execute` -> `MCPClient.call_tool` -> MCP Server (Process) -> Result -> `AgentBrain` -> LLM.

## Constraints & Trade-offs
- **Stdio Only:** For MVP and Raspberry Pi simplicity, we ignore SSE/HTTP transports.
- **Error Handling:** If an MCP server crashes, the agent should gracefully handle it (e.g., disable those skills or restart the server).
- **Security:** Since servers run locally, we must trust the configured commands. `USER_ID` whitelist still protects the bot interface, but the bot has access to whatever the MCP server has.

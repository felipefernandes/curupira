# mcp_client Specification

## Purpose
Enable the bot to connect to external MCP Servers and use their tools as if they were native skills.

## Requirements

### Requirement: MCP Client Support
The system MUST be capable of connecting to an MCP Server via stdio or SSE.

#### Scenario: Connect to Local Server
1.  Configuration specifies an MCP server command (e.g., `npx -y @modelcontextprotocol/server-filesystem`).
2.  The system initiates the connection on startup.
3.  The system lists available tools from the MCP server.

### Requirement: Tool Adaptation
The system MUST adapt MCP Tools into the `BaseSkill` format so they can be used transparently by the `AgentBrain`.

#### Scenario: Execution of MCP Tool
1.  LLM selects a tool provided by an MCP server.
2.  `AgentBrain` calls `execute`.
3.  The adapter routes the call to the MCP Client, which sends the request to the external server.
4.  The result is returned and fed back to the LLM.

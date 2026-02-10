# Capability: MCP Client Integration

## ADDED Requirements

### Requirement: Connect to Local MCP Servers
The AgentBrain MUST be able to connect to local MCP servers defined in the configuration.

#### Scenario: Startup Connection
1.  Agent reads `MCP_SERVERS` config.
2.  Agent establishes a Stdio connection to each defined server process.
3.  Server processes persist for the duration of the Agent's life.

#### Scenario: Connection Failure
1.  A configured server fails to start or crashes.
2.  The Agent logs the error.
3.  The Agent continues operation without that server's tools.

### Requirement: Discover Tools from MCP Servers
The AgentBrain MUST be able to query connected MCP servers for their available tools.

#### Scenario: Tool Listing
1.  On startup, after connection, the Agent calls `list_tools` on each client.
2.  The Agent registers each discovered tool as an available `Skill`.
3.  The tool becomes accessible to the LLM (Gemini/Groq).

### Requirement: Execute MCP Tools
The AgentBrain MUST be able to execute tools provided by MCP servers.

#### Scenario: Tool Execution
1.  The LLM calls a tool (e.g., `list_files`).
2.  The AgentBrain identifies it as an MCP tool.
3.  The Agent delegates execution to the corresponding `MCPClient`.
4.  The `MCPClient` sends a `call_tool` JSON-RPC request to the server.
5.  The server executes the tool and returns the result.
6.  The Agent returns the result to the LLM.

#### Scenario: Execution Failure
1.  Tool execution fails (JSON-RPC error or timeout).
2.  The AgentBrain catches the error.
3.  The Agent returns a descriptive error message to the LLM.

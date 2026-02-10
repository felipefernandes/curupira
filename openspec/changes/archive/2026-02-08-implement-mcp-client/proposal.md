# Proposal: Implement MCP Client

| Field | Value |
| --- | --- |
| **Change ID** | `implement-mcp-client` |
| **Status** | Proposed |
| **Author** | Antigravity |
| **Date** | 2026-02-08 |

## Summary
Implement a Model Context Protocol (MCP) Client within the Curupira `AgentBrain`. This will allow the bot to connect to external MCP Servers, dynamically discovering and using tools provided by these servers, effectively expanding its skills without modifying the core codebase for each new integration.

## Motivation
As outlined in Phase 5 of the Roadmap, we need a lightweight way to extend the agent's capabilities. MCP provides a standard protocol for exposing tools and resources. By implementing an MCP Client, Curupira can leverage the existing and future ecosystem of MCP servers (e.g., database access, file system, git) while keeping the core agent logic clean and efficient.

## Scope
- Implement an async MCP Client (using `mcp` python SDK if viable/lightweight, or a custom lightweight implementation if `mcp` is too heavy/incompatible).
- Integrate MCP tool discovery into `AgentBrain`.
- Adapt MCP tools to be consumable by Gemini and Groq providers.
- Configure MCP servers via `.env` or a config file.

## Limitations
- Initial implementation will focus on Stdio transport (local servers) to maintain simplicity and compatibility with the Raspberry Pi environment.
- SSE support can be added later if needed for remote servers.

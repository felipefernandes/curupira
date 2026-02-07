# Implement Lightweight Agentic Architecture

## Summary
Transform Curupira from a regex-based bot into a true Agentic AI by implementing a `BaseSkill` system with Native Function Calling (Gemini/Groq) and an "Agent Loop" (Brain) that autonomously selects tools. This change also introduces the foundation for MCP (Model Context Protocol) Client support.

## Problem Statement
Currently, Curupira's "skills" (Weather, Reminders) are regex-triggered automation scripts. This has several limitations:
1.  **Rigidity:** Adding a new skill requires writing complex regex and manual parsing logic.
2.  **No Decision Making:** The bot cannot decide *when* to use a tool based on context; it only reacts to specific keywords.
3.  **Scalability:** Integrating external tools (like Vercel, GA4) or MCP servers is difficult without a standard interface.

## Proposed Solution
1.  **Skill Standard:** Create a `BaseSkill` abstract class that defines `name`, `description`, `parameters` (JSON Schema), and `execute()`.
2.  **Function Calling:** Refactor the `get_ai_response` logic to use the LLM's native Function Calling capabilities (supported by both Gemini and Groq) to select tools.
3.  **Agent Loop:** Implement a simple "Think-Act-Observe" loop where the bot:
    *   receives a message,
    *   decides if it needs a tool,
    *   executes the tool,
    *   feeds the result back to the LLM to generate the final response.
4.  **MCP Foundation:** Ensure the `BaseSkill` architecture is compatible with MCP Tool definitions to facilitate future MCP Client implementation.

## Impact
- **Users:** More natural interactions. The bot can "figure out" how to help without memorizing commands.
- **Devs:** Easier to add new skills (just define the class and schema).
- **System:** Slightly increased token usage (due to tool definitions in context), but significant gain in capability.

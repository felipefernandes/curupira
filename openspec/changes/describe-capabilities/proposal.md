# Proposal: Skill Capabilities Description

**Change ID**: `describe-capabilities`
**Issue**: [#55](https://github.com/felipefernandes/curupira/issues/55)

## Summary
Implement a mechanism for the bot to introspect its registered skills and describe their capabilities to the user upon request. This addresses the need for users to discover what the bot can do dynamically, especially as new skills (MCP) are added.

## Motivation
Currently, the bot knows its tools via the system prompt, but there is no explicit tool for it to retrieve a structured list of capabilities to present to the user. When a user asks "What can you do with GitHub?", the bot creates a response based on its system prompt context, which might be concise or incomplete. A dedicated `list_skills` or `describe_capabilities` tool allows:
1.  **Dynamic Discovery**: The bot can list new MCP tools added at runtime without hallucination.
2.  **Detailed Help**: The bot can explain specific parameters or usage examples by inspecting the skill's schema.

## Proposed Solution
1.  Create a built-in `IntrospectionSkill` that has access to the `AgentBrain`'s skill registry.
2.  Implement a tool `describe_capabilities(skill_name: Optional[str] = None)`:
    *   If `skill_name` is provided, returns detailed documentation for that specific skill.
    *   If `skill_name` is omitted, returns a high-level list of all available skills and their summaries.
3.  Register this skill automatically in `AgentBrain`.

## UX Impact
- **User**: "O que você sabe fazer?"
- **Bot**: *Calls `describe_capabilities()`* -> "Eu posso: 1. Gerenciar repositórios GitHub... 2. Prever o tempo..."
- **User**: "Como funciona a skill do GitHub?"
- **Bot**: *Calls `describe_capabilities(skill_name="github")`* -> "A skill GitHub permite: listar issues, criar PRs..."

## Risks
- **Prompt Size**: Listing *all* details might be too large. The tool should return a summary by default and details only when requested.

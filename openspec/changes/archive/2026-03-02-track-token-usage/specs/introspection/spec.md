## ADDED Requirements

### Requirement: Token Usage Diagnostics
The system MUST be able to query its database and return an accumulated report of its API usage over time (such as prompt tokens vs completion tokens) categorized chronologically or by provider.

#### Scenario: User queries for bot token spendings
- **GIVEN** the bot has been interacting using Gemini and Groq, saving multiple usage logs
- **WHEN** the user asks "Qual foi meu custo até agora?", "Mostre o gasto de tokens"
- **THEN** the AgentBrain triggers the new `get_usage_report` introspection skill
- **AND** the tool queries `MemoryManager` to calculate the aggregate usage grouped by Provider and calculates an estimated price inside the output string to clearly inform the user.

## ADDED Requirements

### Requirement: Persist LLM Token Usage
The system MUST record the exact number of `prompt_tokens` and `completion_tokens` consumed by the LLM (Groq, Gemini) during the conversation process into the internal SQLite database.

#### Scenario: Agent processes a User prompt via Gemini
- **GIVEN** the bot is set to use `gemini` provider and is answering a message
- **WHEN** the `AgentBrain` receives the `response` with populated `usage_metadata`
- **THEN** it MUST extract the metrics and call the memory manager logic to persist the numbers along with the current timestamp and the provider/model names without failing or blocking the response delivery.

#### Scenario: Agent processes a User prompt via Groq
- **GIVEN** the bot is set to use `groq` provider and is answering a message
- **WHEN** the `AgentBrain` receives the `response` with populated `usage`
- **THEN** it MUST extract the metrics and call the memory manager logic to persist the numbers along with the current timestamp and the provider/model names.

# memory Specification

## Purpose
TBD - created by archiving change implement-memory-system. Update Purpose after archive.
## Requirements
### Requirement: Long-term Fact Storage
The system MUST be able to store and retrieve persistent facts about the user.

#### Scenario: Learning User's Name
- **GIVEN** the user tells the bot "Meu sobrenome é Fernandes"
- **WHEN** the bot processes this information
- **THEN** the bot MUST store "Fernandes" as the "surname" fact for that user
- **AND** the bot MUST start addressing the user with the surname

### Requirement: Conversation History
The system MUST maintain a log of recent messages to provide conversational context.

#### Scenario: Contextual Reply
- **GIVEN** the user asks "Qual é a temperatura?"
- **AND** the bot replies "50 graus"
- **WHEN** the user immediately asks "É perigoso?"
- **THEN** the bot MUST understand the question refers to "50 graus"

### Requirement: Lightweight Persistence
The memory storage MUST use a file-based database to minimize resource usage.

#### Scenario: Restart Persistence
- **GIVEN** the bot has learned a fact
- **WHEN** the bot process is restarted
- **THEN** the fact MUST still be available in memory

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


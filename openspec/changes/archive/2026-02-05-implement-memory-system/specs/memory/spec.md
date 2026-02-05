## ADDED Requirements
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

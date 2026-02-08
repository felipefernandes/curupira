# Reminders Spec Updates

## ADDED Requirements

### Requirement: Agentic Natural Language Reminders

#### Scenario: Agentic Invocation
- **Given** the user says "Me lembre de comprar leite em 10 minutos"
- **When** the Agent analyzes the intent
- **Then** it MUST invoke the tool `add_reminder` with arguments `{"message": "comprar leite", "delay_minutes": 10}`
- **And** the System MUST return a confirmation message to the user: "Lembrete criado: comprar leite em 10 minutos."

### Requirement: Agentic Reminder Management

#### Scenario: List Reminders Agentic
- **Given** the user says "Quais são meus lembretes?"
- **When** the Agent analyzes the intent
- **Then** it MUST invoke the tool `list_reminders` with empty arguments `context`
- **And** the System MUST return a list of reminders in a JSON-like structure: `{"reminders": [{"id": 1, "message": "...", "at": "..."}]}`

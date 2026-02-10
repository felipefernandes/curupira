# reminders Spec Delta

## MODIFIED Requirements

### Requirement: Natural Language Reminders
The system MUST be able to schedule reminders based on natural language requests, supporting both relative times (e.g., "in 10 minutes") AND absolute times/dates (e.g., "tomorrow at 9am", "at 14:00").

#### Scenario: Schedule Absolute Time Reminder
1.  User sends: "Me lembre de tomar remédio às 20h".
2.  System calculates the delay until 20:00 today (or tomorrow if 20:00 passed).
3.  System schedules the reminder.
4.  System replies: "Lembrete criado para 20:00: tomar remédio".

#### Scenario: Schedule Relative Time Reminder
1.  User sends: "Me lembre em 1 hora".
2.  System schedules for `now + 1h`.
3.  System replies: "Lembrete criado para [Time+1h]".

### Requirement: Agentic Natural Language Reminders
The Agent MUST use the `add_reminder` tool with a flexible `when` parameter instead of just `delay_minutes` to support the natural language requirements.

#### Scenario: Agentic Invocation (Absolute)
- **Given** the user says "Lembrar de reunião amanhã cedo"
- **When** the Agent invokes `add_reminder`
- **Then** it MUST pass `{"message": "reunião", "when": "amanhã cedo"}` (or similar natural string)
- **And** the System MUST parse this to a concrete datetime.

## ADDED Requirements

### Requirement: Capability Boundary
The system MUST NOT offer or schedule a reminder as a fallback for a capabilities failure (e.g., "I can't search web, but I can remind you"). It MUST explicitly state it cannot perform the requested action.

#### Scenario: Web Search Failure
- **Given** the user asks "Pesquise X na web" (and web search is disabled/unavailable)
- **When** the Agent requires a tool it doesn't have
- **Then** it MUST NOT call `add_reminder`
- **And** it MUST reply "Eu não tenho acesso à web para pesquisar isso."

### Requirement: Immediate Feedback
For reminders scheduled for "now" or less than 1 minute, the system MUST provide immediate feedback that the reminder is firing/will fire instantly.

#### Scenario: 0-minute Reminder
- **Given** the user says "Me lembre agora"
- **When** the reminder is scheduled with 0 delay
- **Then** the confirmation message MUST say "Disparando lembrete agora mesmo!"
- **And** the reminder message should be delivered immediately.

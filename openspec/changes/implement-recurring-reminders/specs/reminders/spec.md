# reminders Specification

## ADDED Requirements

### Requirement: Recurring Reminders (Rotinas)
The system MUST support scheduling of reminders that repeat automatically on a daily basis.

#### Scenario: Schedule Daily Reminder
- **Given** the user says "Me lembre de tomar remédio todo dia às 20h"
- **When** the Agent processes the request
- **Then** a reminder is created with `recurrence="DAILY"` and `target_time="20:00"`
- **And** the System confirms: "Lembrete recorrente criado: tomar remédio todo dia às 20:00."
- **And** the reminder fires today/tomorrow at 20:00 and reschedules itself for the next day automatically.

#### Scenario: List Recurring Reminders
- **Given** a daily reminder exists
- **When** the user asks "quais meus lembretes?"
- **Then** the list includes the item marked as recurring (e.g., "[Recorrente: Diário] Tomar remédio").

#### Scenario: Delete Recurring Reminder
- **Given** a recurring reminder is active
- **When** the user asks to delete it
- **Then** the recurring job is cancelled and removed from the database permanently.

# reminders Specification

## Purpose
TBD - created by archiving change implement-reminders. Update Purpose after archive.
## Requirements
### Requirement: Natural Language Reminders
The system MUST be able to schedule reminders based on natural language requests from the user, executed via the AI model's intent detection.

#### Scenario: Schedule Short-Term Reminder
1.  User sends: "Me lembre de desligar o forno em 15 minutos".
2.  System replies naturally (e.g., "Pode deixar, te aviso!").
3.  System saves the reminder in persistent storage (Database).
4.  System schedules a background job.
5.  After 15 minutes (+/- system latency), the System sends a message: "⏰ Lembrete: desligar o forno".

### Requirement: Persistent Reminders
The system MUST persist reminders so that they are not lost if the application restarts.

#### Scenario: Restart Recovery
1.  User schedules a reminder for 1 hour from now.
2.  The application is stopped and restarted after 10 minutes.
3.  The system identifies the pending reminder in the database.
4.  The system reschedules the reminder job.
5.  At the correct time (50 mins later), the reminder is delivered.

### Requirement: Reminder Management
The system MUST allow value listing and deletion of scheduled reminders.

#### Scenario: List Reminders
1.  User asks: "Quais são meus lembretes?".
2.  System responds with a list of PENDING reminders, including their ID and scheduled time.

#### Scenario: Delete Reminder
1.  User asks: "Cancele o lembrete 1".
2.  System confirms deletion.
3.  The specific reminder does NOT fire at the scheduled time.


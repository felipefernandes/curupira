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

### Requirement: Update Reminder Attributes
The system SHALL allow updating the message text and/or the trigger time of an existing pending reminder.

#### Scenario: Update message only
- **WHEN** a request to update reminder #123 with new message "Buy milk and eggs" is received
- **THEN** the stored message for #123 is updated
- **AND** the trigger time remains unchanged

#### Scenario: Update time only
- **WHEN** a request to update reminder #123 with new delay of 30 minutes is received
- **THEN** the reminder is rescheduled to trigger 30 minutes from now
- **AND** the message remains unchanged

#### Scenario: Update both
- **WHEN** a request to update both message and time is received
- **THEN** both attributes are updated and the job is rescheduled

### Requirement: Execute Reminder
The system SHALL execute the reminder by verifying its PENDING status and fetching the latest message content from the database.

#### Scenario: Execution with updated message
- **WHEN** the reminder job triggers
- **THEN** the system retrieves the current message from the database (not the scheduled payload)
- **AND** sends the message to the user if status is PENDING


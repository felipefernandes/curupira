## ADDED Requirements

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

## MODIFIED Requirements

### Requirement: Execute Reminder
The system SHALL execute the reminder by verifying its PENDING status and fetching the latest message content from the database.

#### Scenario: Execution with updated message
- **WHEN** the reminder job triggers
- **THEN** the system retrieves the current message from the database (not the scheduled payload)
- **AND** sends the message to the user if status is PENDING

## Context
Current reminder implementation stores message copy in JobQueue. Updating a reminder requires updating both DB and JobQueue.
For better data integrity (Diet philosophy), the execution time should rely on the DB as the single source of truth for the message content.

## Decisions
- **Decision**: Fetch message from DB at execution time.
  - **Reason**: Allows updating the message in DB without needing to find and patch the job object's data payload.
- **Decision**: Command format `[[REMINDER_UPDATE|ID|MINUTES|MESSAGE]]`.
  - **Reason**: Consistent with creating reminders. Flexible to support partial updates (time only, msg only).

## Risks
- **Race Condition**: If user deletes reminder right before execution.
  - **Mitigation**: `execute_reminder` already checks status `PENDING`. Adding message fetch should handle "row not found" gracefully.

# Design: Recurring Reminders

## Data Model
- **Table**: `reminders`
- **New Column**: `recurrence` (TEXT, Nullable)
- **Format**: String representation of the rule.
  - `DAILY:{time}` (e.g., `DAILY:08:00`)
  - `WEEKLY:{day}:{time}` (e.g., `WEEKLY:MON:09:00`) - *Future/Nice to have, starting with Daily is safer.*
  - Null = One-time reminder.

## Architecture
- **Startup Recovery**:
  - `recover_reminders` currently fetches PENDING reminders and schedules `run_once`.
  - **New Logic**:
    - If `recurrence` is present:
      - Schedule `run_daily` (or equivalent) using the target time.
      - **Crucial**: Recurring reminders don't usually map to a single "PENDING" row that gets deleted/marked SENT after one execution. They persist.
      - **State Management**:
        - One-time: Status `PENDING` -> `SENT`.
        - Recurring: Status `ACTIVE` -> `CANCELLED`. It never goes to `SENT` permanently.
        - Logging: We might want a separate execution log, but for now, just firing the message is enough.

## Natural Language Parsing
- Current `_preprocess_time_string` maps "toda manhã" to "amanhã às 08:00".
- **Update**:
  - Detect "toda/todo" + freq.
  - Set `recurrence` flag in `AddReminderSkill`.
  - Pass this flag to manager.

## JobQueue Integration
- `python-telegram-bot`'s `JobQueue` has `run_daily`.
- We will use `run_daily(callback, time=..., days=...)`.
- **Callback**: Needs to handle the message sending.

## Dependencies
- No new external pip dependencies required. `dateparser` is already there (can it parse "every day"? maybe not well, explicit regex might be better for "toda X").

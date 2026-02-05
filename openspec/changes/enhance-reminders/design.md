# Design: Persistent Reminders

## Database Schema (SQLite)
We will extend the existing `db` (managed by `MemoryManager` but accessible to skills).

Table: `reminders`
- `id`: INTEGER PRIMARY KEY AUTOINCREMENT
- `user_id`: INTEGER
- `message`: TEXT
- `remind_at`: DATETIME (ISO format)
- `created_at`: DATETIME
- `status`: TEXT ('PENDING', 'SENT', 'CANCELLED')

## Architecture

### 1. `ReminderManager` (`skills/reminders.py`)
- `add_reminder(user_id, message, seconds_from_now)`: Saves to DB, returns ID.
- `list_reminders(user_id)`: Returns list of pending reminders.
- `delete_reminder(reminder_id)`: Marks as CANCELLED.
- `load_pending_reminders()`: Called on startup to reschedule jobs.

### 2. JobQueue Integration
- When adding a reminder, we save to DB *and* schedule `run_once`.
- The job callback now needs to receive the `reminder_id`.
- Inside the callback: Check if reminder status is still 'PENDING' in DB. If 'CANCELLED', do nothing. After sending, mark as 'SENT'.

### 3. LLM Protocol Extension
- **List**:
    - User: "Quais meus lembretes?"
    - SysPrompt: "If asked to list, output `[[REMINDER_LIST]]`".
    - Bot: Intercepts, fetches from DB, formats a list ("1. [18:00] Comprar pão"), and sends to user.
- **Delete**:
    - User: "Cancele o lembrete de comprar pão".
    - SysPrompt: "If asked to cancel, output `[[REMINDER_DELETE|ID]]`. You might need to list reminders first if ID is unknown, but assume user sees the list." (Or we provide a fuzzy delete? No, strictly ID for MVP reliability).
    - Bot: Marks as cancelled in DB.

## Startup Recovery
- `post_init`: Call `ReminderManager.recover_jobs(application.job_queue)`.
- It queries `status='PENDING'` and `remind_at > now`.
- Reschedules them.
- If `remind_at < now` (missed while offline), send "⚠️ Perdi este lembrete: ..." immediately.

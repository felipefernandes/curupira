## 1. Preparation
- [x] 1.1 Read `skills/reminders.py` and `bot.py` context.

## 2. Refactor (Single Source of Truth)
- [x] 2.1 Modify `execute_reminder` in `bot.py` to fetch `message` from DB using `reminder_id`.
- [x] 2.2 Verify fallback to job data if DB fetch fails (optional, or error handling).

## 3. Implementation (Update Logic)
- [x] 3.1 Implement `update_reminder(id, message, delay_seconds)` in `ReminderManager`.
  - Handle `None` values (partial updates).
  - Recalculate `remind_at` if delay changes.
- [x] 3.2 Update `bot.py` handler for `[[REMINDER_UPDATE|...]]`.
  - Parse arguments (ALLOW `0` or `-` for no change).
  - Call `update_reminder`.
  - If time changed, reschedule job (cancel old, create new).

## 4. AI Instruction
- [x] 4.1 Update system prompt in `bot.py` to include `[[REMINDER_UPDATE]]` usage instructions.

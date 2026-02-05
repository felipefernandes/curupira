# Change: Enhance Reminders Skill (Phase 5.5)

## Why
Phase 5 implemented basic "fire-and-forget" reminders. Phase 5.5 aims to make Curupira a reliable assistant by adding persistence (SQLite) and management capabilities (List, Delete, Edit). Without this, reminders are lost on restart, and users cannot manage their schedule.

## What Changes
- **Persistence**: Create `reminders` table in SQLite.
- **Boot Recovery**: Load and reschedule pending reminders on bot startup.
- **New Commands (In-Band)**:
    - `[[REMINDER_LIST]]`: User asks to see reminders.
    - `[[REMINDER_DELETE|ID]]`: User asks to delete a reminder.
- **Refactoring**: Move reminder logic from `bot.py` to `skills/reminders.py`.

## Impact
- **Affected specs**: `reminders` (MODIFIED)
- **Affected code**: `bot.py` (Delegation), `config.py` (No change), `skills/reminders.py` (New), `skills/memory.py` (DB schema update).

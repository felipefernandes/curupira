# Change: Update Reminders

## Why
Users currently cannot modify existing reminders (typos, changing time). They have to delete and recreate them, which is friction.
This change enables users to update reminder messages and times, aligning with Phase 5.5 of the Roadmap.

## What Changes
- **New Feature**: Update reminder attributes (Message, Time).
- **Refactor**: "Single Source of Truth" pattern for reminder execution. The worker will fetch the latest message from DB instead of relying on stale job data.
- **Bot Logic**: New AI command `[[REMINDER_UPDATE|ID|MINUTES|MESSAGE]]`.

## Impact
- **Affected Specs**: `reminders`
- **Affected Code**: `bot.py` (handler), `skills/reminders.py` (DB logic)

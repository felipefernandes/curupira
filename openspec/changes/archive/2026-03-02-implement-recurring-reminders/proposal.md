# Proposal: Recurring Reminders (Rotinas)

## Goal
Enable users to schedule recurring reminders (e.g., "every day", "every monday") to support routine management.

## Context
Currently, the bot only supports one-time reminders. Users expecting to set up routines (like "read news every morning") are confused when the bot schedules a single event for the next day. This change addresses Issue #76.

## User Review Required
> [!NOTE]
> We will stick to simple recurrence patterns (Daily/Weekly) supported natively by `python-telegram-bot`'s `JobQueue` or simple interval logic to avoid heavy dependencies like `croniter` or `dateutil` if possible, aligning with the "Diet" philosophy unless complex patterns are strictly required.

## Proposed Changes
1.  **Database**: Update `reminders` table to include a `recurrence` column.
2.  **Logic**: Update `ReminderManager` to handle recurring schedules (`run_daily`, `run_repeating`).
3.  **Parsing**: Enhance `AddReminderSkill` to detect recurrence keywords in natural language.
4.  **UX**: Update `ListRemindersSkill` to display recurrence information.

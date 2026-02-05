# Change: Implement Reminders Skill (Phase 5)

## Why
Phase 5 of the Roadmap requires a Reminder system. Users want to interact naturally ("Me lembre de sair em 10 minutos") rather than using rigid slash commands. This transforms Curupira into a helpful proactive assistant.

## What Changes
- Update **System Prompt** (`bot.py`) to instruct the LLM on how to request a reminder scheduling using a specific text protocol (e.g., `[[REMIND|TIME|MSG]]`).
- Implement **Output Parsing** in `bot.py` to detect these commands in the AI response.
- Create a `schedule_reminder_job` callback in `bot.py`.
- Use `JobQueue` to schedule the execution.

## Impact
- **Affected specs**: `reminders` (NEW)
- **Affected code**: `bot.py` (Prompt + Parsing + Job Handler).
- **Dependencies**: `python-dateutil` (likely needed for robust date parsing if done by python, but we will rely on LLM to normalize time for us to ISO or relative seconds to keep it lite).

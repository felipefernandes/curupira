# Refactor Reminders to Agentic Architecture

## Why
To fully leverage the new `AgentBrain` (Phase 5) capabilities, the Reminders skill needs to be optimized for LLM tool calling. The current implementation is functional but can be improved by ensuring consistent context usage (`job_queue`), better parameter descriptions for the AI models (especially Llama 3), and robust error handling within the skill execution flow.

## What Changes
- Refactor `AddReminderSkill`, `ListRemindersSkill`, `DeleteReminderSkill`, and `UpdateReminderSkill` in `skills/reminders.py`.
- Ensure strict type hinting and docstrings for all tool parameters.
- Standardize the return values of `execute` methods to provide clear, structured data for the Agent to interpret.
- Verify that `job_queue` is correctly retrieved from the execution context.

## Impact
- **Agent**: The bot will be able to schedule, list, and modify reminders more reliably.
- **User**: Natural language interactions related to reminders will be more accurate.
- **Codebase**: Cleaner separation between the `ReminderManager` logic and the Skill adapters.

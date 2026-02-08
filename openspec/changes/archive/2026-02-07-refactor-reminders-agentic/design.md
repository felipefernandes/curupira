# Refactor Reminders for Agentic Architecture

## Problem
The current `reminders.py` implementation relies on a partially "hardcoded" skill structure (`AddReminderSkill`, `ListRemindersSkill`, etc.) that might not fully leverage the dynamic tool calling capabilities introduced in the new Agentic Architecture (Phase 5). Specifically, we need to ensure:
1.  Tool definitions (parameters, descriptions) are optimal for the LLM (Groq/Llama3 & Gemini).
2.  The `ReminderManager` is cleanly separated from the `BaseSkill` wrappers.
3.  The integration with `AgentBrain` is seamless, potentially simplifying how the job queue is accessed (since `job_queue` is now passed in context).

## Solution
We will refactor `skills/reminders.py` to:
1.  Consolidate or refine the Skill classes to be more "agent-native".
2.  Ensure docstrings and parameter descriptions are highly descriptive for the AI.
3.  Verify that `job_queue` access from the `context` dictionary is robust.
4.  Standardize the return format of skills to be JSON-friendly strings that the Agent can easily parse and present to the user.

## Design
No major architectural changes to the database or `ReminderManager` logic itself. The focus is on the **interface** layer (the Skills) exposed to the `AgentBrain`.

### Key Changes
- **Unified Skill?** Consider if separate classes for Add/List/Delete are better or if a single `ReminderSkill` with sub-actions is preferred. *Decision: Keep separate skills for clarity and better tool selection by the LLM.*
- **Context Usage**: Ensure `job_queue` is checked safely.
- **Output Formatting**: Skills should return structured dicts, but we might want to add a "human_readable" field or let the LLM generate the response based on the raw data.

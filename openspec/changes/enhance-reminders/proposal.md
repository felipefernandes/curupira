# Proposal: Enhance Reminder Capabilities

## Metadata
- **Change ID:** `enhance-reminders`
- **Author:** Curupira Team
- **Status:** Draft
- **Created:** 2026-02-10

## Summary
Enhance the reminder skill to support absolute times and natural language time expressions, fix tool usage errors with Groq, and improve user feedback for immediate reminders.

## Motivation
Users report frustration with:
1.  **Hallucinations:** Asking for capabilities that the bot doesn't have (e.g. web search) the bot is guessing and setting incorrect reminders instead of saying it doesn't have the capability.
2.  **Errors:** API 400 errors due to malformed tool calls (XML injection) or schema validation failures.
3.  **Usability:** Inability to set reminders for specific times (e.g., "at 10am") without the bot calculating minutes (often incorrectly).
4.  **Feedback:** Confusion when "immediate" reminders disappear from the pending list instantly.

## Scope
-   **Modify** `skills/reminders.py`:
    -   Update `add_reminder` to accept `when` parameter (string) which can be relative ("10m") or absolute/natural ("tomorrow 10am", "14:00").
    -   Implement time parsing logic (using `dateparser` or similar).
    -   Improve feedback message to explicitly state the calculated absolute time.
-   **Modify** `agent.py`:
    -   Inject **Current System Time** into the system prompt to help the LLM understand "morning", "afternoon", etc.
    -   Enhance system instruction to handle "unknown capability" gracefully instead of falling back to a reminder.
    -   Improve error handling for Groq 400 tool-use errors.
-   **Modify** `openspec/specs/reminders/spec.md`:
    -   Add requirements for natural language time parsing.
    -   Add requirements for "sent" reminder visibility (optional log or history).

## Risks
-   **Timezone Complexity:** The bot runs on a server/Pi. We will assume the user is in the same timezone as the bot ("System Local Time") for now, as verified by the user's metadata timestamp.
-   **Parsing Reliability:** Natural language date parsing requires a robust library. We will add `dateparser` to requirements.


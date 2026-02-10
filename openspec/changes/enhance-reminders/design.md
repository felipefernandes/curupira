# Design: Reminder Enhancements

## Architecture Changes

### 1. Skill Parameter Update (`add_reminder`)
Instead of `delay_minutes` (int), we will switch to a more flexible schema or add a new optional parameter.
To maintain backward compatibility or strictly improve, we will deprecate `delay_minutes` in favor of `when` (string).

**New Schema:**
```json
{
  "message": "string",
  "when": "string (e.g. '10m', '1 hour', 'tomorrow 9am', '2026-02-10 14:00')"
}
```

### 2. Time Parsing Logic
We will introduce `dateparser` library to handle the `when` string.
- If `when` is a number or matches `^\d+$`, treat as minutes (legacy support).
- Else, pass to `dateparser.parse(when, settings={'PREFER_DATES_FROM': 'future'})`.
- If parsing fails, return a clear error to the LLM/User asking for clarification.

### 3. Agent System Prompt
We will append the current time to the system prompt dynamically.
`"Horário atual do sistema: YYYY-MM-DD HH:MM"`
This allows the LLM to infer "morning" (e.g., set for 09:00 next day if currently night) or relative times better, though the heavy lifting of calculation will be moved to Python code via `dateparser`.

### 4. 400 Error Handling
The Groq 400 error `{'code': 'tool_use_failed', 'failed_generation': '<function=add_reminder...` suggests the model is generating XML-style calls which the API is then trying to parse as JSON or rejecting.
We are already handling `XML` detection in `agent.py`, but it might be slipping through or the prompt is encouraging it.
We will:
- Reinforce `JSON` format in system prompt if needed.
- Ensure the `tool_choice` logic is robust.

### 5. "Immediate" Reminder Confusion
If a reminder is set for < 1 minute, the response should say "Disparando agora mesmo!" instead of "Agendado para 0 minutos".
And `list_reminders` could optionally show "Recently Sent" reminders, but for now, clear immediate feedback is the priority.


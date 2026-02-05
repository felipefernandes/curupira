# Design: Reminders Skill

## Architecture: "LLM-Driven Tool Use"

To avoid complex intent classifiers or multiple LLM calls (which are slow/expensive), we will use an **In-Band Command Protocol**.

1.  **User Instruction**: "User: Me lembre de comprar pão daqui a 10 minutos."
2.  **LLM Processing**: The System Prompt will have a new section instruction:
    > "If the user asks to set a reminder, calculate the relative time or absolute time and output a hidden command at the end of your response: `[[REMINDER|MINUTES|MESSAGE]]`."
3.  **Bot Parsing**:
    - The `responder` function detects `[[REMINDER|...]]`.
    - It strips this tag from the text sent to the user (so the user only sees "Claro, te lembro em 10 minutos!").
    - It extracts `MINUTES` (int) and `MESSAGE` (string).
4.  **Job Scheduling**:
    - Calls `application.job_queue.run_once(callback, when=minutes*60, ...)`
5.  **Execution**:
    - When time is up, `reminder_callback` sends the message: "⏰ Lembrete: comprar pão".

## Decision: Relative vs Absolute Time
- **MVP (Phase 5)**: We will focus on **Relative Time in Minutes** (e.g., "in 10 mins", "in 2 hours" -> converted to minutes by LLM).
- **Reasoning**: Handling absolute time ("at 5pm") requires the LLM to know the *current* time precisely and handle timezones perfectly. While possible, it's safer to ask the LLM to output "minutes from now" since the user usually provides relative context or the LLM can approximate user intent.
- **Refinement**: We will inject `Current System Time` into the System Prompt so the LLM *can* handle absolute time conversion if needed.

## Persistence
- **State**: In-Memory (Standard `JobQueue`).
- **Limitation**: If bot restarts, reminders are lost. (Acceptable for Phase 5 MVP "Lite").

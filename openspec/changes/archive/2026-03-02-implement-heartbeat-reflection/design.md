# Design: Heartbeat Reflection

## Logic Flow
1.  **Trigger**: `job_queue` calls `system_heartbeat` every N seconds.
2.  **Context Gathering**:
    -   Time: `datetime.now()`
    -   Hardware: `psutil` (via `HardwareMonitoringSkill` logic)
    -   *Future: Calendar events, Pending Reminders*
3.  **Reflection (LLM)**:
    -   Prompt: "You are the Guardian. Analyze context. Is there something critical the user needs to know? If yes, draft a short friendly message. If no, say 'SILENCE'."
    -   Model: Llama 3 70b (via Groq) is strictly preferred due to speed and instruction following for "SILENCE".
4.  **Action**:
    -   Output == "SILENCE" -> Log "Reflection: Silent" -> **STOP**
    -   Output != "SILENCE" -> Log "Reflection: Speaking" -> Send to Telegram User.

## Safety
-   **Rate Limiting**: The job interval controls frequency.
-   **Context Window**: Keep the context prompt minimal to save tokens.
-   **Persona**: Ensure the message maintains the "Curupira" persona even in proactive mode.

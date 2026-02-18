# Proposal: Heartbeat Reflection (Silent Prompting)

## Goal
Transform Curupira from a reactive bot to a proactive assistant by implementing a "Reflection Loop" within the existing system heartbeat. This addresses **Issue #69**.

## Why
Currently, the `system_heartbeat` only logs "System is healthy". The **Manifesto** calls for "Proactive Humanity". The bot should use this cycle to analyze its state (and user context) to decide *if* it should speak, without being summoned.

## Strategy
1.  **Guardian Loop**: In `AgentBrain`, implement `monitor_and_reflect()`.
2.  **Silent Prompt**: Send a structured prompt to Groq (Llama 3 70b is preferred for speed/cost):
    *   "Current Time: X. System: Y. Reminders: Z. Should I say something? Reply 'SILENCE' or the message."
3.  **Filtration**: If response is "SILENCE" (or close to it), do nothing. If it's a message, send it to the user.
4.  **Interval**: Reuse `HEARTBEAT_INTERVAL` (default 30m) to minimize cost/noise.

## What Changes
1.  **`core/config.py`**: Add `REFLECTION_ENABLED` (default True).
2.  **`core/agent.py`**: Add `reflect(context)` method using Groq API.
3.  **`bot.py`**: Update `system_heartbeat` to call `agent.reflect()` and send messages if needed.
4.  **`skills/`**: Ensure stats gathering is reusable for this context.

## User Review Required
-   **Model Choice**: We will force Groq/Llama3 for this loop if available, as it's the "reflector" (fast/cheap). Is this acceptable?
-   **Silence Protocol**: The bot will be instructed to be "Strictly Silent" unless necessary.

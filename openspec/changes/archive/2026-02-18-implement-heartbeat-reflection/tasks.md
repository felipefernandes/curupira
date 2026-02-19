# Tasks: Implement Heartbeat Reflection

- [x] **Configuration**
  - [x] Add `REFLECTION_ENABLED` and `REFLECTION_MODEL` to `core/config.py`

- [x] **Core Agent Logic**
  - [x] Implement `AgentBrain.reflect(context)`
  - [x] Create system prompt for reflection (enforcing "SILENCE")

- [x] **Bot Integration**
  - [x] Update `system_heartbeat` in `bot.py` to collect context (Stats, Time)
  - [x] Call `brain.reflect()`
  - [x] Handle response: Log silence OR send Telegram message

- [x] **Validation**
  - [x] functionality: Set interval to 1min and observe logs/chat
  - [x] verification: Verify "SILENCE" output is filtered

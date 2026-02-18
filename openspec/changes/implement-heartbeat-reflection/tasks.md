# Tasks: Implement Heartbeat Reflection

- [ ] **Configuration**
  - [ ] Add `REFLECTION_ENABLED` and `REFLECTION_MODEL` to `core/config.py`

- [ ] **Core Agent Logic**
  - [ ] Implement `AgentBrain.reflect(context)`
  - [ ] Create system prompt for reflection (enforcing "SILENCE")

- [ ] **Bot Integration**
  - [ ] Update `system_heartbeat` in `bot.py` to collect context (Stats, Time)
  - [ ] Call `brain.reflect()`
  - [ ] Handle response: Log silence OR send Telegram message

- [ ] **Validation**
  - [ ] functionality: Set interval to 1min and observe logs/chat
  - [ ] verification: Verify "SILENCE" output is filtered

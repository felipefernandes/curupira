# Implementation Tasks

- [x] Define `agent_core` spec delta
- [x] Define `skill_system` spec delta
- [x] Define `mcp_client` spec delta
- [x] Refactor `config.py` to support model tool definitions
- [x] Implement `skills/base.py` (`BaseSkill`)
- [x] Refactor `skills/weather_manager.py` to inherit `BaseSkill`
- [x] Refactor `skills/reminders.py` to inherit `BaseSkill`
- [x] Implement `AgentBrain` in `bot.py` (replacing regex logic)
- [x] Update `bot.py` message handler to use `AgentBrain`
- [x] Verify functionality with `pytest` (mocked LLM calls)
- [x] Manual verification with Telegram

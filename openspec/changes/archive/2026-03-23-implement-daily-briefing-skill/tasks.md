# Tasks: Implement Daily Briefing Skill

- [x] Create `skills/daily_briefing.py` with DailyBriefingSkill class
- [x] Add `daily_briefing` to `_SKILLS_DEFAULTS` in `core/config.py`
- [x] Add `daily_briefing = true` to `[skills]` in `default.config.toml`
- [x] Add `compose_briefing()` method to AgentBrain in `core/agent.py`
- [x] Modify `system_heartbeat` in `bot.py` to trigger daily briefing
- [x] Register DailyBriefingSkill in `bot.py` skill registration section
- [x] Write unit tests in `tests/test_daily_briefing.py`

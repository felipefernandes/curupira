# Design: Daily Briefing Skill

## Architecture

### Flow
1. `system_heartbeat` runs every 30 min (existing)
2. If daily_briefing enabled AND within greeting window AND hasn't sent today:
   a. Call `DailyBriefingSkill.execute()` to gather data
   b. Call `brain.compose_briefing()` with gathered data
   c. Send formatted briefing to user
   d. Mark greeting as sent (via `brain._last_greeting_date`) to prevent duplicate greeting
3. If daily_briefing disabled: existing behavior (simple greeting via reflect)

### Components

#### `skills/daily_briefing.py` - DailyBriefingSkill
- Inherits from `BaseSkill`
- `execute()` gathers data from available skills:
  - Weather (if weather_skill available)
  - Google Calendar events for today (if google_calendar configured)
  - RSS headlines (if rss enabled, pick first configured feed)
- Returns structured JSON with all gathered data
- Handles failures gracefully (if one source fails, include others)

#### `core/agent.py` - AgentBrain.compose_briefing()
- New method that takes briefing data dict
- Sends to LLM with a prompt to compose a natural morning briefing in Portuguese
- Includes "Bom dia" greeting naturally
- Returns formatted text

#### `bot.py` - system_heartbeat modification
- Check if daily_briefing is enabled
- Check if within greeting window AND not already greeted today
- If yes: gather data → compose → send → mark greeting done
- If no: fall through to existing reflect() logic

### Config
- `[skills] daily_briefing = true` in config.toml
- `SKILL_DAILY_BRIEFING_ENABLED` env var
- Default: `true` in `_SKILLS_DEFAULTS`

### Key Decision: Briefing replaces greeting
When daily_briefing is enabled, we skip the reflect() greeting entirely for that day
and instead send the briefing. This avoids duplicate messages.

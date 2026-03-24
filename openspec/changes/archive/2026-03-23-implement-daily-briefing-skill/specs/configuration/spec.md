# Spec: Daily Briefing Configuration

## Config Toggle
- `[skills] daily_briefing = true` in `default.config.toml`
- `SKILL_DAILY_BRIEFING_ENABLED` env var override
- Default: `true`

## Config Loading
- Add `"daily_briefing": True` to `_SKILLS_DEFAULTS` in `core/config.py`
- Uses existing `skill_enabled("daily_briefing")` mechanism

## Behavior
- When `true`: heartbeat triggers briefing during greeting window instead of simple greeting
- When `false`: original "Bom dia" greeting via reflect() (unchanged behavior)

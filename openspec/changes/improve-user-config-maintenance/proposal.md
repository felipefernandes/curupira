# Proposal: Improve User Configuration Maintenance

## Overview
As Curupira evolves, the number of settings (API keys, skill preferences, core behavior) has grown. Currently, these are managed via `.env` files and environment variables, which can be difficult for non-technical users to access and maintain. This proposal introduces a centralized, human-readable configuration file (TOML) to simplify bot management.

## Goals
- Provide a single source of truth for bot configuration (`config.toml`).
- Enable/disable skills via simple `true`/`false` toggles.
- Organize settings into logical categories (AI, Telegram, Skills, Preferences).
- Support env var overrides for advanced users (Docker, CI).
- Simplify the "First Run" experience with a default configuration template.

## Strategy
1. **Introduction of TOML**: Use the `toml` (or `tomli`/`tomli-w`) library to handle configuration.
2. **Unified Loader**: Modify `core/config.py` to load from `config.toml` (if present), then environment variables.
3. **Skill Registry Integration**: Ensure skills in `bot.py` follow the "enabled" flag from the configuration.
4. **Onboarding Integration**: Align configuration with existing `user-facts` when relevant (e.g., default preferences).

## Proposed `config.toml` Structure (Draft)
```toml
[bot]
telegram_token = "..."
authorized_user_id = 0
ai_provider = "groq" # gemini, groq

[ai.gemini]
api_key = "..."
model = "gemini-2.0-flash"

[ai.groq]
api_key = "..."
model = "llama-3.3-70b-versatile"
temperature = 0.7

[skills]
weather = true
reminders = true
job_hunter = true
rss = true
sports = true
github = false

[skills.rss]
feeds = { "G1" = "...", "TechCrunch" = "..." }

[skills.job_hunter]
keywords = ["Python", "AI", "Remote"]
score_cutoff = 0.5
```

## Impact
- **Non-technical Users**: Easier setup and maintenance.
- **Developers**: Faster testing by changing simple flags.
- **Backward Compatibility**: Existing `.env` setups will continue to work (env vars take precedence or act as fallback).

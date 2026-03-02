# Tasks: Centralized Configuration System

## Infrastructure (Preparation)
- [x] Create `default.config.toml` template with current baseline settings.
- [x] Validate `tomllib` is available (Standard in Python 3.11+). Confirmed: Python 3.13.

## Core Logic Changes
- [x] Update `core/config.py` to use `tomllib` for reading `config.toml`.
- [x] Ensure nested TOML tables map to logically grouped config objects (e.g., `config.AI['gemini']`).
- [x] Merge TOML settings with environment variables (Env vars overwrite TOML).
- [x] Implement a helper in `core/config.py` to get "enabled" status of a skill (`skill_enabled()`).

## Skill Integration
- [x] Update `bot.py` registration logic: Check `config.skill_enabled(SKILL_NAME)` before registering.
- [x] Support custom skill preferences from `config.toml` (RSS feeds, JobHunter keywords, Sports API keys).

## Verification (Testing)
- [x] Create `tests/test_config_toml.py` to verify load priority (Env > TOML > Default). 16 tests.
- [x] Run current unit tests to ensure no regressions in backward compatibility. 332 passed.
- [x] Test the bot's behavior when a skill is disabled in `config.toml` (covered by unit tests).

## Documentation & UX
- [x] Update `README.md` section on Quick Start to mention `config.toml`.
- [x] Update `install.sh` to copy `default.config.toml` to `config.toml` on first run.
- [x] Add `config.toml` to `.gitignore` to prevent accidental API key exposure.
- [ ] (Optional) Add a `/status_config` command to verify current loaded config source.

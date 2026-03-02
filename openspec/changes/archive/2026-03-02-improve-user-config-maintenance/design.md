# Design: Centralized Configuration System

## Context
Curupira's configuration is currently fragmented across:
- Environment variables (`.env`).
- JSON for MCP servers (`mcp.json`).
- Hardcoded dictionaries for RSS feeds.
- Hardcoded intervals for heartbeat.

## Architectural Reasoning
A unified TOML configuration system allows:
1. **Human Readability**: TOML is more readable than JSON for non-technical users.
2. **Schema Support**: TOML structures map well to Python dictionaries and nested settings.
3. **Environment Preference**: Maintaining support for environment variables is crucial for secure deployments (Secrets management).

## Configuration Load Order
The proposed priority (highest to lowest):
1. **Environment Variables** (OS environment, typically set by Docker, CI/CD, or manual export).
2. **`.env` File** (Loaded via `python-dotenv`).
3. **`config.toml`** (Primary user configuration).
4. **Default Internal Constants** (Code defaults).

## Proposed Changes

### `core/config.py`
- Introduce a `load_config()` function called at module level.
- Handle `ImportError` for `tomli` (if not available, fall back to environment only).
- Support a secondary `default.config.toml` for templates.

### `bot.py`
- Modify skill registration logic to check `config.SKILLS_ENABLED` dictionary.
- Example:
  ```python
  if config.SKILLS['weather']['enabled']:
      brain.register_skill(WeatherSkill())
  ```

### Directory Structure
```
curupira/
├── config.toml         # User-maintained configuration
├── default.config.toml # Template (version-controlled)
├── core/
│   └── config.py        # Logic to unify and provide settings
```

## Decisions & Trade-offs
- **TOML vs YAML**: TOML is part of the standard Python ecosystem (PEP 518) and simpler to parse without complex dependencies in newer Python versions (`tomllib` in 3.11+).
- **Skill Control**: Adding an `enabled` flag to each skill block allows quick performance tuning and selective bot behavior without deleting code.
- **Backward Compatibility**: To avoid breaking existing setups, the `config.py` module will still export the same uppercase constants.

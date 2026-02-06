# Change: Implement Weather Skill (Phase 6)

## Why
Phase 6 aims to give Curupira "awareness" of the physical world. Answering "Vai chover?" is a classic assistant feature. We need to integrate a Weather API and use the existing Memory system to store the user's location.

## What Changes
- **New Skill**: `skills/weather_manager.py` (Handling Open-Meteo API).
- **Prompt Update**: Instruct LLM to use `[[WEATHER|CITY]]` when weather is requested.
- **Location Logic**:
    - Leverages existing `MemoryManager` to store "user_city" in `facts`.
    - If unknown, the LLM asks the user.
    - If known, the LLM uses it in the command.

## Impact
- **Affected specs**: `weather` (NEW)
- **Affected code**: `bot.py` (Parser), `skills/weather_manager.py` (New), `requirements.txt` (requests/httpx).
- **Dependencies**: `httpx` (Async HTTP client) for calling Open-Meteo.

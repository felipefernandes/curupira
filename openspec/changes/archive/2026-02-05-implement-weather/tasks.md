# Tasks: Implement Weather Skill

## Implementation
- [ ] **Dependencies**
    - [ ] Add `httpx` to `requirements.txt`.
- [ ] **Weather Manager (`skills/weather.py`)**
    - [ ] `get_coordinates(city_name)` (Open-Meteo Geocoding).
    - [ ] `get_forecast(lat, lon)` (Open-Meteo Forecast).
    - [ ] `get_weather_card(city_name)`: Orchestrates fetching and formatting.
- [ ] **Bot Integration (`bot.py`)**
    - [ ] Initialize `WeatherManager`.
    - [ ] Update **System Prompt**: Add instructions for `[[WEATHER|CITY]]` and location fact usage.
    - [ ] Update **Responder**: Detect tag, call `weather_manager.get_weather_card`, and append to response.

## Verification
- [ ] **Manual Test (Explicit)**: "Previsão do tempo para Rio de Janeiro".
- [ ] **Manual Test (Implicit)**: "Moro em São Paulo" (Save fact) -> "Vai chover hoje?" (Use fact).

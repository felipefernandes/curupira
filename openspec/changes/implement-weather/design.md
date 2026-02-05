# Design: Weather Skill

## API Choice: Open-Meteo
- **Pros**: Free, No API Key, Comprehensive (Current + Forecast).
- **Cons**: Requires Lat/Lon.
- **Solution**: Open-Meteo also provides a Geocoding API (`https://geocoding-api.open-meteo.com/v1/search`).
    - Step 1: `search?name=City` -> Get Lat/Lon.
    - Step 2: `forecast?latitude=...` -> Get Weather.

## Architecture: "In-Band Retrieval"
To avoid the complexity (and latency) of a full RAG loop (User -> LLM -> Tool -> LLM -> Response), we will use a **Retrieval-Response** pattern for the MVP.

1.  **Intent**: User asks "Vai chover em Sorocaba?".
2.  **LLM**: Detects context, extracts city. Output: "Vou verificar! [[WEATHER|Sorocaba]]".
    - *Note*: If city is missing, LLM checks `facts`. If still missing, LLM asks user.
3.  **Bot**: Intercepts `[[WEATHER|...]]`.
4.  **WeatherManager**: Fetches data. Structure:
    - Current Temp
    - Rain chance (precipitation_probability)
    - Condition code (mapped to emojis ☀️🌧️).
5.  **Response**: Bot appends a **Formatted Weather Card** to the LLM's initial "Vou verificar!".
    - *Example*:
      "Vou verificar!
       
       🌍 **Previsão para Sorocaba:**
       🌡️ **Agora**: 24°C
       ☔ **Chuva**: 0%
       📅 **Máx/Mín**: 28°C / 18°C"

## Persistence (Location)
- We rely on the existing `System Prompt` instructions regarding user facts.
- "Se o usuário falar onde mora, salve como fato 'user_city'".
- In the Weather instructions: "Use the fact 'user_city' if the user doesn't specify a city in the prompt."

## Future / Alternatives
- Ideally, the LLM would *interpret* the data ("Não vai chover, pode sair tranquilamente").
- However, injecting the API result back into the chat requires a second inference call. For this phase, a static card is sufficient and faster.

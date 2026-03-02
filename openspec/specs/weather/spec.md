# weather Specification

## Purpose
TBD - created by archiving change implement-weather. Update Purpose after archive.
## Requirements
### Requirement: Weather Forecast
The system MUST provide weather information when requested, utilizing external APIs.
The weather response MUST include a human-readable condition description in Portuguese
(e.g., "Céu limpo", "Parcialmente nublado", "Chuva moderada") instead of a raw
WMO weather code integer. The mapping from WMO code to description MUST be resolved
inside the skill before returning data to the LLM.

#### Scenario: Explicit Location
1. User sends: "Como está o tempo em Curitiba?".
2. System identifies intent and city "Curitiba".
3. System displays current temperature, humidity and a readable condition
   description (e.g., "Céu limpo") for Curitiba.
4. The response MUST NOT contain a numeric weather code.

#### Scenario: Implicit Location (Memory)
1. User has previously stated: "Moro em Campinas".
2. System has stored "user_city: Campinas" in facts.
3. User sends: "Vai chover?".
4. System infers location "Campinas".
5. System displays forecast for Campinas with a readable condition description.

#### Scenario: Missing Location
1. System has no location stored.
2. User sends: "Como está o tempo?".
3. System replies asking for the city (e.g., "De qual cidade você gostaria de saber?").

#### Scenario: Unknown WMO Code
1. The Open-Meteo API returns a weather code not present in the internal mapping table.
2. System MUST return a safe fallback string (e.g., "Condição desconhecida (código: 99)")
   instead of crashing or returning a bare integer.


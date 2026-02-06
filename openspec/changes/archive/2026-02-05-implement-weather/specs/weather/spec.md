# Specification: Weather Skill

## ADDED Requirements

### Requirement: Weather Forecast
The system MUST provide weather information when requested, utilizing external APIs.

#### Scenario: Explicit Location
1.  User sends: "Como está o tempo em Curitiba?".
2.  System identifies intent and city "Curitiba".
3.  System displays current temperature and conditions for Curitiba.

#### Scenario: Implicit Location (Memory)
1.  User has previously stated: "Moro em Campinas".
2.  System has stored "user_city: Campinas" in facts.
3.  User sends: "Vai chover?".
4.  System infers location "Campinas".
5.  System displays forecast for Campinas.

#### Scenario: Missing Location
1.  System has no location stored.
2.  User sends: "Como está o tempo?".
3.  System replies asking for the city (e.g., "De qual cidade você gostaria de saber?"). (Handled by LLM naturally).

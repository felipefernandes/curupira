# Spec: Daily Briefing Skill

## Skill Definition
- **name**: `daily_briefing`
- **description**: "Coleta dados de clima, agenda e notícias para montar um briefing diário."
- **skill_group**: `daily_briefing`

## Parameters
```json
{
  "type": "object",
  "properties": {
    "city": {
      "type": "string",
      "description": "Cidade para previsão do tempo (opcional, usa padrão do usuário)"
    }
  },
  "required": []
}
```

## Execute Flow
1. Gather weather data (if WeatherSkill available)
2. Gather today's calendar events (if Google Calendar configured)
3. Gather RSS headlines (if RSS enabled, limit 3 per feed, max 2 feeds)
4. Return `self.success(data)` with structured briefing data

## Return Format
```json
{
  "status": "success",
  "data": {
    "weather": { "location": "...", "temperature": 25, "condition": "..." },
    "events": [{ "summary": "...", "start": "...", "end": "..." }],
    "news": [{ "source": "G1", "title": "...", "link": "..." }]
  }
}
```

## Error Handling
- Each data source is independent; if one fails, others still return
- Missing skills = empty section (not error)
- All errors logged, never crash

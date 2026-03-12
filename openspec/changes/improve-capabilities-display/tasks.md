## 1. BaseSkill — Adicionar metadados de grupo

- [x] 1.1 Adicionar property `skill_group` ao `BaseSkill` em `skills/base.py` com default retornando `self.name`
- [x] 1.2 Adicionar property `skill_group_emoji` ao `BaseSkill` em `skills/base.py` com default `"🔧"`

## 2. IntrospectionSkill — Atualizar lógica de listagem e detalhe

- [x] 2.1 Refatorar `_list_all_skills()` para agrupar tools por `skill_group` e retornar uma entrada por grupo com emoji e resumo das descriptions
- [x] 2.2 Refatorar `_describe_skill()` para aceitar `skill_group` como identificador primário, retornando todos os tools do grupo em formato bullet; manter fallback por `tool.name` exato para compatibilidade

## 3. Declarar grupos nas skills existentes

- [x] 3.1 `skills/mcp_skill.py` — derivar `skill_group` do prefixo do tool name; `skill_group_emoji` via mapa (github → 🐙)
- [x] 3.2 `skills/google_calendar.py` — declarar `skill_group = "calendar"` e `skill_group_emoji = "📅"`
- [x] 3.3 `skills/reminders.py` — declarar `skill_group = "reminders"` e `skill_group_emoji = "⏰"` (4 classes)
- [x] 3.4 `skills/rss.py` — declarar `skill_group = "rss"` e `skill_group_emoji = "📰"` (2 classes)
- [x] 3.5 `skills/weather_manager.py` — declarar `skill_group = "weather"` e `skill_group_emoji = "🌦️"`
- [x] 3.6 `skills/hardware.py` e `skills/system_control.py` — declarar `skill_group = "system"` e `skill_group_emoji = "🖥️"`
- [x] 3.7 `skills/job_hunter.py` — declarar `skill_group = "jobs"` e `skill_group_emoji = "💼"` (2 classes)
- [x] 3.8 `skills/sports_manager.py` — declarar `skill_group = "sports"` e `skill_group_emoji = "⚽"`
- [x] 3.9 `skills/usage_report.py` — declarar `skill_group = "usage"` e `skill_group_emoji = "📊"`
- [x] 3.10 `skills/memory.py` e `skills/time.py` — declarar `skill_group = "system"`

## 4. Verificação manual

- [x] 4.1 Iniciar o bot localmente e perguntar "O que você sabe fazer?" — verificar que a resposta lista ~8-10 grupos com emoji, uma linha por grupo
- [x] 4.2 Perguntar "Me explica o GitHub" — verificar que o bot retorna os 3 tools do grupo em bullet points
- [x] 4.3 Perguntar detalhes de uma skill inexistente — verificar que o bot informa o erro e exibe o resumo agrupado

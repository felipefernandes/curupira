# Change: Fix weather skill returning raw WMO condition code to the user

## Why

A skill de previsão do tempo retorna ao LLM um campo `condition_code` contendo
um número inteiro do padrão WMO (World Meteorological Organization), como `2`.
O LLM frequentemente repassa esse código diretamente na resposta ao usuário,
resultando em mensagens sem sentido como "O código de condição é 2." (Issue #122).

## What Changes

- `skills/weather_manager.py` — substituir o campo `condition_code` (inteiro bruto)
  por `condition` (string legível em português), mapeado via tabela WMO interna
  antes de retornar ao LLM.
- `openspec/specs/weather/spec.md` — modificar o requisito existente para
  especificar que a resposta DEVE incluir uma descrição textual da condição.

## Impact

- Affected specs: `weather`
- Affected code: `skills/weather_manager.py`
- Backward compatible: sim — apenas substitui um campo interno do payload JSON
  entre a skill e o LLM; o usuário final verá linguagem natural em vez de um número.

## Tasks

### 1. Implementação

- [x] 1.1 Adicionar tabela de mapeamento WMO → descrição PT-BR em `skills/weather_manager.py`
      (cobre os códigos 0–99 conforme documentação Open-Meteo)
- [x] 1.2 Criar função `_wmo_description(code: int) -> str` que retorna a descrição
      ou fallback `"Condição desconhecida (código: {code})"` para códigos ausentes
- [x] 1.3 Substituir `"condition_code": current.get("weather_code")` por
      `"condition": _wmo_description(current.get("weather_code", -1))`
      no payload retornado pelo método `execute()`

### 2. Testes

- [x] 2.1 Adicionar testes unitários em `tests/test_weather_manager.py` cobrindo:
      - Código conhecido → descrição correta em PT-BR (ex: `0` → `"Céu limpo"`)
      - Código de borda (ex: `99` → "Trovoada com granizo intenso")
      - Código desconhecido (ex: `-1` ou `999`) → fallback com o número
- [x] 2.2 Garantir que o campo `condition_code` NÃO está mais presente no payload
      retornado pela skill

### 3. Validação

- [x] 3.1 Executar suite completa de testes: `pytest --tb=short -q`
      → 351 passed, 1 skipped
- [ ] 3.2 Verificar manualmente no Telegram com "Como está o tempo em São Paulo?"
      e confirmar que a resposta não contém número bruto

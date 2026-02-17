# Change: Fix Groq Tool Calls

## Why
O modelo Llama 3 via Groq API ocasionalmente gera chamadas de função malformadas, concatenando argumentos JSON ao nome da ferramentas (ex: `get_weather {"city": "São Paulo"}`). A API do Groq valida o nome contra a lista de tools disponíveis e retorna erro 400 `tool_use_failed`, impedindo qualquer interação com o bot.

## What Changes
- Adicionar instrução explícita (negative constraint) ao `system_prompt` em `core/agent.py` para proibir concatenação de argumentos no nome da função
- Affected specs: `tool-execution`

## Impact
- Affected specs: `tool-execution` (nova capability)
- Affected code: `core/agent.py` (método `process`, bloco `system_prompt`)
- Sem **BREAKING** changes — a alteração é aditiva ao prompt e não afeta a interface externa

# Design: Fix Groq Tool Calls

## Context
O modelo Llama 3 via Groq API tem tendência a alucinar o formato de tool calls, inserindo JSON de argumentos no campo de nome ou concatenando-o (ex: `get_weather {"city": "São Paulo"}` ou `list_reminders={}`). Isso gera erro 400 `tool_use_failed` na API do Groq, que valida o nome da função gerada contra a lista de ferramentas antes de retornar ao cliente.

## Goals / Non-Goals
- **Goals**: Reduzir a incidência de tool calls malformadas usando prompt engineering
- **Non-Goals**: Não vamos modificar a camada de parsing/repair do `agent.py` (já existem workarounds para XML e nome+args no código, mas o erro 400 impede que cheguem a ser usados)

## Decisions
- **Decision**: System Prompt Hardening — adicionar instrução negativa explícita ao prompt
- **Alternatives considered**:
  - Output Parsing/Repair: Inviável porque o erro 400 ocorre na camada da API do Groq antes da resposta chegar ao cliente
  - Trocar de modelo: Desproporcional; o modelo funciona bem na maioria dos casos

## Risks / Trade-offs
- Prompts mais longos consomem mais tokens → Impacto mínimo (uma linha adicional)
- A instrução pode não eliminar 100% das alucinações → O código existente em `agent.py` (linhas 257-272) já trata o caso como fallback quando a resposta chega ao cliente

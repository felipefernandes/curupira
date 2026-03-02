# Change: Track Token Usage

## Why
Atualmente o bot consome APIs externas (Groq, Gemini) sem registrar internamente o volume de tokens utilizado (prompt_tokens, completion_tokens). Isso dificulta que o usuário saiba quanto está gastando ou se está próximo dos limites de seu plano. A Issue #127 demanda uma funcionalidade de introspecção que capture a meta-informação de uso destas requisições, armazene num banco local e permita ao usuário consultar gastos convertidos monetariamente por meio de uma skill.

## What Changes
1. **MemoryManager (`core/memory.py`)**: Criar tabela `token_usage` para persistir dados associados ao `provider`, `model`, `prompt_tokens`, `completion_tokens` e `timestamp`. Adicionar métodos como `log_token_usage` e `get_usage_summary`.
2. **LLM Client (`core/agent.py`)**: Interceptar os objetos de resposta (`response.usage` no OpenAI/Groq, `response.usage_metadata` no Gemini) dentro das ramificações assíncronas de conversação e função `process`, salvando o uso no DB via `MemoryManager`.
3. **Skill (`skills/usage_report.py`)**: Criar uma skill chamada `UsageReportSkill` que executa `get_usage_summary` da memória, converte opcionalmente com taxas conhecidas (em config ou constantes mapeadas) e devolve um resumo textual do uso.
4. **Boot/Registro (`bot.py` e `config.toml`)**: Registrar a skill em questão e permitir opcionalmente gerenciar as taxas.

## Impact
- Affected specs: `monitoring` e `introspection`.
- Affected code: `core/agent.py`, `core/memory.py`, `skills/usage_report.py`.
- Benefício chave: Controle detalhado do tráfego das LLMs, transparência de custos para o usuário, e rastreamento local das transações cognitivas do Curupira.

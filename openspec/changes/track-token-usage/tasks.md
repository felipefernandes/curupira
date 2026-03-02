# Ordem Lógica (Track Token Usage)

1. [ ] Atualizar o SQLite `core/memory.py`:
  - Adicionar a tabela `token_usage` no schema. 
  - Colunas: `id (INTEGER)`, `provider (TEXT)`, `model (TEXT)`, `prompt_tokens (INTEGER)`, `completion_tokens (INTEGER)`, `timestamp (DATETIME)`.
  - Criar `log_token_usage(provider, model, prompt_tokens, completion_tokens)`: Insere nova medição.
  - Criar `get_usage_summary()`: Retorna um report consolidado em dicionário agrupando os gastos por provedor e totalizando promt_tokens vs completion_tokens.
2. [ ] Modificar `core/agent.py` para processar custos:
  - Recuperar a métrica `usage` nos objetos `client.chat.completions` (Groq/OpenAI) e `response.usage_metadata` (Google).
  - Adicionar a ponte no `bot.py` para injetar `memory_manager` dentro do `context` ou via refatoração no `AgentBrain`. Se `memory_manager` estiver em dict context associado a chave local, use para chamar o método `log_token_usage` após cada geração finalizada da requisição à LLM.
3. [ ] Criar a Skill `get_usage_report`:
  - Arquivo `skills/usage_report.py`.
  - Essa skill consulta o método `get_usage_summary()` em `memory_manager`.
  - Devolve um output formatado pro curupira de quantos tokens foram usados em prompt e output por Provider, convertendo uma tabela genérica em reais ou dólares na formatação (ex: 1M tokens custa $X).
4. [ ] Atualizar Instalação/Configuração:
  - Registar a skill `UsageReportSkill` no array de `_SKILLS_DEFAULTS` no config e adicioná-la no `bot.py`.
  - Atualizar testes (ex. `core/tests/test_memory.py` ou isolado).

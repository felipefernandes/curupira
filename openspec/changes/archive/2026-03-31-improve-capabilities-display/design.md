## Context

A `IntrospectionSkill` atual em `skills/introspection.py` lista todos os tools registrados em `self._agent.skills` de forma plana — cada entrada é um `BaseSkill` individual. Skills com múltiplos tools (ex: GitHub com `list_repos`, `list_issues`, `create_issue`) aparecem como 3 linhas distintas, resultando em ~18 itens na resposta.

O `BaseSkill` não tem conceito de agrupamento: só possui `name`, `display_name`, e `description`. A mudança precisa ser backward-compatible — skills existentes não devem precisar de refactor imediato.

Faz parte da issue #160 do github.


## Goals / Non-Goals

**Goals:**
- Adicionar `skill_group` e `skill_group_emoji` ao `BaseSkill` (com defaults)
- Atualizar `_list_all_skills()` para agrupar por `skill_group` e emitir uma linha por grupo
- Atualizar `_describe_skill()` para aceitar um `skill_group` e retornar todos os tools daquele grupo
- Skills sem `skill_group` explícito se agrupam individualmente (comportamento atual preservado)

**Non-Goals:**
- Refatorar todas as skills existentes de uma vez (pode ser feito incrementalmente)
- Criar UI de menu interativo ou botões inline do Telegram
- Persistir estado de grupo em banco de dados
- Alterar a assinatura de `execute()` ou o formato MCP-Lite de `success()`/`error()`

## Decisions

### 1. Adicionar `skill_group` e `skill_group_emoji` ao `BaseSkill`

**Decisão**: Adicionar duas properties opcionais com defaults em `BaseSkill`:
- `skill_group: str` — nome do grupo (default: o próprio `name` da skill)
- `skill_group_emoji: str` — emoji do grupo (default: `"🔧"`)

**Alternativas consideradas**:
- Extrair agrupamento de `display_name` por convenção (ex: `"🐙 GitHub — ..."`) → frágil, depende de parsing de string
- Registrar grupos num dict externo em `bot.py` → acoplamento desnecessário fora do Skills Framework
- Usar metadados em arquivo YAML/JSON separado → overhead desnecessário para o Raspberry Pi

**Rationale**: Properties com defaults em `BaseSkill` são zero-overhead, backward-compatible, e seguem o padrão já estabelecido de `display_name`.

### 2. Agrupamento dinâmico em `_list_all_skills()`

**Decisão**: Ao listar, iterar `self._agent.skills`, agrupar por `skill_group`, e para cada grupo emitir:
```
{emoji} {group_name} — {resumo das descriptions dos tools do grupo}
```
O resumo é construído concatenando as `description`s dos tools do grupo (truncadas se necessário).

**Alternativas consideradas**:
- Fazer o LLM resumir os tools → latência e custo desnecessários para algo determinístico
- Usar apenas a description do primeiro tool do grupo → perde contexto das outras capacidades

### 3. `describe_capabilities(skill_name)` aceita nome de grupo OU nome de tool

**Decisão**: O parâmetro `skill_name` passa a ser interpretado como `skill_group` primeiro. Se nenhum grupo bate, tenta match por `tool.name` exato (compatibilidade retroativa).

**Rationale**: O usuário dirá "me explica o GitHub", não "me explica o `list_repos`". Não quebra chamadas existentes que passam o `tool.name` diretamente.

## Risks / Trade-offs

- **Skills sem `skill_group` declarado aparecem individualmente** → comportamento atual, aceitável durante migração incremental
- **Resumo gerado por concatenação pode ficar verboso** → mitigado com truncamento simples (ex: max 80 chars para o resumo do grupo)
- **Nenhuma dependência nova, nenhum I/O, nenhum estado persistido** → risco mínimo para o Raspberry Pi

## Migration Plan

1. Adicionar properties `skill_group` / `skill_group_emoji` ao `BaseSkill` com defaults
2. Atualizar `IntrospectionSkill._list_all_skills()` e `_describe_skill()`
3. Atualizar skills existentes para declarar seu grupo (GitHub, RSS, Calendar, Reminders, etc.)
4. Testar manualmente via Telegram perguntando "o que você faz" e "me explica o GitHub"

**Rollback**: Reverter apenas `skills/introspection.py` e `skills/base.py` — sem migração de dados.

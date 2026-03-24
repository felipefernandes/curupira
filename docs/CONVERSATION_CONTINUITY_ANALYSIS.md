# 🔗 Análise: Perda de Continuidade Conversacional no Curupira

**Data**: 2026-03-24
**Status**: Causa raiz identificada + Soluções propostas
**Equipe**: memory-continuity team (codebase-investigator + solution-architect + team-lead)
**Prioridade**: 🔴 **CRÍTICA** - Impacta experiência fundamental do bot

---

## 🚨 O Problema

O Curupira **perde contexto entre turnos adjacentes** da mesma conversa, causando:

### Cenário 1: Job Hunter
```
Bot: "Encontrei 2 vagas: Splitero e OutraEmpresa. Quer mais informações?"
User: "Me fale sobre a Splitero"
Bot: "Desculpe, não entendo. Como posso ajudar?"
```

### Cenário 2: Continuidade de Diálogo
```
User: "Me conte uma piada"
Bot: [conta piada] "Quer mais piadas?"
User: "Quero mais"
Bot: "Olá! Sou o Curupira. Como posso ajudar?" [RESET COMPLETO]
```

**Padrão identificado**: O bot executa tarefas, mas **não mantém diálogo contextualizado**. Ele responde como se cada mensagem fosse a primeira interação.

---

## 🔍 Causa Raiz (Investigação Técnica)

### 🎯 Problema Principal: Histórico como Texto Plano

**Arquivo**: [`core/agent.py:771-773`](core/agent.py#L771-L773) (Groq) e [`core/agent.py:1025-1029`](core/agent.py#L1025-L1029) (Gemini)

#### Como funciona HOJE (❌ Errado):
```python
# Groq
messages = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": f"Histórico:\n{chat_history}\n\nMensagem Atual: {user_msg}"}
]
```

O histórico é **concatenado como texto** dentro de uma mensagem de usuário. Para a LLM, isso não é uma conversa multi-turno real - é apenas um bloco de texto descrevendo conversas passadas.

#### Como DEVERIA ser (✅ Correto):
```python
messages = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": "busque vagas de emprego"},
    {"role": "assistant", "content": "Encontrei 2 vagas: Splitero e..."},
    {"role": "user", "content": "me fale sobre a Splitero"}  # ← Contexto real preservado
]
```

---

### 🔴 Problemas Identificados

| # | Problema | Severidade | Arquivo | Impacto |
|---|----------|-----------|---------|---------|
| **1** | Histórico como texto plano (não multi-turn) | **CRÍTICA** | [`agent.py:771-773`](core/agent.py#L771-L773) | LLM não entende conversas anteriores como turnos reais |
| **2** | Janela fixa de 30 minutos | **ALTA** | [`bot.py:216`](bot.py#L216) | Conversas >30min perdem TODO o contexto |
| **3** | Tool results não persistidos | **ALTA** | [`bot.py:269`](bot.py#L269) | Job Hunter menciona "Splitero", mas resultado da skill não fica no histórico |
| **4** | Limite de 20 mensagens | **MÉDIA** | [`memory.py:185`](skills/memory.py#L185) | Conversas longas perdem início |
| **5** | Jobs sem contexto | **BAIXA** | [`bot.py:324`](bot.py#L324) | Tasks agendadas rodam com `chat_history=[]` |

---

### 📊 Fluxo Atual (Problema Detalhado)

```
1. User: "busque vagas de emprego"
   └─> Salvo em conversations: role=user, content="busque vagas"

2. Bot executa job_hunter (skill)
   └─> Encontra: {Splitero: {cargo: "Dev", salário: "10k"}}
   └─> ⚠️ Tool result NÃO é salvo no DB

3. Bot responde: "Encontrei 2 vagas: Splitero e..."
   └─> Salvo em conversations: role=model, content="Encontrei 2 vagas..."
   └─> ⚠️ Mas os DADOS das vagas não estão no texto

4. User: "me fale sobre a Splitero" (5 segundos depois)
   └─> get_context() busca últimas 20 msgs dos últimos 30 min
   └─> Retorna: "User: busque vagas\nModel: Encontrei 2 vagas..."
   └─> ⚠️ Não há menção a "Splitero" nos dados recuperados

5. Bot recebe prompt:
   "Histórico:
   User: busque vagas de emprego
   Model: Encontrei 2 vagas...

   Mensagem Atual: me fale sobre a Splitero"

   └─> LLM: "Não tenho informações sobre Splitero no contexto" ❌
```

**Por que falha?**: O nome "Splitero" só apareceu na **resposta textual** do bot, não nos **dados estruturados** que o bot tinha acesso. Quando o contexto é reconstruído, a LLM só vê texto, não os dados originais.

---

## 🏗️ Soluções Propostas

### ✅ **Solução 1: Migrar para Mensagens Estruturadas** (Recomendada)
**Complexidade**: Alta | **Impacto**: Resolve 100% do problema

#### Mudanças necessárias:

**A) [`skills/memory.py`](skills/memory.py) - Retornar lista de mensagens**
```python
async def get_context(self, user_id, limit=20, minutes_ago=30):
    # Antes: retorna string formatada
    # Depois: retorna List[Dict]
    messages = []
    async with aiosqlite.connect(self.db_path) as db:
        async with db.execute("""
            SELECT role, content FROM conversations
            WHERE user_id = ? AND timestamp >= ?
            ORDER BY id ASC LIMIT ?
        """, (user_id, cutoff_time, limit)) as cursor:
            async for role, content in cursor:
                messages.append({"role": role, "content": content})
    return messages
```

**B) [`core/agent.py:771-773`](core/agent.py#L771-L773) - Construir array de mensagens**
```python
# Groq
messages = [{"role": "system", "content": system_prompt}]
messages.extend(chat_history)  # chat_history agora é List[Dict]
messages.append({"role": "user", "content": user_msg})
```

**C) [`bot.py:216`](bot.py#L216) - Passar lista em vez de string**
```python
context_history = await memory_manager.get_context(user_id, limit=20, minutes_ago=120)
# Agora retorna List[Dict], não string
```

**Benefícios**:
- ✅ LLM entende conversas como turnos reais (comportamento nativo)
- ✅ Melhor qualidade de resposta em todos os cenários
- ✅ Elimina formatação manual de texto
- ✅ Prepara terreno para adicionar tool_calls estruturados no futuro

---

### 🟡 **Solução 2: Session Context Buffer** (Quick Win)
**Complexidade**: Baixa | **Impacto**: Resolve 70-80% do problema

#### Conceito:
Salvar **tool results** no SQLite para que sejam incluídos no contexto.

**Nova tabela**:
```sql
CREATE TABLE session_context (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    session_id TEXT,
    type TEXT,  -- 'tool_result' ou 'metadata'
    skill_name TEXT,
    content TEXT,  -- JSON com resultado da skill
    timestamp DATETIME
);
```

**Fluxo**:
```python
# Em bot.py, após executar skill
tool_result = await brain.process(...)
await memory_manager.log_tool_result(
    user_id=user_id,
    skill_name="job_hunter",
    result={"vagas": [{"empresa": "Splitero", ...}]}
)

# Em memory.py get_context()
context = await get_conversations(user_id, limit=20)
tool_results = await get_recent_tool_results(user_id, minutes_ago=120)
return format_context_with_tools(context, tool_results)
```

**Benefícios**:
- ✅ Implementação rápida (1-2 horas)
- ✅ Não quebra código existente
- ✅ Resolve cenário do Job Hunter especificamente

**Limitações**:
- ❌ Ainda usa texto plano (não resolve problema fundamental)
- ❌ Aumenta consumo de tokens (tool results podem ser grandes)

---

### 🟢 **Recomendação Final: Estratégia em 2 Fases**

#### **Fase 1 (Urgente - 2-3 horas)**: Solução 2 (Session Context Buffer)
- Resolve o problema imediato do Job Hunter
- Buy time para planejar refactor maior

#### **Fase 2 (Strategic - 1-2 dias)**: Solução 1 (Mensagens Estruturadas)
- Refactor completo para arquitetura correta
- Implementar incrementalmente (Groq primeiro, depois Gemini)
- Adicionar testes de regressão

---

## ⚙️ Configurações a Ajustar

### 1. TTL da Sessão
**Atual**: 30 minutos ([`bot.py:216`](bot.py#L216))
**Recomendado**: 2-4 horas (ou até usuário iniciar nova conversa explicitamente)

```python
# Em config.py
SESSION_TTL_MINUTES = 240  # 4 horas
SESSION_MESSAGE_LIMIT = 50  # aumentar de 20 para 50
```

### 2. Limite de Mensagens
**Atual**: 20 mensagens
**Recomendado**: 50 mensagens (ou token-based limit)

### 3. Tool Results Truncation
Para evitar overflow de tokens, truncar tool results grandes:
```python
MAX_TOOL_RESULT_CHARS = 2000  # ~500 tokens
```

---

## 📈 Comparação de Impacto

| Métrica | Atual | Solução 2 (Buffer) | Solução 1 (Estruturado) |
|---------|-------|-------------------|-------------------------|
| **Continuidade de diálogo** | ❌ 3/10 | 🟡 7/10 | ✅ 10/10 |
| **Tokens/turno** | ~800 | ~1200 (+50%) | ~900 (+12%) |
| **Latência** | 0ms | +5ms | 0ms |
| **Qualidade de resposta** | 6/10 | 7/10 | 9/10 |
| **Tempo de implementação** | - | 2-3h | 6-8h |
| **Risco de regressão** | - | Baixo | Médio |

---

## 🛠️ Plano de Implementação

### **Fase 1: Quick Fix (2-3 horas)**
- [ ] Criar tabela `session_context` no SQLite
- [ ] Adicionar `log_tool_result()` em [`memory.py`](skills/memory.py)
- [ ] Modificar [`bot.py:269`](bot.py#L269) para salvar tool results
- [ ] Atualizar `get_context()` para incluir tool results
- [ ] Testar com Job Hunter
- [ ] Aumentar TTL para 120 minutos

### **Fase 2: Refactor Estrutural (1-2 dias)**
- [ ] Modificar `get_context()` para retornar `List[Dict]`
- [ ] Atualizar [`agent.py`](core/agent.py) (Groq) para array de mensagens
- [ ] Atualizar [`agent.py`](core/agent.py) (Gemini) para contents estruturados
- [ ] Adicionar testes de integração
- [ ] Validar com conversas longas (>20 turnos)
- [ ] Deploy incremental (feature flag?)

---

## ❓ Questões para Decisão

1. **Preferência de implementação**: Fase 1 apenas, ou direto para Fase 2?
2. **TTL ideal**: 2 horas, 4 horas, ou até logout explícito?
3. **Tool results**: Sempre incluir, ou só quando relevante (keyword detection)?
4. **Jobs automáticos**: Devem ter acesso a histórico de conversa, ou continuar isolados?
5. **Migração de dados**: Conversas antigas no formato texto devem ser convertidas?

---

## 🔗 Relação com MEMORY_ENHANCEMENT_ANALYSIS.md

**Documento anterior** ([`MEMORY_ENHANCEMENT_ANALYSIS.md`](MEMORY_ENHANCEMENT_ANALYSIS.md)):
- **Escopo**: Memória de **longo prazo** (>30 min, dias/semanas atrás)
- **Solução**: FTS5, RAG, sumarização
- **Foco**: "Lembrar aquela conversa de semana passada sobre café"

**Este documento**:
- **Escopo**: Contexto **imediato** (segundos/minutos, mesma conversa)
- **Solução**: Mensagens estruturadas, session buffer
- **Foco**: "Lembrar o que acabei de falar 30 segundos atrás"

**São problemas complementares**, não excludentes. Ambos devem ser implementados:
- **Este documento primeiro** (urgente - quebra experiência básica)
- **MEMORY_ENHANCEMENT depois** (melhoria incremental - busca em histórico antigo)

---

## 📚 Arquivos Modificados (Referência Rápida)

| Arquivo | Linhas | Mudança |
|---------|--------|---------|
| [`skills/memory.py`](skills/memory.py) | 185-203 | `get_context()` retornar List[Dict] |
| [`core/agent.py`](core/agent.py) | 771-773 | Construir array de mensagens (Groq) |
| [`core/agent.py`](core/agent.py) | 1025-1029 | Construir contents estruturados (Gemini) |
| [`bot.py`](bot.py) | 216 | Passar list em vez de string |
| [`bot.py`](bot.py) | 269 | Salvar tool results (Fase 1) |
| [`core/config.py`](core/config.py) | - | Adicionar SESSION_TTL_MINUTES |

---

## 🎬 Próximos Passos

**Decisão necessária**: Qual caminho seguir?

1. **🚀 Quick Fix (Fase 1)**: Implementar Session Context Buffer agora (2-3h)
2. **🏗️ Refactor Completo (Fase 2)**: Ir direto para mensagens estruturadas (1-2 dias)
3. **📋 Planejamento**: Criar issues/tasks detalhadas antes de começar

**Recomendação da equipe**: Começar com Fase 1 hoje, planejar Fase 2 para próxima semana.

---

**Status**: ✅ Análise completa | 🟡 Aguardando decisão de implementação

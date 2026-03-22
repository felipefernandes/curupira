# 🧠 Análise: Memória Inteligente para Curupira (Diet-Compatible)

**Autor**: Análise Técnica
**Data**: 2026-03-03
**Status**: Proposta de Arquitetura
**Contexto**: [Issue/Feature Request - Memória mais inteligente]

---

## 🎯 Objetivo

Melhorar a capacidade de recuperação de contexto do Curupira, permitindo:
- **Lembrar conversas antigas** (além de 30 minutos)
- **Buscar informações por relevância** (não apenas por tempo)
- **Relacionar conceitos** (ex: "aquela vez que falamos sobre café" → conversa de 2 semanas atrás)

**Restrição Hard**: Manter compatibilidade com **Raspberry Pi 3 (1GB RAM)** e filosofia **Diet** (offboard processing).

---

## 📊 Análise de Opções

### **Opção 1: RAG Híbrido (Embeddings Offboard)**

#### Arquitetura
```
┌─────────────┐
│ Raspberry Pi│
│  (SQLite)   │  ──► Armazena apenas texto + metadata
└──────┬──────┘
       │
       │ Quando precisa buscar
       ▼
┌─────────────┐
│  API Cloud  │  ──► Groq/Gemini gera embeddings
│ (Embeddings)│      e faz busca semântica
└─────────────┘
```

#### Prós
- ✅ **Zero impacto de RAM local** (embeddings não ficam no Pi)
- ✅ Usa APIs que já pagamos (Groq tem embedding grátis via `llama-3-8b`)
- ✅ Mantém SQLite como fonte única de verdade

#### Contras
- ❌ Latência extra (1 chamada API por busca de memória)
- ❌ Custo de tokens (embedding de conversas antigas)
- ❌ Dependência de rede

#### Implementação Estimada
```python
# Pseudo-código
async def semantic_search(query: str, user_id: int, top_k: int = 5):
    # 1. Gerar embedding da query (Groq API)
    query_embedding = await groq_embed(query)

    # 2. Buscar no SQLite por similaridade (cosine)
    # Embeddings armazenados como JSON/BLOB
    results = await db.execute("""
        SELECT content,
               cosine_similarity(embedding, ?) as score
        FROM conversations
        WHERE user_id = ?
        ORDER BY score DESC LIMIT ?
    """, (query_embedding, user_id, top_k))

    return results
```

**Custo**: ~5-10ms latência + ~500 tokens/busca

---

### **Opção 2: Sumarização Hierárquica (Sem Embeddings)**

#### Arquitetura
```
Conversas antigas (> 30 min)
       ↓
   Sumarizadas periodicamente pela LLM
       ↓
Armazenadas como "memory_snapshots" no SQLite
       ↓
Injetadas no contexto como "Resumo de conversas passadas"
```

#### Prós
- ✅ **Zero dependência de embeddings**
- ✅ Reduz drasticamente o tamanho da memória (10 msgs → 1 parágrafo)
- ✅ Mantém 100% local (SQLite)
- ✅ Compatível com qualquer LLM

#### Contras
- ❌ Perde granularidade (não recupera mensagens exatas)
- ❌ Custo de tokens na sumarização (mas pode ser feito offline)

#### Implementação Estimada
```python
# Job assíncrono (roda 1x/dia)
async def summarize_old_conversations(user_id: int):
    # 1. Pegar conversas de 1-7 dias atrás (ainda não sumarizadas)
    old_convos = await db.get_conversations(
        user_id,
        days_ago_start=1,
        days_ago_end=7
    )

    # 2. Pedir para LLM sumarizar
    summary = await llm.complete(
        f"Resuma as seguintes conversas em 2-3 parágrafos:\n{old_convos}"
    )

    # 3. Salvar no SQLite
    await db.save_memory_snapshot(user_id, summary, period="last_week")
```

**Custo**: ~2000 tokens/dia (sumarização) | **0 tokens** na recuperação

---

### **Opção 3: Híbrido - BM25 (TF-IDF Local)**

#### Arquitetura
```python
# Busca por palavras-chave (sem embeddings)
# Usando algoritmo BM25 (usado pelo Google Search antes de ML)

import sqlite3
# SQLite já tem FTS5 (Full-Text Search) nativo!

CREATE VIRTUAL TABLE conversations_fts USING fts5(
    content,
    user_id UNINDEXED
);
```

#### Prós
- ✅ **Busca semântica "boa o suficiente"** (baseada em TF-IDF)
- ✅ **Zero dependências externas** (FTS5 é nativo do SQLite)
- ✅ **RAM mínima** (~10KB de índice por 1000 mensagens)
- ✅ **Velocidade brutal** (<5ms por query)

#### Contras
- ❌ Não entende sinônimos (buscar "carro" não acha "automóvel")
- ❌ Sensível a typos

#### Implementação Estimada
```python
# Migration para adicionar FTS
async def migrate_to_fts():
    await db.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS conversations_fts
        USING fts5(content, user_id UNINDEXED)
    """)

    # Popular com dados existentes
    await db.execute("""
        INSERT INTO conversations_fts(content, user_id)
        SELECT content, user_id FROM conversations
    """)

# Uso
async def search_memory(query: str, user_id: int):
    results = await db.execute("""
        SELECT content, rank
        FROM conversations_fts
        WHERE conversations_fts MATCH ? AND user_id = ?
        ORDER BY rank
        LIMIT 5
    """, (query, user_id))
    return results
```

**Custo**: 0 tokens | 0 dependências | <5ms latência

---

## 🏆 Recomendação (Abordagem Pragmática)

### **Estratégia em Camadas (Melhor Custo-Benefício)**

```
┌─────────────────────────────────────────────┐
│ Layer 1: Contexto Imediato (atual)         │
│ - Últimas 20 msgs dos últimos 30 min       │
│ - 0 custo, latência zero                   │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│ Layer 2: FTS5 (Busca por palavras-chave)   │
│ - SQLite nativo, busca em conversas antigas│
│ - Ativado quando o agente precisa "lembrar"│
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│ Layer 3: Snapshots Sumarizados (semanal)   │
│ - Resumo de conversas de 1-4 semanas atrás │
│ - Gerado offline (1x/semana)               │
└─────────────────────────────────────────────┘
```

### **Fluxo de Uso**

```python
async def get_intelligent_context(user_id: int, current_message: str):
    # Layer 1: Sempre incluir (grátis)
    recent = await memory.get_context(user_id, limit=20, minutes_ago=30)

    # Layer 2: Se a mensagem menciona "lembra quando...", "você disse que..."
    if requires_memory_search(current_message):
        related = await memory.fts_search(current_message, user_id, limit=3)
    else:
        related = []

    # Layer 3: Sempre incluir snapshots (overhead baixo)
    snapshots = await memory.get_snapshots(user_id, weeks_ago=4)

    return {
        "recent_context": recent,
        "related_memories": related,
        "long_term_summary": snapshots
    }
```

---

## 📈 Comparação de Performance

| Métrica | Atual | Opção 1 (RAG) | Opção 2 (Sumarização) | **Opção 3 (Híbrido)** |
|---------|-------|---------------|------------------------|------------------------|
| **RAM no Pi** | ~50MB | ~50MB | ~60MB | ~55MB |
| **Latência/busca** | 0ms | 100-200ms | 0ms | <5ms |
| **Custo tokens/dia** | ~5k | ~15k | ~7k | ~5k |
| **Setup** | ✅ Pronto | 🔧 Complexo | 🔧 Médio | ✅ Simples |
| **Qualidade** | 6/10 | 9/10 | 7/10 | **8/10** |

---

## 🛠️ Plano de Implementação (Opção Híbrida)

### **Fase 1: FTS5 Migration** (~2-3 horas)
- [ ] Criar tabela `conversations_fts` com FTS5
- [ ] Migrar conversas existentes
- [ ] Adicionar triggers para auto-atualização
- [ ] Testes de busca

### **Fase 2: Skill de Busca Semântica** (~1-2 horas)
- [ ] Criar `SearchMemorySkill` (permite agente buscar memórias antigas)
- [ ] Integrar no prompt do agente
- [ ] Testes com queries reais

### **Fase 3: Sumarização Periódica** (~3-4 horas)
- [ ] Job semanal para sumarizar conversas antigas
- [ ] Tabela `memory_snapshots`
- [ ] Injeção automática no contexto
- [ ] Dashboard de memória (opcional)

**Total Estimado**: 6-9 horas de desenvolvimento

---

## 🔬 Experimento Proposto

### **MVP Rápido (1 hora)**
Testar FTS5 com os dados atuais:

```bash
# No Pi, abrir SQLite
sqlite3 data/curupira.db

# Criar FTS
CREATE VIRTUAL TABLE conversations_fts USING fts5(content, user_id UNINDEXED);
INSERT INTO conversations_fts(content, user_id) SELECT content, user_id FROM conversations;

# Testar busca
SELECT content FROM conversations_fts WHERE conversations_fts MATCH 'café' LIMIT 5;
```

Se o resultado for satisfatório → **Go para implementação completa**

---

## ❓ Questões Abertas

1. **Quantas conversas antigas você quer manter indexadas?**
   - Opção A: Últimos 30 dias (balance custo/utilidade)
   - Opção B: Últimos 90 dias
   - Opção C: Tudo (lifetime)

2. **Quando ativar busca inteligente?**
   - Opção A: Sempre (+ latência constante)
   - Opção B: Apenas quando detectar keywords ("lembra", "você disse")
   - Opção C: Skill explícita (agente decide quando usar)

3. **Sumarização: Semanal ou Mensal?**
   - Semanal = mais granularidade, + custo
   - Mensal = menos custo, - detalhe

---

## 📚 Referências Técnicas

- [SQLite FTS5 Docs](https://www.sqlite.org/fts5.html)
- [BM25 Algorithm](https://en.wikipedia.org/wiki/Okapi_BM25)
- [Groq Embeddings API](https://console.groq.com/docs/embeddings) (se optar por RAG)
- Paper: "Hierarchical Memory for Long-Context LLMs" (Google Research, 2024)

---

## 🎬 Próximos Passos

**Você decide**:
1. Rodar o experimento FTS5 (1 hora) para validar a abordagem?
2. Ir direto para implementação da Opção Híbrida?
3. Explorar outra arquitetura customizada?

Vamos discutir qual caminho faz mais sentido para o seu uso! 🚀

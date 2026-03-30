---
trigger: model_decision
description: Sempre que houver sugestão de instalação de novas bibliotecas (`pip install`, `requirements.txt`), criação de novas Skills ou alterações no loop principal (`AgentBrain`).
---

# Rule: Resource & Performance Audit (Raspberry Pi 3 Optimized)

**Gatilho**: Sempre que houver sugestão de instalação de novas bibliotecas (`pip install`, `requirements.txt`), criação de novas Skills ou alterações no loop principal (`AgentBrain`).

## 1. Auditoria de Dependências (Foco em RAM)
Antes de adicionar qualquer biblioteca ao projeto:
1. **Verificação de "Peso"**: Pesquise ou estime o impacto de memória da biblioteca. 
   - **Proibição Estrita**: Rejeite automaticamente Pandas, Numpy, Scipy, Matplotlib ou qualquer lib de C-extensions pesadas, a menos que haja uma versão "Lite" compatível com 1GB de RAM.
2. **Alternativas Nativas**: Sempre sugira usar `json`, `sqlite3`, `collections` ou `pickle` (nativos do Python) antes de buscar soluções externas.
3. **Verificação de Arquitetura**: Garanta que a biblioteca funciona em arquitetura ARMv7 (Raspberry Pi 3).

## 2. Validação de Assincronismo (Non-Blocking)
Para cada nova função ou Skill:
1. **Check de Async**: Todo I/O (chamadas de API, leitura de disco, requests ao Telegram) DEVE usar `async/await`.
2. **Bloqueio de Loop**: Identifique funções síncronas que possam levar mais de 50ms para executar. Se existirem, exija o uso de `run_in_executor` para não travar o bot.
3. **Conexões**: Garanta o uso de `aiohttp` em vez de `requests`.

## 3. Eficiência do AgentBrain
Ao mexer no núcleo de decisão:
1. **Token Management**: Como o hardware é limitado, minimize o tamanho do prompt enviado ao Gemini/Groq para reduzir o tempo de processamento e latência.
2. **Garbage Collection**: Em funções que manipulam grandes volumes de texto, sugira o uso de `del` ou limpeza de variáveis para libertar memória assim que possível.

## 4. Protocolo de Resposta
Se uma alteração violar a filosofia "Diet", o agente deve responder:
> "⚠️ **Alerta de Performance (Curupira):** A implementação proposta para [X] pode comprometer os recursos do Raspberry Pi 3 devido a [Motivo]. Sugiro a alternativa [Y] para manter o sistema leve."
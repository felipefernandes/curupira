# 📊 Análise de Planejamento - Curupira Bot

**Data:** 2026-03-03
**Objetivo:** Avaliar issues planejadas, identificar sobreposições com features implementadas e propor novas skills

---

## 1️⃣ Status Atual: Features Implementadas ✅

### Skills Ativas (Código em Produção)

| Skill | Arquivo | Descrição | Issue Original |
|-------|---------|-----------|----------------|
| **Time** | `time.py` | Horário atual | Built-in |
| **Memory** | `memory.py` | Fatos persistentes do usuário | #88 ✅ |
| **Weather** | `weather_manager.py` | Previsão do tempo | - |
| **Hardware** | `hardware.py` | Monitoramento de CPU/RAM/Temp | - |
| **Reminders** | `reminders.py` | Lembretes únicos + recorrentes | #76 ✅ |
| **RSS** | `rss.py` | Leitor de feeds RSS/Atom | #54, #86 ✅ |
| **Job Hunter** | `job_hunter.py` | Busca de vagas de emprego | #95 ✅ |
| **Sports** | `sports_manager.py` | Resultados esportivos | #113 ✅ |
| **Usage Report** | `usage_report.py` | Relatório de consumo de tokens | #127 ✅ |
| **System Control** | `system_control.py` | Execução de comandos (Power User) | #42 ✅ |
| **Introspection** | `introspection.py` | Auto-análise de capacidades | #55 ✅ |
| **GitHub (MCP)** | `github.py` | Integração via MCP | - |

### Infraestrutura Implementada

- ✅ Arquivo de configuração central (`config.toml`) - #121
- ✅ Health Check / Doctor (`check_health.py`) - #72
- ✅ Multi-turn streaming (UX conversacional) - #81
- ✅ Sistema de memória persistente (SQLite + JSON)
- ✅ Greetings proativos (Bom dia/Boa noite) - #104
- ✅ MCP Client (Model Context Protocol)
- ✅ Retry logic com backoff exponencial (Rate limits)
- ✅ Segurança multi-camadas (LLM Guard + Whitelist)

---

## 2️⃣ Issues Abertas vs Features Implementadas

### 🟢 SEM SOBREPOSIÇÃO (Novas Features Planejadas)

| Issue | Título | Prioridade | Notas |
|-------|--------|------------|-------|
| #110 | **Skill Smart Home** | - | Nova área: IoT/automação residencial |
| #109 | **RSS v1.2 - Auto-tradução** | Enhancement | Melhoria da skill RSS existente |
| #90 | **Sistema de prioridade para fatos** | Enhancement | Melhoria do sistema de memória |
| #62 | **Gestão de Mantimentos** | Enhancement | Nova área: compras/lista de mercado |
| #61 | **Tempo de Transporte (Maps)** | Medium | Nova: navegação/rotas |
| #60 | **Compreender áudio** | **High** | Nova: speech-to-text |
| #59 | **Entertainment (Cinema/Teatro)** | Low | Nova: entretenimento |
| #50 | **Emails v1.0** | Medium | Nova: SMTP/IMAP |
| #49 | **Skill Notion** | Medium | Nova: produtividade |
| #48 | **Google Agenda** | **High** | Nova: calendário |
| #47 | **Google Analytics** | Low | Nova: métricas web |
| #46 | **Skill PDF** | Low | Nova: manipulação de PDFs |
| #45 | **Skill Vercel** | Low | Nova: deploy logs |
| #44 | **Navegação Web** | Enhancement | Nova: web scraping |
| #43 | **Gerenciamento de Arquivos** | Enhancement | Nova: file operations |

### 🟡 POSSÍVEL SOBREPOSIÇÃO (Requer Análise)

| Issue | Título | Status Atual | Análise |
|-------|--------|--------------|---------|
| #102 | **Preflight Context: Hardware no prompt** | Parcial | ✅ Hardware skill existe, ❌ mas NÃO é injetado automaticamente no prompt |

**Conclusão #102:** A skill `hardware.py` já existe e funciona quando chamada, mas **não é executada automaticamente antes de cada mensagem**. A issue propõe injeção proativa no system prompt.

---

## 3️⃣ Brainstorming: Novas Skills & Features 🧠

### 🎯 Critérios de Priorização

**Alta Prioridade:**
- Utilidade para maioria dos usuários (uso diário)
- Baixo custo de implementação (API gratuita ou sem API)
- Alinhado com filosofia "Diet" (leve, eficiente)

**Média Prioridade:**
- Casos de uso específicos mas relevantes
- Requer API paga (mas com tier gratuito razoável)

**Baixa Prioridade:**
- Nicho específico
- Alto custo computacional/monetário
- Complexidade alta vs benefício limitado

---

### 🚀 Novas Skills Propostas (Overthinking Mode ON)

#### **Categoria: Produtividade & Organização**

| Skill | Descrição | Prioridade | API/Lib | Notas |
|-------|-----------|------------|---------|-------|
| **📝 Notas Rápidas** | Salvar notas de texto, buscar, listar | ⭐⭐⭐ | SQLite local | Simples, útil, sem API externa |
| **✅ Tarefas (TODO List)** | Criar, listar, marcar tarefas concluídas | ⭐⭐⭐ | SQLite local | Overlap com Google Tasks? Decidir |
| **🗓️ Google Calendar** | Agendar eventos, consultar agenda | ⭐⭐⭐ | Google Calendar API | Já planejada (#48) |
| **📧 Email v1.0** | Enviar, ler emails | ⭐⭐ | SMTP/IMAP | Já planejada (#50) |
| **📄 Notion** | Criar páginas, buscar dados | ⭐⭐ | Notion API | Já planejada (#49) |
| **📊 Google Sheets** | Ler/escrever planilhas | ⭐⭐ | Google Sheets API | Útil para logs/relatórios |
| **🔖 Bookmarks/Links** | Salvar URLs, categorizar, buscar | ⭐⭐ | SQLite local | Útil para research |

#### **Categoria: Informação & Conhecimento**

| Skill | Descrição | Prioridade | API/Lib | Notas |
|-------|-----------|------------|---------|-------|
| **📚 Wikipedia** | Buscar resumos de artigos | ⭐⭐⭐ | Wikipedia API (gratuita) | Conhecimento geral rápido |
| **🌐 Web Search** | Buscar no Google/DuckDuckGo | ⭐⭐⭐ | Serper/SerpAPI | Já usado no Job Hunter |
| **📖 Dicionário/Tradutor** | Definições, sinônimos, tradução | ⭐⭐ | Google Translate/DeepL | Útil para estudos |
| **🧮 Calculadora Avançada** | Expressões matemáticas, conversões | ⭐⭐ | Python `sympy`/`pint` | Científico/engenharia |
| **🎓 Cursos/Tutoriais** | Recomendar cursos (Udemy, Coursera) | ⭐ | Web scraping | Nicho, complexo |

#### **Categoria: Casa & Vida Pessoal**

| Skill | Descrição | Prioridade | API/Lib | Notas |
|-------|-----------|------------|---------|-------|
| **🏠 Smart Home** | Controlar luzes, sensores (Home Assistant) | ⭐⭐⭐ | Home Assistant API | Já planejada (#110) |
| **🛒 Lista de Compras** | Gerenciar mantimentos, receitas | ⭐⭐⭐ | SQLite local | Já planejada (#62) |
| **🚗 Transporte/Rotas** | Tempo de viagem, rotas | ⭐⭐ | Google Maps API | Já planejada (#61) |
| **💊 Lembretes de Medicamentos** | Tracking de remédios, horários | ⭐⭐ | SQLite + Reminders | Extensão da skill de lembretes |
| **🍽️ Receitas** | Buscar receitas, sugestões | ⭐ | Spoonacular/Edamam | Entretenimento |

#### **Categoria: Finanças**

| Skill | Descrição | Prioridade | API/Lib | Notas |
|-------|-----------|------------|---------|-------|
| **💰 Rastreador de Gastos** | Registrar despesas, relatórios | ⭐⭐⭐ | SQLite local | Útil para orçamento pessoal |
| **💱 Conversor de Moedas** | Taxas de câmbio em tempo real | ⭐⭐ | ExchangeRate-API (free) | Rápido, útil |
| **📈 Ações/Cripto** | Preço de ativos, alertas | ⭐⭐ | Alpha Vantage/CoinGecko | Investidores |
| **🧾 Boletos/Contas** | Lembretes de vencimento | ⭐⭐ | SQLite + Reminders | Overlap com reminders |

#### **Categoria: Entretenimento & Mídia**

| Skill | Descrição | Prioridade | API/Lib | Notas |
|-------|-----------|------------|---------|-------|
| **🎬 Cinema/Streaming** | Filmes em cartaz, recomendações | ⭐⭐ | TMDb API | Já planejada (#59) |
| **🎵 Música** | Buscar letras, info de artistas | ⭐ | Genius/Last.fm | Nicho |
| **📺 TV/Séries** | Próximos episódios, recomendações | ⭐ | TVMaze API | Nicho |
| **🎮 Gaming** | Preços de jogos, notícias | ⭐ | Steam/RAWG API | Nicho |

#### **Categoria: Saúde & Bem-estar**

| Skill | Descrição | Prioridade | API/Lib | Notas |
|-------|-----------|------------|---------|-------|
| **🧘 Meditação/Mindfulness** | Timer, guias | ⭐ | Local | Simples, útil |
| **💧 Hidratação** | Lembretes para beber água | ⭐⭐ | SQLite + Reminders | Saúde |
| **🏃 Exercícios** | Tracking de atividades | ⭐ | SQLite local | Fitness |

#### **Categoria: Desenvolvedor/Tech**

| Skill | Descrição | Prioridade | API/Lib | Notas |
|-------|-----------|------------|---------|-------|
| **📊 Google Analytics** | Métricas de sites | ⭐ | GA4 API | Já planejada (#47) |
| **☁️ Vercel Logs** | Status de deploys | ⭐ | Vercel API | Já planejada (#45) |
| **🐳 Docker Status** | Status de containers | ⭐⭐ | Docker API local | DevOps |
| **📝 Logs/Monitoring** | Análise de logs do sistema | ⭐⭐ | Local (journalctl) | Overlap com system_control |
| **🔐 Secrets Manager** | Gerenciar API keys de forma segura | ⭐⭐ | Vault/Local encryption | Segurança |

#### **Categoria: Comunicação**

| Skill | Descrição | Prioridade | API/Lib | Notas |
|-------|-----------|------------|---------|-------|
| **📱 WhatsApp** | Enviar mensagens (via API não oficial) | ⭐ | Twilio/WPP Connect | Risco de ban |
| **💬 Slack/Discord** | Enviar/ler mensagens | ⭐ | Webhook/API oficial | Empresarial |
| **🔔 Notificações Push** | Enviar para celular (Pushover, NTFY) | ⭐⭐ | Pushover/NTFY | Útil para alertas |

#### **Categoria: Voz & Multimidia**

| Skill | Descrição | Prioridade | API/Lib | Notas |
|-------|-----------|------------|---------|-------|
| **🎤 Speech-to-Text** | Transcrever áudios | ⭐⭐⭐ | Whisper/Google STT | Já planejada (#60) |
| **🔊 Text-to-Speech** | Enviar respostas em áudio | ⭐⭐ | gTTS/Piper TTS | Acessibilidade |
| **🎨 Geração de Imagens** | DALL-E/Stable Diffusion | ⭐ | API paga | Alto custo |

#### **Categoria: Automação & Integrações**

| Skill | Descrição | Prioridade | API/Lib | Notas |
|-------|-----------|------------|---------|-------|
| **🔗 IFTTT/Zapier** | Webhooks para automações | ⭐⭐ | Webhooks | Flexibilidade |
| **📂 Dropbox/Drive** | Upload/download de arquivos | ⭐⭐ | Google Drive/Dropbox API | Cloud storage |
| **🖨️ Impressão Remota** | Enviar docs para impressora | ⭐ | CUPS/Cloud Print | Nicho |

---

### 🎯 Top 10 Skills Recomendadas (por Impacto x Esforço)

| # | Skill | Impacto | Esforço | Score | Justificativa |
|---|-------|---------|---------|-------|---------------|
| 1 | **📝 Notas Rápidas** | Alto | Baixo | 9/10 | Útil diariamente, sem API externa |
| 2 | **🎤 Speech-to-Text** | Alto | Médio | 8/10 | Acessibilidade, já planejada (#60) |
| 3 | **🗓️ Google Calendar** | Alto | Médio | 8/10 | Produtividade core, já planejada (#48) |
| 4 | **💰 Rastreador de Gastos** | Alto | Baixo | 8/10 | Finanças pessoais, local |
| 5 | **📚 Wikipedia** | Médio | Baixo | 7/10 | Conhecimento geral, API gratuita |
| 6 | **🏠 Smart Home** | Alto | Alto | 7/10 | IoT/automação, já planejada (#110) |
| 7 | **🛒 Lista de Compras** | Médio | Baixo | 7/10 | Vida diária, já planejada (#62) |
| 8 | **💱 Conversor de Moedas** | Médio | Baixo | 6/10 | Útil, API gratuita |
| 9 | **🌐 Web Search** | Alto | Médio | 6/10 | Expansão do conhecimento |
| 10 | **🔔 Notificações Push** | Médio | Baixo | 6/10 | Alertas proativos além do Telegram |

---

## 4️⃣ Roadmap Proposto (Q2 2026)

### 🔥 Sprint 1: Quick Wins (1-2 semanas)

1. **#102 - Preflight Context** (Hardware no prompt) - Melhoria de UX existente
2. **📝 Notas Rápidas** - Nova skill, impacto alto, esforço baixo
3. **💱 Conversor de Moedas** - Útil, API gratuita, rápido
4. **#109 - RSS Auto-tradução** - Melhoria de skill existente

### ⚡ Sprint 2: High Priority (2-3 semanas)

5. **#60 - Speech-to-Text** - Acessibilidade, alta demanda
6. **#48 - Google Calendar** - Produtividade core
7. **💰 Rastreador de Gastos** - Finanças pessoais
8. **#90 - Sistema de prioridade para fatos** - Melhoria de memória

### 🚀 Sprint 3: Expansão (3-4 semanas)

9. **#110 - Smart Home** - IoT, complexidade média-alta
10. **📚 Wikipedia** - Conhecimento geral
11. **#62 - Lista de Compras** - Vida diária
12. **🌐 Web Search** - Expansão de capacidades

### 🔮 Backlog (Q3-Q4 2026)

- #50 - Emails v1.0
- #49 - Skill Notion
- #61 - Tempo de Transporte (Maps)
- #59 - Entertainment (Cinema/Teatro)
- Outras skills de nicho conforme demanda

---

## 5️⃣ Próximos Passos Imediatos

### ✅ Ações Recomendadas

1. **Revisar e priorizar issues abertas**
   - Fechar issues duplicadas ou obsoletas
   - Atualizar labels de prioridade

2. **Implementar Quick Wins (Sprint 1)**
   - #102 (Preflight Context) - 1 dia
   - Notas Rápidas - 2 dias
   - Conversor de Moedas - 1 dia

3. **Documentar skills existentes**
   - Atualizar README com lista completa de skills
   - Criar docs/SKILLS_CATALOG.md

4. **Coletar feedback de usuários**
   - Quais skills são mais usadas?
   - Quais features estão faltando?

---

## 📌 Notas Finais

### Filosofia "Diet" em Novas Skills

Ao implementar novas skills, seguir os princípios:

- ✅ **Local First**: Preferir SQLite/JSON sobre APIs quando possível
- ✅ **Free Tier**: APIs gratuitas ou com limites generosos
- ✅ **Async**: Sempre assíncrono para não travar o bot
- ✅ **Lightweight**: Evitar bibliotecas pesadas (ex: Pandas)
- ✅ **Resilient**: Fallbacks para quando APIs falharem
- ✅ **Proactive**: Skills que trabalham para o usuário, não contra ele

### Métricas de Sucesso

- **Adoção**: % de usuários que usam cada skill por mês
- **Confiabilidade**: Uptime e taxa de erro por skill
- **Performance**: Tempo médio de resposta
- **Custo**: Gasto de tokens/API por skill

---

**Documento gerado em:** 2026-03-03
**Autor:** Claude Code (Sonnet 4.5)
**Para discussão com:** Felipe Fernandes

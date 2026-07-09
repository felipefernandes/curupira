# Roadmap CurupiraBOT

## 🚀 Fase 1: SETUP
- [x] MVP, setup, arquivo de instalação amigável, fazer a primeira interação com o usuário via Telegram.

## 🧠 Fase 2: MEMÓRIA
- [x] Adicionar camadas de memória (curto e longo prazo).
- [x] **Memória de Longo Prazo:** Usar banco de dados leve (Ex: ChromaDB, SQLite) com boa integração para LLMs.
- [x] **Memória de Curto Prazo:** Usar JSON ou similar para baixo consumo de RAM.
- [x] **Objetivo:** Permitir que o Curupira lembre de informações do usuário e do sistema persistentemente.

## 👤 Fase 3: Personalização
- [x] **Onboarding:** Apresentação, definição do nome do usuário e sobrenome do Curupira (variável de ambiente).
- [x] **Persistência:** Nome do usuário salvo e usado nas interações.
- [x] **Personalidade:** Lembrar preferências e estilo de interação do usuário.

## 💓 Fase 4: Heartbeat
- [x] Sistema de heartbeat enxuto compatível com Raspberry Pi 3 (baixa RAM/CPU).

## 🤖 Fase 5: Arquitetura Agêntica Lightweight
- [x] **Function Calling:** Refatorar Skills para usar Function Calling (Gemini/Groq) ao invés de Regex.
- [x] **Padronização:** Classe base `BaseSkill` para facilitar extensão.
- [x] **Brain:** Loop de Agente para decisão de skills com baixo consumo.
- [x] **MCP:** Implementar Cliente Model Context Protocol para ferramentas externas.

---

## 🛠️ Skills (Core & Implementadas)

### 📅 Lembretes
- [x] **Core:** Sistema de agendamento via JobQueue.
- [x] **Consultas:** Ler lembretes (hoje, amanhã, semana).
- [x] **Linguagem Natural:** Prazos flexíveis ("semana que vem").
- [x] **Gestão:** Remover e alterar lembretes existentes.

### 🌦️ Previsão do Tempo
- [x] **Consultas:** "Vai chover?", "Previsão para amanhã".
- [x] **Backend:** API de clima (Open-Meteo / wttr.in).
- [x] **Localização:** Detecção automática ou manual persistente.

### 🖥️ Monitoramento de Hardware
- [x] Leitura de temperatura, CPU e RAM.
- [x] Feedback visual com emojis.

### 🛡️ System Control (Power User)
- [x] **Diagnósticos do SO:** Comandos read-only seguros (IP, disco, hostname, uptime, memória).
- [x] **Leitura de Logs:** Acesso programático a journalctl e logs do sistema com filtros.
- [x] **Leitura de Arquivos:** Leitura segura de arquivos de texto/log com proteção OOM.
- [x] **Configuração de Rede:** Conexão WiFi via NetworkManager (nmcli).
- [x] **LLM Security Guard:** Validação dual-layer (whitelist + LLM Groq) para prevenir comandos destrutivos.
- [x] **Execução Customizada:** "Escape hatch" para power users executarem comandos validados pelo Security Guard.

### 📰 RSS Reader
- [x] **Leitura de feeds:** Busca as últimas entradas de qualquer URL RSS/Atom. (Issue #54)
- [x] **Listagem:** Lista feeds pré-configurados via `RSS_FEEDS_JSON`.
- [x] **Resiliência:** Timeout de 15s, User-Agent personalizado e Segurança (Whitelist).

### 🧠 Memória de Longo Prazo (Facts)
- [x] **Injeção de fatos no prompt:** Dados persistentes do usuário (cidade, preferências) injetados automaticamente. (Issue #88)
- [x] **Save proativo:** Agente chama `save_user_fact` ao aprender dados relevantes sem intervenção.

### 🧙 Persona & Comportamento
- [x] **Persona Curupira:** System prompt estruturado com identidade, hardware-awareness e regras de comportamento. (Issue #68)
- [x] **Temperatura configurável:** `GROQ_TEMPERATURE` e `GROQ_TEMPERATURE_REFLECTION` via `.env`.
- [x] **Filtro de CoT:** Remove blocos `<think>` do output (Qwen3, DeepSeek-R1) antes de enviar ao usuário.
- [x] **Typing indicator:** Status "Escrevendo..." no Telegram durante processamento e retries.

---

### 🎯 Job Hunter
- [x] **Busca de Vagas:** Integração com APIs externas de busca. (Issue #95)
- [x] **Avaliação de IA:** Avaliação e scoring de vagas relevantes baseadas nas preferências do usuário.
- [x] **Configuração flexível:** Opções para domínios, keywords e prompt override.

---

## 📦 Releases Planejados (Milestones)

### 🚀 v0.10.0: O "Jarvis" Proativo e Contextual
Foco em dar iniciativa ao bot, melhorias na injeção de contexto e aprimoramento contínuo da UX de conversação (Memory & Persona).
(Issue #90)
- [x] **Grounding Dinâmico:** Injeção de contexto vital (Hora atual, Load, etc) pré-prompt. (Issue #70)
- [x] **Persistência Proativa:** Mensagens proativas no histórico para continuidade. (Issue #85)
- [x] **Multi-turn/Streaming UX:** Suporte para conversação natural pré-tools e streaming responses. (Issue #81)

### 🛠️ v0.11.0: Confiabilidade e Arquitetura Agêntica Avançada
Foco na saúde do sistema e evolução das capacidades técnicas (MCP-Lite) usando ferramentas orientadas a sistema.
- [ ] **Doctor (Health Checks):** Diagnóstico de integridade do ambiente (ZRAM, Chaves, Git). (Issue #72)
- [x] **Padronização MCP-Lite:** Isolar lógicas das skills para retorno JSON padronizado. (Issue #71)
- [x] **Skill de Terminal (Power User):** Execução segura de comandos shell locais com LLM Security Guard dual-layer. (Issue #42)
- [x] **Monitoramento de Logs:** Detecção de anomalias via leitura de journalctl e arquivos de log sob demanda. (Issue #53)

### ⚙️ v0.12.0: UX de Configuração e Manutenção ✅
Foco em simplificar a manutenção para usuários não-técnicos e aumentar a configurabilidade do sistema. (Issue #121 — PR #123)
- [x] **config.toml centralizado:** Template comentado `default.config.toml` com todas as configurações em um lugar. 
- [x] **Prioridade de configuração:** ENV > .env > config.toml > defaults internos, com retrocompatibilidade total.
- [x] **Feature Flags por Skill:** Habilitar/desabilitar qualquer skill via `[skills] weather = false` no config.toml.
- [x] **Sumário de startup:** Log automático das skills ativas/inativas e provedor de IA ao iniciar o bot.
- [x] **Segurança:** `config.toml` adicionado ao `.gitignore`; secrets permanecem exclusivamente em ENV/.env.
- [x] **install.sh atualizado:** Copia template automaticamente no primeiro setup.

### 💼 v1.0.0: O Assistente Pessoal Completo ("Day-to-day Helper")
Integrações essenciais para rotina e facilidades da vida pessoal.
- [x] **Compreensão de Áudio:** Ouvir e processar solicitações via voz. (Issue #60)
- [x] **Google Agenda:** OAuth2, listagem/criação/cancelamento de eventos, sincronização automática com lembretes. (Issue #48)
- [ ] **Tempo de Transporte:** Consultas de rotas e estimativa (Maps). (Issue #61)
- [ ] **Compras Inteligentes:** Gerenciamento e auxílio em compras de casa/mantimentos. (Issue #62)

### 🧠 v1.0.1: Proatividade Real (Pattern Analysis)
Foco em tornar o Curupira genuinamente proativo — não apenas reativo a comandos.
- [x] **Analisador de Padrões:** Detecta skills usadas com frequência via histórico de conversas (`conversations.metadata`).
- [x] **Suggestion Registry:** Mapa extensível de skill → sugestão de automação; nova skill = nova entrada no dict, zero mudança de código.
- [x] **Anti-spam:** Cooldown configurável via `facts` table (padrão 30 dias entre sugestões da mesma skill).
- [x] **Integração com Heartbeat:** Job independente no `job_queue` (padrão 24h); respeita manifesto Diet — sem FastAPI, sem dependências pesadas.
- [x] **Cobertura de testes:** 100% de cobertura em `skills/pattern_analyzer.py` (24 testes).

### 📈 v1.1.0: Produtividade Profissional e Tools
Ferramentas direcionadas para ganho de produtividade no trabalho e integrações corporativas.
- [ ] **E-mails v1.0:** Leitura e envio de anexos (SMTP/Resend). (Issue #50)
- [ ] **Sistema de Arquivos:** Operações de I/O por linguagem natural. (Issue #43)
- [ ] **Leitor de Documentos (PDF):** Síntese estruturada de relatórios PDF. (Issue #46)
- [x] **Navegação Web Headless:** Acesso e extração de URLs sem API (Trafilatura + httpx). (Issue #44)
- [ ] **Integração Notion:** Construção e input pro "segundo cérebro". (Issue #49)
- [ ] **Entretenimento (Cinema/Teatro):** Busca de diversão local via APIs. (Issue #59)
- [ ] **Vercel & Analytics:** Reports, logs e stats básicos (Dev/Prod). (Issues #45, #47)


### v1.1.1:
- [ ] **Scoring de Memória (Facts):** Sistema de prioridade para fatos persistentes do usuário no prompt. 

### 📦 v1.2.0: Rastreamento e Logística (O "Curupira Carteiro")
Foco em acompanhamento de entregas e integrações de logística.
- [ ] **Rastreio de Pacotes:** Suporte a rastreamento de encomendas (Correios, etc) via linguagem natural. (Issue #179)

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
- [ ] **Scoring de Memória (Facts):** Sistema de prioridade para fatos persistentes do usuário no prompt. (Issue #90)
- [ ] **Grounding Dinâmico:** Injeção de contexto vital (Hora atual, Load, etc) pré-prompt. (Issue #70)
- [ ] **Fluxo de RSS Claro:** Listagem individualizada com links vs resumos genéricos. (Issue #87)
- [ ] **Persistência Proativa:** Mensagens proativas no histórico para continuidade. (Issue #85)
- [x] **Multi-turn/Streaming UX:** Suporte para conversação natural pré-tools e streaming responses. (Issue #81)

### 🛠️ v0.11.0: Confiabilidade e Arquitetura Agêntica Avançada
Foco na saúde do sistema e evolução das capacidades técnicas (MCP-Lite) usando ferramentas orientadas a sistema.
- [ ] **Doctor (Health Checks):** Diagnóstico de integridade do ambiente (ZRAM, Chaves, Git). (Issue #72)
- [ ] **Padronização MCP-Lite:** Isolar lógicas das skills para retorno JSON padronizado. (Issue #71)
- [ ] **Skill de Terminal (Power User):** Execução segura de comandos shell locais. (Issue #42)
- [ ] **Monitoramento de Logs:** Detecção de anomalias no sistema. (Issue #53)

### 💼 v1.0.0: O Assistente Pessoal Completo ("Day-to-day Helper")
Integrações essenciais para rotina e facilidades da vida pessoal.
- [ ] **Compreensão de Áudio:** Ouvir e processar solicitações via voz. (Issue #60)
- [ ] **Google Agenda:** Gestão completa e cruzamento de horários. (Issue #48)
- [ ] **Tempo de Transporte:** Consultas de rotas e estimativa (Maps). (Issue #61)
- [ ] **Compras Inteligentes:** Gerenciamento e auxílio em compras de casa/mantimentos. (Issue #62)

### 📈 v1.1.0: Produtividade Profissional e Tools
Ferramentas direcionadas para ganho de produtividade no trabalho e integrações corporativas.
- [ ] **E-mails v1.0:** Leitura e envio de anexos (SMTP/Resend). (Issue #50)
- [ ] **Sistema de Arquivos:** Operações de I/O por linguagem natural. (Issue #43)
- [ ] **Leitor de Documentos (PDF):** Síntese estruturada de relatórios PDF. (Issue #46)
- [ ] **Navegação Web Headless:** Acesso e extração de URLs sem API (BS4/Trafilatura). (Issue #44)
- [ ] **Integração Notion:** Construção e input pro "segundo cérebro". (Issue #49)
- [ ] **Entretenimento (Cinema/Teatro):** Busca de diversão local via APIs. (Issue #59)
- [ ] **Vercel & Analytics:** Reports, logs e stats básicos (Dev/Prod). (Issues #45, #47)
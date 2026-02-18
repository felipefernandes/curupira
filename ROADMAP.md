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
- [x] **Resiliência:** Timeout de 15s, User-Agent personalizado e tratamento de feeds inválidos.

---

## 🔮 Backlog Priorizado (Q1 2026)

### 🚀 Prioridade Alta (Core Assistant)
Estas skills transformam o Curupira em um assistente pessoal proativo.
- [ ] **Google Agenda:** Gestão completa de calendário (OAuth). (Issue #48)
- [ ] **Compreensão de Áudio:** Transcrição e resposta a áudios. (Issue #60)


### 🛠️ Prioridade Média (Produtividade)
Ferramentas de produtividade pessoal.
- [ ] **Tempo de Transporte:** Rotas e trânsito (Maps). (Issue #61)
- [ ] **Emails:** Leitura e envio. (Issue #50)
- [ ] **Notion:** Segundo cérebro. (Issue #49)

### 🤓 Prioridade Baixa (DevOps & Tools)
Monitoramento técnico e entretenimento.
- [ ] **Monitoramento:** Vercel (#45), Analytics (#47), Logs (#53).
- [ ] **Outros:** PDF (#46), Entretenimento (#59).
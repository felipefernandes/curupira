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

---

## 🔮 Skills Futuras (Backlog)

### 💻 Terminal & Sistema (Power User)
- [ ] Execução segura de comandos shell (logs, disco).
- [ ] Monitoramento avançado com alertas proativos.

### 📂 Gerenciamento de Arquivos
- [ ] Operações de arquivo: Criar, ler, escrever, deletar, mover, copiar.

### 🌐 Navegação Web (Headless)
- [ ] Acesso a URLs e extração de texto limpo (`trafilatura`/`bs4`).
- [ ] Resumo de conteúdo web.

### ☁️ Integração Vercel & Logs
- [ ] Conexão API Vercel para logs de deployment.
- [ ] Resumo inteligente de logs extensos.

### 📄 Relatórios & Notificações
- [ ] Geração de PDFs leves (`fpdf2`).
- [ ] Envio de e-mails com anexos (SMTP/Resend).

### 📊 Monitoramento & Analytics
- [ ] Integração GA4 (Métricas diárias).
- [ ] Detecção de anomalias estatísticas.

### 🔗 Integrações Externas
- [ ] Google Agenda.
- [ ] Notion.
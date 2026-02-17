[![🧜‍♀️ Iara - Revisora de Código](https://github.com/felipefernandes/curupira/actions/workflows/ai-code-review.yml/badge.svg)](https://github.com/felipefernandes/curupira/actions/workflows/ai-code-review.yml)
[![codecov](https://codecov.io/gh/felipefernandes/curupira/graph/badge.svg?token=CODECOV_TOKEN)](https://codecov.io/gh/felipefernandes/curupira) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

# 🍃 CurupiraBot

> **Seu assistente pessoal leve, proativo e brasileiro.**
> 
> *"Um assistente virtual projetado para rodar em hardware modesto (como um Raspberry Pi 3), democratizando o acesso à Inteligência Artificial Agêntica."*

Baseado na **Arquitetura da Restrição** e no **Conceito Diet**, ele transforma limitações de hardware em eficiência, "vivendo" no seu servidor para monitorar, alertar e assistir, sem exigir supercomputadores.

> 📜 **Leia nosso [Manifesto Curupira](MANIFESTO.md) para entender a filosofia por trás do código.**

## 🚀 Funcionalidades Atuais

*   **🧠 Memória Persistente**: Lembra do seu nome, suas preferências e contexto de conversas passadas.
*   **🎭 Personalidade Dinâmica**: Escolhe um "sobrenome" único para se diferenciar de outros Curupiras e mantém consistência na comunicação.
*   **💓 Heartbeat & Proatividade**: Sistema de agendamento interno (`JobQueue`) que permite ao bot iniciar interações e monitorar o sistema sem dependências externas (cron).
*   **⏰ Lembretes Naturais**: Peça *"Me lembre de tirar o bolo em 20 min"* e o Curupira entende, agenda e te avisa.
*   **🌦️ Previsão do Tempo**: Pergunte *"Vai chover?"* e ele verifica a previsão local (Open-Meteo) para você.
*   **🔌 Multi-Provedor de IA**: Suporte nativo para **Groq** (LLaMA 3 - *default para velocidade*) e **Google Gemini** (Flash - *para janelas de contexto maiores*).
*   **🌡️ Monitoramento de Hardware**: Pergunte *"Como está o sistema?"* para ver uso de CPU, RAM, Disco e Temperatura do Raspberry Pi em tempo real.

## 🛠️ Tecnologias

*   **Python 3.10+**
*   **python-telegram-bot** (Async + JobQueue)
*   **SQLite + JSON** (Sistema de Memória Lite)
*   **Groq API / Google GenAI**

## ⚖️ Filosofia (Resumo)

*   **Democratização**: Funciona em hardware de baixo custo (1GB RAM).
*   **Eficiência "Diet"**: Processamento offboard, lógica local leve.
*   **Acessibilidade**: Interface via Telegram, sem complexidade.
*   **Privacidade**: Você controla quem fala com seu agente.

_Veja mais em [MANIFESTO.md](MANIFESTO.md)_

---

## 📦 Instalação e Setup

Este projeto foi otimizado para rodar em um **Raspberry Pi**, mas funciona em qualquer ambiente Python.

### 1. Clonar o Repositório
```bash
git clone https://github.com/felipefernandes/curupira.git
cd curupira
```

### 2. Ambiente Virtual
```bash
python3 -m venv venv
# Linux/Mac
source venv/bin/activate
# Windows
.\venv\Scripts\activate
```

### 3. Dependências
```bash
pip install -r requirements.txt
```
*Certifique-se de que instalou o `python-telegram-bot[job-queue]` para as features de tempo funcionarem.*
 
 Para desenvolvimento e testes:
 ```bash
 pip install -r requirements-dev.txt
 ```

### 4. Configuração (.env)
Crie um arquivo `.env` na raiz do projeto:

```ini
# Telegram Token (Pegue com o @BotFather)
TELEGRAM_TOKEN=seu_token_aqui

# ID do seu Usuário no Telegram (Segurança: o bot só responde a você)
# Use o @userinfobot para descobrir seu ID
AUTHORIZED_USER_ID=123456789

# Escolha seu Cérebro: 'groq' ou 'gemini'
AI_PROVIDER=groq

# Chaves de API
GROQ_API_KEY=gsk_...
GEMINI_API_KEY=...
```

### 5. Configurando GitHub (Opcional)

Para usar a integração com o GitHub via MCP (Model Context Protocol), adicione seu token no `.env`:

```ini
# GitHub Integration (Opcional)
GITHUB_PERSONAL_ACCESS_TOKEN=ghp_...
```

> **Migração:** Se você usava `mcp.json` para configurar o GitHub, basta mover o token para o `.env` e remover o `mcp.json`. A skill agora é carregada automaticamente via `skills/github.py`.

> **Segurança:** Crie um [Personal Access Token (classic)](https://github.com/settings/tokens) com os **escopos mínimos necessários**:
> - `repo` (read-only) — para listar repositórios e issues
> - `read:org` — se precisar acessar repos de organizações
>
> O `.env` já está no `.gitignore`. Variáveis de ambiente do sistema têm precedência sobre o `.env`.

### 6. Executar
```bash
python bot.py
```

---

## 🤝 Como Contribuir

Este é um projeto Open Source e adoramos colaborações!

Para detalhes sobre o fluxo de trabalho, padrões de código e uso da Iara (nossa agente de revisão), por favor consulte o arquivo [CONTRIBUTING.md](CONTRIBUTING.md).

## 📄 Licença

Distribuído sob a licença MIT. Veja `LICENSE` para mais informações.

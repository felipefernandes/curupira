[![🧜‍♀️ Iara - Revisora de Código](https://github.com/felipefernandes/curupira/actions/workflows/ai-code-review.yml/badge.svg)](https://github.com/felipefernandes/curupira/actions/workflows/ai-code-review.yml)
[![codecov](https://codecov.io/gh/felipefernandes/curupira/graph/badge.svg?token=CODECOV_TOKEN)](https://codecov.io/gh/felipefernandes/curupira) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

# 🍃 CurupiraBot

> **Seu assistente pessoal leve, proativo e brasileiro.**
> 
> *"Um assistente virtual projetado para rodar em hardware modesto (como um Raspberry Pi 3), democratizando o acesso à Inteligência Artificial Agêntica."*

Baseado na **Arquitetura da Restrição** e no **Conceito Diet**, ele transforma limitações de hardware em eficiência, "vivendo" no seu servidor para monitorar, alertar e assistir, sem exigir supercomputadores.

> 📜 **Leia nosso [Manifesto Curupira](MANIFESTO.md) para entender a filosofia por trás do código.**

## 📋 Índice

*   [🚀 Início Rápido](#-início-rápido)
*   [🛠️ Tecnologias](#️-tecnologias)
*   [🧠 Desenvolvimento de Skills](#-desenvolvimento-de-skills)
*   [⚖️ Filosofia](#️-filosofia)
*   [📦 Instalação Completa](docs/INSTALL.md)
*   [🤝 Como Contribuir](CONTRIBUTING.md)
*   [🗺️ Roadmap](ROADMAP.md)

## 🚀 Funcionalidades Atuais

*   **🧠 Memória Persistente**: Lembra do seu nome, suas preferências e contexto de conversas passadas.
*   **🎭 Personalidade Dinâmica**: Escolhe um "sobrenome" único para se diferenciar de outros Curupiras e mantém consistência na comunicação.
*   **💓 Heartbeat & Proatividade**: Sistema de agendamento interno (`JobQueue`) que permite ao bot iniciar interações e monitorar o sistema sem dependências externas (cron).
*   **⏰ Lembretes Naturais**: Peça *"Me lembre de tirar o bolo em 20 min"* e o Curupira entende, agenda e te avisa.
*   **🌦️ Previsão do Tempo**: Pergunte *"Vai chover?"* e ele verifica a previsão local (Open-Meteo) para você.
*   **🔌 Multi-Provedor de IA**: Suporte nativo para **Groq** (LLaMA 3 - *default para velocidade*) e **Google Gemini** (Flash - *para janelas de contexto maiores*).
*   **🌡️ Monitoramento de Hardware**: Pergunte *"Como está o sistema?"* para ver uso de CPU, RAM, Disco e Temperatura do Raspberry Pi em tempo real.
*   **📰 RSS Reader**: Peça *"Quais são as notícias de hoje?"* e o Curupira busca as últimas manchetes de feeds RSS/Atom configurados.
*   **📅 Google Calendar**: Integração completa com OAuth2 para listar, adicionar e cancelar eventos. Sincronização automática que transforma eventos em lembretes proativos.
*   **🔍 Análise de Padrões**: Detecta quais skills você usa com frequência e sugere automações proativamente — ex: *"Você sempre me pergunta sobre o Botafogo. Quer alertas automáticos de jogos?"*

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

## 🚀 Início Rápido

Se você já tem experiência com Python, siga estes passos:

1.  **Clone e Acesse**: `git clone https://github.com/felipefernandes/curupira.git && cd curupira`
2.  **Ambiente**: `python -m venv venv && source venv/bin/activate`
3.  **Instale**: `pip install -r requirements.txt`
4.  **Configure**: Copie o template de configuração e edite com seus tokens:
    ```bash
    cp default.config.toml config.toml
    # Edite config.toml com suas chaves e preferências
    ```
    > Alternativamente, crie um `.env` baseado no exemplo do [Guia de Instalação](docs/INSTALL.md).
5.  **Rode**: `python bot.py`

### 🩺 Diagnóstico de Integridade (Doctor)

Se o bot apresentar problemas ou se você quiser validar sua instalação (ZRAM, FFmpeg, chaves de API, etc), execute o script de diagnóstico standalone:
```bash
python check_health.py
```

> 📖 **Instruções detalhadas?** Veja o nosso [Guia de Instalação e Setup](docs/INSTALL.md).

---

## 🛠️ Tecnologias

*   **Python 3.10+** (Core)
*   **python-telegram-bot** (Interface Async)
*   **SQLite + JSON** (Memória Lite e Persistente)
*   **Groq / Google Gemini** (Provedores de IA)

---

## 🧠 Desenvolvimento de Skills

O Curupira é modular. Você pode estender as capacidades dele criando novas _Skills_. 

⚠️ **Importante**: Todas as novas skills devem seguir o nosso **[Framework de Criação de Skills (MCP-Lite)](docs/SKILLS_FRAMEWORK.md)** para garantir eficiência e compatibilidade.

---

## ⚖️ Filosofia (Resumo)

*   **Democratização**: Funciona em hardware de baixo custo (1GB RAM).
*   **Eficiência "Diet"**: Processamento offboard, lógica local leve.
*   **Acessibilidade**: Interface via Telegram, sem complexidade.
*   **Privacidade**: Você controla quem fala com seu agente.

_Leia o [MANIFESTO.md](MANIFESTO.md) para a visão completa._

---

## 🤝 Como Contribuir

Este é um projeto Open Source e adoramos colaborações! 

Para detalhes sobre o fluxo de trabalho obrigatório (GitFlow + Revisão pela 🧜‍♀️ Iara), consulte o arquivo **[CONTRIBUTING.md](CONTRIBUTING.md)**.

## 📄 Licença

Distribuído sob a licença MIT. Veja `LICENSE` para mais informações.

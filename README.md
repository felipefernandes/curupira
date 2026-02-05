# 🍃 CurupiraBot

> **Seu assistente pessoal leve, proativo e brasileiro.**
> 
> *"Eu sou o Curupira, guardião do sistema e seu assistente pessoal."*

O **CurupiraBot** é um assistente virtual projetado para rodar em hardware modesto (como um **Raspberry Pi 3**), mas com capacidades avançadas de **Memória**, **Personalidade** e **Proatividade**. Diferente de bots passivos, o Curupira "vive" no seu servidor, monitora sua saúde e pode te mandar lembretes e insights por conta própria.

## 🚀 Funcionalidades Atuais

*   **🧠 Memória Persistente**: Lembra do seu nome, suas preferências e contexto de conversas passadas.
*   **🎭 Personalidade Dinâmica**: Escolhe um "sobrenome" único para se diferenciar de outros Curupiras e mantém consistência na comunicação.
*   **💓 Heartbeat & Proatividade**: Sistema de agendamento interno (`JobQueue`) que permite ao bot iniciar interações e monitorar o sistema sem dependências externas (cron).
*   **⏰ Lembretes Naturais**: Peça *"Me lembre de tirar o bolo em 20 min"* e o Curupira entende, agenda e te avisa.
*   **🌦️ Previsão do Tempo**: Pergunte *"Vai chover?"* e ele verifica a previsão local (Open-Meteo) para você.
*   **🔌 Multi-Provedor de IA**: Suporte nativo para **Groq** (LLaMA 3 - *default para velocidade*) e **Google Gemini** (Flash - *para janelas de contexto maiores*).

## 🛠️ Tecnologias

*   **Python 3.10+**
*   **python-telegram-bot** (Async + JobQueue)
*   **SQLite + JSON** (Sistema de Memória Lite)
*   **Groq API / Google GenAI**

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

### 5. Executar
```bash
python bot.py
```

---

## 🤝 Como Contribuir

Este é um projeto Open Source e adoramos colaborações!

### Roadmap
Confira o arquivo [ROADMAP.md](ROADMAP.md) para ver as próximas fases planejadas (ex: Monitoramento de Hardware, Automação de Arquivos).

### Estrutura & Padrões (OpenSpec)
Este projeto utiliza uma metodologia leve de especificações chamada **OpenSpec** para manter o código organizado.

1.  **Mudanças Grandes?**
    *   Evite mudar código diretamente.
    *   Crie uma proposta em `openspec/changes/nova-feature/`.
    *   Consulte `openspec/projec.md` e `openspec/AGENTS.md` para entender a arquitetura.

2.  **Pull Requests**
    *   Fork o projeto.
    *   Crie sua branch (`feature/minha-feature`).
    *   Garanta que a funcionalidade rode bem em hardware limitado (evite Docker pesado ou DBs complexos se possível).

## 📄 Licença

Distribuído sob a licença MIT. Veja `LICENSE` para mais informações.

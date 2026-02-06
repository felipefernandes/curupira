# 🍃 CurupiraBot

> **Seu assistente pessoal leve, proativo e brasileiro.**
> 
> *"Eu sou o Curupira, guardião do sistema e seu assistente pessoal."*

O **CurupiraBot** é um assistente virtual projetado para rodar em hardware modesto (como um **Raspberry Pi 3**), democratizando o acesso à Inteligência Artificial Agêntica. Baseado na **Arquitetura da Restrição** e no **Conceito Diet**, ele transforma limitações de hardware em eficiência, "vivendo" no seu servidor para monitorar, alertar e assistir, sem exigir supercomputadores.

> 📜 **Leia nosso [Manifesto Curupira](MANIFESTO.md) para entender a filosofia por trás do código.**

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

### Fluxo de Contribuição

O projeto conta com a **Iara** 🧜‍♀️, uma revisora de código automatizada que analisa todos os PRs.

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  1. Branch  │───▶│   2. PR     │───▶│  3. Iara    │
│   feature/  │    │   Aberto    │    │  Revisa IA  │
└─────────────┘    └─────────────┘    └──────┬──────┘
                                             │
┌─────────────┐    ┌─────────────┐           │
│  5. Merge   │◀───│  4. Ajustar │◀──────────┘
│    main     │    │  (se necessário)        │
└─────────────┘    └─────────────┘
```

1. **Crie uma branch**: `git checkout -b feature/minha-feature`
2. **Desenvolva**: Siga as convenções do projeto (veja `openspec/project.md`).
3. **Abra um PR**: A Iara irá revisar automaticamente buscando:
   - 🐛 Bugs e erros lógicos
   - 🔒 Problemas de segurança
   - ⚡ Eficiência "Diet" (memória/CPU)
   - 📚 Qualidade de código
4. **Ajuste conforme feedback**: Atualize o PR até a aprovação.
5. **Merge**: Após revisão aprovada, faça merge na `main`.

### Estrutura & Padrões (OpenSpec)
Este projeto utiliza uma metodologia leve de especificações chamada **OpenSpec** para manter o código organizado.

1.  **Mudanças Grandes?**
    *   Evite mudar código diretamente.
    *   Crie uma proposta em `openspec/changes/nova-feature/`.
    *   Consulte `openspec/project.md` e `openspec/AGENTS.md` para entender a arquitetura.

## 📄 Licença

Distribuído sob a licença MIT. Veja `LICENSE` para mais informações.

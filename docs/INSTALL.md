# 📦 Instalação e Configuração Detalhada

Este guia fornece instruções passo a passo para configurar o CurupiraBOT em seu ambiente local ou em um Raspberry Pi.

---

## 🛠️ Requisitos Prévios

*   **Python 3.10+**
*   **Conta no Telegram** (e um Bot Token do [@BotFather](https://t.me/botfather))
*   **Acesso à Internet** (para APIs da Groq/Gemini)

---

## 🚀 Passo a Passo de Instalação

### 1. Clonar o Repositório
```bash
git clone https://github.com/felipefernandes/curupira.git
cd curupira
```

### 2. Ambiente Virtual
É altamente recomendado o uso de um ambiente virtual para isolar as dependências.
```bash
python3 -m venv venv
# Linux/Mac
source venv/bin/activate
# Windows
.\venv\Scripts\activate
```

### 3. Instalar Dependências
```bash
pip install -r requirements.txt
```
*Certifique-se de que instalou o `python-telegram-bot[job-queue]` para as features de tempo funcionarem.*

Para propósitos de desenvolvimento e execução de testes:
```bash
pip install -r requirements-dev.txt
```

### 4. Configuração do ambiente (.env)
O Curupira utiliza um arquivo `.env` para gerenciar segredos. Crie um na raiz do projeto:

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
# GEMINI_API_KEY=...
```

---

## ⚙️ Configurações Opcionais

### 5. Configurando RSS
Por padrão o Curupira já vem com G1, TechCrunch e Hacker News. Para personalizar, adicione no `.env`:

```ini
# Feeds RSS personalizados (JSON)
RSS_FEEDS_JSON={"G1": "https://g1.globo.com/rss/g1/", "Meu Blog": "https://meublog.com/feed"}
```

### 6. Configurando integração com GitHub
Para usar as habilidades de GitHub, adicione seu token no `.env`:

```ini
# GitHub Integration (Opcional)
GITHUB_PERSONAL_ACCESS_TOKEN=ghp_...
```

> **Nota**: Crie um [Personal Access Token (classic)](https://github.com/settings/tokens) com os escopos mínimos necessários (`repo` read-only).

---

## 🏃 Execução

Para iniciar o bot após a configuração:
```bash
python bot.py
```

Para garantir que o sistema está íntegro:
```bash
python -m pytest tests/
```

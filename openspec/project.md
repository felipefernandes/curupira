# Project Context

## Purpose
O Curupira é uma alternativa "Lite" ao OpenClaw, projetado para alta performance em hardware limitado (por exemplo o Raspberry Pi 3 Model B com 1GB RAM). Ele atua como um assistente pessoal, pode fazer monitoramento do sistema e automação de tarefas definidas pelo usuário. O sistema opera de forma "headless" (sem interface gráfica), utilizando o Telegram como interface principal.

## Tech Stack
- **Linguagem:** Python 3 (foco em `asyncio`)
- **Interface:** Telegram (via `python-telegram-bot`)
- **IA (Cérebro):** 
  - Google Gemini 1.5 Flash (Processamento principal)
  - Groq / LLaMA 3.3 70b (Alternativa rápida/performática)
- **Hardware Alvo:** Raspberry Pi 3 Model B (ou superior)
- **Gerenciamento de Dependências:** `pip` + `requirements.txt` / `venv`

## Project Conventions

### Code Style
- **Pythonico:** Seguir PEP 8 onde possível.
- **Leveza:** Evitar estritamente bibliotecas pesadas de Data Science (Pandas, Numpy) para economizar RAM.
- **Assincronismo:** Priorizar funções `async/await` para não bloquear o loop de eventos, crucial para o hardware limitado.
- **Comentários:** Docstrings claras para funções e classes.

### Architecture Patterns
- **Modular:** Núcleo (`bot.py`) separado de habilidades/ferramentas (`skills/`).
- **Segurança por Design:** Whitelist estrita de `USER_ID` para execução de comandos.
- **Configuração:** Segredos e variáveis de ambiente gerenciados via `.env` e validados em `config.py`.

### Testing Strategy
- **Manual:** Verificação funcional via interação com o bot no Telegram.
- **Logs:** Monitoramento de logs (`logging`) para depuração de erros em tempo de execução.
- **Preventiva:** Validação de variáveis de ambiente na inicialização.

### Git Workflow
- Manter o histórico limpo.
- Commits descritivos.
- Não versionar arquivos sensíveis (ex: `.env`).

## Domain Context
- **Persona:** O bot adota a persona do "Curupira", sendo amigável, perspicaz, e direto.
- **Monitoramento automatizado:** Monitoramento de hardware (temperatura, uso de CPU/RAM).
- **Automação:** Execução de scripts e tarefas definidas pelo usuário.

## Important Constraints
- **Recursos de Hardware:** Máximo 1GB de RAM. O código deve ser eficiente em memória.
- **Rede:** Dependência de conexão estável para APIs (Telegram, Gemini, Groq).
- **Acesso:** Estritamente pessoal. Apenas usuários com ID autorizado no Telegram podem interagir.

## External Dependencies
- **Telegram Bot API:** Para comunicação bidirecional.
- **Google Generative AI API (Gemini):** Para raciocínio complexo e geração de texto.
- **Groq API:** Para inferência rápida de LLM.

# Project Context

## Purpose
O Curupira nasce do **Manifesto Curupira**, buscando democratizar a Inteligência Agêntica. É uma alternativa "Diet" e eficiente, projetada para alta performance em hardware limitado (como o Raspberry Pi 3 Model B). Ele atua como um parceiro proativo, monitorando e assistindo o usuário através de uma interface acessível (Telegram), priorizando a simplicidade e o baixo custo operacional.

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

### Fluxo de Contribuição (Revisão Automatizada)
O projeto utiliza a **Iara** 🧜‍♀️, uma revisora de código automatizada (DeepSeek V3) que analisa todos os PRs.

1. **Criar Branch**: `git checkout -b feature/minha-feature`
2. **Desenvolver**: Fazer as alterações seguindo as convenções do projeto.
3. **Abrir PR**: Push e criar Pull Request para `main`.
4. **Revisão Iara**: A Iara comenta automaticamente no PR com análise de:
   - 🐛 Bugs potenciais
   - 🔒 Problemas de segurança
   - ⚡ Eficiência "Diet" (uso de memória/CPU)
   - 📚 Qualidade de código
5. **Iterar**: Corrigir conforme feedback e atualizar o PR.
6. **Merge**: Após aprovação, fazer merge na `main`.

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

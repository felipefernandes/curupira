# Projeto Curupira: O Protetor do Sistema (DietOpenclaw)

Status: Arquivo de Instrução Base para Agentes de IA (Antigravity) 
Hardware Alvo: Raspberry Pi 3 Model B (1GB RAM) 
Arquitetura: Python Minimalista (Assíncrono)

1. Filosofia do Projeto

O Curupira é uma alternativa "Lite" ao OpenClaw, projetado para alta performance em hardware limitado. Ele atua como um assistente pessoal inteligente, focado em monitoramento de sistema e automação de tarefas definidas pelo usuário.

2. Pilares Técnicos

* Cérebro: Google Gemini 1.5 Flash (Processamento principal) e Groq (LLaMA 3 - Alternativa rápida).
* Interface: Telegram (python-telegram-bot) - Interface leve e universal.
* Automação: 
  - Execução de scripts e tarefas customizadas.
  - Monitoramento de hardware (temperatura, CPU, RAM).
* Eficiência: 
  - Foco em baixo consumo de memória (Headless).
  - Código assíncrono.

3. Estrutura do Projeto (Sugestão para o Agente)
```
curupira/
├── .env                # Chaves e IDs (Não versionado)
├── .gitignore          # Proteção de segredos
├── requirements.txt    # Dependências mínimas
├── bot.py              # Núcleo do sistema (Core)
├── config.py           # Validação de ambiente
├── ROADMAP.md          # Objetivos e Fases do Projeto
├── docs/               # Documentação técnica detalhada
│   ├── INSTALL.md      # Guia de instalação completo
│   └── SKILLS_FRAMEWORK.md # Guia oficial para criação de novas skills
└── skills/             # Pasta modular para automações
    └── system.py       # Monitoramento de hardware
```

4. Requisitos de Setup Local (Instruções para o Antigravity)

* Ambiente Virtual: Sempre utilizar `python3 -m venv venv`.
* Dependências Core: 
    - `python-telegram-bot`
    - `google-genai`
    - `groq`
    - `python-dotenv`
* Variáveis Obrigatórias:
    - `TELEGRAM_TOKEN`
    - `GEMINI_API_KEY`
    - `GROQ_API_KEY` (Opcional, mas recomendado)
    - `AUTHORIZED_USER_ID`

5. Setup no Raspberry Pi (Deploy)

1.  **Clone o Repositório**:
    ```bash
    git clone https://github.com/felipefernandes/curupira.git
    cd curupira
    ```

2.  **Crie o Ambiente Virtual**:
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Instale as Dependências**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure o Ambiente**:
    - Crie o arquivo `.env`: `nano .env`
    - Cole suas chaves (TELEGRAM_TOKEN, GEMINI_API_KEY, GROQ_API_KEY, AUTHORIZED_USER_ID).

5.  **Execute**:
    ```bash
    python bot.py
    ```

6. Comportamento Esperado (Persona)

* O Curupira deve ser **amigável, perspicaz e direto**.
* Ele é um assistente proativo, que conhece o sistema onde habita.
* Respostas da IA devem ser formatadas em Markdown para melhor leitura no Telegram.

7. Restrições de Desenvolvimento

* NÃO instale bibliotecas pesadas de Data Science localmente (Pandas/Numpy) para economizar RAM.
* NÃO utilize bases de dados complexas (preferir JSON ou SQLite para persistência mínima).
* SEMPRE priorize funções async para não travar o loop de eventos no Pi 3B.
* TODA nova funcionalidade de automação deve seguir o **[Skills Framework](docs/SKILLS_FRAMEWORK.md)**.

8. Fluxo de Contribuição (Revisão Automatizada)

O projeto utiliza a **Iara** 🧜‍♀️, uma revisora de código automatizada (DeepSeek V3) integrada ao GitHub Actions.

* **Criar Branch**: `git checkout -b feature/minha-feature`
* **Abrir PR**: A Iara revisa automaticamente verificando bugs, segurança, eficiência "Diet" e qualidade.
* **Iterar**: Corrigir conforme feedback da Iara e atualizar o PR.
* **Merge**: Após aprovação, fazer merge na `main`.

Gerado para Felipe Fernandes (@felipefernandesweb)

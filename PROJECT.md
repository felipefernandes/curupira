# Projeto Curupira: O Protetor do Sistema (DietOpenclaw)

Status: Arquivo de Instrução Base para Agentes de IA (Antigravity) 
Hardware Alvo: Raspberry Pi 3 Model B (1GB RAM) 
Arquitetura: Python Minimalista (Assíncrono)

1. Filosofia do Projeto

O Curupira é uma alternativa "Lite" ao OpenClaw, focado em alta performance em hardware limitado. Ele deve ser modular, seguro e atuar como um assistente para um Agile Coach / Game Producer com foco em cibersegurança.

2. Pilares Técnicos

* Cérebro: Google Gemini 1.5 Flash (via API) - Processamento pesado offboard.
* Interface: Telegram (python-telegram-bot) - Baixo consumo de memória.
* Segurança: - Whitelist rígida por USER_ID.
  - Gestão de segredos via .env.
  - Scripts de auditoria básica de sistema.
* Eficiência: - Limite de memória Python (ZRAM assistido).
  - Sem Interface Gráfica (Headless).

3. Estrutura do Projeto (Sugestão para o Agente)
```
curupira/
├── .env                # Chaves e IDs (Não versionado)
├── .gitignore          # Proteção de segredos
├── requirements.txt    # Dependências mínimas
├── bot.py              # Núcleo do sistema (Core)
├── config.py           # Validação de ambiente
└── skills/             # Pasta modular para automações
    ├── system.py       # Monitoramento de hardware
    └── <outras ferramentas/habilidades>
```

4. Requisitos de Setup Local (Instruções para o Antigravity)

* Ambiente Virtual: Sempre utilizar `python3 -m venv venv`.
* Dependências Core: - `python-telegram-bot`
- `google-generativeai`
- `python-dotenv`
* Variáveis Obrigatórias:
- `TELEGRAM_TOKEN`
- `GEMINI_API_KEY`
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
    - Cole suas chaves (TELEGRAM_TOKEN, GEMINI_API_KEY, AUTHORIZED_USER_ID).

5.  **Execute**:
    ```bash
    python bot.py
    ```

6. Comportamento Esperado (Persona)

* O Curupira deve ser direto, técnico e protetor.
* Se o comando vier de um usuário não autorizado, ignorar silenciosamente ou emitir alerta de segurança.
* Se a temperatura do Pi subir (vcgencmd), o bot deve avisar o usuário proativamente.
* Respostas da IA devem ser formatadas em Markdown para melhor leitura no Telegram.

6. Restrições de Desenvolvimento

* NÃO instale bibliotecas pesadas de Data Science localmente (Pandas/Numpy).
* NÃO utilize bases de dados complexas (preferir JSON ou SQLite para persistência mínima).
* SEMPRE priorize funções async para não travar o loop de eventos no Pi 3B.

Gerado para Felipe Fernandes (@felipefernandesweb)

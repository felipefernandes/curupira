## Tasks

### 1. Implementar Módulo Core (`core/health.py`)
- [x] 1.1 Criar validador de **Memória e ZRAM** (detectar se memoria + swap são suficientes ou se há config de zram ativa).
- [x] 1.2 Criar validador de **Segredos e ENV** (checagem das chaves do Groq, Gemini e Telegram; lendo configurações de config.toml e .env).
- [x] 1.3 Criar validador de **Dependências de Sistema** (checar presença de execução `ffmpeg` no PATH).
- [x] 1.4 Criar validador de **Conectividade** (testes de ping/request rápido vs URLs base do Telegram API e LMM/Groq API).
- [x] 1.5 Criar validador de **Git** (comparar branch atual com origin para identificar se o código está desatualizado, e se houve mudanças locais pendentes).
- [x] 1.6 Unificar a chamada em uma classe/função `run_full_diagnostic()` gerando relatório tipado (Dictionary ou TypedDict).

### 2. Script Standalone (Doctor CLI)
- [x] 2.1 Criar o script na raiz `check_health.py` executando e printando os status com cores ou formatações limpas (✅ / ❌ / ⚠️) na tela do terminal do ambiente.

### 3. Integração ao Bot e Chat Logs
- [x] 3.1 Atualizar inicialização do Bot para em log de Console gerar o resumo do Health Check.
- [x] 3.2 Modificar a Skill de "System Status" (em `skills/system_manager.py` ou atual monitoramento) para poder devolver as falhas descritas no prompt da requisição, alertando em formato de frase (Ex: "Aviso: ZRAM está desativado...").

### 4. Testes e Validação
- [x] 4.1 Adicionar testes unitários de ZRAM falso, missing bins, conectividade simulada.
- [x] 4.2 Documentar o uso do comando `check_health.py` no `README.md`.

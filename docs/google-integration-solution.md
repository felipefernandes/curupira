# Solução Definitiva: Integração Google Calendar - Curupira

**Data**: 2026-03-20
**Time**: google-integration-solution (3 agentes)
**Status**: ✅ Análise Completa

---

## 📋 Sumário Executivo

### Problema Identificado

**Bug Crítico**: Token OAuth do Google expira rapidamente (aparentemente "no dia seguinte") devido a **inconsistência no salvamento de credenciais** entre dois módulos do sistema.

**Causa Raiz**:
- `skills/google_calendar.py` → Salva token **criptografado** ✅
- `skills/calendar_reminder_bridge.py` → Salva token em **texto plano** ❌

**Impacto**: Após primeira renovação automática (~50 min), o arquivo de token fica corrompido, forçando re-autenticação manual.

### Solução Proposta

1. **Correção Imediata**: Centralizar lógica de salvamento de credenciais
2. **Melhoria UX**: Implementar fluxo OAuth mais amigável inspirado no Openclaw/gogcli
3. **Prevenção**: Adicionar file locking para evitar race conditions

**Tempo Estimado de Fix**: 30 minutos (bug crítico)
**Ganho**: Autenticação persistente indefinida (como deveria ser)

---

## 🔍 Análise Detalhada do Problema Atual

### Arquitetura de Autenticação (Estado Atual)

```
┌─────────────────────────────────────────────────────────────────┐
│ PRIMEIRA AUTENTICAÇÃO (Usuário clica "Configure o calendário") │
└─────────────────────────────────────────────────────────────────┘

1️⃣  google_calendar.py:_setup_calendar()
    └─ Gera PKCE pair (code_verifier + code_challenge)
    └─ Salva em data/pkce_state.json (plaintext, 10 min TTL)
    └─ Inicia OAuthCallbackServer (porta 8080)
    └─ Retorna auth_url + callback_url

2️⃣  Usuário abre URL e autoriza (Google)
    └─ Google redireciona para http://127.0.0.1:8080/callback?code=XXX

3️⃣  OAuthCallbackServer.wait_for_code() captura código
    └─ Sinaliza asyncio.Event

4️⃣  google_calendar.py:_exchange_code_for_tokens()
    └─ Lê code_verifier de data/pkce_state.json
    └─ Faz POST para token_url com code_verifier (PKCE)
    └─ Recebe access_token + refresh_token
    └─ ✅ SALVA TOKEN CRIPTOGRAFADO via TokenCipher.encrypt_token()
    └─ Deleta data/pkce_state.json (single-use)

5️⃣  Token armazenado em: data/google_token.json (CRIPTOGRAFADO)
    └─ Criptografia: Fernet (AES-128-CBC + HMAC-SHA256)
    └─ Chave derivada de: PBKDF2(TELEGRAM_TOKEN, salt, iterations=100k)
```

### O Bug Crítico (Linha 122)

**Arquivo**: `skills/calendar_reminder_bridge.py`

```python
async def _refresh_token(self, creds: Credentials) -> bool:
    try:
        await asyncio.wait_for(
            asyncio.to_thread(creds.refresh, Request()),
            timeout=30.0
        )

        # ❌ BUG AQUI - Salva SEM criptografia!
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())  # PLAINTEXT ⚠️

        return True
```

**Comparação com código correto** (`skills/google_calendar.py` linha 258-275):

```python
def _save_token(self, creds: Credentials):
    try:
        token_json = creds.to_json()

        # ✅ CORRETO - Criptografa antes de salvar
        encrypted_data = TokenCipher.encrypt_token(token_json)

        with open(TOKEN_FILE, "wb") as f:
            f.write(encrypted_data)  # BINARY ✅

        self.logger.info("Token salvo com sucesso (encrypted)")
```

### Timeline da Falha

| Tempo | Evento | Status |
|-------|--------|--------|
| T=0 | Usuário autoriza pela primeira vez | ✅ Token salvo criptografado |
| T=30-50 min | Bridge executa job de sincronização | ✅ Token ainda válido |
| T=50 min | Access token expira, bridge chama `_refresh_token()` | ✅ Refresh bem-sucedido |
| T=50 min | **Bridge salva token em plaintext** | ❌ **ARQUIVO CORROMPIDO** |
| T=50+ min | Próxima tentativa de uso (skill ou bridge) | ❌ `TokenCipher.decrypt_token()` retorna `None` |
| T=50+ min | Sistema deleta arquivo corrompido | ⚠️ Força re-autenticação |
| Próxima manhã | Usuário tenta usar calendar | ❌ "Não autenticado" |

**Por que parece "expirar no dia seguinte"?**
- Geralmente usuário não interage com calendar por ~12-24h (noite/madrugada)
- Na manhã seguinte, descobre que precisa re-autenticar
- Percebe como se credenciais tivessem "expirado rapidamente"

---

## 🌐 Como o Openclaw Resolve (Benchmark)

### Projeto Referência: gogcli

**gogcli** é uma CLI para Google Calendar desenvolvida em Go, parte do ecossistema Openclaw.

#### Arquitetura de Storage

**Backend Múltiplo com OS Keyring**:
```
├─ macOS: Keychain (integração nativa com AES-256)
├─ Windows: Credential Manager
├─ Linux: Secret Service (GNOME Keyring, KWallet)
└─ Fallback: File backend criptografado (JWT)
```

**Vantagens**:
- ✅ Usa criptografia nativa do OS (hardware-backed quando disponível)
- ✅ Proteção automática por senha/biometria do usuário
- ✅ Não requer implementação custom de crypto

**Desvantagens para Curupira**:
- ⚠️ Dependências de SO (não portável)
- ⚠️ Complexidade desnecessária para single-user bot
- ⚠️ Raspberry Pi headless pode não ter keyring

#### Fluxo de Autenticação

```bash
# Setup único
gog auth credentials credentials.json  # Armazena client_id/secret
gog auth add user@gmail.com           # OAuth flow (uma vez)

# Uso subsequente
gog calendar list  # Auto-refresh, sem re-autenticação
```

**Features**:
- Auto-refresh transparente de tokens
- Suporte headless (múltiplos fallback modes)
- Isolamento de tokens por cliente/conta
- "Authenticate once, use indefinitely"

#### Centralização de Storage

**gogcli Approach** (simplificado):
```go
// Uma função única para salvar tokens
func SaveToken(client string, email string, token *oauth2.Token) error {
    key := fmt.Sprintf("token:%s:%s", client, email)

    // Serializa
    data, _ := json.Marshal(token)

    // Salva no keyring (automaticamente criptografado)
    return keyring.Set(key, string(data))
}

// TODOS os módulos usam a mesma função
// - OAuth flow inicial
// - Token refresh background jobs
// - CLI commands
```

**Resultado**: Impossível ter inconsistência de salvamento.

---

## ✅ Proposta de Solução para Curupira

### Fase 1: Correção Crítica (Implementação Imediata)

#### 1.1. Centralizar Salvamento de Credenciais

**Criar módulo compartilhado**: `core/credential_manager.py`

```python
"""
Gerenciamento centralizado de credenciais Google OAuth.
Garante consistency entre todos os módulos que manipulam tokens.
"""

from pathlib import Path
from google.oauth2.credentials import Credentials
from core.token_encryption import TokenCipher
from core.config import DATA_DIR
import logging

TOKEN_FILE = DATA_DIR / "google_token.json"
logger = logging.getLogger(__name__)


def save_google_credentials(creds: Credentials) -> None:
    """
    Salva credenciais Google com criptografia consistente.

    USO:
    - google_calendar.py: após exchange de código
    - calendar_reminder_bridge.py: após refresh de token
    - Qualquer futuro módulo que manipule tokens

    Args:
        creds: Objeto Credentials do google-auth

    Raises:
        IOError: Se falhar ao escrever arquivo
        ValueError: Se creds inválido
    """
    if not creds:
        raise ValueError("Credentials object is None")

    try:
        # Serializa para JSON
        token_json = creds.to_json()

        # Criptografa (Fernet)
        encrypted_data = TokenCipher.encrypt_token(token_json)

        # Salva em modo binário
        with open(TOKEN_FILE, "wb") as f:
            f.write(encrypted_data)

        logger.info(
            f"Google credentials saved successfully "
            f"(encrypted, {len(encrypted_data)} bytes)"
        )

    except Exception as e:
        logger.error(f"Failed to save Google credentials: {e}")
        raise


def load_google_credentials() -> Credentials | None:
    """
    Carrega credenciais Google descriptografadas.

    Returns:
        Credentials object ou None se arquivo não existir/corrompido
    """
    if not TOKEN_FILE.exists():
        logger.warning(f"Token file not found: {TOKEN_FILE}")
        return None

    try:
        # Lê arquivo criptografado
        with open(TOKEN_FILE, "rb") as f:
            encrypted_data = f.read()

        # Descriptografa
        token_json = TokenCipher.decrypt_token(encrypted_data)

        if not token_json:
            logger.error("Failed to decrypt token (corrupted or wrong key)")
            return None

        # Deserializa para Credentials
        creds = Credentials.from_authorized_user_info(
            eval(token_json)  # JSON string → dict
        )

        logger.info("Google credentials loaded successfully")
        return creds

    except Exception as e:
        logger.error(f"Failed to load Google credentials: {e}")
        return None


def delete_google_credentials() -> bool:
    """
    Deleta arquivo de credenciais (revoke/logout).

    Returns:
        True se deletado com sucesso
    """
    try:
        if TOKEN_FILE.exists():
            TOKEN_FILE.unlink()
            logger.info("Google credentials deleted")
            return True
        return False
    except Exception as e:
        logger.error(f"Failed to delete credentials: {e}")
        return False
```

#### 1.2. Atualizar `calendar_reminder_bridge.py`

**Linha 122 (ANTES)**:
```python
with open(TOKEN_FILE, "w") as f:
    f.write(creds.to_json())
```

**Linha 122 (DEPOIS)**:
```python
# Importar no topo do arquivo
from core.credential_manager import save_google_credentials

# No método _refresh_token()
save_google_credentials(creds)
```

#### 1.3. Atualizar `google_calendar.py`

**Substituir método `_save_token()` (linha 258-276)**:
```python
# Importar no topo
from core.credential_manager import (
    save_google_credentials,
    load_google_credentials,
    delete_google_credentials
)

# Método _save_token() vira wrapper
def _save_token(self, creds: Credentials):
    """Salva token usando credential manager centralizado."""
    save_google_credentials(creds)

# Método _load_token() vira wrapper
def _load_token(self) -> Credentials | None:
    """Carrega token usando credential manager centralizado."""
    return load_google_credentials()
```

**Resultado**: Impossível ter inconsistência de salvamento.

---

### Fase 2: Melhorias de Robustez (Médio Prazo)

#### 2.1. File Locking durante Refresh

**Problema**: Race condition se skill e bridge refresham simultaneamente.

**Solução** (adicionar em `credential_manager.py`):

```python
import fcntl  # Unix
# import msvcrt  # Windows (alternativa)
from pathlib import Path

LOCK_FILE = DATA_DIR / ".google_token.lock"


def save_google_credentials_with_lock(creds: Credentials) -> None:
    """
    Salva credenciais com file lock exclusivo.
    Previne race conditions em refresh simultâneo.
    """
    LOCK_FILE.touch(exist_ok=True)

    with open(LOCK_FILE, "w") as lock:
        # Acquire exclusive lock (blocks até obter)
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)

        try:
            # Check se outro processo já refreshou enquanto esperava
            existing = load_google_credentials()
            if existing and existing.valid:
                logger.info("Token already refreshed by another process")
                return

            # Salva
            save_google_credentials(creds)

        finally:
            # Release lock
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
```

**Uso**:
```python
# Em vez de save_google_credentials(creds)
save_google_credentials_with_lock(creds)
```

#### 2.2. Token Health Check (Background Job)

**Objetivo**: Detectar proativamente tokens corrompidos.

**Implementação** (adicionar em `bot.py`):

```python
async def check_token_health():
    """
    Verifica saúde do token Google periodicamente.
    Alerta usuário se houver problemas.
    """
    from core.credential_manager import load_google_credentials
    from core.audit_logger import AuditLogger

    logger = logging.getLogger("token_health")
    audit = AuditLogger()

    try:
        creds = load_google_credentials()

        if not creds:
            logger.warning("Token health check: No credentials found")
            audit.log_event("token_health_check", {
                "status": "missing",
                "action_required": "user_reauth"
            })
            # TODO: Notificar usuário via Telegram
            return

        if not creds.valid:
            if creds.expired and creds.refresh_token:
                logger.info("Token expired but refresh_token present (OK)")
                audit.log_event("token_health_check", {
                    "status": "expired_recoverable"
                })
            else:
                logger.error("Token invalid and no refresh_token (BAD)")
                audit.log_event("token_health_check", {
                    "status": "invalid_unrecoverable",
                    "action_required": "user_reauth"
                })
                # TODO: Notificar usuário via Telegram
        else:
            logger.debug("Token health check: OK")
            audit.log_event("token_health_check", {"status": "healthy"})

    except Exception as e:
        logger.error(f"Token health check failed: {e}")


# Agendar job (executar diariamente às 8h)
scheduler.add_job(
    check_token_health,
    trigger="cron",
    hour=8,
    minute=0,
    id="token_health_check"
)
```

---

### Fase 3: Melhorias de UX (Longo Prazo)

#### 3.1. OAuth State Caching (Fluxo Assíncrono)

**Problema Atual**: Se usuário fechar navegador, precisa recomeçar.

**Solução Inspirada em gogcli**: Cache de state persistente.

```python
# Em oauth_pkce_state.py
def save_oauth_state_with_expiry(
    state: str,
    code_verifier: str,
    user_id: int,
    expiry_seconds: int = 600
):
    """
    Salva state OAuth com TTL de 10 min (padrão).
    Permite fluxo assíncrono multi-device.
    """
    import time

    data = {
        "state": state,
        "code_verifier": code_verifier,
        "user_id": user_id,
        "expires_at": time.time() + expiry_seconds
    }

    # Salvar em SQLite (mais robusto que JSON)
    # ... implementação ...
```

**Benefício**: Usuário pode:
1. Iniciar auth no celular
2. Abrir link no desktop
3. Colar código de volta no Telegram horas depois
4. State ainda válido (se dentro de 10 min)

#### 3.2. Comando de Status

**Feature**: `/calendar_status` para verificar autenticação.

```python
@skill("calendar_status")
async def calendar_status(context: SkillContext) -> str:
    """
    Verifica status da autenticação Google Calendar.

    Retorna:
    - ✅ Autenticado e válido
    - ⚠️ Autenticado mas expirado (auto-refresh disponível)
    - ❌ Não autenticado (requer configuração)
    """
    creds = load_google_credentials()

    if not creds:
        return (
            "❌ **Não autenticado**\n\n"
            "Use /setup_calendar para configurar."
        )

    if creds.valid:
        # Calcular tempo até expiração
        from datetime import datetime, timezone
        expires_in = (creds.expiry - datetime.now(timezone.utc)).total_seconds()

        return (
            f"✅ **Autenticado e válido**\n\n"
            f"Token expira em: {int(expires_in // 60)} minutos\n"
            f"Refresh disponível: {'Sim' if creds.refresh_token else 'Não'}"
        )
    else:
        if creds.refresh_token:
            return (
                "⚠️ **Token expirado (auto-renovação disponível)**\n\n"
                "Na próxima ação, o token será renovado automaticamente."
            )
        else:
            return (
                "❌ **Token inválido**\n\n"
                "Refresh token não disponível. Use /setup_calendar novamente."
            )
```

#### 3.3. Logout/Revoke

**Feature**: `/calendar_logout` para revogar acesso.

```python
@skill("calendar_logout")
async def calendar_logout(context: SkillContext) -> str:
    """
    Revoga acesso ao Google Calendar e deleta credenciais locais.
    """
    from core.credential_manager import (
        load_google_credentials,
        delete_google_credentials
    )
    import requests

    creds = load_google_credentials()

    if not creds:
        return "Você não está autenticado."

    try:
        # Revogar token no Google
        revoke_url = "https://oauth2.googleapis.com/revoke"
        requests.post(revoke_url, params={"token": creds.token})

        # Deletar arquivo local
        delete_google_credentials()

        return (
            "✅ **Acesso revogado com sucesso**\n\n"
            "Suas credenciais foram removidas localmente e no Google."
        )

    except Exception as e:
        logger.error(f"Logout failed: {e}")
        return f"❌ Erro ao revogar acesso: {e}"
```

---

## 📊 Comparação: Antes vs Depois

### Persistência de Credenciais

| Aspecto | ANTES (Bug) | DEPOIS (Fix) |
|---------|-------------|--------------|
| **Primeira auth** | ✅ Criptografado | ✅ Criptografado |
| **Após 1º refresh** | ❌ Plaintext (corrompido) | ✅ Criptografado |
| **Duração** | ~50 min até falhar | ♾️ Indefinido |
| **Re-auth manual** | A cada ~1h | Nunca (exceto revoke) |

### Consistência de Storage

| Módulo | ANTES | DEPOIS |
|--------|-------|--------|
| `google_calendar.py` | Custom `_save_token()` | `credential_manager.save()` |
| `calendar_reminder_bridge.py` | Plaintext `f.write()` | `credential_manager.save()` |
| **Consistency** | ❌ Divergente | ✅ Centralizado |

### Experiência do Usuário

| Cenário | ANTES | DEPOIS |
|---------|-------|--------|
| Setup inicial | ⚠️ Complexo (14 passos) | ⚠️ Igual (melhorias em Fase 3) |
| Uso diário | ❌ Re-auth frequente | ✅ Transparente |
| Debugging | 😤 "Por que expirou?" | 😌 `/calendar_status` |
| Logout | ⚠️ Manual (deletar arquivo) | ✅ `/calendar_logout` |

---

## 🚀 Passos de Implementação

### Sprint 1: Bug Fix Crítico (Prioridade Máxima)

**Objetivo**: Eliminar corrupção de token.

**Tasks**:
- [ ] Criar `core/credential_manager.py` com funções centralizadas
- [ ] Atualizar `calendar_reminder_bridge.py` linha 122
- [ ] Atualizar `google_calendar.py` para usar credential manager
- [ ] Testar fluxo completo (auth → refresh → uso)
- [ ] Validar que token persiste após 24h+

**Tempo Estimado**: 2-3 horas
**Risco**: Baixo (mudança localizada)

### Sprint 2: Robustez (Recomendado)

**Objetivo**: Prevenir race conditions e detectar problemas proativamente.

**Tasks**:
- [ ] Implementar file locking em `save_google_credentials_with_lock()`
- [ ] Adicionar job de health check (`check_token_health()`)
- [ ] Configurar alertas Telegram para problemas de token
- [ ] Adicionar métricas de refresh (quantos refreshes/dia)

**Tempo Estimado**: 4-5 horas
**Risco**: Médio (concorrência pode ter edge cases)

### Sprint 3: UX Improvements (Nice-to-have)

**Objetivo**: Tornar experiência mais amigável.

**Tasks**:
- [ ] Implementar `/calendar_status` command
- [ ] Implementar `/calendar_logout` command
- [ ] State caching em SQLite (OAuth assíncrono)
- [ ] Melhorar mensagens de erro (mais contexto)
- [ ] Documentação user-friendly do setup

**Tempo Estimado**: 6-8 horas
**Risco**: Baixo (features aditivas)

---

## 🎯 Critérios de Sucesso

### Teste de Aceitação

**Cenário 1: Autenticação Inicial**
```
GIVEN: Usuário não autenticado
WHEN: Executa /setup_calendar
THEN: Token salvo criptografado em data/google_token.json
```

**Cenário 2: Refresh Automático (Bridge)**
```
GIVEN: Token expirado, refresh_token válido
WHEN: Bridge executa job de sincronização
THEN: Token renovado e salvo criptografado (não plaintext)
```

**Cenário 3: Persistência de Longo Prazo**
```
GIVEN: Usuário autenticado há 7 dias
WHEN: Usa /list_events
THEN: Funciona sem re-autenticação
```

**Cenário 4: Race Condition**
```
GIVEN: Skill e bridge tentam refresh simultâneo
WHEN: Ambos detectam token expirado
THEN: Apenas um refresh ocorre (file lock), outro reutiliza
```

### Métricas de Monitoramento

**Adicionar em `logs/security_audit.log`**:

```json
{
  "event": "token_refresh",
  "timestamp": "2026-03-20T10:30:00Z",
  "source": "calendar_reminder_bridge",
  "success": true,
  "method": "save_google_credentials",
  "encryption": "fernet"
}
```

**Dashboard Simples** (logs diários):
```bash
# Quantos refreshes bem-sucedidos hoje?
grep "token_refresh" logs/security_audit.log | grep "success\": true" | wc -l

# Algum token corrompido detectado?
grep "Failed to decrypt token" logs/curupira.log
```

---

## 📚 Referências

### Análises Realizadas

1. **Análise do Código Atual (Agent: current-integration-analyst)**
   - Identificação de 6 camadas de segurança implementadas
   - Bug crítico em `calendar_reminder_bridge.py:122`
   - Timeline de falha detalhada

2. **Pesquisa Openclaw (Agent: openclaw-researcher)**
   - gogcli: OS Keyring implementation
   - Boas práticas de centralização
   - Issues similares na comunidade Openclaw

### Fontes Externas

- [Connect Openclaw to Gmail Tutorial](https://www.agentmail.to/blog/connect-openclaw-to-gmail)
- [gogcli GitHub Repository](https://github.com/steipete/gogcli)
- [99designs/keyring Go Package](https://pkg.go.dev/github.com/99designs/keyring)
- [Openclaw Issue #48153: Token overwriting bug](https://github.com/openclaw/openclaw/issues/48153)
- [Openclaw Issue #2036: OAuth refresh race condition](https://github.com/openclaw/openclaw/issues/2036)

### Documentação Google OAuth

- [OAuth 2.0 for Mobile & Desktop Apps](https://developers.google.com/identity/protocols/oauth2/native-app)
- [Refreshing an access token (offline access)](https://developers.google.com/identity/protocols/oauth2/web-server#offline)

---

## 🤝 Consenso do Time

**Acordado por**:
- ✅ current-integration-analyst (análise técnica)
- ✅ openclaw-researcher (benchmark)
- ✅ solution-architect (consolidação)

**Decisões Chave**:

1. **Manter Fernet Encryption** (não migrar para OS Keyring)
   - Justificativa: Simplicidade, portabilidade, suficiente para single-user bot
   - Trade-off: Não usa hardware-backed encryption (aceitável)

2. **Centralizar Storage Logic** (não apenas documentar)
   - Justificativa: Única forma de garantir consistency
   - Implementação: Módulo `credential_manager.py`

3. **File Locking Opcional em Sprint 2** (não obrigatório)
   - Justificativa: Edge case raro (skill e bridge refresham simultaneamente)
   - Prioridade: Média (pode implementar depois)

4. **UX Improvements em Sprint 3** (não bloqueia fix)
   - Justificativa: Bug crítico é mais urgente
   - `/calendar_status` e `/calendar_logout` são nice-to-have

---

## ✅ Próximos Passos

### ✅ Fase 1: Implementação Completa (2026-03-21)

1. ✅ **Criar `core/credential_manager.py`**
   - Módulo criado com 3 funções: save, load, delete
   - Docstrings completos, error handling, async safety comments
   - **Status**: COMPLETO

2. ✅ **Aplicar Fix em `calendar_reminder_bridge.py`**
   - Linha 122 corrigida: plaintext → `save_google_credentials(creds)`
   - Import adicionado, verificado sem outros plaintext writes
   - **Status**: COMPLETO

3. ✅ **Refatorar `google_calendar.py`**
   - `_save_token()` e `_load_token()` delegam para credential manager
   - API pública preservada (backward compatible)
   - **Status**: COMPLETO

4. ✅ **Health Check Job Adicionado**
   - Função `check_token_health()` criada em `bot.py`
   - Agendado diariamente às 8:00 AM
   - Notificações Telegram + audit logging implementados
   - **Status**: COMPLETO

### 🧪 Validação (Pós-Merge no Raspberry Pi)

5. 🔲 **Teste Manual: Primeira Autenticação**
   - Deletar `data/google_token.json`
   - Executar `/setup_calendar`
   - Verificar token salvo criptografado (arquivo binário)

6. 🔲 **Teste Manual: Token Refresh**
   - Aguardar background sync job ou forçar refresh
   - Verificar token ainda criptografado após refresh

7. 🔲 **Teste Manual: Persistência de Longo Prazo**
   - Usar calendar por 24-48h
   - Confirmar que NÃO pede re-autenticação

8. 🔲 **Monitorar Logs**
   - `grep "Token salvo com sucesso" logs/curupira.log`
   - Verificar ausência de "Failed to decrypt token"

### 🔮 Melhorias Futuras (Sprint 2+)

9. 🔲 Implementar file locking (opcional, se race conditions observadas)
10. 🔲 Criar `/calendar_status` e `/calendar_logout` commands
11. 🔲 Documentar setup user-friendly para usuários finais

---

## 🆘 Troubleshooting: Alertas de Autenticação

### Alerta: "⚠️ Google Calendar não autenticado"

**Quando aparece**: Health check diário (8:00 AM) detecta que não há credenciais salvas.

**Causa**: Arquivo `data/google_token.json` não existe ou foi deletado.

**Solução**:
```
1. Abra conversa com o Curupira no Telegram
2. Digite: /setup_calendar
3. Siga as instruções para autorizar acesso ao Google
4. Aguarde confirmação: "✅ Token salvo com sucesso"
```

**Após re-autenticar**: O problema não deve ocorrer novamente (token persiste indefinidamente).

---

### Alerta: "❌ Google Calendar: token inválido"

**Quando aparece**: Health check diário detecta que credenciais estão corrompidas e não podem ser renovadas.

**Causas possíveis**:
- Você revogou acesso nas configurações do Google
- Arquivo de token foi corrompido manualmente
- Chave de criptografia mudou (TELEGRAM_TOKEN alterado no `.env`)

**Solução**:
```
1. Abra conversa com o Curupira no Telegram
2. Digite: /setup_calendar
3. Autorize novamente o acesso ao Google
```

**Nota**: Se o problema persistir após re-autenticação, verifique logs:
```bash
grep "Failed to decrypt token" logs/curupira.log
grep "token_health_check" logs/security_audit.log
```

---

### Token Expira Rapidamente (Re-autenticação Frequente)

**Sintoma**: Precisa executar `/setup_calendar` todos os dias ou várias vezes ao dia.

**Se isso ocorrer APÓS este fix**: Algo está errado! Este fix deveria eliminar esse problema.

**Diagnóstico**:
```bash
# 1. Verificar se token está sendo salvo criptografado
file data/google_token.json
# Esperado: "data/google_token.json: data" (binário)
# Errado: "data/google_token.json: JSON data" (plaintext)

# 2. Verificar logs de refresh
grep "Token renovado" logs/curupira.log
grep "Token salvo com sucesso" logs/curupira.log

# 3. Verificar se credential_manager está sendo usado
grep "Google credentials saved successfully" logs/curupira.log
```

**Se token estiver em plaintext**:
- Verificar que `calendar_reminder_bridge.py` linha 122 chama `save_google_credentials()`
- Verificar que import foi adicionado: `from core.credential_manager import save_google_credentials`

---

### Logs de Referência

**Logs esperados (tudo OK)**:
```
# Primeira autenticação
INFO - Token salvo com sucesso (encrypted)
INFO - Google credentials saved successfully (encrypted, 412 bytes)

# Background refresh (a cada 30-50 min)
INFO - Token renovado durante sync do calendário
INFO - Google credentials saved successfully (encrypted, 412 bytes)

# Health check diário (8:00 AM)
DEBUG - Token health check: OK
```

**Logs de problema**:
```
# Token corrompido
ERROR - Failed to decrypt token (corrupted or plaintext)
ERROR - Falha ao descriptografar token (chave inválida ou dados corrompidos)

# Token ausente
WARNING - Token file not found: data/google_token.json
WARNING - Token health check: No credentials found
```

---

### Comandos Úteis de Diagnóstico

```bash
# Status do arquivo de token
ls -lh data/google_token.json
file data/google_token.json

# Últimas 50 linhas de log relevantes
tail -50 logs/curupira.log | grep -i "token\|calendar\|credentials"

# Audit log de eventos de saúde
jq 'select(.event == "token_health_check")' logs/security_audit.log | tail -5

# Verificar se health check job está agendado
grep "Token health check job agendado" logs/curupira.log
```

---

### Quando Reportar um Bug

Se após seguir este guia o problema persistir, abra uma issue no GitHub com:

**Informações necessárias**:
```
1. Versão do Curupira: git log -1 --oneline
2. Saída de: file data/google_token.json
3. Últimos logs relevantes (remova tokens/secrets):
   tail -100 logs/curupira.log | grep -i "calendar\|token"
4. Audit log de health checks:
   jq 'select(.event == "token_health_check")' logs/security_audit.log | tail -10
```

**Template de issue**:
```markdown
## Bug: Google Calendar Re-autenticação Frequente

**Sintoma**: [descreva o problema]

**Frequência**: [a cada X horas/dias]

**Logs**:
[cole logs aqui, removendo qualquer token/secret]

**Arquivo de token**:
[resultado de: file data/google_token.json]

**Ambiente**:
- Raspberry Pi Model: [3B/4/etc]
- Python version: [3.10/3.11/etc]
```

---

**Documento Gerado**: 2026-03-20
**Versão**: 1.0
**Status**: Pronto para Implementação ✅

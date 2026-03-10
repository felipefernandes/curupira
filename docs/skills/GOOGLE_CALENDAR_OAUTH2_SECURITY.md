# Google Calendar OAuth2 - Análise de Segurança

## Resumo Executivo

O Curupira implementa **5 camadas de defesa em profundidade** para OAuth2 do Google Calendar:

1. **PKCE (RFC 7636)**: Proteção contra code interception attacks
2. **Encryption at Rest**: Tokens criptografados com Fernet (AES-128 + HMAC-SHA256)
3. **Audit Logging**: Rastreamento JSON estruturado de eventos OAuth2
4. **Secure Logging**: Sanitização de error responses (nunca loga response bodies)
5. **Existing Protections**: .gitignore, OutputSanitizer, auth_code validation

**Client Type**: Confidential Client (app com client_secret)
**Compliance**: RFC 6749, RFC 7636, OWASP OAuth Cheat Sheet, NIST 800-111, NIST 800-92

---

## Arquitetura de Segurança

### 1. Client Type: Confidential Client

Curupira é um **Confidential Client** conforme RFC 6749 §2.1:
- Possui `client_secret` armazenado em `.env` (servidor seguro)
- Token exchange via POST HTTPS (client_secret no body, não na URL)
- PKCE é **opcional** para Confidential Clients (obrigatório apenas para Public Clients)

**Por que client_secret em POST é seguro:**
- RFC 6749 §3.2.1 define que client_secret deve ser enviado via POST body
- HTTPS criptografa todo o body (TLS 1.2+)
- Nunca aparece em URLs ou logs

### 2. Authorization Flow com PKCE

```
┌─────────────┐                                      ┌──────────────┐
│   Usuário   │                                      │    Google    │
└──────┬──────┘                                      └──────┬───────┘
       │                                                    │
       │ 1. "Configure calendário"                         │
       │────────────────────────────►                      │
       │                             ┌──────────────────┐  │
       │                             │ PKCE Pair Gen    │  │
       │                             │ - code_verifier  │  │
       │                             │ - code_challenge │  │
       │                             │ - state          │  │
       │                             └──────────────────┘  │
       │                             Save to              │
       │                             data/pkce_state.json  │
       │                                                    │
       │ 2. Authorization URL (com PKCE)                   │
       │◄────────────────────────────                      │
       │ https://accounts.google.com/o/oauth2/auth?        │
       │   client_id=...&                                  │
       │   code_challenge=...&                             │
       │   code_challenge_method=S256&                     │
       │   state=...                                       │
       │                                                    │
       │ 3. User clicks URL                                │
       │───────────────────────────────────────────────────►
       │                                                    │
       │ 4. User authorizes                                │
       │───────────────────────────────────────────────────►
       │                                                    │
       │ 5. Authorization Code                             │
       │◄───────────────────────────────────────────────────
       │                                                    │
       │ 6. "configure com código: ABC123"                 │
       │────────────────────────────►                      │
       │                             ┌──────────────────┐  │
       │                             │ Load PKCE State  │  │
       │                             │ Get code_verifier│  │
       │                             └──────────────────┘  │
       │                                                    │
       │                             7. Token Exchange     │
       │                             POST /token           │
       │                             {                     │
       │                               code: "ABC123",     │
       │                               code_verifier: "...",
       │                               client_secret: "..." │
       │                             }                     │
       │                             ─────────────────────►
       │                                                    │
       │                             8. Access Token       │
       │                             ◄─────────────────────
       │                             ┌──────────────────┐  │
       │                             │ Encrypt Token    │  │
       │                             │ Save to disk     │  │
       │                             │ Audit Log        │  │
       │                             └──────────────────┘  │
       │                                                    │
       │ 9. "✅ Autenticação concluída!"                   │
       │◄────────────────────────────                      │
       │                                                    │
```

### 3. PKCE Implementation Details

**Módulo**: `skills/oauth_pkce_state.py`

**RFC 7636 Compliance:**
- `code_verifier`: 43 chars (base64url-encoded, 32 random bytes)
- `code_challenge`: BASE64URL(SHA256(code_verifier))
- `code_challenge_method`: S256

**Security Properties:**
- **TTL**: 10 minutos (match com expiração de auth codes do Google)
- **Single-use**: State deletado após uso bem-sucedido
- **Expiration check**: States expirados são rejeitados e deletados
- **CSRF Protection**: State parameter valida CSRF attacks

**Storage**: `data/pkce_state.json` (plaintext, mas protected por .gitignore)

**Exemplo de State File:**
```json
{
  "state": "a1b2c3d4...",
  "code_verifier": "x9y8z7...",
  "expires_at": "2026-03-09T23:55:00"
}
```

### 4. Token Encryption at Rest

**Módulo**: `core/token_encryption.py`

**Algorithm**: Fernet (symmetric encryption)
- AES-128-CBC (encryption)
- HMAC-SHA256 (authentication)
- Timestamp verification (built-in)

**Key Derivation**: PBKDF2-HMAC-SHA256
- Input: TELEGRAM_TOKEN (from .env)
- Salt: `curupira_token_encryption_v1` (fixed, app-specific)
- Iterations: 100,000 (OWASP recommendation for 2023)
- Output: 32 bytes (Fernet key)

**Security Guarantees:**
- ✅ Tokens não legíveis em disco
- ✅ Proteção se `data/` for exposto (backup, physical access)
- ✅ Key rotation: Se TELEGRAM_TOKEN mudar, tokens ficam inacessíveis (força re-auth)
- ✅ Authenticated encryption (HMAC previne tampering)

**Storage Format**: `data/google_token.json` (binary, Fernet-encoded)

**Example (encrypted file content):**
```
gAAAAABm8KxL9QjZ... (base64-encoded Fernet token)
```

**⚠️ Important**: Se TELEGRAM_TOKEN mudar, usuário precisa re-autenticar.

### 5. Audit Logging

**Módulo**: `core/audit_logger.py`

**Log File**: `logs/security_audit.log`

**Format**: JSON structured (one event per line)

**Events Tracked:**
- `oauth2_auth_start`: Início do fluxo OAuth
- `oauth2_auth_success`: Autenticação bem-sucedida
- `oauth2_auth_failed`: Falha de autenticação (com error_type)
- `oauth2_token_refresh`: Refresh de access token (success/failure)

**Log Entry Example:**
```json
{
  "timestamp": "2026-03-09T23:45:12Z",
  "event": "oauth2_auth_success",
  "user_id": 123456789,
  "success": true,
  "details": {"provider": "google_calendar"}
}
```

**Benefits:**
- Rastreamento completo de autenticações
- Detecção de anomalias (múltiplas falhas = possível ataque)
- Forensics e compliance
- Fácil parsing (JSON structured)

**Security**: Logger dedicado (não propaga para root logger = não contamina logs principais)

### 6. Secure Logging

**Location**: `skills/google_calendar.py` linha ~540

**Problem (before):**
```python
except httpx.HTTPStatusError as e:
    self.logger.error(f"Resposta: {e.response.text}")  # ❌ INSEGURO
```

**Solution (after):**
```python
except httpx.HTTPStatusError as e:
    try:
        error_data = e.response.json()
        error_type = error_data.get("error", "unknown")
        self.logger.error(f"Tipo de erro OAuth2: {error_type}")  # ✅ SEGURO
    except Exception:
        pass  # Status code já foi logado
```

**Why?**
- RFC 6749 §5.2: Error responses podem conter `error_description` sensível
- Logar apenas `error` (enum padronizado) mantém debugging útil sem expor informação

**Aplicado também em**: `skills/calendar_reminder_bridge.py`

### 7. Gestão de Secrets

**Camadas de Proteção:**

1. **`.gitignore`** (linha 3, 12, 20, 32, 36):
   ```
   .env                      # TELEGRAM_TOKEN, GCAL_CLIENT_SECRET
   config.toml               # User config (pode conter API keys)
   data/                     # google_token.json (encrypted)
   logs/                     # security_audit.log
   *.json (except whitelist) # Protege pkce_state.json
   ```

2. **`OutputSanitizer`** (em `system_control.py`):
   - 14 padrões de detecção de secrets
   - Redacta automaticamente em outputs do bot

3. **Auth Code Validation** (`google_calendar.py`):
   - Rejeita placeholders LLM (17 variantes)
   - Valida formato OAuth2 (20-512 chars, alphanumeric + `-_/=`)

4. **HTTPS Only**:
   - Token exchange via HTTPS POST
   - TLS 1.2+ obrigatório

---

## Melhorias Futuras (Opcional)

### 1. Token Rotation Policy
Implementar rotação automática de refresh tokens (Google suporta via `reauth` scope).

### 2. Multi-User PKCE State
Atualmente, PKCE state é global (single-user bot). Se expandir para multi-user:
- Usar `user_id` como chave no state storage
- Implementar cleanup de states órfãos

### 3. Hardware Security Module (HSM)
Para production enterprise, considerar HSM para key storage (em vez de PBKDF2 de TELEGRAM_TOKEN).

### 4. Audit Log Rotation
Implementar logrotate para `security_audit.log` (evitar crescimento ilimitado).

---

## Referências

**RFCs:**
- [RFC 6749](https://datatracker.ietf.org/doc/html/rfc6749) - OAuth 2.0 Authorization Framework
- [RFC 7636](https://datatracker.ietf.org/doc/html/rfc7636) - Proof Key for Code Exchange (PKCE)

**OWASP:**
- [OAuth 2.0 Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/OAuth2_Cheat_Sheet.html)

**NIST:**
- [NIST 800-111](https://csrc.nist.gov/publications/detail/sp/800-111/final) - Guide to Storage Encryption
- [NIST 800-92](https://csrc.nist.gov/publications/detail/sp/800-92/final) - Guide to Computer Security Log Management

**Cryptography:**
- [Fernet Spec](https://github.com/fernet/spec/blob/master/Spec.md) - Fernet symmetric encryption
- [PBKDF2](https://datatracker.ietf.org/doc/html/rfc2898) - Password-Based Key Derivation Function 2

---

**Última Atualização**: 2026-03-09
**Responsável**: Curupira Security Team

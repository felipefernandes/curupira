"""
Google Calendar Skill for Curupira
===================================
Manages Google Calendar events via natural language using the Google Calendar API v3.

Features:
- OAuth2 authentication and token management
- List, create, and cancel calendar events
- Proactive reminders for upcoming events (via bridge)

Follows Curupira MCP-Lite framework (single skill, multiple tools).
"""

import asyncio
import httpx
import logging
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlencode

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from skills.base import BaseSkill
from core.config import (
    GCAL_CLIENT_ID,
    GCAL_CLIENT_SECRET,
    GCAL_CALENDARS,
    GCAL_CALENDAR_IDS,
    GCAL_WRITE_CALENDAR_ID
)

# Security modules for OAuth2 hardening
from skills.oauth_pkce_state import PKCEState
from core.credential_manager import (
    save_google_credentials,
    load_google_credentials,
    delete_google_credentials
)
from core.audit_logger import (
    log_oauth2_auth_start,
    log_oauth2_auth_success,
    log_oauth2_auth_failed,
    log_oauth2_token_refresh
)
from skills.oauth_http_server import OAuthCallbackServer, extract_code_from_url


# Google Calendar API scopes
# Using https://www.googleapis.com/auth/calendar (read/write access)
# - Required for: create, update, delete calendar events
# - calendar.readonly would be insufficient for full functionality
# - Same scope must be used in calendar_reminder_bridge.py (shared token)
SCOPES = ["https://www.googleapis.com/auth/calendar"]

# Token storage path
DATA_DIR = Path(__file__).parent.parent / "data"
TOKEN_FILE = DATA_DIR / "google_token.json"

# Invalid auth_code placeholders that LLMs commonly generate
# Using set for O(1) lookup performance
INVALID_AUTH_CODE_PLACEHOLDERS = frozenset({
    'none', 'nenhum', 'nenhum código', 'nenhum código fornecido',
    'n/a', 'null', 'sem código', 'não fornecido', '[seu_codigo]',
    '[codigo]', 'seu codigo', 'código', 'codigo', 'placeholder',
    'seu_código', '[seu código]', 'example', 'exemplo', 'test',
    'teste', 'invalid', 'inválido'
})


class GoogleCalendarSkill(BaseSkill):
    """
    Skill for managing Google Calendar events.

    Provides multi-tool access to Google Calendar API:
    - setup_calendar: OAuth2 authentication flow
    - list_calendar_events: List events for a time range
    - add_calendar_event: Create new events
    - cancel_calendar_event: Delete events
    """

    def __init__(self):
        self.logger = logging.getLogger("GoogleCalendarSkill")

        # Ensure data directory exists
        if not DATA_DIR.exists():
            DATA_DIR.mkdir(parents=True, exist_ok=True)

        # Validate configuration
        if not GCAL_CLIENT_ID or not GCAL_CLIENT_SECRET:
            self.logger.warning(
                "Google Calendar not configured. Set GCAL_CLIENT_ID and GCAL_CLIENT_SECRET in .env"
            )

        # Initialize context and user_id for audit logging
        # These will be populated by execute() method
        self.context: Dict[str, Any] = {}
        self.user_id: int = 0

        # OAuth state tracking (dual-channel approach)
        # Allows simultaneous listening for HTTP callback OR Telegram message
        self._oauth_server: Optional[OAuthCallbackServer] = None
        self._awaiting_auth = False
        self._auth_start_time = None

    def _resolve_calendar_id(self, requested_id: Optional[str], default_id: str) -> str:
        """
        Resolves a requested calendar name or alias to the actual Google Calendar ID.
        
        Uses case-insensitive lookup in GCAL_CALENDARS. If not found, returns
        the requested_id string as-is (assuming it's a raw calendar ID/email).
        """
        if not requested_id:
            return default_id
        
        req_clean = requested_id.strip().lower()
        
        # 1. Busca case-insensitive no dicionário de aliases
        for alias, real_id in GCAL_CALENDARS.items():
            if alias.lower() == req_clean:
                return real_id
                
        # 2. Fallback: Assume que o usuário forneceu o ID/e-mail real do calendário
        return requested_id

    @property
    def name(self) -> str:
        return "google_calendar"

    @property
    def display_name(self) -> str:
        return "📅 Google Agenda"

    @property
    def skill_group(self) -> str:
        return "calendar"

    @property
    def skill_group_emoji(self) -> str:
        return "📅"

    @property
    def description(self) -> str:
        return (
            "Gerencia eventos no Google Calendar: listar, criar e cancelar eventos. "
            "Use 'setup_calendar' para configurar autenticação inicial."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["setup_calendar", "list_calendar_events", "add_calendar_event", "cancel_calendar_event"],
                    "description": (
                        "Ação a executar: setup_calendar (autenticação), list_calendar_events (listar), "
                        "add_calendar_event (criar), cancel_calendar_event (cancelar)"
                    ),
                },
                "time_range": {
                    "type": "string",
                    "description": "Período para listar (list_calendar_events): 'today', 'tomorrow', 'week'",
                },
                "summary": {
                    "type": "string",
                    "description": "Título do evento (add_calendar_event)",
                },
                "start_time": {
                    "type": "string",
                    "description": "Início do evento ISO8601 (add_calendar_event). Ex: '2026-03-10T15:00:00'",
                },
                "end_time": {
                    "type": "string",
                    "description": "Fim do evento ISO8601 (add_calendar_event). Ex: '2026-03-10T16:00:00'",
                },
                "description": {
                    "type": "string",
                    "description": "Descrição do evento (add_calendar_event, opcional)",
                },
                "event_id": {
                    "type": "string",
                    "description": "ID do evento para cancelar (cancel_calendar_event)",
                },
                "auth_code": {
                    "type": "string",
                    "description": "Código de autorização OAuth2 (setup_calendar)",
                },
                "calendar_id": {
                    "type": "string",
                    "description": "Apelido ou ID da agenda (ex: 'primary', 'work', 'family'). Opcional.",
                },
            },
            "required": ["action"],
        }

    async def execute(self, context: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        Executes the requested calendar action.

        Args:
            context: Execution context (user_id, etc.)
            **kwargs: Action parameters

        Returns:
            Dict with status, data, and optional message
        """
        # Save context for audit logging
        self.context = context
        self.user_id = context.get("user_id", 0)  # Default to 0 if not available

        action = kwargs.get("action")

        if not action:
            return self.error("Ação não especificada")

        # Dispatch to appropriate handler
        try:
            if action == "setup_calendar":
                return await self._setup_calendar(kwargs.get("auth_code"))
            elif action == "list_calendar_events":
                return await self._list_calendar_events(
                    kwargs.get("time_range", "today"),
                    kwargs.get("calendar_id"),
                )
            elif action == "add_calendar_event":
                return await self._add_calendar_event(
                    kwargs.get("summary"),
                    kwargs.get("start_time"),
                    kwargs.get("end_time"),
                    kwargs.get("description"),
                    kwargs.get("calendar_id"),
                )
            elif action == "cancel_calendar_event":
                return await self._cancel_calendar_event(
                    kwargs.get("event_id"),
                    kwargs.get("calendar_id"),
                )
            else:
                return self.error(f"Ação desconhecida: {action}")

        except Exception as e:
            self.logger.error(f"Erro em {action}: {e}", exc_info=True)
            return self.error(f"Falha ao executar {action}: {str(e)}")

    # ── Internal Methods (OAuth2 & Token Management) ───────────────────────

    def _load_token(self) -> Optional[Credentials]:
        """
        Loads OAuth2 credentials from encrypted token file.

        Security:
            - Tokens are encrypted at rest using Fernet (AES-128-CBC + HMAC-SHA256)
            - Encryption key derived from TELEGRAM_TOKEN via PBKDF2 (100k iterations)
            - If decryption fails (e.g., TELEGRAM_TOKEN changed), returns None (forces re-auth)

        Note:
            Delegates to centralized credential_manager to ensure consistency
            across all modules. Maintains backward-compatible behavior of deleting
            corrupted tokens.
        """
        try:
            creds = load_google_credentials()

            if creds is None:
                # Token file missing or corrupted
                if TOKEN_FILE.exists():
                    self.logger.error("Falha ao descriptografar token (chave inválida ou dados corrompidos)")
                    self.logger.warning("Deletando token corrompido - usuário precisará re-autenticar")
                    try:
                        if not delete_google_credentials():
                            self.logger.error("Erro ao deletar token corrompido: operação falhou")
                    except Exception as del_err:
                        self.logger.error(f"Erro ao deletar token corrompido: {del_err}")
                return None

            return creds

        except Exception as e:
            self.logger.error(f"Erro ao carregar token: {type(e).__name__}")
            # Delete corrupted token file to force re-authentication
            if TOKEN_FILE.exists():
                self.logger.warning("Deletando token inválido - usuário precisará re-autenticar")
                try:
                    if not delete_google_credentials():
                        self.logger.error("Erro ao deletar token: operação falhou")
                except Exception as del_err:
                    self.logger.error(f"Erro ao deletar token: {del_err}")
            return None

    def _save_token(self, creds: Credentials):
        """
        Saves OAuth2 credentials to encrypted token file.

        Security:
            - Tokens are encrypted before writing to disk using Fernet
            - Encryption key derived from TELEGRAM_TOKEN
            - Protects tokens if data/ directory is exposed (backup, physical access)

        Note:
            Delegates to centralized credential_manager to ensure consistency
            across all modules (google_calendar.py, calendar_reminder_bridge.py).
        """
        try:
            save_google_credentials(creds)
            self.logger.info("Token salvo com sucesso (encrypted)")
        except Exception as e:
            self.logger.error(f"Erro ao salvar token: {type(e).__name__}")
            raise

    async def _refresh_token(self, creds: Credentials) -> bool:
        """
        Refreshes expired access token using refresh token.

        Returns:
            True if refresh successful, False otherwise

        Security:
            - Logs refresh attempts to audit log
            - Timeout protection (30s max)
            - Encrypted token storage after refresh
        """
        try:
            # Add timeout to prevent indefinite blocking
            await asyncio.wait_for(
                asyncio.to_thread(creds.refresh, Request()),
                timeout=30.0
            )
            self._save_token(creds)
            self.logger.info("Token renovado com sucesso")

            # Audit log: token refresh success
            log_oauth2_token_refresh(self.user_id, success=True)

            return True
        except asyncio.TimeoutError:
            self.logger.error("Timeout ao renovar token (30s)")
            log_oauth2_token_refresh(self.user_id, success=False)
            return False
        except Exception as e:
            self.logger.error(f"Erro ao renovar token: {type(e).__name__}")
            log_oauth2_token_refresh(self.user_id, success=False)
            return False

    async def _get_valid_credentials(self) -> Optional[Credentials]:
        """
        Gets valid credentials, refreshing if needed.

        Returns:
            Credentials object or None if authentication required
        """
        creds = self._load_token()

        if not creds:
            return None

        if not creds.valid:
            if creds.expired and creds.refresh_token:
                # Try to refresh
                if await self._refresh_token(creds):
                    return creds
                else:
                    return None
            else:
                # Token invalid and can't refresh
                return None

        return creds

    def _validate_auth_code(self, auth_code: Optional[str]) -> Optional[str]:
        """
        Validates and normalizes auth_code parameter.

        Filters out common LLM-generated placeholders and malformed values.

        Args:
            auth_code: Raw authorization code from LLM tool call

        Returns:
            Normalized auth_code or None if invalid

        Security:
            - Prevents processing of placeholder/dummy values
            - Validates basic format constraints for OAuth2 codes
            - Google OAuth codes are typically 40-100 chars, alphanumeric with hyphens/underscores
        """
        if not auth_code:
            return None

        # Normalize whitespace
        normalized = auth_code.strip()

        # Check against known invalid placeholders (O(1) lookup with frozenset)
        if normalized.lower() in INVALID_AUTH_CODE_PLACEHOLDERS:
            self.logger.warning(f"Rejected invalid placeholder auth_code: {normalized[:20]}...")
            return None

        # Basic format validation for OAuth2 authorization codes
        # Google codes are typically:
        # - 40-100 characters long
        # - Alphanumeric with allowed special chars: - _ / =
        # - No spaces or other special characters

        if len(normalized) < 20:
            self.logger.warning(f"auth_code too short ({len(normalized)} chars), likely invalid")
            return None

        if len(normalized) > 512:
            self.logger.warning(f"auth_code too long ({len(normalized)} chars), likely invalid")
            return None

        # Check for suspicious characters (spaces, quotes, brackets, etc.)
        # Valid chars: alphanumeric + - _ / =
        if not re.match(r'^[A-Za-z0-9\-_/=]+$', normalized):
            self.logger.warning("auth_code contains invalid characters")
            return None

        return normalized

    async def _get_client(self) -> Optional[httpx.AsyncClient]:
        """
        Gets authenticated HTTP client for Google Calendar API.

        Returns:
            httpx.AsyncClient or None if not authenticated
        """
        creds = await self._get_valid_credentials()

        if not creds:
            return None

        # Create client with authorization header
        headers = {
            "Authorization": f"Bearer {creds.token}",
            "Content-Type": "application/json",
        }

        return httpx.AsyncClient(
            base_url="https://www.googleapis.com/calendar/v3",
            headers=headers,
            timeout=10.0,
        )

    # ── Tool Implementations ───────────────────────────────────────────────

    async def _send_telegram_message(self, text: str):
        """
        Sends message to user via Telegram.

        This integrates with the bot's message sending system.
        Implementation depends on bot architecture.

        Args:
            text: Message to send to user

        TODO: Implement integration with bot.py
        Options:
        - Callback function passed in context
        - Async queue for outgoing messages
        - Direct Telegram API call with user_id
        """
        self.logger.info(f"[TELEGRAM] Would send message: {text[:50]}...")
        # Placeholder - needs integration with bot.py
        # await self.context.get('send_message_callback')(text)
        pass

    async def _start_oauth_server_background(self):
        """
        Background task that waits for authorization code via HTTP callback.

        When code is captured, automatically:
        1. Performs token exchange
        2. Sends success/error message to user via Telegram
        3. Cleans up state (_awaiting_auth = False)

        This is the "auto-capture" channel in dual-channel approach.
        Runs in parallel with message handler (fallback manual channel).

        Returns:
            None (runs in background via asyncio.create_task)
        """
        if not self._oauth_server:
            self.logger.error("Cannot start background task: no OAuth server instance")
            return

        try:
            self.logger.info("Background task: waiting for authorization code via HTTP callback...")

            # Wait for code with 5-minute timeout
            code = await self._oauth_server.wait_for_code()

            if code:
                self.logger.info("✅ Code captured automatically via HTTP callback")

                # Perform token exchange
                result = await self._exchange_code_for_tokens(code)

                if result["status"] == "success":
                    await self._send_telegram_message(
                        "✅ Autenticação concluída com sucesso!\n"
                        "Você pode usar o Google Calendar agora."
                    )
                else:
                    await self._send_telegram_message(
                        f"❌ Erro na autenticação: {result.get('error')}"
                    )

                # Clean up state
                self._awaiting_auth = False
                self._auth_start_time = None

        except asyncio.TimeoutError:
            self.logger.warning("⏱️ Timeout waiting for authorization code (5 min)")
            await self._send_telegram_message(
                "⏱️ Tempo esgotado para autenticação.\n"
                "Tente novamente: 'configure calendário'"
            )
            self._awaiting_auth = False
            self._auth_start_time = None

        except Exception as e:
            self.logger.error(f"Error in background task: {type(e).__name__}: {e}")
            self._awaiting_auth = False
            self._auth_start_time = None

        finally:
            # Always close server
            if self._oauth_server:
                try:
                    await self._oauth_server.stop()
                except Exception as e:
                    self.logger.error(f"Error stopping OAuth server: {e}")
                self._oauth_server = None

    async def _exchange_code_for_tokens(self, auth_code: str) -> Dict[str, Any]:
        """
        Exchanges authorization code for access/refresh tokens.

        Shared function used by both:
        - Auto-capture (background task via HTTP callback)
        - Manual fallback (user pastes URL via Telegram)

        Args:
            auth_code: Authorization code from Google OAuth redirect

        Returns:
            {"status": "success"/"error", "error": error_message (if error)}

        Security:
            - Loads and validates PKCE code_verifier
            - Single-use PKCE state (deleted after read)
            - Encrypted token storage
            - Audit logging for all outcomes
        """
        try:
            # Stop OAuth callback server if running
            if hasattr(self, '_oauth_server') and self._oauth_server:
                await self._oauth_server.stop()
                self._oauth_server = None
                self.logger.info("OAuth callback server stopped")

            # Load PKCE state from file (single-user bot, so safe to load latest)
            pkce_state_file = Path(__file__).parent.parent / "data" / "pkce_state.json"

            code_verifier = None
            if pkce_state_file.exists():
                try:
                    import json
                    from datetime import datetime as dt

                    with open(pkce_state_file, "r") as f:
                        pkce_data = json.load(f)

                    # Check expiration
                    expires_at = dt.fromisoformat(pkce_data["expires_at"])
                    if dt.now() < expires_at:
                        code_verifier = pkce_data["code_verifier"]

                        # Single-use: delete after reading
                        pkce_state_file.unlink()
                        self.logger.info("PKCE state loaded and deleted (single-use)")
                    else:
                        self.logger.warning("PKCE state expired")
                        pkce_state_file.unlink()
                except Exception as e:
                    self.logger.error(f"Error loading PKCE state: {type(e).__name__}")

            if not code_verifier:
                # Fallback: sem PKCE (backward compatibility)
                self.logger.warning("No PKCE state - token exchange without code_verifier")

            redirect_uri = "http://127.0.0.1:8080/callback"
            token_url = "https://oauth2.googleapis.com/token"

            # Token exchange payload with PKCE
            token_data = {
                "code": auth_code,
                "client_id": GCAL_CLIENT_ID,
                "client_secret": GCAL_CLIENT_SECRET,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            }

            # Include code_verifier if available (PKCE)
            if code_verifier:
                token_data["code_verifier"] = code_verifier

            # Exchange code for tokens with timeout
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(token_url, data=token_data)
                response.raise_for_status()
                token_response = response.json()

            # Create credentials from token response
            creds = Credentials(
                token=token_response.get("access_token"),
                refresh_token=token_response.get("refresh_token"),
                token_uri=token_url,
                client_id=GCAL_CLIENT_ID,
                client_secret=GCAL_CLIENT_SECRET,
                scopes=SCOPES,
            )

            # Save encrypted credentials
            self._save_token(creds)

            # Audit log: authentication success
            log_oauth2_auth_success(self.user_id, provider="google_calendar")

            return {"status": "success"}

        except httpx.HTTPStatusError as e:
            error_type = "unknown"
            try:
                error_data = e.response.json()
                error_type = error_data.get("error", "unknown")
                self.logger.error(f"OAuth2 error type: {error_type}")
            except Exception:
                pass

            self.logger.error(f"HTTP error {e.response.status_code} during token exchange")
            log_oauth2_auth_failed(self.user_id, error_type, provider="google_calendar")

            return {"status": "error", "error": f"Authentication failed ({error_type})"}

        except httpx.TimeoutException:
            self.logger.error("Timeout during token exchange")
            log_oauth2_auth_failed(self.user_id, "TimeoutException", provider="google_calendar")
            return {"status": "error", "error": "Timeout during authentication"}

        except Exception as e:
            self.logger.error(f"Error in token exchange: {type(e).__name__}")
            log_oauth2_auth_failed(self.user_id, type(e).__name__, provider="google_calendar")
            return {"status": "error", "error": "Authentication failed"}

    async def _setup_calendar(self, auth_code: Optional[str] = None) -> Dict[str, Any]:
        """
        Handles OAuth2 authentication flow.

        Args:
            auth_code: Authorization code from Google (optional, for first-time setup)

        Returns:
            Success with instructions or confirmation
        """
        if not GCAL_CLIENT_ID or not GCAL_CLIENT_SECRET:
            return self.error(
                "Google Calendar não configurado. Configure GCAL_CLIENT_ID e GCAL_CLIENT_SECRET no .env"
            )

        # Validate auth_code se fornecido
        if auth_code:
            # Tenta extrair código de URL (fallback manual)
            extracted = extract_code_from_url(auth_code)
            if extracted:
                auth_code = extracted
                self.logger.info("Código extraído de URL fornecida pelo usuário")

            # Valida código
            auth_code = self._validate_auth_code(auth_code)
            if not auth_code:
                return self.error("Código de autorização inválido. Tente novamente.")

        # Check if already authenticated
        creds = await self._get_valid_credentials()
        if creds:
            return self.success(
                {"status": "authenticated"},
                message="Você já está autenticado no Google Calendar"
            )

        # If no auth_code provided, generate authorization URL
        if not auth_code:
            try:
                # Build OAuth2 authorization URL WITH PKCE (localhost redirect)
                #
                # IMPORTANT: Using localhost redirect (127.0.0.1) instead of OOB
                # Google descontinuou OOB flow em janeiro de 2023
                #
                # Security improvements:
                # 1. PKCE: Protects against authorization code interception attacks
                # 2. Localhost redirect: Google OAuth 2.0 compliant method
                # 3. 127.0.0.1 instead of localhost: Google allows HTTP for IP loopback
                #
                # Using Localhost Redirect flow:
                # - redirect_uri: "http://127.0.0.1:8080/callback" (servidor HTTP local)
                # - Servidor captura código automaticamente
                # - Fallback manual: usuário cola URL completa se servidor inacessível
                # - access_type=offline: Requests refresh token for long-term access
                # - prompt=consent: Forces approval screen (ensures refresh token)

                # Generate PKCE pair
                pkce_pair = PKCEState.generate_pkce_pair()

                # Save code_verifier for token exchange
                PKCEState.save_pkce_state(pkce_pair["state"], pkce_pair["code_verifier"])

                # Start local HTTP server
                server = OAuthCallbackServer(port=8080, timeout=300)  # 5 min timeout
                callback_url = await server.start()

                # Audit log: OAuth flow started
                log_oauth2_auth_start(self.user_id)

                # Build authorization URL
                scope = " ".join(SCOPES)
                params = {
                    "client_id": GCAL_CLIENT_ID,
                    "redirect_uri": callback_url,  # http://127.0.0.1:8080/callback
                    "response_type": "code",
                    "scope": scope,
                    "access_type": "offline",
                    "prompt": "consent",
                    "state": pkce_pair["state"],
                    "code_challenge": pkce_pair["code_challenge"],
                    "code_challenge_method": "S256",
                }

                auth_url = f"https://accounts.google.com/o/oauth2/auth?{urlencode(params)}"

                # Save server instance for later use
                self._oauth_server = server

                # Mark state as awaiting authentication (dual-channel)
                self._awaiting_auth = True
                import time
                self._auth_start_time = time.time()

                # Start background task to wait for HTTP callback (auto-capture channel)
                asyncio.create_task(self._start_oauth_server_background())

                return self.success(
                    {"auth_url": auth_url, "callback_url": callback_url},
                    message=(
                        f"🔐 **Autenticação Google Calendar**\n\n"
                        f"**Passo 1:** Abra este link:\n{auth_url}\n\n"
                        f"**Passo 2:** Autorize o Curupira\n\n"
                        f"**Passo 3:** O código será capturado automaticamente!\n\n"
                        f"_Caso o navegador mostre erro de conexão:_\n"
                        f"Copie a URL completa da barra de endereço e envie aqui."
                    )
                )

            except Exception as e:
                self.logger.error(f"Erro ao iniciar OAuth flow: {e}")
                return self.error("Falha ao iniciar autenticação. Tente novamente.")

        # Exchange auth_code for tokens with PKCE
        result = await self._exchange_code_for_tokens(auth_code)

        # Clean up authentication state (manual fallback channel won)
        self._awaiting_auth = False
        self._auth_start_time = None

        if result["status"] == "success":
            return self.success(
                {"status": "authenticated"},
                message="✅ Autenticação concluída com sucesso! Você pode usar o Google Calendar agora."
            )
        else:
            return self.error(result.get("error", "Falha na autenticação. Verifique o código fornecido."))

    async def _list_calendar_events(self, time_range: str, calendar_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Lists calendar events for a time range.

        Args:
            time_range: "today", "tomorrow", or "week"
            calendar_id: Optional calendar name/alias or raw ID to query.

        Returns:
            Success with events list or error
        """
        client = await self._get_client()

        if not client:
            return self.error(
                "Não autenticado. Use 'Configure o calendário' para autenticar."
            )

        # Parse time range
        now = datetime.now()

        if time_range == "today":
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=1)
        elif time_range == "tomorrow":
            start = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=1)
        elif time_range == "week":
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=7)
        else:
            return self.error(f"Período inválido: {time_range}")

        # Format as ISO8601
        time_min = start.isoformat() + "Z"
        time_max = end.isoformat() + "Z"

        try:
            async def fetch_calendar(calendar_id: str) -> list:
                try:
                    res = await client.get(
                        f"/calendars/{calendar_id}/events",
                        params={
                            "timeMin": time_min,
                            "timeMax": time_max,
                            "singleEvents": True,
                            "orderBy": "startTime",
                            "maxResults": 50,
                        },
                    )
                    res.raise_for_status()
                    return res.json().get("items", [])
                except httpx.HTTPStatusError as err:
                    self.logger.error(
                        f"Erro HTTP {err.response.status_code} ao listar eventos do calendário {calendar_id}"
                    )
                    return []
                except Exception as err:
                    self.logger.error(
                        f"Erro inesperado ao listar eventos do calendário {calendar_id}: {err}"
                    )
                    return []

            # Determinar as agendas a serem consultadas resolvendo aliases
            resolved_cals = []
            if calendar_id and calendar_id.strip().lower() not in ("all", "todos"):
                resolved_cals = [self._resolve_calendar_id(calendar_id, None)]
            else:
                resolved_cals = GCAL_CALENDAR_IDS

            # Buscar de forma concorrente em todos os calendários configurados
            tasks = [fetch_calendar(cal_id) for cal_id in resolved_cals if cal_id]
            results = await asyncio.gather(*tasks)

            raw_events = []
            for items in results:
                raw_events.extend(items)

            # Deduplicação e normalização dos eventos
            seen_uids = set()
            seen_keys = set()
            events = []
            for item in raw_events:
                # 1. Chaves de deduplicação
                ical_uid = item.get("iCalUID")
                event_id = item.get("id")
                
                start_datetime = item.get("start", {}).get("dateTime")
                start_date = item.get("start", {}).get("date")
                start_val = start_datetime or start_date
                summary = item.get("summary", "Sem título").strip()
                fallback_key = (summary, start_val)

                if ical_uid:
                    if ical_uid in seen_uids:
                        continue
                    seen_uids.add(ical_uid)
                elif event_id:
                    if event_id in seen_uids:
                        continue
                    seen_uids.add(event_id)
                else:
                    if fallback_key in seen_keys:
                        continue
                    seen_keys.add(fallback_key)

                # 2. Filtragem de eventos de dia inteiro já encerrados
                end_datetime = item.get("end", {}).get("dateTime")
                end_date = item.get("end", {}).get("date")

                if start_date and end_date:
                    from datetime import datetime as dt
                    try:
                        event_end = dt.fromisoformat(end_date)
                        range_start = dt.fromisoformat(start.isoformat().split('T')[0])
                        if event_end <= range_start:
                            continue
                    except Exception as parse_err:
                        self.logger.warning(f"Erro ao parsear datas de evento de dia inteiro: {parse_err}")

                event = {
                    "id": event_id,
                    "summary": summary,
                    "start": start_val,
                    "end": end_datetime or end_date,
                    "description": item.get("description", ""),
                }
                events.append(event)

            # Ordenação cronológica por data/hora de início
            def get_start_sort_key(ev):
                val = ev.get("start") or ""
                if len(val) == 10:
                    return val + "T00:00:00"
                return val

            events.sort(key=get_start_sort_key)

            await client.aclose()

            return self.success(
                {"events": events, "count": len(events), "time_range": time_range},
                message=f"Encontrados {len(events)} evento(s) para {time_range}"
            )

        except httpx.TimeoutException:
            await client.aclose()
            self.logger.error("Timeout ao conectar com Google Calendar")
            return self.error("Timeout ao acessar o Google Calendar. Tente novamente.")
        except (httpx.ConnectError, httpx.NetworkError) as e:
            await client.aclose()
            self.logger.error(f"Erro de conexão com Google Calendar: {type(e).__name__}")
            return self.error("Não foi possível conectar ao Google Calendar. Verifique sua conexão.")
        except httpx.HTTPStatusError as e:
            await client.aclose()
            self.logger.error(f"Erro HTTP ao listar eventos: {e.response.status_code}")
            return self.error(f"Falha ao listar eventos: {e.response.status_code}")
        except Exception as e:
            await client.aclose()
            self.logger.error(f"Erro ao listar eventos: {e}")
            return self.error(f"Falha ao listar eventos: {str(e)}")

    async def _add_calendar_event(
        self,
        summary: Optional[str],
        start_time: Optional[str],
        end_time: Optional[str] = None,
        description: Optional[str] = None,
        calendar_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Creates a new calendar event.

        Args:
            summary: Event title
            start_time: Start time (ISO8601)
            end_time: End time (ISO8601, optional - defaults to 1h after start)
            description: Event description (optional)
            calendar_id: Optional calendar name/alias or raw ID to add event to.

        Returns:
            Success with event details or error
        """
        if not summary or not start_time:
            return self.error("Título (summary) e horário de início (start_time) são obrigatórios")

        client = await self._get_client()

        if not client:
            return self.error("Não autenticado. Use 'Configure o calendário' para autenticar.")

        # Resolve target calendar ID
        target_calendar = self._resolve_calendar_id(calendar_id, GCAL_WRITE_CALENDAR_ID)

        # Default end_time to 1 hour after start if not provided
        if not end_time:
            try:
                start_dt = datetime.fromisoformat(start_time.replace("Z", ""))
                end_dt = start_dt + timedelta(hours=1)
                end_time = end_dt.isoformat()
            except Exception as e:
                return self.error(f"Formato de data inválido: {e}")

        # Create event payload
        event_data = {
            "summary": summary,
            "start": {"dateTime": start_time, "timeZone": "America/Sao_Paulo"},
            "end": {"dateTime": end_time, "timeZone": "America/Sao_Paulo"},
        }

        if description:
            event_data["description"] = description

        try:
            response = await client.post(
                f"/calendars/{target_calendar}/events",
                json=event_data,
            )
            response.raise_for_status()
            created_event = response.json()

            await client.aclose()

            return self.success(
                {
                    "event_id": created_event.get("id"),
                    "summary": created_event.get("summary"),
                    "start": created_event.get("start", {}).get("dateTime"),
                    "htmlLink": created_event.get("htmlLink"),
                },
                message=f"✅ Evento '{summary}' criado com sucesso"
            )

        except httpx.TimeoutException:
            await client.aclose()
            self.logger.error("Timeout ao conectar com Google Calendar")
            return self.error("Timeout ao criar evento. Tente novamente.")
        except (httpx.ConnectError, httpx.NetworkError) as e:
            await client.aclose()
            self.logger.error(f"Erro de conexão com Google Calendar: {type(e).__name__}")
            return self.error("Não foi possível conectar ao Google Calendar. Verifique sua conexão.")
        except httpx.HTTPStatusError as e:
            await client.aclose()
            self.logger.error(f"Erro HTTP ao criar evento: {e.response.status_code}")
            return self.error(f"Falha ao criar evento: {e.response.status_code}")
        except Exception as e:
            await client.aclose()
            self.logger.error(f"Erro ao criar evento: {e}")
            return self.error(f"Falha ao criar evento: {str(e)}")

    async def _cancel_calendar_event(
        self,
        event_id: Optional[str],
        calendar_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Deletes a calendar event.

        Args:
            event_id: Event ID to delete
            calendar_id: Optional calendar name/alias or raw ID to delete event from.

        Returns:
            Success confirmation or error
        """
        if not event_id:
            return self.error("ID do evento (event_id) é obrigatório")

        client = await self._get_client()

        if not client:
            return self.error("Não autenticado. Use 'Configure o calendário' para autenticar.")

        # Resolve target calendar ID
        target_calendar = self._resolve_calendar_id(calendar_id, GCAL_WRITE_CALENDAR_ID)

        try:
            response = await client.delete(f"/calendars/{target_calendar}/events/{event_id}")
            response.raise_for_status()

            await client.aclose()

            return self.success(
                {"deleted": event_id},
                message="✅ Evento cancelado com sucesso"
            )

        except httpx.TimeoutException:
            await client.aclose()
            self.logger.error("Timeout ao conectar com Google Calendar")
            return self.error("Timeout ao cancelar evento. Tente novamente.")
        except (httpx.ConnectError, httpx.NetworkError) as e:
            await client.aclose()
            self.logger.error(f"Erro de conexão com Google Calendar: {type(e).__name__}")
            return self.error("Não foi possível conectar ao Google Calendar. Verifique sua conexão.")
        except httpx.HTTPStatusError as e:
            await client.aclose()
            if e.response.status_code == 404:
                return self.error("Evento não encontrado")
            self.logger.error(f"Erro HTTP ao cancelar evento: {e.response.status_code}")
            return self.error(f"Falha ao cancelar evento: {e.response.status_code}")
        except Exception as e:
            await client.aclose()
            self.logger.error(f"Erro ao cancelar evento: {e}")
            return self.error(f"Falha ao cancelar evento: {str(e)}")

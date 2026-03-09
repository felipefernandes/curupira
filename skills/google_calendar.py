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
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlencode

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from skills.base import BaseSkill
from core.config import GCAL_CLIENT_ID, GCAL_CLIENT_SECRET, GCAL_CALENDAR_ID


# Google Calendar API scopes
SCOPES = ["https://www.googleapis.com/auth/calendar"]

# Token storage path
DATA_DIR = Path(__file__).parent.parent / "data"
TOKEN_FILE = DATA_DIR / "google_token.json"


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

    @property
    def name(self) -> str:
        return "google_calendar"

    @property
    def display_name(self) -> str:
        return "📅 Google Agenda"

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
        action = kwargs.get("action")

        if not action:
            return self.error("Ação não especificada")

        # Dispatch to appropriate handler
        try:
            if action == "setup_calendar":
                return await self._setup_calendar(kwargs.get("auth_code"))
            elif action == "list_calendar_events":
                return await self._list_calendar_events(kwargs.get("time_range", "today"))
            elif action == "add_calendar_event":
                return await self._add_calendar_event(
                    kwargs.get("summary"),
                    kwargs.get("start_time"),
                    kwargs.get("end_time"),
                    kwargs.get("description"),
                )
            elif action == "cancel_calendar_event":
                return await self._cancel_calendar_event(kwargs.get("event_id"))
            else:
                return self.error(f"Ação desconhecida: {action}")

        except Exception as e:
            self.logger.error(f"Erro em {action}: {e}", exc_info=True)
            return self.error(f"Falha ao executar {action}: {str(e)}")

    # ── Internal Methods (OAuth2 & Token Management) ───────────────────────

    def _load_token(self) -> Optional[Credentials]:
        """Loads OAuth2 credentials from token file."""
        if not TOKEN_FILE.exists():
            return None

        try:
            creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
            return creds
        except Exception as e:
            self.logger.error(f"Erro ao carregar token: {e}")
            return None

    def _save_token(self, creds: Credentials):
        """Saves OAuth2 credentials to token file."""
        try:
            with open(TOKEN_FILE, "w") as f:
                f.write(creds.to_json())
            self.logger.info("Token salvo com sucesso")
        except Exception as e:
            self.logger.error(f"Erro ao salvar token: {e}")
            raise

    async def _refresh_token(self, creds: Credentials) -> bool:
        """
        Refreshes expired access token using refresh token.

        Returns:
            True if refresh successful, False otherwise
        """
        try:
            await asyncio.to_thread(creds.refresh, Request())
            self._save_token(creds)
            self.logger.info("Token renovado com sucesso")
            return True
        except Exception as e:
            self.logger.error(f"Erro ao renovar token: {e}")
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

        # Check if already authenticated
        creds = await self._get_valid_credentials()
        if creds:
            return self.success(
                {"status": "authenticated"},
                message="Você já está autenticado no Google Calendar"
            )

        # If no auth_code provided, generate authorization URL
        if not auth_code:
            # Create OAuth flow
            client_config = {
                "installed": {
                    "client_id": GCAL_CLIENT_ID,
                    "client_secret": GCAL_CLIENT_SECRET,
                    "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob"],
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                }
            }

            flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
            auth_url = flow.authorization_url(prompt="consent")[0]

            return self.success(
                {"auth_url": auth_url},
                message=(
                    f"Autenticação necessária. Acesse:\n{auth_url}\n\n"
                    "Após autorizar, copie o código e envie: 'Configure calendário com código: [SEU_CODIGO]'"
                )
            )

        # Exchange auth_code for tokens
        try:
            client_config = {
                "installed": {
                    "client_id": GCAL_CLIENT_ID,
                    "client_secret": GCAL_CLIENT_SECRET,
                    "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob"],
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                }
            }

            flow = InstalledAppFlow.from_client_config(client_config, SCOPES)

            # Fetch token using authorization code
            await asyncio.to_thread(flow.fetch_token, code=auth_code)
            creds = flow.credentials

            # Save credentials
            self._save_token(creds)

            return self.success(
                {"status": "authenticated"},
                message="✅ Autenticação concluída com sucesso! Você pode usar o Google Calendar agora."
            )

        except Exception as e:
            self.logger.error(f"Erro na autenticação OAuth2: {e}")
            return self.error(f"Falha na autenticação: {str(e)}")

    async def _list_calendar_events(self, time_range: str) -> Dict[str, Any]:
        """
        Lists calendar events for a time range.

        Args:
            time_range: "today", "tomorrow", or "week"

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
            response = await client.get(
                f"/calendars/{GCAL_CALENDAR_ID}/events",
                params={
                    "timeMin": time_min,
                    "timeMax": time_max,
                    "singleEvents": True,
                    "orderBy": "startTime",
                    "maxResults": 50,
                },
            )
            response.raise_for_status()
            data = response.json()

            events = []
            for item in data.get("items", []):
                event = {
                    "id": item.get("id"),
                    "summary": item.get("summary", "Sem título"),
                    "start": item.get("start", {}).get("dateTime") or item.get("start", {}).get("date"),
                    "end": item.get("end", {}).get("dateTime") or item.get("end", {}).get("date"),
                    "description": item.get("description", ""),
                }
                events.append(event)

            await client.aclose()

            return self.success(
                {"events": events, "count": len(events), "time_range": time_range},
                message=f"Encontrados {len(events)} evento(s) para {time_range}"
            )

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
    ) -> Dict[str, Any]:
        """
        Creates a new calendar event.

        Args:
            summary: Event title
            start_time: Start time (ISO8601)
            end_time: End time (ISO8601, optional - defaults to 1h after start)
            description: Event description (optional)

        Returns:
            Success with event details or error
        """
        if not summary or not start_time:
            return self.error("Título (summary) e horário de início (start_time) são obrigatórios")

        client = await self._get_client()

        if not client:
            return self.error("Não autenticado. Use 'Configure o calendário' para autenticar.")

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
                f"/calendars/{GCAL_CALENDAR_ID}/events",
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

        except httpx.HTTPStatusError as e:
            await client.aclose()
            self.logger.error(f"Erro HTTP ao criar evento: {e.response.status_code}")
            return self.error(f"Falha ao criar evento: {e.response.status_code}")
        except Exception as e:
            await client.aclose()
            self.logger.error(f"Erro ao criar evento: {e}")
            return self.error(f"Falha ao criar evento: {str(e)}")

    async def _cancel_calendar_event(self, event_id: Optional[str]) -> Dict[str, Any]:
        """
        Deletes a calendar event.

        Args:
            event_id: Event ID to delete

        Returns:
            Success confirmation or error
        """
        if not event_id:
            return self.error("ID do evento (event_id) é obrigatório")

        client = await self._get_client()

        if not client:
            return self.error("Não autenticado. Use 'Configure o calendário' para autenticar.")

        try:
            response = await client.delete(f"/calendars/{GCAL_CALENDAR_ID}/events/{event_id}")
            response.raise_for_status()

            await client.aclose()

            return self.success(
                {"deleted": event_id},
                message=f"✅ Evento cancelado com sucesso"
            )

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

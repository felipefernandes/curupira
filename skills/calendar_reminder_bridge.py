"""
Calendar Reminder Bridge for Curupira
======================================
Background job that syncs upcoming Google Calendar events to the local reminders database.

This bridge ensures users receive proactive notifications for upcoming events.
"""

import asyncio
import aiosqlite
import httpx
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Dict, Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from skills.memory import DB_FILE
from skills.reminders import ReminderManager
from core.config import GCAL_CALENDAR_IDS

# Security module for token encryption
import json
from core.token_encryption import TokenCipher
from core.credential_manager import save_google_credentials


# Google Calendar API scopes
# Must match google_calendar.py since both share the same OAuth token
# Needs write access for create/update/delete operations in GoogleCalendarSkill
SCOPES = ["https://www.googleapis.com/auth/calendar"]

# Token storage path
DATA_DIR = Path(__file__).parent.parent / "data"
TOKEN_FILE = DATA_DIR / "google_token.json"


class CalendarReminderBridge:
    """
    Background job to sync Google Calendar events to local reminders.

    Runs periodically (default: every 30 minutes) to:
    1. Fetch upcoming events from Google Calendar (next 4 hours)
    2. Create reminders for events that don't already have one
    3. Prevent duplicates using event's iCalUID stored in external_id
    """

    def __init__(self, user_id: int):
        """
        Initialize the bridge.

        Args:
            user_id: Telegram user ID to create reminders for
        """
        self.user_id = user_id
        self.logger = logging.getLogger("CalendarReminderBridge")
        self.reminder_manager = ReminderManager(db_path=DB_FILE)

    def _load_token(self) -> Credentials | None:
        """
        Loads OAuth2 credentials from encrypted token file.

        Security:
            - Tokens are encrypted at rest using Fernet (AES-128-CBC + HMAC-SHA256)
            - Shared encryption with google_calendar.py for consistency
            - If decryption fails, returns None (silent failure)
        """
        if not TOKEN_FILE.exists():
            return None

        try:
            # Read encrypted data
            with open(TOKEN_FILE, "rb") as f:
                encrypted_data = f.read()

            # Decrypt token JSON
            token_json = TokenCipher.decrypt_token(encrypted_data)

            if not token_json:
                self.logger.error("Falha ao descriptografar token")
                self.logger.warning("Deletando token corrompido - usuário precisará re-autenticar")
                try:
                    TOKEN_FILE.unlink()
                except Exception as del_err:
                    self.logger.error(f"Erro ao deletar token corrompido: {del_err}")
                return None

            # Parse JSON and create Credentials
            creds = Credentials.from_authorized_user_info(
                json.loads(token_json),
                SCOPES
            )
            return creds

        except Exception as e:
            self.logger.error(f"Erro ao carregar token: {type(e).__name__}")
            # Delete corrupted token file to force re-authentication
            if TOKEN_FILE.exists():
                self.logger.warning("Deletando token inválido - usuário precisará re-autenticar")
                try:
                    TOKEN_FILE.unlink()
                except Exception as del_err:
                    self.logger.error(f"Erro ao deletar token: {del_err}")
            return None

    async def _refresh_token(self, creds: Credentials) -> bool:
        """
        Refreshes expired access token.

        Returns:
            True if refresh successful, False otherwise
        """
        try:
            # Add timeout to prevent indefinite blocking
            await asyncio.wait_for(
                asyncio.to_thread(creds.refresh, Request()),
                timeout=30.0
            )

            # Save refreshed token (encrypted)
            await asyncio.to_thread(save_google_credentials, creds)

            self.logger.info("Token renovado durante sync do calendário")
            return True
        except asyncio.TimeoutError:
            self.logger.error("Timeout ao renovar token durante sync (30s)")
            return False
        except Exception as e:
            self.logger.error(f"Erro ao renovar token durante sync: {type(e).__name__}")
            return False

    async def _get_valid_credentials(self) -> Credentials | None:
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
                if await self._refresh_token(creds):
                    return creds
                else:
                    return None
            else:
                return None

        return creds

    async def _fetch_upcoming_events(self) -> List[Dict[str, Any]]:
        """
        Fetches upcoming events from Google Calendar (next 4 hours).

        Returns:
            List of event dictionaries
        """
        creds = await self._get_valid_credentials()

        if not creds:
            self.logger.warning("Calendário não autenticado - pulando sync")
            return []

        # Fetch events for next 4 hours (use UTC timezone-aware datetime)
        now = datetime.now(timezone.utc)
        time_min = now.isoformat().replace("+00:00", "Z")
        time_max = (now + timedelta(hours=4)).isoformat().replace("+00:00", "Z")

        try:
            async with httpx.AsyncClient(
                base_url="https://www.googleapis.com/calendar/v3",
                headers={
                    "Authorization": f"Bearer {creds.token}",
                    "Content-Type": "application/json",
                },
                timeout=10.0,
            ) as client:

                async def fetch_calendar(calendar_id: str) -> list:
                    try:
                        res = await client.get(
                            f"/calendars/{calendar_id}/events",
                            params={
                                "timeMin": time_min,
                                "timeMax": time_max,
                                "singleEvents": True,
                                "orderBy": "startTime",
                                "maxResults": 20,
                            },
                        )
                        res.raise_for_status()
                        return res.json().get("items", [])
                    except httpx.HTTPStatusError as err:
                        self.logger.error(
                            f"Erro HTTP {err.response.status_code} ao sincronizar agenda {calendar_id}"
                        )
                        return []
                    except Exception as err:
                        self.logger.error(
                            f"Erro inesperado ao sincronizar agenda {calendar_id}: {err}"
                        )
                        return []

                # Executa busca concorrente em todas as agendas configuradas
                tasks = [fetch_calendar(cal_id) for cal_id in GCAL_CALENDAR_IDS]
                results = await asyncio.gather(*tasks)

                raw_items = []
                for items in results:
                    raw_items.extend(items)

                # Deduplicação em memória para evitar criar lembretes idênticos
                seen_uids = set()
                seen_keys = set()
                events = []
                for item in raw_items:
                    ical_uid = item.get("iCalUID")
                    event_id = item.get("id")
                    
                    start_val = item.get("start", {}).get("dateTime") or item.get("start", {}).get("date")
                    summary = item.get("summary", "Evento sem título").strip()
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

                    # Garante que tenhamos um iCalUID único ou ID para salvar como external_id
                    event = {
                        "id": event_id,
                        "iCalUID": ical_uid or event_id or f"{summary}_{start_val}",
                        "summary": summary,
                        "start": start_val,
                        "description": item.get("description", ""),
                    }
                    events.append(event)

                self.logger.info(
                    f"Fetched e deduplicados {len(events)} evento(s) de {len(GCAL_CALENDAR_IDS)} calendário(s)"
                )
                return events

        except httpx.TimeoutException:
            self.logger.error("Timeout ao conectar com Google Calendar durante sync")
            return []
        except (httpx.ConnectError, httpx.NetworkError) as e:
            self.logger.error(f"Erro de conexão com Google Calendar durante sync: {type(e).__name__}")
            return []
        except httpx.HTTPStatusError as e:
            self.logger.error(f"HTTP error ao buscar eventos: {e.response.status_code}")
            return []
        except Exception as e:
            self.logger.error(f"Erro ao buscar eventos do calendário: {e}")
            return []

    async def _check_existing_reminder(self, external_id: str) -> bool:
        """
        Checks if a reminder already exists for this event.

        Args:
            external_id: Event's iCalUID

        Returns:
            True if reminder exists, False otherwise
        """
        try:
            async with aiosqlite.connect(str(DB_FILE)) as db:
                async with db.execute(
                    "SELECT id FROM reminders WHERE external_id = ? AND status = 'PENDING'",
                    (external_id,)
                ) as cursor:
                    row = await cursor.fetchone()
                    return row is not None
        except Exception as e:
            self.logger.error(f"Erro ao verificar reminder existente: {e}")
            return False

    async def _create_event_reminder(self, event: Dict[str, Any]):
        """
        Creates a reminder for an event (10 minutes before start time).

        Args:
            event: Event dictionary with id, iCalUID, summary, start
        """
        try:
            # Parse event start time
            start_str = event.get("start")
            if not start_str:
                return

            # Parse datetime with timezone support
            # Google Calendar returns: 2026-03-10T14:30:00Z (UTC)
            if start_str.endswith("Z"):
                # Convert "Z" to "+00:00" for proper UTC timezone parsing
                start_dt = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
            else:
                start_dt = datetime.fromisoformat(start_str)

            # Calculate reminder time (10 minutes before event)
            remind_at = start_dt - timedelta(minutes=10)

            # Get current time in UTC (timezone-aware)
            now = datetime.now(timezone.utc)

            # Don't create if reminder time is in the past
            if remind_at < now:
                return

            # Calculate delay in seconds
            delay_seconds = int((remind_at - now).total_seconds())

            # Create reminder message with [AGENDA] prefix
            message = f"[AGENDA] {event.get('summary', 'Evento')}"

            # Save reminder with external_id
            reminder_id = await self.reminder_manager.add_reminder(
                user_id=self.user_id,
                message=message,
                delay_seconds=delay_seconds,
                recurrence=None,
                is_task=False,
            )

            # Update external_id
            async with aiosqlite.connect(str(DB_FILE)) as db:
                await db.execute(
                    "UPDATE reminders SET external_id = ? WHERE id = ?",
                    (event.get("iCalUID"), reminder_id)
                )
                await db.commit()

            self.logger.info(
                f"Created reminder {reminder_id} for event '{event.get('summary')}' "
                f"(external_id: {event.get('iCalUID')})"
            )

        except Exception as e:
            self.logger.error(f"Erro ao criar reminder para evento: {e}")

    async def sync_events(self):
        """
        Main sync method.

        Fetches upcoming events and creates reminders for those that don't have one.
        """
        self.logger.info("Iniciando sincronização de eventos do Google Calendar...")

        # Fetch upcoming events
        events = await self._fetch_upcoming_events()

        if not events:
            self.logger.info("Nenhum evento próximo encontrado")
            return

        # Process each event
        created_count = 0
        skipped_count = 0

        for event in events:
            ical_uid = event.get("iCalUID")

            if not ical_uid:
                self.logger.warning(f"Evento sem iCalUID: {event.get('id')}")
                continue

            # Check if reminder already exists
            exists = await self._check_existing_reminder(ical_uid)

            if exists:
                skipped_count += 1
                continue

            # Create reminder
            await self._create_event_reminder(event)
            created_count += 1

        self.logger.info(
            f"Sync completo: {created_count} lembretes criados, {skipped_count} já existentes"
        )


async def run_calendar_sync(user_id: int):
    """
    Entry point for calendar sync job.

    Args:
        user_id: Telegram user ID
    """
    bridge = CalendarReminderBridge(user_id)
    await bridge.sync_events()

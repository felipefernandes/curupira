"""
Testes para CalendarReminderBridge
"""
import pytest
from pathlib import Path
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock, AsyncMock
from google.oauth2.credentials import Credentials

from skills.calendar_reminder_bridge import (
    CalendarReminderBridge,
    TOKEN_FILE
)


@pytest.fixture
def bridge():
    """Fixture que cria instância do bridge."""
    return CalendarReminderBridge(user_id=123456789)


@pytest.fixture
def cleanup_token_file():
    """Remove token file antes e depois de cada teste."""
    if TOKEN_FILE.exists():
        TOKEN_FILE.unlink()
    yield
    if TOKEN_FILE.exists():
        TOKEN_FILE.unlink()


@pytest.fixture
def mock_credentials():
    """Cria credenciais mock para testes."""
    return Credentials(
        token="mock_access_token",
        refresh_token="mock_refresh_token",
        token_uri="https://oauth2.googleapis.com/token",
        client_id="mock_client_id",
        client_secret="mock_client_secret",
        scopes=["https://www.googleapis.com/auth/calendar"]
    )


class TestBridgeInitialization:
    """Testa inicialização do bridge."""

    def test_bridge_initialization(self, bridge):
        """Verifica que bridge é inicializado corretamente."""
        assert bridge.user_id == 123456789
        assert bridge.logger is not None
        assert bridge.reminder_manager is not None


class TestLoadToken:
    """Testa carregamento de tokens."""

    def test_load_token_file_not_exists(self, bridge, cleanup_token_file):
        """Verifica que retorna None se arquivo não existe."""
        result = bridge._load_token()
        assert result is None

    def test_load_token_corrupted_file_auto_deletes(self, bridge, cleanup_token_file):
        """Verifica que token corrompido é deletado automaticamente."""
        # Criar arquivo corrompido
        with open(TOKEN_FILE, "w") as f:
            f.write("invalid data")

        assert TOKEN_FILE.exists()

        result = bridge._load_token()

        # Verifica que retornou None
        assert result is None
        # Verifica que arquivo foi deletado
        assert not TOKEN_FILE.exists()

    def test_load_token_deletion_failure_logged(self, bridge, cleanup_token_file):
        """Verifica que falha ao deletar token é logada."""
        # Criar arquivo corrompido
        with open(TOKEN_FILE, "w") as f:
            f.write("corrupted data")

        # Mockar Path.unlink() para lançar exceção
        original_unlink = Path.unlink
        def mock_unlink(self, *args, **kwargs):
            if str(self) == str(TOKEN_FILE):
                raise PermissionError("Access denied")
            return original_unlink(self, *args, **kwargs)

        with patch.object(Path, 'unlink', mock_unlink):
            with patch.object(bridge.logger, 'error') as mock_error:
                result = bridge._load_token()

                # Verifica que retornou None
                assert result is None
                # Verifica que erro foi logado
                assert any("Erro ao deletar token corrompido" in str(call) for call in mock_error.call_args_list)


class TestEventReminderCreation:
    """Testa criação de reminders a partir de eventos do calendário."""

    @pytest.mark.asyncio
    async def test_create_event_reminder_with_utc_timezone(self, bridge):
        """Verifica que parsing de datetime com 'Z' funciona corretamente (timezone-aware)."""
        # Simular evento do Google Calendar com data UTC
        future_time = datetime.now(timezone.utc) + timedelta(hours=1)
        event = {
            "id": "test_event_1",
            "iCalUID": "test-ical-uid-1",
            "summary": "Reunião de teste",
            "start": future_time.isoformat().replace("+00:00", "Z"),  # Formato Google: 2026-03-10T15:30:00Z
            "description": "Descrição do evento"
        }

        with patch.object(bridge.reminder_manager, 'add_reminder', return_value=1) as mock_add:
            with patch('aiosqlite.connect') as mock_connect:
                # Mock database connection para UPDATE de external_id
                mock_db = AsyncMock()
                mock_db.execute = AsyncMock()
                mock_db.commit = AsyncMock()
                mock_connect.return_value.__aenter__.return_value = mock_db

                await bridge._create_event_reminder(event)

                # Verifica que add_reminder foi chamado
                assert mock_add.call_count == 1
                call_kwargs = mock_add.call_args[1]

                # Verifica que mensagem contém [AGENDA] prefix
                assert call_kwargs["message"] == "[AGENDA] Reunião de teste"
                assert call_kwargs["user_id"] == 123456789
                assert call_kwargs["recurrence"] is None
                assert call_kwargs["is_task"] is False

                # Verifica que delay_seconds é aproximadamente 50 minutos (60 min - 10 min reminder)
                delay = call_kwargs["delay_seconds"]
                expected_delay = int((future_time - datetime.now(timezone.utc) - timedelta(minutes=10)).total_seconds())
                assert abs(delay - expected_delay) < 5  # Tolerância de 5 segundos

    @pytest.mark.asyncio
    async def test_create_event_reminder_past_event_skipped(self, bridge):
        """Verifica que eventos no passado não geram reminders."""
        # Evento que já aconteceu (1 hora atrás)
        past_time = datetime.now(timezone.utc) - timedelta(hours=1)
        event = {
            "id": "test_event_past",
            "iCalUID": "test-ical-uid-past",
            "summary": "Evento passado",
            "start": past_time.isoformat().replace("+00:00", "Z"),
        }

        with patch.object(bridge.reminder_manager, 'add_reminder') as mock_add:
            await bridge._create_event_reminder(event)

            # Verifica que add_reminder NÃO foi chamado (evento no passado)
            mock_add.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_event_reminder_no_start_time(self, bridge):
        """Verifica que evento sem start time não gera erro."""
        event = {
            "id": "test_event_no_start",
            "iCalUID": "test-ical-uid-no-start",
            "summary": "Evento sem horário",
            "start": None,  # Sem start time
        }

        with patch.object(bridge.reminder_manager, 'add_reminder') as mock_add:
            # Não deve lançar exceção
            await bridge._create_event_reminder(event)

            # Verifica que add_reminder NÃO foi chamado
            mock_add.assert_not_called()

    @pytest.mark.asyncio
    async def test_fetch_upcoming_events_uses_utc(self, bridge):
        """Verifica que _fetch_upcoming_events usa datetime.now(timezone.utc)."""
        with patch.object(bridge, '_get_valid_credentials', return_value=MagicMock(token="test_token")):
            with patch('httpx.AsyncClient') as mock_client_class:
                # Mock httpx.AsyncClient response
                mock_response = AsyncMock()
                mock_response.json.return_value = {"items": []}
                mock_response.raise_for_status = MagicMock()

                mock_client_instance = AsyncMock()
                mock_client_instance.get.return_value = mock_response
                mock_client_instance.__aenter__.return_value = mock_client_instance
                mock_client_instance.__aexit__.return_value = None

                mock_client_class.return_value = mock_client_instance

                # Chamar _fetch_upcoming_events
                events = await bridge._fetch_upcoming_events()

                # Verificar que timeMin/timeMax foram passados
                call_args = mock_client_instance.get.call_args
                params = call_args[1]["params"]

                # Verificar que timeMin e timeMax terminam com "Z" (UTC)
                assert params["timeMin"].endswith("Z")
                assert params["timeMax"].endswith("Z")

                # Verificar que formato é ISO 8601
                from datetime import datetime
                # Deve ser parseável
                datetime.fromisoformat(params["timeMin"].replace("Z", "+00:00"))
                datetime.fromisoformat(params["timeMax"].replace("Z", "+00:00"))

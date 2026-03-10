"""
Testes para CalendarReminderBridge
"""
import pytest
from pathlib import Path
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

"""
Tests para Google Calendar Skill (skills/google_calendar.py)

IMPORTANTE: Este arquivo testa o comportamento ATUAL da skill.
Quando a skill for modificada para incluir PKCE, Encryption e Audit,
estes testes devem ser atualizados para refletir o novo comportamento.
"""
import pytest
import json
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime, timedelta

from skills.google_calendar import (
    GoogleCalendarSkill,
    INVALID_AUTH_CODE_PLACEHOLDERS,
    TOKEN_FILE,
    DATA_DIR
)


@pytest.fixture
def cleanup_token_file():
    """Remove arquivo de token antes e depois de cada teste."""
    if TOKEN_FILE.exists():
        TOKEN_FILE.unlink()
    yield
    if TOKEN_FILE.exists():
        TOKEN_FILE.unlink()


@pytest.fixture
def skill():
    """Cria instância do GoogleCalendarSkill para cada teste."""
    return GoogleCalendarSkill()


@pytest.fixture
def mock_credentials():
    """Cria mock de Credentials para testes."""
    creds = Mock()
    creds.valid = True
    creds.expired = False
    creds.refresh_token = "refresh_token_123"
    creds.token = "access_token_123"
    creds.to_json = Mock(return_value=json.dumps({
        "token": "access_token_123",
        "refresh_token": "refresh_token_123",
        "token_uri": "https://oauth2.googleapis.com/token",
        "client_id": "test_client_id",
        "client_secret": "test_client_secret",
        "scopes": ["https://www.googleapis.com/auth/calendar"]
    }))
    return creds


class TestSkillInitialization:
    """Testa inicialização do GoogleCalendarSkill."""

    def test_skill_name(self, skill):
        """Verifica que nome da skill está correto."""
        assert skill.name == "google_calendar"

    def test_skill_display_name(self, skill):
        """Verifica que display_name está correto."""
        assert skill.display_name == "📅 Google Agenda"

    def test_skill_description(self, skill):
        """Verifica que descrição está presente."""
        assert "Google Calendar" in skill.description or "Google Agenda" in skill.description

    def test_data_directory_creation(self):
        """Verifica que diretório data/ é criado na inicialização."""
        # Remover temporariamente se existir
        import shutil
        if DATA_DIR.exists():
            shutil.rmtree(DATA_DIR)

        GoogleCalendarSkill()

        assert DATA_DIR.exists()

    @patch('skills.google_calendar.GCAL_CLIENT_ID', None)
    @patch('skills.google_calendar.GCAL_CLIENT_SECRET', None)
    def test_initialization_without_credentials_logs_warning(self, caplog):
        """Verifica que inicialização sem credenciais loga warning."""
        GoogleCalendarSkill()

        assert "Google Calendar not configured" in caplog.text


class TestParametersSchema:
    """Testa schema de parâmetros da skill."""

    def test_parameters_include_action(self, skill):
        """Verifica que schema inclui parâmetro 'action'."""
        params = skill.parameters

        assert "action" in params["properties"]
        assert params["required"] == ["action"]

    def test_action_enum_values(self, skill):
        """Verifica que action tem enum com ações válidas."""
        action_property = skill.parameters["properties"]["action"]

        assert "enum" in action_property
        assert "setup_calendar" in action_property["enum"]
        assert "list_calendar_events" in action_property["enum"]
        assert "add_calendar_event" in action_property["enum"]
        assert "cancel_calendar_event" in action_property["enum"]


class TestAuthCodeValidation:
    """Testa validação de auth_code."""

    def test_validate_auth_code_valid_code(self, skill):
        """Verifica que auth_code válido é aceito."""
        valid_code = "4/1AfrIepBRMIOs-Bxc_BSjkI2UCXv6EH8qlt9J8J6N1nn4HGV-GkVp-H8U5R4"

        result = skill._validate_auth_code(valid_code)

        assert result == valid_code

    def test_validate_auth_code_none(self, skill):
        """Verifica que auth_code None retorna None."""
        assert skill._validate_auth_code(None) is None

    def test_validate_auth_code_empty_string(self, skill):
        """Verifica que auth_code vazio retorna None."""
        assert skill._validate_auth_code("") is None

    def test_validate_auth_code_whitespace_only(self, skill):
        """Verifica que auth_code com apenas whitespace retorna None."""
        assert skill._validate_auth_code("   ") is None

    @pytest.mark.parametrize("placeholder", list(INVALID_AUTH_CODE_PLACEHOLDERS)[:5])
    def test_validate_auth_code_rejects_placeholders(self, skill, placeholder):
        """Verifica que placeholders conhecidos são rejeitados."""
        result = skill._validate_auth_code(placeholder)

        assert result is None

    def test_validate_auth_code_too_short(self, skill):
        """Verifica que auth_code muito curto é rejeitado."""
        short_code = "abc123"

        result = skill._validate_auth_code(short_code)

        assert result is None

    def test_validate_auth_code_too_long(self, skill):
        """Verifica que auth_code muito longo é rejeitado."""
        long_code = "a" * 600

        result = skill._validate_auth_code(long_code)

        assert result is None

    def test_validate_auth_code_invalid_characters(self, skill):
        """Verifica que auth_code com caracteres inválidos é rejeitado."""
        invalid_codes = [
            "code with spaces",
            "code@with#special$chars",
            "código-com-acento",
            "[bracketed-code]"
        ]

        for code in invalid_codes:
            result = skill._validate_auth_code(code)
            assert result is None, f"Should reject: {code}"

    def test_validate_auth_code_strips_whitespace(self, skill):
        """Verifica que whitespace é removido de auth_code válido."""
        code_with_spaces = "  4/1AfrIepBRMIOs-Bxc_BSjkI2UCXv6EH8qlt9J8J6N1nn4HGV-GkVp-H8U5R4  "

        result = skill._validate_auth_code(code_with_spaces)

        assert result == code_with_spaces.strip()

    def test_validate_auth_code_case_insensitive_placeholder_check(self, skill):
        """Verifica que verificação de placeholders é case-insensitive."""
        assert skill._validate_auth_code("NONE") is None
        assert skill._validate_auth_code("None") is None
        assert skill._validate_auth_code("none") is None


class TestTokenManagement:
    """Testa gestão de tokens (load/save)."""

    def test_load_token_file_not_exists(self, skill, cleanup_token_file):
        """Verifica que _load_token retorna None se arquivo não existir."""
        assert skill._load_token() is None

    def test_save_and_load_token(self, skill, cleanup_token_file, mock_credentials):
        """Verifica que save + load preserva credentials."""
        # Save
        skill._save_token(mock_credentials)

        # Load
        with patch('skills.google_calendar.Credentials.from_authorized_user_file') as mock_from_file:
            mock_from_file.return_value = mock_credentials
            loaded_creds = skill._load_token()

        assert loaded_creds is not None
        mock_from_file.assert_called_once()

    def test_load_token_corrupted_file(self, skill, cleanup_token_file):
        """Verifica que _load_token retorna None se arquivo estiver corrompido."""
        # Criar arquivo corrompido
        with open(TOKEN_FILE, "w") as f:
            f.write("invalid json {{{")

        result = skill._load_token()

        assert result is None

    def test_save_token_creates_file(self, skill, cleanup_token_file, mock_credentials):
        """Verifica que _save_token cria arquivo."""
        skill._save_token(mock_credentials)

        assert TOKEN_FILE.exists()

    def test_save_token_content_is_json(self, skill, cleanup_token_file, mock_credentials):
        """Verifica que _save_token salva JSON válido."""
        skill._save_token(mock_credentials)

        with open(TOKEN_FILE, "r") as f:
            data = json.load(f)  # Não deve levantar exceção

        assert "token" in data


class TestGetValidCredentials:
    """Testa _get_valid_credentials."""

    @pytest.mark.asyncio
    async def test_get_valid_credentials_no_token_file(self, skill, cleanup_token_file):
        """Verifica que retorna None se não há token salvo."""
        result = await skill._get_valid_credentials()

        assert result is None

    @pytest.mark.asyncio
    async def test_get_valid_credentials_valid_token(self, skill, cleanup_token_file, mock_credentials):
        """Verifica que retorna credentials se token é válido."""
        with patch.object(skill, '_load_token', return_value=mock_credentials):
            result = await skill._get_valid_credentials()

        assert result == mock_credentials

    @pytest.mark.asyncio
    async def test_get_valid_credentials_expired_refreshes(self, skill, cleanup_token_file, mock_credentials):
        """Verifica que token expirado é renovado automaticamente."""
        mock_credentials.valid = False
        mock_credentials.expired = True
        mock_credentials.refresh_token = "refresh_token_123"

        with patch.object(skill, '_load_token', return_value=mock_credentials):
            with patch.object(skill, '_refresh_token', return_value=True):
                result = await skill._get_valid_credentials()

        assert result == mock_credentials

    @pytest.mark.asyncio
    async def test_get_valid_credentials_refresh_fails(self, skill, cleanup_token_file, mock_credentials):
        """Verifica que retorna None se refresh falhar."""
        mock_credentials.valid = False
        mock_credentials.expired = True

        with patch.object(skill, '_load_token', return_value=mock_credentials):
            with patch.object(skill, '_refresh_token', return_value=False):
                result = await skill._get_valid_credentials()

        assert result is None


class TestRefreshToken:
    """Testa _refresh_token."""

    @pytest.mark.asyncio
    async def test_refresh_token_success(self, skill, mock_credentials):
        """Verifica que refresh bem-sucedido salva token."""
        mock_request = Mock()

        with patch('skills.google_calendar.Request', return_value=mock_request):
            with patch.object(skill, '_save_token') as mock_save:
                with patch('asyncio.to_thread', return_value=AsyncMock()):
                    result = await skill._refresh_token(mock_credentials)

        assert result is True
        mock_save.assert_called_once_with(mock_credentials)

    @pytest.mark.asyncio
    async def test_refresh_token_timeout(self, skill, mock_credentials):
        """Verifica que timeout ao renovar retorna False."""
        import asyncio

        async def timeout_coro(*args, **kwargs):
            raise asyncio.TimeoutError()

        with patch('asyncio.wait_for', side_effect=timeout_coro):
            result = await skill._refresh_token(mock_credentials)

        assert result is False

    @pytest.mark.asyncio
    async def test_refresh_token_exception(self, skill, mock_credentials):
        """Verifica que exceção ao renovar retorna False."""
        with patch('asyncio.wait_for', side_effect=Exception("Refresh error")):
            result = await skill._refresh_token(mock_credentials)

        assert result is False


class TestExecuteDispatch:
    """Testa dispatch de actions no execute."""

    @pytest.mark.asyncio
    async def test_execute_no_action(self, skill):
        """Verifica que retorna erro se action não especificada."""
        result = await skill.execute({})

        assert result["status"] == "error"
        assert "não especificada" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_execute_unknown_action(self, skill):
        """Verifica que retorna erro se action desconhecida."""
        result = await skill.execute({}, action="invalid_action")

        assert result["status"] == "error"
        assert "desconhecida" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_execute_dispatches_to_setup_calendar(self, skill):
        """Verifica que action='setup_calendar' chama _setup_calendar."""
        with patch.object(skill, '_setup_calendar', return_value=AsyncMock()):
            await skill.execute({}, action="setup_calendar", auth_code="test_code")

            skill._setup_calendar.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_dispatches_to_list_calendar_events(self, skill):
        """Verifica que action='list_calendar_events' chama _list_calendar_events."""
        with patch.object(skill, '_list_calendar_events', return_value=AsyncMock()):
            await skill.execute({}, action="list_calendar_events", time_range="today")

            skill._list_calendar_events.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_dispatches_to_add_calendar_event(self, skill):
        """Verifica que action='add_calendar_event' chama _add_calendar_event."""
        with patch.object(skill, '_add_calendar_event', return_value=AsyncMock()):
            await skill.execute({}, action="add_calendar_event", summary="Test Event")

            skill._add_calendar_event.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_dispatches_to_cancel_calendar_event(self, skill):
        """Verifica que action='cancel_calendar_event' chama _cancel_calendar_event."""
        with patch.object(skill, '_cancel_calendar_event', return_value=AsyncMock()):
            await skill.execute({}, action="cancel_calendar_event", event_id="event123")

            skill._cancel_calendar_event.assert_called_once()


class TestSetupCalendar:
    """Testa _setup_calendar (OAuth flow)."""

    @pytest.mark.asyncio
    @patch('skills.google_calendar.GCAL_CLIENT_ID', None)
    @patch('skills.google_calendar.GCAL_CLIENT_SECRET', None)
    async def test_setup_calendar_not_configured(self, skill):
        """Verifica que retorna erro se credenciais não configuradas."""
        result = await skill._setup_calendar()

        assert result["status"] == "error"
        assert "não configurado" in result["message"].lower()

    @pytest.mark.asyncio
    @patch('skills.google_calendar.GCAL_CLIENT_ID', 'test_client_id')
    @patch('skills.google_calendar.GCAL_CLIENT_SECRET', 'test_client_secret')
    async def test_setup_calendar_already_authenticated(self, skill, mock_credentials):
        """Verifica que retorna sucesso se já autenticado."""
        with patch.object(skill, '_get_valid_credentials', return_value=mock_credentials):
            result = await skill._setup_calendar()

        assert result["status"] == "success"
        assert "já está autenticado" in result["message"].lower()

    @pytest.mark.asyncio
    @patch('skills.google_calendar.GCAL_CLIENT_ID', 'test_client_id')
    @patch('skills.google_calendar.GCAL_CLIENT_SECRET', 'test_client_secret')
    async def test_setup_calendar_generates_auth_url(self, skill):
        """Verifica que gera URL de autorização se não autenticado."""
        with patch.object(skill, '_get_valid_credentials', return_value=None):
            result = await skill._setup_calendar()

        assert result["status"] == "success"
        assert "data" in result
        assert "auth_url" in result["data"]
        assert "accounts.google.com/o/oauth2/auth" in result["data"]["auth_url"]

    @pytest.mark.asyncio
    @patch('skills.google_calendar.GCAL_CLIENT_ID', 'test_client_id')
    @patch('skills.google_calendar.GCAL_CLIENT_SECRET', 'test_client_secret')
    async def test_setup_calendar_rejects_invalid_auth_code(self, skill):
        """Verifica que rejeita auth_code inválido."""
        with patch.object(skill, '_get_valid_credentials', return_value=None):
            result = await skill._setup_calendar(auth_code="none")

        # Deve gerar URL novamente em vez de processar código inválido
        assert "auth_url" in result.get("data", {})


class TestGetClient:
    """Testa _get_client."""

    @pytest.mark.asyncio
    async def test_get_client_not_authenticated(self, skill):
        """Verifica que retorna None se não autenticado."""
        with patch.object(skill, '_get_valid_credentials', return_value=None):
            result = await skill._get_client()

        assert result is None

    @pytest.mark.asyncio
    async def test_get_client_authenticated(self, skill, mock_credentials):
        """Verifica que retorna httpx.AsyncClient se autenticado."""
        with patch.object(skill, '_get_valid_credentials', return_value=mock_credentials):
            client = await skill._get_client()

        assert client is not None
        assert client.base_url == "https://www.googleapis.com/calendar/v3"
        assert "Authorization" in client.headers
        assert f"Bearer {mock_credentials.token}" in client.headers["Authorization"]

        await client.aclose()


class TestInvalidPlaceholdersList:
    """Testa INVALID_AUTH_CODE_PLACEHOLDERS."""

    def test_placeholders_is_frozenset(self):
        """Verifica que INVALID_AUTH_CODE_PLACEHOLDERS é frozenset (immutable)."""
        assert isinstance(INVALID_AUTH_CODE_PLACEHOLDERS, frozenset)

    def test_placeholders_include_common_values(self):
        """Verifica que lista inclui placeholders comuns."""
        expected_placeholders = [
            'none', 'null', 'n/a', 'nenhum', 'nenhum código', 'placeholder', 'test', 'teste'
        ]

        for placeholder in expected_placeholders:
            assert placeholder in INVALID_AUTH_CODE_PLACEHOLDERS, f"Missing: {placeholder}"

    def test_placeholders_lookup_performance(self):
        """Verifica que lookup é O(1) com frozenset."""
        import time

        # Lookup deve ser instantâneo mesmo em set grande
        start = time.time()
        for _ in range(10000):
            _ = 'none' in INVALID_AUTH_CODE_PLACEHOLDERS
        elapsed = time.time() - start

        # 10k lookups devem levar < 10ms
        assert elapsed < 0.01


class TestEdgeCases:
    """Testa casos extremos."""

    @pytest.mark.asyncio
    async def test_execute_exception_handling(self, skill):
        """Verifica que exceções em execute são capturadas."""
        with patch.object(skill, '_setup_calendar', side_effect=Exception("Test error")):
            result = await skill.execute({}, action="setup_calendar")

        assert result["status"] == "error"
        assert "falha" in result["message"].lower()

    def test_validate_auth_code_unicode_characters(self, skill):
        """Verifica que auth_code com Unicode é rejeitado."""
        unicode_code = "código-com-acentuação-café"

        result = skill._validate_auth_code(unicode_code)

        assert result is None


# NOTA: Testes para _list_calendar_events, _add_calendar_event e _cancel_calendar_event
# requerem mock de httpx.AsyncClient e são mais complexos. Serão adicionados em seguida.

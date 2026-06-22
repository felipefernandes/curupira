"""
Tests para Google Calendar Skill (skills/google_calendar.py)

IMPORTANTE: Este arquivo testa o comportamento ATUAL da skill.
Quando a skill for modificada para incluir PKCE, Encryption e Audit,
estes testes devem ser atualizados para refletir o novo comportamento.
"""
import pytest
import json
import httpx
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime

from skills.google_calendar import (
    GoogleCalendarSkill,
    INVALID_AUTH_CODE_PLACEHOLDERS,
    TOKEN_FILE
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

    def test_skill_group(self, skill):
        """Verifica skill_group e skill_group_emoji."""
        assert skill.skill_group == "calendar"
        assert skill.skill_group_emoji == "📅"

    def test_data_directory_creation(self, tmp_path):
        """Verifica que diretório data/ é criado na inicialização."""
        temp_data_dir = tmp_path / "data"

        with patch("skills.google_calendar.DATA_DIR", temp_data_dir):
            GoogleCalendarSkill()
            assert temp_data_dir.exists()

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
        """Verifica que save + load preserva credentials (com encryption)."""
        # Save (criptografado)
        skill._save_token(mock_credentials)

        # Verificar que arquivo existe
        assert TOKEN_FILE.exists()

        # Load (descriptografa)
        loaded_creds = skill._load_token()

        assert loaded_creds is not None
        # Verificar que credenciais foram recuperadas corretamente
        assert loaded_creds.token == mock_credentials.token

    def test_load_token_corrupted_file(self, skill, cleanup_token_file):
        """Verifica que _load_token retorna None se arquivo estiver corrompido."""
        # Criar arquivo corrompido
        with open(TOKEN_FILE, "w") as f:
            f.write("invalid json {{{")

        result = skill._load_token()

        assert result is None

    def test_load_token_corrupted_file_auto_deletes(self, skill, cleanup_token_file):
        """Verifica que _load_token deleta token corrompido automaticamente."""
        # Criar arquivo corrompido (não criptografado)
        with open(TOKEN_FILE, "w") as f:
            f.write("invalid json {{{")

        assert TOKEN_FILE.exists()

        result = skill._load_token()

        # Verifica que retornou None
        assert result is None
        # Verifica que arquivo foi deletado automaticamente
        assert not TOKEN_FILE.exists()

    def test_load_token_deletion_failure_logged(self, skill, cleanup_token_file):
        """Verifica que falha ao deletar token corrompido é logada."""
        from unittest.mock import patch

        # Criar arquivo corrompido
        with open(TOKEN_FILE, "w") as f:
            f.write("corrupted data")

        # Mockar Path.unlink() para lançar exceção quando chamado em TOKEN_FILE
        original_unlink = Path.unlink
        def mock_unlink(self, *args, **kwargs):
            if str(self) == str(TOKEN_FILE):
                raise PermissionError("Access denied")
            return original_unlink(self, *args, **kwargs)

        with patch.object(Path, 'unlink', mock_unlink):
            with patch.object(skill.logger, 'error') as mock_error:
                result = skill._load_token()

                # Verifica que retornou None
                assert result is None
                # Verifica que erro foi logado
                assert any("Erro ao deletar token corrompido" in str(call) for call in mock_error.call_args_list)

    def test_save_token_creates_file(self, skill, cleanup_token_file, mock_credentials):
        """Verifica que _save_token cria arquivo."""
        skill._save_token(mock_credentials)

        assert TOKEN_FILE.exists()

    def test_save_token_content_is_encrypted(self, skill, cleanup_token_file, mock_credentials):
        """Verifica que _save_token salva token criptografado (não plaintext JSON)."""
        skill._save_token(mock_credentials)

        # Ler como bytes (arquivo criptografado)
        with open(TOKEN_FILE, "rb") as f:
            encrypted_data = f.read()

        # Verificar que é bytes (não JSON plaintext)
        assert isinstance(encrypted_data, bytes)
        assert len(encrypted_data) > 0

        # Verificar que NÃO é JSON plaintext
        with pytest.raises(Exception):  # Deve falhar ao tentar parsear como JSON
            json.loads(encrypted_data)


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
        assert "não especificada" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_execute_unknown_action(self, skill):
        """Verifica que retorna erro se action desconhecida."""
        result = await skill.execute({}, action="invalid_action")

        assert result["status"] == "error"
        assert "desconhecida" in result["error"].lower()

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
        assert "não configurado" in result["error"].lower()

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

        # Deve retornar erro para código inválido
        assert result["status"] == "error"
        assert "inválido" in result["error"].lower()


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
        # httpx retorna base_url como objeto URL, não string
        assert str(client.base_url).rstrip('/') == "https://www.googleapis.com/calendar/v3"
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
        assert "falha" in result["error"].lower()

    def test_validate_auth_code_unicode_characters(self, skill):
        """Verifica que auth_code com Unicode é rejeitado."""
        unicode_code = "código-com-acentuação-café"

        result = skill._validate_auth_code(unicode_code)

        assert result is None


class TestListCalendarEvents:
    """Testa _list_calendar_events."""

    @pytest.mark.asyncio
    async def test_list_calendar_events_filters_all_day_events_from_yesterday(self, skill, mock_credentials):
        """Verifica que eventos all-day de ontem são filtrados ao listar eventos de hoje."""
        # Cenário: Listar eventos de "today" (2026-03-11)
        # - Evento all-day de ontem (2026-03-10 00:00 - 23:59) tem end.date = 2026-03-11
        # - Google Calendar API retorna esse evento porque end dentro do range
        # - Filtro deve remover esse evento (end <= range_start)

        # Mock Google Calendar API response
        mock_api_response = {
            "items": [
                {
                    "id": "event_yesterday",
                    "summary": "Evento de Ontem (All-Day)",
                    "start": {"date": "2026-03-10"},  # Ontem
                    "end": {"date": "2026-03-11"},    # Hoje (all-day end = start + 1 day)
                    "description": "Evento que iniciou ontem"
                },
                {
                    "id": "event_today",
                    "summary": "Evento de Hoje (All-Day)",
                    "start": {"date": "2026-03-11"},  # Hoje
                    "end": {"date": "2026-03-12"},    # Amanhã
                    "description": "Evento de hoje"
                },
                {
                    "id": "event_timed",
                    "summary": "Reunião às 14h",
                    "start": {"dateTime": "2026-03-11T14:00:00-03:00"},
                    "end": {"dateTime": "2026-03-11T15:00:00-03:00"},
                    "description": "Evento com horário"
                }
            ]
        }

        # Mock httpx.AsyncClient
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_api_response
        mock_response.raise_for_status = MagicMock()

        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.aclose = AsyncMock()

        # Mock datetime.now() to return 2026-03-11
        mock_now = datetime(2026, 3, 11, 10, 0, 0)  # 2026-03-11 10:00:00

        with patch.object(skill, '_get_client', return_value=mock_client), \
             patch('skills.google_calendar.datetime') as mock_datetime:
            mock_datetime.now.return_value = mock_now
            mock_datetime.fromisoformat = datetime.fromisoformat  # Preserve original fromisoformat
            result = await skill._list_calendar_events(time_range="today")

        # Verificar resultado
        assert result["status"] == "success"
        assert "events" in result["data"]
        events = result["data"]["events"]

        # Deve ter apenas 2 eventos (evento de ontem filtrado)
        assert len(events) == 2

        # Verificar que evento de ontem foi filtrado
        event_ids = [e["id"] for e in events]
        assert "event_yesterday" not in event_ids, "Evento all-day de ontem deveria ser filtrado"

        # Verificar que eventos de hoje estão presentes
        assert "event_today" in event_ids
        assert "event_timed" in event_ids

    @pytest.mark.asyncio
    async def test_list_calendar_events_includes_all_day_events_from_today(self, skill, mock_credentials):
        """Verifica que eventos all-day de hoje são incluídos."""
        # Mock Google Calendar API response
        mock_api_response = {
            "items": [
                {
                    "id": "event_today",
                    "summary": "Evento de Hoje",
                    "start": {"date": "2026-03-11"},  # Hoje
                    "end": {"date": "2026-03-12"},    # Amanhã (all-day)
                    "description": "Evento de hoje"
                }
            ]
        }

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_api_response
        mock_response.raise_for_status = MagicMock()

        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.aclose = AsyncMock()

        # Mock datetime.now() to return 2026-03-11
        mock_now = datetime(2026, 3, 11, 10, 0, 0)  # 2026-03-11 10:00:00

        with patch.object(skill, '_get_client', return_value=mock_client), \
             patch('skills.google_calendar.datetime') as mock_datetime:
            mock_datetime.now.return_value = mock_now
            mock_datetime.fromisoformat = datetime.fromisoformat  # Preserve original fromisoformat
            result = await skill._list_calendar_events(time_range="today")

        # Verificar que evento de hoje está presente
        assert result["status"] == "success"
        events = result["data"]["events"]
        assert len(events) == 1
        assert events[0]["id"] == "event_today"
        assert events[0]["weekday"] == "quarta-feira"

    @pytest.mark.asyncio
    async def test_list_calendar_events_includes_weekday_field(self, skill):
        """Verifica se o campo weekday é adicionado corretamente para cada dia da semana."""
        mock_api_response = {
            "items": [
                {
                    "id": "event_mon",
                    "summary": "Evento Segunda",
                    "start": {"date": "2026-03-09"},
                    "end": {"date": "2026-03-10"},
                },
                {
                    "id": "event_wed",
                    "summary": "Evento Quarta",
                    "start": {"dateTime": "2026-03-11T10:00:00-03:00"},
                    "end": {"dateTime": "2026-03-11T11:00:00-03:00"},
                },
            ]
        }

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_api_response
        mock_response.raise_for_status = MagicMock()

        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.aclose = AsyncMock()

        mock_now = datetime(2026, 3, 9, 8, 0, 0) # 2026-03-09 é Segunda

        with patch.object(skill, '_get_client', return_value=mock_client), \
             patch('skills.google_calendar.datetime') as mock_datetime:
            mock_datetime.now.return_value = mock_now
            mock_datetime.fromisoformat = datetime.fromisoformat
            result = await skill._list_calendar_events(time_range="week")

        assert result["status"] == "success"
        events = result["data"]["events"]
        assert len(events) == 2

        # event_mon should be "segunda-feira"
        event_mon = next(e for e in events if e["id"] == "event_mon")
        assert event_mon["weekday"] == "segunda-feira"

        # event_wed should be "quarta-feira"
        event_wed = next(e for e in events if e["id"] == "event_wed")
        assert event_wed["weekday"] == "quarta-feira"

    @pytest.mark.asyncio
    async def test_list_calendar_events_not_authenticated(self, skill):
        """Verifica que retorna erro se não autenticado."""
        with patch.object(skill, '_get_client', return_value=None):
            result = await skill._list_calendar_events(time_range="today")

        assert result["status"] == "error"
        assert "não autenticado" in result["error"].lower()


# NOTA: Testes para _add_calendar_event e _cancel_calendar_event
# requerem mock de httpx.AsyncClient e serão adicionados conforme necessário.


class TestMultipleCalendarsAndWriteTarget:
    """Testa múltiplos calendários (listagem, deduplicação, resiliência) e alvo de escrita."""

    @pytest.mark.asyncio
    @patch('skills.google_calendar.GCAL_CALENDAR_IDS', ['cal1', 'cal2'])
    async def test_list_events_multiple_calendars_success(self, skill):
        """Verifica se eventos de múltiplos calendários são unificados."""
        mock_client = MagicMock()
        mock_response1 = MagicMock()
        mock_response1.status_code = 200
        mock_response1.json.return_value = {
            "items": [{"id": "ev1", "summary": "Evento 1", "start": {"dateTime": "2026-03-11T10:00:00Z"}}]
        }
        
        mock_response2 = MagicMock()
        mock_response2.status_code = 200
        mock_response2.json.return_value = {
            "items": [{"id": "ev2", "summary": "Evento 2", "start": {"dateTime": "2026-03-11T12:00:00Z"}}]
        }

        # Mock mock_client.get para retornar as respostas diferentes dependendo da chamada
        async def mock_get(url, *args, **kwargs):
            if "cal1" in url:
                return mock_response1
            elif "cal2" in url:
                return mock_response2
            raise Exception("URL inválido no mock")

        mock_client.get = mock_get
        mock_client.aclose = AsyncMock()

        # Mock datetime.now()
        mock_now = datetime(2026, 3, 11, 8, 0, 0)

        with patch.object(skill, '_get_client', return_value=mock_client), \
             patch('skills.google_calendar.datetime') as mock_datetime:
            mock_datetime.now.return_value = mock_now
            mock_datetime.fromisoformat = datetime.fromisoformat
            result = await skill._list_calendar_events(time_range="today")

        assert result["status"] == "success"
        events = result["data"]["events"]
        assert len(events) == 2
        assert events[0]["id"] == "ev1"
        assert events[1]["id"] == "ev2"

    @pytest.mark.asyncio
    @patch('skills.google_calendar.GCAL_CALENDAR_IDS', ['cal1', 'cal2'])
    async def test_list_events_multiple_calendars_deduplication(self, skill):
        """Verifica se eventos com mesmo iCalUID são deduplicados e ordenados corretamente."""
        mock_client = MagicMock()
        mock_response1 = MagicMock()
        mock_response1.status_code = 200
        mock_response1.json.return_value = {
            "items": [
                {"id": "ev1", "iCalUID": "shared_uid", "summary": "Alinhamento", "start": {"dateTime": "2026-03-11T15:00:00Z"}},
                {"id": "ev2", "iCalUID": "unique_uid_1", "summary": "Dentista", "start": {"dateTime": "2026-03-11T10:00:00Z"}}
            ]
        }
        
        mock_response2 = MagicMock()
        mock_response2.status_code = 200
        mock_response2.json.return_value = {
            # O mesmo evento "Alinhamento" compartilhado (mesmo iCalUID)
            "items": [{"id": "ev3", "iCalUID": "shared_uid", "summary": "Alinhamento", "start": {"dateTime": "2026-03-11T15:00:00Z"}}]
        }

        async def mock_get(url, *args, **kwargs):
            if "cal1" in url:
                return mock_response1
            return mock_response2

        mock_client.get = mock_get
        mock_client.aclose = AsyncMock()
        mock_now = datetime(2026, 3, 11, 8, 0, 0)

        with patch.object(skill, '_get_client', return_value=mock_client), \
             patch('skills.google_calendar.datetime') as mock_datetime:
            mock_datetime.now.return_value = mock_now
            mock_datetime.fromisoformat = datetime.fromisoformat
            result = await skill._list_calendar_events(time_range="today")

        assert result["status"] == "success"
        events = result["data"]["events"]
        # De 3 eventos recebidos brutos, 2 devem restar após deduplicação de "shared_uid"
        assert len(events) == 2
        # Devem estar ordenados cronologicamente: Dentista (10:00) primeiro, Alinhamento (15:00) depois
        assert events[0]["summary"] == "Dentista"
        assert events[1]["summary"] == "Alinhamento"

    @pytest.mark.asyncio
    @patch('skills.google_calendar.GCAL_CALENDAR_IDS', ['valid_cal', 'failing_cal'])
    async def test_list_events_multiple_calendars_partial_failure(self, skill):
        """Verifica se falha em um calendário é tolerada (resiliência)."""
        mock_client = MagicMock()
        mock_response1 = MagicMock()
        mock_response1.status_code = 200
        mock_response1.json.return_value = {
            "items": [{"id": "ev1", "summary": "Evento Válido", "start": {"dateTime": "2026-03-11T10:00:00Z"}}]
        }

        async def mock_get(url, *args, **kwargs):
            if "valid_cal" in url:
                return mock_response1
            # Simula um erro HTTP 403 no calendário proibido/inexistente
            response_error = MagicMock()
            response_error.status_code = 403
            raise httpx.HTTPStatusError("Forbidden", request=MagicMock(), response=response_error)

        mock_client.get = mock_get
        mock_client.aclose = AsyncMock()
        mock_now = datetime(2026, 3, 11, 8, 0, 0)

        with patch.object(skill, '_get_client', return_value=mock_client), \
             patch('skills.google_calendar.datetime') as mock_datetime:
            mock_datetime.now.return_value = mock_now
            mock_datetime.fromisoformat = datetime.fromisoformat
            result = await skill._list_calendar_events(time_range="today")

        # Deve ser "success" porque o calendário válido retornou resultados com resiliência
        assert result["status"] == "success"
        events = result["data"]["events"]
        assert len(events) == 1
        assert events[0]["summary"] == "Evento Válido"

    @pytest.mark.asyncio
    @patch('skills.google_calendar.GCAL_WRITE_CALENDAR_ID', 'write_target_cal')
    async def test_add_event_uses_write_calendar_id(self, skill):
        """Verifica se criação de evento usa a agenda especificada em GCAL_WRITE_CALENDAR_ID."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "new_event_123",
            "summary": "Reunião de Escrita",
            "start": {"dateTime": "2026-03-11T15:00:00Z"},
            "htmlLink": "http://link"
        }
        mock_response.raise_for_status = MagicMock()
        
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.aclose = AsyncMock()

        with patch.object(skill, '_get_client', return_value=mock_client):
            result = await skill._add_calendar_event(
                summary="Reunião de Escrita",
                start_time="2026-03-11T15:00:00Z"
            )

        assert result["status"] == "success"
        # Verifica se o endpoint POST foi chamado com a agenda de escrita correta
        mock_client.post.assert_called_once()
        call_url = mock_client.post.call_args[0][0]
        assert "write_target_cal" in call_url

    @pytest.mark.asyncio
    @patch('skills.google_calendar.GCAL_WRITE_CALENDAR_ID', 'write_target_cal')
    async def test_cancel_event_uses_write_calendar_id(self, skill):
        """Verifica se cancelamento de evento usa a agenda especificada em GCAL_WRITE_CALENDAR_ID."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_response.raise_for_status = MagicMock()
        
        mock_client.delete = AsyncMock(return_value=mock_response)
        mock_client.aclose = AsyncMock()

        with patch.object(skill, '_get_client', return_value=mock_client):
            result = await skill._cancel_calendar_event(event_id="delete_event_123")

        assert result["status"] == "success"
        # Verifica se o endpoint DELETE foi chamado com a agenda de escrita correta
        mock_client.delete.assert_called_once()
        call_url = mock_client.delete.call_args[0][0]
        assert "write_target_cal" in call_url

    @patch('skills.google_calendar.GCAL_CALENDARS', {'primary': 'primary', 'work': 'ffernandes@gazeus.com'})
    def test_resolve_calendar_id_alias(self, skill):
        """Verifica se resolve aliases corretamente (case-insensitive) e faz fallback."""
        assert skill._resolve_calendar_id("work", "fallback") == "ffernandes@gazeus.com"
        assert skill._resolve_calendar_id("WORK", "fallback") == "ffernandes@gazeus.com"
        assert skill._resolve_calendar_id("primary", "fallback") == "primary"
        # Sem solicitado -> usa fallback
        assert skill._resolve_calendar_id(None, "fallback") == "fallback"
        # Se não é um alias -> retorna o próprio ID
        assert skill._resolve_calendar_id("outro_email@gmail.com", "fallback") == "outro_email@gmail.com"

    @pytest.mark.asyncio
    @patch('skills.google_calendar.GCAL_CALENDARS', {'primary': 'primary', 'work': 'ffernandes@gazeus.com'})
    @patch('skills.google_calendar.GCAL_CALENDAR_IDS', ['primary', 'ffernandes@gazeus.com'])
    async def test_list_events_with_specific_calendar_id(self, skill):
        """Verifica se apenas a agenda informada em calendar_id é consultada."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "items": [{"id": "ev_work", "summary": "Daily Gazeus", "start": {"dateTime": "2026-03-11T10:00:00Z"}}]
        }
        
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.aclose = AsyncMock()
        mock_now = datetime(2026, 3, 11, 8, 0, 0)

        with patch.object(skill, '_get_client', return_value=mock_client), \
             patch('skills.google_calendar.datetime') as mock_datetime:
            mock_datetime.now.return_value = mock_now
            mock_datetime.fromisoformat = datetime.fromisoformat
            result = await skill._list_calendar_events(time_range="today", calendar_id="work")

        assert result["status"] == "success"
        events = result["data"]["events"]
        assert len(events) == 1
        assert events[0]["summary"] == "Daily Gazeus"
        
        # O mock_client deve ter sido chamado apenas uma vez com a URL do calendário do trabalho (Gazeus)
        mock_client.get.assert_called_once()
        call_url = mock_client.get.call_args[0][0]
        assert "ffernandes@gazeus.com" in call_url

    @pytest.mark.asyncio
    @patch('skills.google_calendar.GCAL_CALENDARS', {'primary': 'primary', 'work': 'ffernandes@gazeus.com'})
    @patch('skills.google_calendar.GCAL_WRITE_CALENDAR_ID', 'primary')
    async def test_add_event_with_specific_calendar_id(self, skill):
        """Verifica se criação de evento na agenda especificada via calendar_id funciona."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "new_event_123",
            "summary": "Daily",
            "start": {"dateTime": "2026-03-11T15:00:00Z"},
            "htmlLink": "http://link"
        }
        mock_response.raise_for_status = MagicMock()
        
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.aclose = AsyncMock()

        with patch.object(skill, '_get_client', return_value=mock_client):
            result = await skill._add_calendar_event(
                summary="Daily",
                start_time="2026-03-11T15:00:00Z",
                calendar_id="work"
            )

        assert result["status"] == "success"
        mock_client.post.assert_called_once()
        call_url = mock_client.post.call_args[0][0]
        # Deve ter sido direcionado para o email do trabalho
        assert "ffernandes@gazeus.com" in call_url

    @pytest.mark.asyncio
    @patch('skills.google_calendar.GCAL_CALENDARS', {'primary': 'primary', 'work': 'ffernandes@gazeus.com'})
    @patch('skills.google_calendar.GCAL_WRITE_CALENDAR_ID', 'primary')
    async def test_cancel_event_with_specific_calendar_id(self, skill):
        """Verifica se cancelamento de evento na agenda especificada via calendar_id funciona."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_response.raise_for_status = MagicMock()
        
        mock_client.delete = AsyncMock(return_value=mock_response)
        mock_client.aclose = AsyncMock()

        with patch.object(skill, '_get_client', return_value=mock_client):
            result = await skill._cancel_calendar_event(event_id="delete_123", calendar_id="work")

        assert result["status"] == "success"
        mock_client.delete.assert_called_once()
        call_url = mock_client.delete.call_args[0][0]
        # Deve ter sido deletado da agenda do trabalho
        assert "ffernandes@gazeus.com" in call_url


class TestEventDeduplication:
    """Verifica as regras de deduplicação e coexistência de eventos."""

    @pytest.mark.asyncio
    @patch('skills.google_calendar.GCAL_CALENDARS', {'primary': 'primary', 'work': 'ffernandes@gazeus.com'})
    @patch('skills.google_calendar.GCAL_CALENDAR_IDS', ['primary', 'ffernandes@gazeus.com'])
    async def test_deduplication_by_ical_uid(self, skill):
        """Verifica se eventos com o mesmo iCalUID são deduplicados."""
        mock_client = MagicMock()
        mock_response_primary = MagicMock()
        mock_response_primary.status_code = 200
        mock_response_primary.json.return_value = {
            "items": [
                {
                    "id": "ev_1",
                    "iCalUID": "shared_uid_123",
                    "summary": "Reunião Geral",
                    "start": {"dateTime": "2026-03-11T10:00:00Z"},
                    "end": {"dateTime": "2026-03-11T11:00:00Z"}
                }
            ]
        }
        
        mock_response_work = MagicMock()
        mock_response_work.status_code = 200
        mock_response_work.json.return_value = {
            "items": [
                {
                    "id": "ev_2",
                    "iCalUID": "shared_uid_123", # Mesmo iCalUID
                    "summary": "Reunião Geral",
                    "start": {"dateTime": "2026-03-11T10:00:00Z"},
                    "end": {"dateTime": "2026-03-11T11:00:00Z"}
                }
            ]
        }
        
        # Simula chamadas para os dois calendários de forma que cada get retorne um mock_response diferente
        mock_client.get = AsyncMock(side_effect=[mock_response_primary, mock_response_work])
        mock_client.aclose = AsyncMock()
        mock_now = datetime(2026, 3, 11, 8, 0, 0)

        with patch.object(skill, '_get_client', return_value=mock_client), \
             patch('skills.google_calendar.datetime') as mock_datetime:
            mock_datetime.now.return_value = mock_now
            mock_datetime.fromisoformat = datetime.fromisoformat
            result = await skill._list_calendar_events(time_range="today")

        assert result["status"] == "success"
        events = result["data"]["events"]
        # Deve ter deduplicado pelo iCalUID, retornando apenas 1 evento
        assert len(events) == 1
        assert events[0]["id"] == "ev_1"

    @pytest.mark.asyncio
    @patch('skills.google_calendar.GCAL_CALENDARS', {'primary': 'primary', 'work': 'ffernandes@gazeus.com'})
    @patch('skills.google_calendar.GCAL_CALENDAR_IDS', ['primary', 'ffernandes@gazeus.com'])
    async def test_deduplication_by_event_id(self, skill):
        """Verifica se eventos com o mesmo ID são deduplicados (caso não tenham iCalUID)."""
        mock_client = MagicMock()
        mock_response_primary = MagicMock()
        mock_response_primary.status_code = 200
        mock_response_primary.json.return_value = {
            "items": [
                {
                    "id": "event_id_999",
                    "summary": "Café",
                    "start": {"dateTime": "2026-03-11T15:00:00Z"},
                    "end": {"dateTime": "2026-03-11T15:30:00Z"}
                }
            ]
        }
        
        mock_response_work = MagicMock()
        mock_response_work.status_code = 200
        mock_response_work.json.return_value = {
            "items": [
                {
                    "id": "event_id_999", # Mesmo ID
                    "summary": "Café",
                    "start": {"dateTime": "2026-03-11T15:00:00Z"},
                    "end": {"dateTime": "2026-03-11T15:30:00Z"}
                }
            ]
        }
        
        mock_client.get = AsyncMock(side_effect=[mock_response_primary, mock_response_work])
        mock_client.aclose = AsyncMock()
        mock_now = datetime(2026, 3, 11, 8, 0, 0)

        with patch.object(skill, '_get_client', return_value=mock_client), \
             patch('skills.google_calendar.datetime') as mock_datetime:
            mock_datetime.now.return_value = mock_now
            mock_datetime.fromisoformat = datetime.fromisoformat
            result = await skill._list_calendar_events(time_range="today")

        assert result["status"] == "success"
        events = result["data"]["events"]
        assert len(events) == 1
        assert events[0]["id"] == "event_id_999"

    @pytest.mark.asyncio
    @patch('skills.google_calendar.GCAL_CALENDARS', {'primary': 'primary', 'work': 'ffernandes@gazeus.com'})
    @patch('skills.google_calendar.GCAL_CALENDAR_IDS', ['primary', 'ffernandes@gazeus.com'])
    async def test_coexistence_same_summary_and_start_different_ids(self, skill):
        """Prova que dois eventos legítimos com o mesmo título e início, mas IDs diferentes, NÃO colidem."""
        mock_client = MagicMock()
        mock_response_primary = MagicMock()
        mock_response_primary.status_code = 200
        mock_response_primary.json.return_value = {
            "items": [
                {
                    "id": "ev_pessoal",
                    "iCalUID": "uid_pessoal",
                    "summary": "Almoço",
                    "start": {"dateTime": "2026-03-11T12:00:00Z"},
                    "end": {"dateTime": "2026-03-11T13:00:00Z"}
                }
            ]
        }
        
        mock_response_work = MagicMock()
        mock_response_work.status_code = 200
        mock_response_work.json.return_value = {
            "items": [
                {
                    "id": "ev_trabalho",
                    "iCalUID": "uid_trabalho", # IDs diferentes
                    "summary": "Almoço",       # Mesmo título
                    "start": {"dateTime": "2026-03-11T12:00:00Z"}, # Mesmo horário
                    "end": {"dateTime": "2026-03-11T13:00:00Z"}
                }
            ]
        }
        
        mock_client.get = AsyncMock(side_effect=[mock_response_primary, mock_response_work])
        mock_client.aclose = AsyncMock()
        mock_now = datetime(2026, 3, 11, 8, 0, 0)

        with patch.object(skill, '_get_client', return_value=mock_client), \
             patch('skills.google_calendar.datetime') as mock_datetime:
            mock_datetime.now.return_value = mock_now
            mock_datetime.fromisoformat = datetime.fromisoformat
            result = await skill._list_calendar_events(time_range="today")

        assert result["status"] == "success"
        events = result["data"]["events"]
        # Devem coexistir porque têm IDs diferentes! (Refuta o falso positivo da Iara)
        assert len(events) == 2
        ids = [ev["id"] for ev in events]
        assert "ev_pessoal" in ids
        assert "ev_trabalho" in ids

    @pytest.mark.asyncio
    @patch('skills.google_calendar.GCAL_CALENDARS', {'primary': 'primary', 'work': 'ffernandes@gazeus.com'})
    @patch('skills.google_calendar.GCAL_CALENDAR_IDS', ['primary', 'ffernandes@gazeus.com'])
    async def test_deduplication_by_fallback_key(self, skill):
        """Verifica se eventos sem nenhum ID/UID mas com o mesmo título e início são deduplicados pelo fallback_key."""
        mock_client = MagicMock()
        mock_response_primary = MagicMock()
        mock_response_primary.status_code = 200
        mock_response_primary.json.return_value = {
            "items": [
                {
                    "summary": "Lembrete Genérico",
                    "start": {"dateTime": "2026-03-11T16:00:00Z"},
                    "end": {"dateTime": "2026-03-11T16:30:00Z"}
                }
            ]
        }
        
        mock_response_work = MagicMock()
        mock_response_work.status_code = 200
        mock_response_work.json.return_value = {
            "items": [
                {
                    "summary": "Lembrete Genérico", # Mesmo título
                    "start": {"dateTime": "2026-03-11T16:00:00Z"}, # Mesmo horário
                    "end": {"dateTime": "2026-03-11T16:30:00Z"}
                }
            ]
        }
        
        mock_client.get = AsyncMock(side_effect=[mock_response_primary, mock_response_work])
        mock_client.aclose = AsyncMock()
        mock_now = datetime(2026, 3, 11, 8, 0, 0)

        with patch.object(skill, '_get_client', return_value=mock_client), \
             patch('skills.google_calendar.datetime') as mock_datetime:
            mock_datetime.now.return_value = mock_now
            mock_datetime.fromisoformat = datetime.fromisoformat
            result = await skill._list_calendar_events(time_range="today")

        assert result["status"] == "success"
        events = result["data"]["events"]
        assert len(events) == 1
        assert events[0]["summary"] == "Lembrete Genérico"



"""
Tests para Audit Logger (core/audit_logger.py)
"""
import json
import pytest
from pathlib import Path
from datetime import datetime
from unittest.mock import patch

from core.audit_logger import (
    AuditLogger,
    get_audit_logger,
    log_oauth2_auth_start,
    log_oauth2_auth_success,
    log_oauth2_auth_failed,
    log_oauth2_token_refresh,
    AUDIT_LOG_FILE
)


@pytest.fixture
def cleanup_audit_log():
    """Remove arquivo de audit log antes e depois de cada teste."""
    if AUDIT_LOG_FILE.exists():
        AUDIT_LOG_FILE.unlink()
    yield
    if AUDIT_LOG_FILE.exists():
        AUDIT_LOG_FILE.unlink()


@pytest.fixture
def audit_logger(cleanup_audit_log):
    """Cria nova instância de AuditLogger para cada teste."""
    return AuditLogger()


class TestAuditLoggerInitialization:
    """Testa inicialização do AuditLogger."""

    def test_creates_logs_directory(self, cleanup_audit_log):
        """Verifica que AuditLogger cria diretório logs/ se não existir."""
        # Garantir que diretório não existe
        logs_dir = AUDIT_LOG_FILE.parent
        if logs_dir.exists():
            # Remover temporariamente
            import shutil
            shutil.rmtree(logs_dir)

        AuditLogger()

        assert logs_dir.exists()

    def test_creates_audit_log_file_on_first_log(self, audit_logger):
        """Verifica que arquivo de audit log é criado ao primeiro log."""
        audit_logger.log_event("test_event", 123456789, True)

        assert AUDIT_LOG_FILE.exists()

    def test_logger_does_not_propagate(self, audit_logger):
        """Verifica que logger não propaga para root logger."""
        assert audit_logger.logger.propagate is False


class TestLogEvent:
    """Testa método log_event."""

    def test_log_event_creates_json_entry(self, audit_logger):
        """Verifica que log_event cria entrada JSON estruturada."""
        audit_logger.log_event("test_event", 123456789, True, {"key": "value"})

        with open(AUDIT_LOG_FILE, "r") as f:
            log_line = f.readline()

        log_entry = json.loads(log_line)

        assert log_entry["event"] == "test_event"
        assert log_entry["user_id"] == 123456789
        assert log_entry["success"] is True
        assert log_entry["details"] == {"key": "value"}

    def test_log_event_includes_timestamp(self, audit_logger):
        """Verifica que log_event inclui timestamp ISO 8601."""
        before = datetime.utcnow()
        audit_logger.log_event("test_event", 123456789, True)
        after = datetime.utcnow()

        with open(AUDIT_LOG_FILE, "r") as f:
            log_entry = json.loads(f.readline())

        # Parse timestamp
        timestamp = datetime.fromisoformat(log_entry["timestamp"].rstrip('Z'))

        assert before <= timestamp <= after

    def test_log_event_defaults_empty_details(self, audit_logger):
        """Verifica que log_event usa {} se details não fornecido."""
        audit_logger.log_event("test_event", 123456789, True)

        with open(AUDIT_LOG_FILE, "r") as f:
            log_entry = json.loads(f.readline())

        assert log_entry["details"] == {}

    def test_log_event_multiple_entries(self, audit_logger):
        """Verifica que múltiplos logs são escritos corretamente."""
        audit_logger.log_event("event1", 111, True)
        audit_logger.log_event("event2", 222, False)
        audit_logger.log_event("event3", 333, True, {"detail": "info"})

        with open(AUDIT_LOG_FILE, "r") as f:
            lines = f.readlines()

        assert len(lines) == 3

        # Verificar primeira entrada
        entry1 = json.loads(lines[0])
        assert entry1["event"] == "event1"
        assert entry1["user_id"] == 111

        # Verificar segunda entrada
        entry2 = json.loads(lines[1])
        assert entry2["event"] == "event2"
        assert entry2["user_id"] == 222
        assert entry2["success"] is False

        # Verificar terceira entrada
        entry3 = json.loads(lines[2])
        assert entry3["details"] == {"detail": "info"}


class TestSingletonPattern:
    """Testa padrão singleton do AuditLogger."""

    def test_get_audit_logger_returns_singleton(self, cleanup_audit_log):
        """Verifica que get_audit_logger retorna sempre a mesma instância."""
        logger1 = get_audit_logger()
        logger2 = get_audit_logger()

        assert logger1 is logger2

    def test_get_audit_logger_creates_instance_on_first_call(self, cleanup_audit_log):
        """Verifica que get_audit_logger cria instância na primeira chamada."""
        # Limpar instância global se existir
        import core.audit_logger
        core.audit_logger._audit_logger_instance = None

        logger = get_audit_logger()

        assert isinstance(logger, AuditLogger)


class TestOAuth2HelperFunctions:
    """Testa funções helper para eventos OAuth2."""

    def test_log_oauth2_auth_start(self, cleanup_audit_log):
        """Verifica log_oauth2_auth_start."""
        log_oauth2_auth_start(123456789)

        with open(AUDIT_LOG_FILE, "r") as f:
            log_entry = json.loads(f.readline())

        assert log_entry["event"] == "oauth2_auth_start"
        assert log_entry["user_id"] == 123456789
        assert log_entry["success"] is True
        assert log_entry["details"] == {}

    def test_log_oauth2_auth_success(self, cleanup_audit_log):
        """Verifica log_oauth2_auth_success."""
        log_oauth2_auth_success(987654321, provider="google_calendar")

        with open(AUDIT_LOG_FILE, "r") as f:
            log_entry = json.loads(f.readline())

        assert log_entry["event"] == "oauth2_auth_success"
        assert log_entry["user_id"] == 987654321
        assert log_entry["success"] is True
        assert log_entry["details"]["provider"] == "google_calendar"

    def test_log_oauth2_auth_success_default_provider(self, cleanup_audit_log):
        """Verifica que log_oauth2_auth_success usa provider padrão."""
        log_oauth2_auth_success(111222333)

        with open(AUDIT_LOG_FILE, "r") as f:
            log_entry = json.loads(f.readline())

        assert log_entry["details"]["provider"] == "google_calendar"

    def test_log_oauth2_auth_failed(self, cleanup_audit_log):
        """Verifica log_oauth2_auth_failed."""
        log_oauth2_auth_failed(555666777, "InvalidGrantError", provider="google_calendar")

        with open(AUDIT_LOG_FILE, "r") as f:
            log_entry = json.loads(f.readline())

        assert log_entry["event"] == "oauth2_auth_failed"
        assert log_entry["user_id"] == 555666777
        assert log_entry["success"] is False
        assert log_entry["details"]["provider"] == "google_calendar"
        assert log_entry["details"]["error"] == "InvalidGrantError"

    def test_log_oauth2_token_refresh_success(self, cleanup_audit_log):
        """Verifica log_oauth2_token_refresh com sucesso."""
        log_oauth2_token_refresh(111222333, success=True)

        with open(AUDIT_LOG_FILE, "r") as f:
            log_entry = json.loads(f.readline())

        assert log_entry["event"] == "oauth2_token_refresh"
        assert log_entry["user_id"] == 111222333
        assert log_entry["success"] is True

    def test_log_oauth2_token_refresh_failure(self, cleanup_audit_log):
        """Verifica log_oauth2_token_refresh com falha."""
        log_oauth2_token_refresh(444555666, success=False)

        with open(AUDIT_LOG_FILE, "r") as f:
            log_entry = json.loads(f.readline())

        assert log_entry["event"] == "oauth2_token_refresh"
        assert log_entry["user_id"] == 444555666
        assert log_entry["success"] is False


class TestLogFormatting:
    """Testa formatação dos logs."""

    def test_log_is_valid_json(self, audit_logger):
        """Verifica que cada linha do log é JSON válido."""
        audit_logger.log_event("event1", 123, True)
        audit_logger.log_event("event2", 456, False)

        with open(AUDIT_LOG_FILE, "r") as f:
            for line in f:
                # Não deve levantar exceção
                json.loads(line)

    def test_log_one_entry_per_line(self, audit_logger):
        """Verifica que cada log é uma linha separada."""
        audit_logger.log_event("event1", 123, True)
        audit_logger.log_event("event2", 456, False)
        audit_logger.log_event("event3", 789, True)

        with open(AUDIT_LOG_FILE, "r") as f:
            lines = [line.strip() for line in f if line.strip()]

        assert len(lines) == 3

    def test_log_timestamp_format(self, audit_logger):
        """Verifica que timestamp está em formato ISO 8601 com 'Z'."""
        audit_logger.log_event("test_event", 123456789, True)

        with open(AUDIT_LOG_FILE, "r") as f:
            log_entry = json.loads(f.readline())

        timestamp = log_entry["timestamp"]

        # Deve terminar com 'Z' (UTC)
        assert timestamp.endswith('Z')

        # Deve ser parseable como ISO 8601
        datetime.fromisoformat(timestamp.rstrip('Z'))


class TestEdgeCases:
    """Testa casos extremos."""

    def test_log_event_with_none_details(self, audit_logger):
        """Verifica que details=None é convertido para {}."""
        audit_logger.log_event("test_event", 123, True, details=None)

        with open(AUDIT_LOG_FILE, "r") as f:
            log_entry = json.loads(f.readline())

        assert log_entry["details"] == {}

    def test_log_event_with_complex_details(self, audit_logger):
        """Verifica que details complexos são serializados corretamente."""
        complex_details = {
            "provider": "google_calendar",
            "error": "InvalidGrant",
            "nested": {
                "key1": "value1",
                "key2": [1, 2, 3]
            }
        }

        audit_logger.log_event("test_event", 123, False, details=complex_details)

        with open(AUDIT_LOG_FILE, "r") as f:
            log_entry = json.loads(f.readline())

        assert log_entry["details"] == complex_details

    def test_log_event_large_user_id(self, audit_logger):
        """Verifica que user_ids grandes são logados corretamente."""
        large_user_id = 9999999999999999

        audit_logger.log_event("test_event", large_user_id, True)

        with open(AUDIT_LOG_FILE, "r") as f:
            log_entry = json.loads(f.readline())

        assert log_entry["user_id"] == large_user_id


class TestIntegration:
    """Testes de integração end-to-end."""

    def test_full_oauth_flow_logging(self, cleanup_audit_log):
        """Simula fluxo OAuth completo com logging."""
        user_id = 123456789

        # 1. Início do fluxo
        log_oauth2_auth_start(user_id)

        # 2. Autenticação bem-sucedida
        log_oauth2_auth_success(user_id, provider="google_calendar")

        # 3. Token refresh bem-sucedido
        log_oauth2_token_refresh(user_id, success=True)

        # Verificar logs
        with open(AUDIT_LOG_FILE, "r") as f:
            logs = [json.loads(line) for line in f]

        assert len(logs) == 3
        assert logs[0]["event"] == "oauth2_auth_start"
        assert logs[1]["event"] == "oauth2_auth_success"
        assert logs[2]["event"] == "oauth2_token_refresh"

    def test_failed_auth_flow_logging(self, cleanup_audit_log):
        """Simula fluxo OAuth com falha."""
        user_id = 987654321

        # 1. Início do fluxo
        log_oauth2_auth_start(user_id)

        # 2. Autenticação falhou
        log_oauth2_auth_failed(user_id, "InvalidGrantError")

        # Verificar logs
        with open(AUDIT_LOG_FILE, "r") as f:
            logs = [json.loads(line) for line in f]

        assert len(logs) == 2
        assert logs[0]["success"] is True
        assert logs[1]["success"] is False
        assert logs[1]["details"]["error"] == "InvalidGrantError"

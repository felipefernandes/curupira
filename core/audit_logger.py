"""
Audit Logging para Eventos de Segurança do Curupira
===================================================
Logger estruturado para rastreamento e auditoria de eventos OAuth2.

Formato: JSON estruturado em logs/security_audit.log
Benefícios:
- Rastreamento completo de autenticações
- Detecção de anomalias (múltiplas falhas)
- Forensics e compliance
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional, Any

LOGS_DIR = Path(__file__).parent.parent / "logs"
AUDIT_LOG_FILE = LOGS_DIR / "security_audit.log"


class AuditLogger:
    """Logger estruturado para eventos de segurança."""

    def __init__(self):
        # Garantir que diretório de logs existe
        LOGS_DIR.mkdir(parents=True, exist_ok=True)

        # Configurar logger dedicado
        self.logger = logging.getLogger("SecurityAudit")
        self.logger.setLevel(logging.INFO)

        # Handler para arquivo dedicado
        handler = logging.FileHandler(AUDIT_LOG_FILE)
        handler.setLevel(logging.INFO)

        # Formato estruturado (JSON) - apenas a mensagem sem timestamp do logging
        # O timestamp é incluído no JSON
        formatter = logging.Formatter('%(message)s')
        handler.setFormatter(formatter)

        self.logger.addHandler(handler)
        self.logger.propagate = False  # Não propagar para root logger

    def log_event(
        self,
        event_type: str,
        user_id: int,
        success: bool,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Loga evento de segurança estruturado.

        Args:
            event_type: Tipo do evento (oauth2_auth_start, oauth2_auth_success, etc.)
            user_id: ID do usuário Telegram
            success: Se evento foi bem-sucedido
            details: Metadados adicionais (sanitizados)

        Exemplo de Output:
            {"timestamp": "2026-03-09T23:45:12Z", "event": "oauth2_auth_start",
             "user_id": 123456789, "success": true, "details": {}}
        """
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            "event": event_type,
            "user_id": user_id,
            "success": success,
            "details": details or {}
        }

        self.logger.info(json.dumps(log_entry))


# Instância global (singleton pattern)
_audit_logger_instance = None


def get_audit_logger() -> AuditLogger:
    """Retorna instância singleton do AuditLogger."""
    global _audit_logger_instance
    if _audit_logger_instance is None:
        _audit_logger_instance = AuditLogger()
    return _audit_logger_instance


# Funções helper para eventos OAuth2
def log_oauth2_auth_start(user_id: int):
    """Loga início de fluxo OAuth2."""
    get_audit_logger().log_event("oauth2_auth_start", user_id, True)


def log_oauth2_auth_success(user_id: int, provider: str = "google_calendar"):
    """Loga autenticação OAuth2 bem-sucedida."""
    get_audit_logger().log_event(
        "oauth2_auth_success",
        user_id,
        True,
        {"provider": provider}
    )


def log_oauth2_auth_failed(user_id: int, error_type: str, provider: str = "google_calendar"):
    """Loga falha de autenticação OAuth2."""
    get_audit_logger().log_event(
        "oauth2_auth_failed",
        user_id,
        False,
        {"provider": provider, "error": error_type}
    )


def log_oauth2_token_refresh(user_id: int, success: bool):
    """Loga refresh de token OAuth2."""
    get_audit_logger().log_event(
        "oauth2_token_refresh",
        user_id,
        success
    )


# Garantir que diretório de logs existe quando módulo é importado
# Isso previne erros no CI quando os testes rodam
LOGS_DIR.mkdir(parents=True, exist_ok=True)

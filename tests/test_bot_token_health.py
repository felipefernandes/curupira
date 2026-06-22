"""
Tests for check_token_health function in bot.py.
"""
import pytest
import logging
from unittest.mock import AsyncMock, MagicMock, patch

from bot import check_token_health


@pytest.fixture
def mock_context():
    context = MagicMock()
    context.bot = AsyncMock()
    context.bot.send_message = AsyncMock()
    return context


@pytest.mark.asyncio
async def test_check_token_health_missing_credentials(mock_context, caplog):
    """When credentials file is missing, logs warning, audits failure and notifies user."""
    mock_audit = MagicMock()
    
    with patch("core.credential_manager.load_google_credentials", return_value=None), \
         patch("core.audit_logger.AuditLogger", return_value=mock_audit), \
         patch("bot.config.AUTHORIZED_USER_ID", 12345):
        with caplog.at_level(logging.WARNING):
            await check_token_health(mock_context)
            
            # Logs warning
            assert "Token health check: No credentials found" in caplog.text
            # Audits event with success=False, status='missing'
            mock_audit.log_event.assert_called_once_with(
                "token_health_check",
                user_id=0,
                success=False,
                details={"status": "missing", "action_required": "user_reauth"}
            )
            # Notifies user via Telegram
            mock_context.bot.send_message.assert_called_once_with(
                chat_id=12345,
                text="⚠️ Google Calendar não autenticado\n\nUse /setup_calendar para reconectar."
            )


@pytest.mark.asyncio
async def test_check_token_health_expired_recoverable(mock_context, caplog):
    """When token is expired but has refresh token, logs info, audits success and does not notify user."""
    mock_audit = MagicMock()
    creds = MagicMock()
    creds.valid = False
    creds.expired = True
    creds.refresh_token = "some_refresh_token"
    
    with patch("core.credential_manager.load_google_credentials", return_value=creds), \
         patch("core.audit_logger.AuditLogger", return_value=mock_audit), \
         patch("bot.config.AUTHORIZED_USER_ID", 12345):
        with caplog.at_level(logging.INFO):
            await check_token_health(mock_context)
            
            # Logs info
            assert "Token expired but refresh_token present (OK)" in caplog.text
            # Audits event with success=True, status='expired_recoverable'
            mock_audit.log_event.assert_called_once_with(
                "token_health_check",
                user_id=0,
                success=True,
                details={"status": "expired_recoverable"}
            )
            # Should NOT notify user (it will be refreshed automatically when used)
            mock_context.bot.send_message.assert_not_called()


@pytest.mark.asyncio
async def test_check_token_health_invalid_unrecoverable(mock_context, caplog):
    """When token is invalid and cannot be refreshed, logs error, audits failure and notifies user."""
    mock_audit = MagicMock()
    creds = MagicMock()
    creds.valid = False
    creds.expired = False # or expired but no refresh_token
    creds.refresh_token = None
    
    with patch("core.credential_manager.load_google_credentials", return_value=creds), \
         patch("core.audit_logger.AuditLogger", return_value=mock_audit), \
         patch("bot.config.AUTHORIZED_USER_ID", 12345):
        with caplog.at_level(logging.ERROR):
            await check_token_health(mock_context)
            
            # Logs error
            assert "Token invalid and no refresh_token (BAD)" in caplog.text
            # Audits event with success=False, status='invalid_unrecoverable'
            mock_audit.log_event.assert_called_once_with(
                "token_health_check",
                user_id=0,
                success=False,
                details={"status": "invalid_unrecoverable", "action_required": "user_reauth"}
            )
            # Notifies user via Telegram
            mock_context.bot.send_message.assert_called_once_with(
                chat_id=12345,
                text="❌ Google Calendar: token inválido\n\nSuas credenciais expiraram. Use /setup_calendar para autenticar novamente."
            )


@pytest.mark.asyncio
async def test_check_token_health_healthy(mock_context, caplog):
    """When credentials are valid, logs debug, audits success and does not notify user."""
    mock_audit = MagicMock()
    creds = MagicMock()
    creds.valid = True
    
    with patch("core.credential_manager.load_google_credentials", return_value=creds), \
         patch("core.audit_logger.AuditLogger", return_value=mock_audit), \
         patch("bot.config.AUTHORIZED_USER_ID", 12345):
        with caplog.at_level(logging.DEBUG):
            await check_token_health(mock_context)
            
            # Logs debug
            assert "Token health check: OK" in caplog.text
            # Audits event with success=True, status='healthy'
            mock_audit.log_event.assert_called_once_with(
                "token_health_check",
                user_id=0,
                success=True,
                details={"status": "healthy"}
            )
            # Should NOT notify user
            mock_context.bot.send_message.assert_not_called()


@pytest.mark.asyncio
async def test_check_token_health_exception_handling(mock_context, caplog):
    """When exception is thrown during health check, logs error and does not propagate."""
    with patch("core.credential_manager.load_google_credentials", side_effect=Exception("Disk error")), \
         patch("bot.config.AUTHORIZED_USER_ID", 12345):
        with caplog.at_level(logging.ERROR):
            await check_token_health(mock_context)
            
            # Logs error
            assert "Token health check failed: Disk error" in caplog.text
            # Should not crash nor notify
            mock_context.bot.send_message.assert_not_called()

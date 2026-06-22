"""
Tests for status command function in bot.py.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from telegram import Update

from bot import status
from core import config


@pytest.fixture
def mock_context():
    return MagicMock()


@pytest.mark.asyncio
async def test_status_update_message_is_none(mock_context):
    """When update.message is None, status command returns early doing nothing."""
    update = MagicMock(spec=Update)
    update.message = None
    
    await status(update, mock_context)


@pytest.mark.asyncio
async def test_status_from_user_is_none(mock_context):
    """When update.message.from_user is None, status command returns early."""
    update = MagicMock(spec=Update)
    message = MagicMock()
    message.from_user = None
    update.message = message
    
    await status(update, mock_context)


@pytest.mark.asyncio
async def test_status_unauthorized_user(mock_context):
    """When user is not authorized, calls acesso_negado and does not reply success."""
    update = MagicMock(spec=Update)
    message = MagicMock()
    message.from_user.id = 99999
    message.reply_text = AsyncMock()
    update.message = message
    
    with patch("bot.is_authorized", return_value=False), \
         patch("bot.acesso_negado", new_callable=AsyncMock) as mock_negado:
        await status(update, mock_context)
        
        mock_negado.assert_called_once_with(update)
        message.reply_text.assert_not_called()


@pytest.mark.asyncio
async def test_status_authorized_user(mock_context):
    """When user is authorized, replies to Telegram with system online message."""
    update = MagicMock(spec=Update)
    message = MagicMock()
    message.from_user.id = config.AUTHORIZED_USER_ID
    message.reply_text = AsyncMock()
    update.message = message
    
    with patch("bot.is_authorized", return_value=True), \
         patch("bot.config.AI_PROVIDER", "gemini"):
        await status(update, mock_context)
        
        message.reply_text.assert_called_once()
        sent_text = message.reply_text.call_args[0][0]
        assert "✅ Sistema Online e você está autenticado!" in sent_text
        assert "IA: GEMINI" in sent_text

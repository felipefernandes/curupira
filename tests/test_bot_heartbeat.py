import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from bot import system_heartbeat
from core import config
from telegram.constants import ParseMode
from telegram.error import TelegramError

@pytest.mark.asyncio
async def test_system_heartbeat_sends_html_message():
    """Test that system_heartbeat sends HTML-formatted message directly."""
    mock_context = MagicMock()
    mock_context.bot = AsyncMock()
    mock_context.bot.send_message = AsyncMock()

    message = "Hello! <b>This is bold</b>"

    mock_brain = AsyncMock()
    mock_brain.reflect.return_value = message

    mock_memory_manager = AsyncMock()

    with patch('bot.brain', mock_brain), \
         patch('bot.memory_manager', mock_memory_manager), \
         patch('bot.config.REFLECTION_ENABLED', True), \
         patch('bot.config.AUTHORIZED_USER_ID', 12345):

        await system_heartbeat(mock_context)

        mock_brain.reflect.assert_called_once()

        # Verify the message was sent with HTML parse mode (no escaping)
        mock_context.bot.send_message.assert_called_once_with(
            chat_id=12345,
            text=message,
            parse_mode=ParseMode.HTML
        )

        mock_memory_manager.log_message.assert_called_once_with(12345, "model", message)

@pytest.mark.asyncio
async def test_system_heartbeat_fallback_on_html_error():
    """Test that system_heartbeat falls back to plain text on HTML parse error."""
    mock_context = MagicMock()
    mock_context.bot = AsyncMock()

    message = "Hello <unsupported_tag>world</unsupported_tag>"

    # First call raises TelegramError, second call (fallback) succeeds
    mock_context.bot.send_message = AsyncMock(
        side_effect=[TelegramError("unsupported start tag"), None]
    )

    mock_brain = AsyncMock()
    mock_brain.reflect.return_value = message

    mock_memory_manager = AsyncMock()

    with patch('bot.brain', mock_brain), \
         patch('bot.memory_manager', mock_memory_manager), \
         patch('bot.config.REFLECTION_ENABLED', True), \
         patch('bot.config.AUTHORIZED_USER_ID', 12345):

        await system_heartbeat(mock_context)

        # Should have been called twice: first with HTML, then fallback without
        assert mock_context.bot.send_message.call_count == 2
        # Fallback sends without parse_mode
        mock_context.bot.send_message.assert_called_with(
            chat_id=12345,
            text=message
        )

@pytest.mark.asyncio
async def test_system_heartbeat_silence():
    """Test that system_heartbeat does not send a message if reflect returns None."""
    mock_context = MagicMock()
    mock_context.bot = AsyncMock()
    mock_context.bot.send_message = AsyncMock()
    
    mock_brain = AsyncMock()
    mock_brain.reflect.return_value = None  # SILENCE

    mock_memory_manager = AsyncMock()

    with patch('bot.brain', mock_brain), \
         patch('bot.memory_manager', mock_memory_manager), \
         patch('bot.config.REFLECTION_ENABLED', True), \
         patch('bot.config.AUTHORIZED_USER_ID', 12345):
         
        await system_heartbeat(mock_context)

        mock_brain.reflect.assert_called_once()
        # Ensure no message was sent or logged
        mock_context.bot.send_message.assert_not_called()
        mock_memory_manager.log_message.assert_not_called()

@pytest.mark.asyncio
async def test_system_heartbeat_memory_manager_exception(caplog):
    """Test that an exception during memory logging does not crash the heartbeat."""
    mock_context = MagicMock()
    mock_context.bot = AsyncMock()
    mock_context.bot.send_message = AsyncMock()
    
    mock_brain = AsyncMock()
    mock_brain.reflect.return_value = "Test message"
    
    mock_memory_manager = AsyncMock()
    mock_memory_manager.log_message.side_effect = Exception("DB Connection Error")

    with patch('bot.brain', mock_brain), \
         patch('bot.memory_manager', mock_memory_manager), \
         patch('bot.config.REFLECTION_ENABLED', True), \
         patch('bot.config.AUTHORIZED_USER_ID', 12345):
         
        # Execute heartbeat, should not raise
        await system_heartbeat(mock_context)

        mock_brain.reflect.assert_called_once()
        mock_context.bot.send_message.assert_called_once()
        mock_memory_manager.log_message.assert_called_once_with(12345, "model", "Test message")
        
        # Verify the error was logged
        assert "Erro ao salvar mensagem proativa no histórico: DB Connection Error" in caplog.text

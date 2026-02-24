import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import html
from bot import system_heartbeat
from core import config
from telegram.constants import ParseMode

@pytest.mark.asyncio
async def test_system_heartbeat_sends_escaped_proactive_message():
    """Test that system_heartbeat correctly escapes HTML in the proactive message."""
    # Mock context
    mock_context = MagicMock()
    mock_context.bot = AsyncMock()
    mock_context.bot.send_message = AsyncMock()
    
    # The message we want the agent to return, containing HTML characters
    unsafe_message = "Hello! <b>This is bold</b> & I love <script>alert(1)</script>"
    expected_escaped_message = html.escape(unsafe_message)

    # We need to mock brain.reflect to return our unsafe_message
    mock_brain = AsyncMock()
    mock_brain.reflect.return_value = unsafe_message

    # Mock memory manager
    mock_memory_manager = AsyncMock()

    with patch('bot.brain', mock_brain), \
         patch('bot.memory_manager', mock_memory_manager), \
         patch('bot.config.REFLECTION_ENABLED', True), \
         patch('bot.config.AUTHORIZED_USER_ID', 12345):
         
        # Execute the heartbeat
        await system_heartbeat(mock_context)

        # Verify reflect was called
        mock_brain.reflect.assert_called_once()
        
        # Verify the message was sent to the authorized user with escaped HTML
        mock_context.bot.send_message.assert_called_once_with(
            chat_id=12345,
            text=expected_escaped_message,
            parse_mode=ParseMode.HTML
        )
        
        # Verify the message was correctly saved to memory
        mock_memory_manager.log_message.assert_called_once_with(12345, "model", unsafe_message)

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

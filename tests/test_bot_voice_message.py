import pytest
import os
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
from telegram import Update
from telegram.ext import ContextTypes
from bot import handle_voice_message, responder
from core import config

def _make_voice_update(user_id=12345, username="testuser", full_name="Test User", file_id="voice_123"):
    update = MagicMock(spec=Update)
    message = MagicMock()
    message.from_user.id = user_id
    message.from_user.username = username
    message.from_user.full_name = full_name
    message.message_id = 456
    
    # Mock voice object
    voice = MagicMock()
    voice.file_id = file_id
    
    # Mock voice.get_file() which returns a File object
    mock_file = AsyncMock()
    mock_file.download_to_drive = AsyncMock()
    voice.get_file = AsyncMock(return_value=mock_file)
    
    message.voice = voice
    message.reply_chat_action = AsyncMock()
    message.reply_text = AsyncMock()
    update.message = message
    
    chat = MagicMock()
    chat.id = user_id
    chat.send_action = AsyncMock()
    update.effective_chat = chat
    
    return update, mock_file

def _make_context():
    context = MagicMock()
    context.job_queue = MagicMock()
    context.bot = MagicMock()
    return context

@pytest.mark.asyncio
async def test_handle_voice_unauthorized():
    """If the user is unauthorized, handle_voice_message rejects and does not download anything."""
    update, mock_file = _make_voice_update(user_id=99999)
    context = _make_context()
    
    with patch("bot.is_authorized", return_value=False), \
         patch("bot.acesso_negado", AsyncMock()) as mock_acesso_negado:
        await handle_voice_message(update, context)
        
        mock_acesso_negado.assert_called_once_with(update)
        mock_file.download_to_drive.assert_not_called()

@pytest.mark.asyncio
async def test_handle_voice_success():
    """Successful voice message transcription and routing to responder."""
    update, mock_file = _make_voice_update(user_id=12345)
    context = _make_context()
    
    # Mock brain.transcribe_audio
    with patch("bot.is_authorized", return_value=True), \
         patch("bot.brain") as mock_brain, \
         patch("bot.responder", AsyncMock()) as mock_responder, \
         patch("os.path.exists", return_value=True), \
         patch("os.remove") as mock_remove:
         
        mock_brain.transcribe_audio = AsyncMock(return_value="Transcrito com sucesso")
        
        await handle_voice_message(update, context)
        
        # Verify chat action "typing" was sent
        update.message.reply_chat_action.assert_called_once_with(action="typing")
        
        # Verify file was downloaded
        mock_file.download_to_drive.assert_called_once()
        
        # Verify brain.transcribe_audio was called
        mock_brain.transcribe_audio.assert_called_once()
        
        # Verify responder was called with transcribed text
        mock_responder.assert_called_once_with(update, context, transcribed_text="Transcrito com sucesso")
        
        # Verify file deletion
        mock_remove.assert_called_once()

@pytest.mark.asyncio
async def test_handle_voice_not_implemented():
    """Fallback message when the provider does not support audio transcription."""
    update, mock_file = _make_voice_update(user_id=12345)
    context = _make_context()
    
    with patch("bot.is_authorized", return_value=True), \
         patch("bot.brain") as mock_brain, \
         patch("bot.responder", AsyncMock()) as mock_responder, \
         patch("os.path.exists", return_value=True), \
         patch("os.remove") as mock_remove:
         
        mock_brain.transcribe_audio = AsyncMock(side_effect=NotImplementedError("Not supported"))
        
        await handle_voice_message(update, context)
        
        # Verify user is notified that it's not supported
        update.message.reply_text.assert_called_once_with(
            "⚠️ Meu cérebro de IA atual não oferece suporte para transcrição de áudio."
        )
        mock_responder.assert_not_called()
        mock_remove.assert_called_once()

@pytest.mark.asyncio
async def test_handle_voice_unexpected_error():
    """Handles unexpected API/network errors gracefully."""
    update, mock_file = _make_voice_update(user_id=12345)
    context = _make_context()
    
    with patch("bot.is_authorized", return_value=True), \
         patch("bot.brain") as mock_brain, \
         patch("bot.responder", AsyncMock()) as mock_responder, \
         patch("os.path.exists", return_value=True), \
         patch("os.remove") as mock_remove:
         
        mock_brain.transcribe_audio = AsyncMock(side_effect=Exception("API Error"))
        
        await handle_voice_message(update, context)
        
        # Verify user is notified of the failure
        update.message.reply_text.assert_called_once_with(
            "❌ Desculpe, não consegui transcrever seu áudio no momento."
        )
        mock_responder.assert_not_called()
        mock_remove.assert_called_once()

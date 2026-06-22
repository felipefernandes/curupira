"""
Tests for the responder() function in bot.py, testing the real production code
with mocks for Telegram objects and modules.
"""
import pytest
import logging
from unittest.mock import AsyncMock, MagicMock, patch
from telegram import Update
from telegram.error import TelegramError
from telegram.constants import ParseMode

from bot import responder
from core import config


# ── Helpers for making Mocks ──────────────────────────────────────────────────

def _make_update(text="teste", user_id=12345, username="testuser", full_name="Test User"):
    update = MagicMock(spec=Update)
    message = MagicMock()
    message.from_user.id = user_id
    message.from_user.username = username
    message.from_user.full_name = full_name
    message.text = text
    message.reply_chat_action = AsyncMock()
    message.reply_text = AsyncMock()
    update.message = message
    
    chat = MagicMock()
    chat.id = user_id
    chat.send_action = AsyncMock()
    update.effective_chat = chat
    
    return update


def _make_context():
    context = MagicMock()
    context.job_queue = MagicMock()
    context.bot = MagicMock()
    return context


def _make_memory_manager(facts=None, surname="Sobrenome"):
    memory = MagicMock()
    memory.add_user = AsyncMock()
    memory.log_message = AsyncMock()
    memory.save_fact = AsyncMock()
    memory.get_fact_value = AsyncMock(return_value=surname)
    memory.get_context = AsyncMock(return_value=[])
    memory.get_facts = AsyncMock(return_value=facts or [])
    return memory


# ── Responder Tests ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_responder_unauthorized_user():
    """If user is not authorized, sends access denied and exits early."""
    update = _make_update(user_id=99999) # unauthorized
    context = _make_context()
    
    with patch("bot.is_authorized", return_value=False), \
         patch("bot.memory_manager", _make_memory_manager()):
        await responder(update, context)
        
        # Verify access denied reply was sent
        update.message.reply_text.assert_called_once_with("⛔ Acesso negado. Este bot é privado.")


@pytest.mark.asyncio
async def test_responder_memory_manager_is_none(caplog):
    """If memory_manager is None, responds with friendly message and warns in logs."""
    update = _make_update(user_id=config.AUTHORIZED_USER_ID)
    context = _make_context()
    
    with patch("bot.is_authorized", return_value=True), \
         patch("bot.memory_manager", None):
        with caplog.at_level(logging.WARNING):
            await responder(update, context)
            
            # Check warning logs
            assert "responder: Tentativa de processar mensagem, mas memory_manager está desativado." in caplog.text
            # Verify reply message
            update.message.reply_text.assert_called_once()
            text = update.message.reply_text.call_args[0][0]
            assert "sistema de memória e histórico está desativado" in text


@pytest.mark.asyncio
async def test_responder_guard_none_does_not_send_or_log():
    """If brain.process() returns None, does not send reply_text or log to memory."""
    update = _make_update(user_id=config.AUTHORIZED_USER_ID)
    context = _make_context()
    memory = _make_memory_manager()
    brain = AsyncMock()
    brain.process.return_value = None # returns None
    
    with patch("bot.is_authorized", return_value=True), \
         patch("bot.memory_manager", memory), \
         patch("bot.brain", brain):
        await responder(update, context)
        
        # Should call typing action
        update.message.reply_chat_action.assert_called_once_with(action="typing")
        # Should log user message
        memory.log_message.assert_any_call(config.AUTHORIZED_USER_ID, "user", "teste")
        # Should NOT log model response (because it was None)
        # Note: first call is 'user' log, there should not be a second call for 'model'
        model_calls = [c for c in memory.log_message.call_args_list if c[0][1] == "model"]
        assert len(model_calls) == 0
        # Should NOT send Telegram reply
        update.message.reply_text.assert_not_called()


@pytest.mark.asyncio
async def test_responder_sends_normalized_html():
    """If brain.process() returns text, normalizes markdown and sends as HTML."""
    update = _make_update(text="olá", user_id=config.AUTHORIZED_USER_ID)
    context = _make_context()
    memory = _make_memory_manager()
    brain = AsyncMock()
    brain.process.return_value = "Olá **amigo**"
    
    with patch("bot.is_authorized", return_value=True), \
         patch("bot.memory_manager", memory), \
         patch("bot.brain", brain):
        await responder(update, context)
        
        # Normalizes markdown (**amigo** -> <b>amigo</b>)
        update.message.reply_text.assert_called_once_with(
            "Olá <b>amigo</b>",
            parse_mode=ParseMode.HTML
        )
        # Logs model message
        memory.log_message.assert_any_call(config.AUTHORIZED_USER_ID, "model", "Olá <b>amigo</b>")


@pytest.mark.asyncio
async def test_responder_telegram_html_error_fallback():
    """On Telegram HTML parsing error, retries with unsupported tags stripped."""
    update = _make_update(text="olá", user_id=config.AUTHORIZED_USER_ID)
    context = _make_context()
    memory = _make_memory_manager()
    brain = AsyncMock()
    brain.process.return_value = "Oi <custom-tag>teste</custom-tag>"
    
    # First call raises TelegramError, second succeeds
    update.message.reply_text.side_effect = [TelegramError("bad HTML"), None]
    
    with patch("bot.is_authorized", return_value=True), \
         patch("bot.memory_manager", memory), \
         patch("bot.brain", brain):
        await responder(update, context)
        
        # Called twice
        assert update.message.reply_text.call_count == 2
        
        # Second call stripped the unsupported tag
        second_call_text = update.message.reply_text.call_args_list[1][0][0]
        assert "<custom-tag>" not in second_call_text
        assert "Oi teste" in second_call_text


@pytest.mark.asyncio
async def test_responder_telegram_all_html_fails_fallback():
    """If even stripped HTML fails, sends as plain text without parse_mode."""
    update = _make_update(text="olá", user_id=config.AUTHORIZED_USER_ID)
    context = _make_context()
    memory = _make_memory_manager()
    brain = AsyncMock()
    brain.process.return_value = "Oi"
    
    # All HTML attempts raise TelegramError, plain text succeeds
    update.message.reply_text.side_effect = [
        TelegramError("bad HTML"),
        TelegramError("still bad HTML"),
        None
    ]
    
    with patch("bot.is_authorized", return_value=True), \
         patch("bot.memory_manager", memory), \
         patch("bot.brain", brain):
        await responder(update, context)
        
        assert update.message.reply_text.call_count == 3
        # Third call has no parse_mode (plain text fallback)
        last_call_kwargs = update.message.reply_text.call_args_list[2][1]
        assert "parse_mode" not in last_call_kwargs


@pytest.mark.asyncio
async def test_responder_onboarding_flow_complete():
    """Tests the onboarding flow step-by-step to cover all states in bot.py."""
    import bot
    
    # Reset onboarding states for test isolation
    bot.onboarding_states.clear()
    
    user_id = config.AUTHORIZED_USER_ID
    memory = _make_memory_manager(surname="") # No surname initially
    context = _make_context()
    
    # ── Step 1: Start Onboarding (state is None) ──
    update1 = _make_update(text="Felipe", user_id=user_id)
    with patch("bot.is_authorized", return_value=True), \
         patch("bot.memory_manager", memory):
        await responder(update1, context)
        
        # Should ask for name
        update1.message.reply_text.assert_called_once_with(
            "Olá! Sou o Curupira. Antes de começarmos, como gostaria de ser chamado?"
        )
        assert bot.onboarding_states[user_id] == bot.WAITING_NAME

    # ── Step 2: WAITING_NAME state ──
    update2 = _make_update(text="Felipe", user_id=user_id)
    with patch("bot.is_authorized", return_value=True), \
         patch("bot.memory_manager", memory):
        await responder(update2, context)
        
        # Should save name and ask for BOT surname
        memory.save_fact.assert_called_once_with(user_id, "personal_name", "Felipe")
        update2.message.reply_text.assert_called_once_with(
            "OK Felipe, como sou único, qual sobrenome devo usar para me diferenciar dos outros Curupiras?"
        )
        assert bot.onboarding_states[user_id] == bot.WAITING_SURNAME

    # ── Step 3: WAITING_SURNAME state ──
    update3 = _make_update(text="Silva", user_id=user_id)
    # Mocking that memory.get_fact_value retrieves the personal name for UX
    memory.get_fact_value = AsyncMock(side_effect=lambda uid, key: "Felipe" if key == "personal_name" else "")
    
    with patch("bot.is_authorized", return_value=True), \
         patch("bot.memory_manager", memory):
        await responder(update3, context)
        
        # Should save assistant surname
        memory.save_fact.assert_any_call(user_id, "assistant_surname", "Silva")
        # Should clear onboarding state
        assert user_id not in bot.onboarding_states
        # Should welcome user
        update3.message.reply_text.assert_called_once_with(
            "Entendido! Configuração concluída! Como posso ajudar hoje?"
        )

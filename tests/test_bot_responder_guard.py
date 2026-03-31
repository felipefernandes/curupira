"""
Tests for the new guard/normalize logic added to bot.py's responder()
and execute_reminder() in this PR.

Following the project pattern (see test_direct_reply.py): bot.py has
module-level side effects, so logic is replicated inline rather than
imported directly.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from telegram.error import TelegramError
from telegram.constants import ParseMode
from core.telegram_formatter import TelegramFormatter, _strip_unsupported_html


# ── Helpers replicating bot.py patterns ───────────────────────────────────────

async def _run_responder_send(response_text, reply_mock: AsyncMock, log_mock=None):
    """
    Replicates the guard + normalize + send block from bot.py responder()
    (lines 276-295).
    """
    memory_log = log_mock or AsyncMock()

    # Guard: process() returned None → content already delivered via direct_html
    if response_text is None:
        return

    response_text = TelegramFormatter.normalize(response_text)
    await memory_log("user_id", "model", response_text)

    try:
        await reply_mock(response_text, parse_mode=ParseMode.HTML)
    except TelegramError:
        clean_text = _strip_unsupported_html(response_text)
        try:
            await reply_mock(clean_text, parse_mode=ParseMode.HTML)
        except TelegramError:
            await reply_mock(response_text)


async def _run_intermediate_reply(text: str, reply_mock: AsyncMock):
    """
    Replicates the intermediate_reply callback from bot.py responder()
    (lines 230-243).
    """
    if text and text.strip():
        safe_text = TelegramFormatter.normalize(text.strip())
        try:
            await reply_mock(safe_text, parse_mode=ParseMode.HTML)
        except TelegramError:
            try:
                await reply_mock(_strip_unsupported_html(safe_text), parse_mode=ParseMode.HTML)
            except TelegramError:
                await reply_mock(text.strip())
        except Exception:
            pass


async def _run_execute_reminder_send(response_text, send_mock: AsyncMock):
    """
    Replicates the normalize + send block from bot.py execute_reminder()
    (lines 338-353).
    """
    if response_text is None:
        response_text = ""
    response_text = TelegramFormatter.normalize(response_text)
    try:
        if response_text:
            await send_mock(chat_id=12345, text=response_text, parse_mode=ParseMode.HTML)
    except TelegramError:
        clean_text = _strip_unsupported_html(response_text)
        try:
            await send_mock(chat_id=12345, text=clean_text, parse_mode=ParseMode.HTML)
        except TelegramError:
            await send_mock(chat_id=12345, text=response_text)


# ── responder() guard tests ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_responder_guard_none_does_not_send():
    """process() returned None → reply_text must never be called."""
    reply_mock = AsyncMock()
    log_mock = AsyncMock()
    await _run_responder_send(None, reply_mock, log_mock)
    reply_mock.assert_not_called()
    log_mock.assert_not_called()


@pytest.mark.asyncio
async def test_responder_guard_none_does_not_log():
    """process() returned None → memory_manager.log_message must not be called."""
    log_mock = AsyncMock()
    await _run_responder_send(None, AsyncMock(), log_mock)
    log_mock.assert_not_called()


@pytest.mark.asyncio
async def test_responder_sends_normalized_text():
    """Normal text response is normalized and sent with ParseMode.HTML."""
    reply_mock = AsyncMock()
    await _run_responder_send("**negrito**", reply_mock)
    reply_mock.assert_called_once()
    sent_text = reply_mock.call_args[0][0]
    assert "<b>negrito</b>" in sent_text
    assert reply_mock.call_args[1]["parse_mode"] == ParseMode.HTML


@pytest.mark.asyncio
async def test_responder_falls_back_to_stripped_html_on_telegram_error():
    """On TelegramError, retries with unsupported tags stripped."""
    call_count = 0

    async def side_effect(text, parse_mode=None):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise TelegramError("bad HTML")

    reply_mock = AsyncMock(side_effect=side_effect)
    await _run_responder_send("<b>ok</b><div>bad</div>", reply_mock)

    assert call_count == 2
    second_text = reply_mock.call_args_list[1][0][0]
    assert "<div>" not in second_text
    assert "<b>ok</b>" in second_text


@pytest.mark.asyncio
async def test_responder_falls_back_to_plain_text_when_all_html_fails():
    """If both HTML attempts fail, sends as plain text (no parse_mode)."""
    async def always_fail_html(text, parse_mode=None):
        if parse_mode == ParseMode.HTML:
            raise TelegramError("HTML error")

    reply_mock = AsyncMock(side_effect=always_fail_html)
    await _run_responder_send("<b>teste</b>", reply_mock)

    last = reply_mock.call_args_list[-1]
    assert last.kwargs.get("parse_mode") is None


# ── intermediate_reply tests ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_intermediate_reply_normalizes_markdown():
    """Markdown in preamble text is converted to HTML before sending."""
    reply_mock = AsyncMock()
    await _run_intermediate_reply("**Buscando...**", reply_mock)
    sent_text = reply_mock.call_args[0][0]
    assert "<b>Buscando...</b>" in sent_text


@pytest.mark.asyncio
async def test_intermediate_reply_empty_does_nothing():
    """Empty text does not call reply_text."""
    reply_mock = AsyncMock()
    await _run_intermediate_reply("", reply_mock)
    reply_mock.assert_not_called()


@pytest.mark.asyncio
async def test_intermediate_reply_falls_back_on_telegram_error():
    """On TelegramError, retries with stripped HTML."""
    call_count = 0

    async def side_effect(text, parse_mode=None):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise TelegramError("unsupported tag")

    reply_mock = AsyncMock(side_effect=side_effect)
    await _run_intermediate_reply("<b>ok</b><div>bad</div>", reply_mock)
    assert call_count == 2


@pytest.mark.asyncio
async def test_intermediate_reply_plain_text_fallback():
    """If both HTML attempts fail, sends plain text."""
    async def always_fail_html(text, parse_mode=None):
        if parse_mode == ParseMode.HTML:
            raise TelegramError("HTML error")

    reply_mock = AsyncMock(side_effect=always_fail_html)
    await _run_intermediate_reply("<b>teste</b>", reply_mock)
    last = reply_mock.call_args_list[-1]
    assert last.kwargs.get("parse_mode") is None


# ── execute_reminder send tests ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_execute_reminder_none_response_does_not_send():
    """When process() returns None, execute_reminder must not call send_message."""
    send_mock = AsyncMock()
    await _run_execute_reminder_send(None, send_mock)
    send_mock.assert_not_called()


@pytest.mark.asyncio
async def test_execute_reminder_empty_response_does_not_send():
    """Empty response (after normalize) must not call send_message."""
    send_mock = AsyncMock()
    await _run_execute_reminder_send("", send_mock)
    send_mock.assert_not_called()


@pytest.mark.asyncio
async def test_execute_reminder_sends_normalized_text():
    """Normal response is normalized and sent."""
    send_mock = AsyncMock()
    await _run_execute_reminder_send("**Tarefa executada!**", send_mock)
    send_mock.assert_called_once()
    sent_text = send_mock.call_args[1]["text"]
    assert "<b>Tarefa executada!</b>" in sent_text


@pytest.mark.asyncio
async def test_execute_reminder_falls_back_on_telegram_error():
    """On TelegramError, retries with stripped HTML."""
    call_count = 0

    async def side_effect(**kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise TelegramError("bad HTML")

    send_mock = AsyncMock(side_effect=side_effect)
    await _run_execute_reminder_send("<b>ok</b><div>bad</div>", send_mock)
    assert call_count == 2
    second_text = send_mock.call_args_list[1][1]["text"]
    assert "<div>" not in second_text

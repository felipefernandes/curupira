"""
Tests for the direct_reply callback from bot.py's responder().

Since bot.py has module-level side effects (AgentBrain instantiation, etc.),
we test the direct_reply logic in isolation by replicating the exact pattern
used in the responder() handler, without importing the full bot module.
"""
import re
import logging
import pytest
from unittest.mock import AsyncMock, MagicMock
from telegram.error import TelegramError
from telegram.constants import ParseMode


def _strip_unsupported_html(text: str) -> str:
    """Minimal replica of bot.py's _strip_unsupported_html for test isolation."""
    ALLOWED = {"b", "i", "u", "s", "code", "pre", "a", "tg-spoiler"}
    def replace_tag(m):
        tag = m.group(1).lstrip("/").split()[0].lower()
        return m.group(0) if tag in ALLOWED else ""
    return re.sub(r"<(/?\w[^>]*)>", replace_tag, text)


async def _run_direct_reply(html: str, reply_mock: AsyncMock) -> None:
    """
    Replicates the direct_reply nested function from bot.py responder(),
    using reply_mock in place of update.message.reply_text.
    """
    async def direct_reply(html: str):
        if not html:
            return
        try:
            await reply_mock(html, parse_mode=ParseMode.HTML)
        except TelegramError as e:
            logging.warning(f"Erro no direct_reply (HTML): {e}")
            try:
                await reply_mock(_strip_unsupported_html(html), parse_mode=ParseMode.HTML)
            except TelegramError:
                await reply_mock(html)
        except Exception as e:
            logging.error(f"Erro no direct_reply: {e}")

    await direct_reply(html)


@pytest.mark.asyncio
async def test_direct_reply_empty_html_does_nothing():
    """Empty html string should return immediately without calling reply_text."""
    reply_mock = AsyncMock()
    await _run_direct_reply("", reply_mock)
    reply_mock.assert_not_called()


@pytest.mark.asyncio
async def test_direct_reply_success():
    """Valid HTML is sent with ParseMode.HTML on the first attempt."""
    reply_mock = AsyncMock()
    await _run_direct_reply("<b>Olá</b>", reply_mock)
    reply_mock.assert_called_once_with("<b>Olá</b>", parse_mode=ParseMode.HTML)


@pytest.mark.asyncio
async def test_direct_reply_telegram_error_falls_back_to_stripped():
    """On TelegramError, retries with stripped HTML."""
    call_count = 0

    async def reply_side_effect(text, parse_mode=None):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise TelegramError("can't parse")

    reply_mock = AsyncMock(side_effect=reply_side_effect)
    await _run_direct_reply("<b>Olá</b><unsupported>X</unsupported>", reply_mock)

    assert reply_mock.call_count == 2
    # Second call should have stripped the unsupported tag
    second_call_text = reply_mock.call_args_list[1].args[0]
    assert "<unsupported>" not in second_call_text


@pytest.mark.asyncio
async def test_direct_reply_both_html_attempts_fail_sends_plain():
    """If both HTML attempts fail, sends the original text as plain fallback."""
    async def always_fail_html(text, parse_mode=None):
        if parse_mode == ParseMode.HTML:
            raise TelegramError("HTML parse error")

    reply_mock = AsyncMock(side_effect=always_fail_html)
    await _run_direct_reply("<b>Olá</b>", reply_mock)

    # Third call is the plain-text fallback (no parse_mode kwarg)
    last_call = reply_mock.call_args_list[-1]
    assert last_call.args[0] == "<b>Olá</b>"
    assert last_call.kwargs.get("parse_mode") is None


@pytest.mark.asyncio
async def test_direct_reply_general_exception_is_caught():
    """A non-TelegramError exception is caught and does not propagate."""
    reply_mock = AsyncMock(side_effect=Exception("unexpected error"))
    # Should not raise
    await _run_direct_reply("<b>Olá</b>", reply_mock)

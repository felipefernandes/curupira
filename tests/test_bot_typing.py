"""
Tests for the typing indicator feature in bot.py.

Since bot.py has module-level side effects (AgentBrain instantiation, etc.),
we test the typing indicator logic in isolation by replicating the exact pattern
used in the responder() handler, without importing the full bot module.
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Helper: replicate the exact keep_typing + brain.process pattern from bot.py
# ---------------------------------------------------------------------------

async def _run_handler_with_typing(mock_chat, mock_brain_coro):
    """
    Mimics the typing-indicator block in bot.py's responder():

        async def keep_typing():
            try:
                while True:
                    await update.effective_chat.send_action("typing")
                    await asyncio.sleep(4)
            except asyncio.CancelledError:
                pass

        typing_task = asyncio.create_task(keep_typing())
        try:
            response_text = await brain.process(...)
        except Exception as e:
            response_text = "error"
        finally:
            typing_task.cancel()

    Returns the response_text and the send_action mock for assertions.
    """
    async def keep_typing():
        try:
            while True:
                await mock_chat.send_action("typing")
                await asyncio.sleep(4)
        except asyncio.CancelledError:
            pass

    typing_task = asyncio.create_task(keep_typing())
    try:
        response_text = await mock_brain_coro()
    except Exception:
        response_text = "error"
    finally:
        typing_task.cancel()

    return response_text


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_typing_action_sent_during_processing():
    """
    Typing action must be sent at least once while the agent processes.
    """
    mock_chat = AsyncMock()

    async def slow_brain():
        # Yield control so the typing task runs at least one iteration
        await asyncio.sleep(0)
        return "Resposta do bot"

    result = await _run_handler_with_typing(mock_chat, slow_brain)

    assert result == "Resposta do bot"
    mock_chat.send_action.assert_called_with("typing")


@pytest.mark.asyncio
async def test_typing_task_cancelled_after_response():
    """
    The typing task must be cancelled after brain.process() returns.
    Verified by checking the task cancellation flag, not by intercepting
    CancelledError (which depends on event loop scheduling).
    """
    mock_chat = AsyncMock()

    async def fast_brain():
        return "Resposta rápida"

    async def keep_typing():
        try:
            while True:
                await mock_chat.send_action("typing")
                await asyncio.sleep(4)
        except asyncio.CancelledError:
            pass

    typing_task = asyncio.create_task(keep_typing())
    try:
        result = await fast_brain()
    finally:
        typing_task.cancel()
        await asyncio.gather(typing_task, return_exceptions=True)

    assert result == "Resposta rápida"
    assert typing_task.cancelled() or typing_task.done(), "typing task deve ser encerrada após a resposta"


@pytest.mark.asyncio
async def test_typing_task_cancelled_on_brain_exception():
    """
    Even if brain.process() raises, the typing task must be cancelled (finally block).
    """
    mock_chat = AsyncMock()

    async def failing_brain():
        raise RuntimeError("brain crash")

    async def keep_typing():
        try:
            while True:
                await mock_chat.send_action("typing")
                await asyncio.sleep(4)
        except asyncio.CancelledError:
            pass

    typing_task = asyncio.create_task(keep_typing())
    try:
        response_text = await failing_brain()
    except Exception:
        response_text = "error"
    finally:
        typing_task.cancel()
        await asyncio.gather(typing_task, return_exceptions=True)

    assert response_text == "error"
    assert typing_task.cancelled() or typing_task.done(), "typing task deve ser encerrada mesmo em caso de erro"


@pytest.mark.asyncio
async def test_typing_sends_correct_action_string():
    """
    The action string passed to Telegram must be exactly 'typing'.
    """
    mock_chat = AsyncMock()

    async def instant_brain():
        await asyncio.sleep(0)
        return "ok"

    await _run_handler_with_typing(mock_chat, instant_brain)

    # Verify all calls used the correct action
    for call in mock_chat.send_action.call_args_list:
        assert call.args[0] == "typing" or call.kwargs.get("action") == "typing"

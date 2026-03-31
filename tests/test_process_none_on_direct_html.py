"""
Tests that verify process() returns None when all tool calls delivered content
via direct_html, preventing a redundant LLM follow-up message.

Also verifies that process() still returns text when:
  - no direct_html was dispatched
  - dispatch failed (callback raised)
  - only some tools used direct_html (mixed case)
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from core.agent import AgentBrain


@pytest.fixture
def agent():
    with patch("core.agent.config") as mock_cfg:
        mock_cfg.AI_PROVIDER = "groq"
        mock_cfg.GROQ_API_KEY = "test-key"
        mock_cfg.GROQ_MODEL = "test-model"
        mock_cfg.GROQ_TEMPERATURE = 0.7
        mock_cfg.GEMINI_API_KEY = "test-key"
        mock_cfg.GEMINI_MODEL = "test-model"
        mock_cfg.RETRY_ATTEMPTS = 1
        mock_cfg.RETRY_INITIAL_DELAY = 0.0
        mock_cfg.skill_enabled = MagicMock(return_value=False)
        a = AgentBrain("groq", "test-model")
    return a


def _make_groq_tool_response(tool_name: str, tool_id: str = "call_1"):
    """Build a mock Groq response that calls a single tool."""
    tool_call = MagicMock()
    tool_call.id = tool_id
    tool_call.function.name = tool_name
    tool_call.function.arguments = "{}"

    msg = MagicMock()
    msg.tool_calls = [tool_call]
    msg.content = None

    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message = msg
    response.usage = None
    return response


def _make_groq_text_response(text: str):
    """Build a mock Groq response with plain text (no tool call)."""
    msg = MagicMock()
    msg.tool_calls = None
    msg.content = text

    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message = msg
    response.usage = None
    return response


@pytest.mark.asyncio
async def test_process_returns_none_when_all_direct_html_dispatched(agent):
    """
    When the only tool call dispatches direct_html successfully,
    process() must return None (content already delivered).
    """
    direct_reply_calls = []

    async def mock_direct_reply(html: str):
        direct_reply_calls.append(html)

    # Skill returns direct_html
    mock_skill = AsyncMock()
    mock_skill.name = "list_reminders"
    mock_skill.description = "list"
    mock_skill.parameters = {}
    mock_skill.execute.return_value = {
        "status": "success",
        "data": [],
        "direct_html": "<b>Nenhum lembrete.</b>",
    }
    agent.register_skill(mock_skill)

    tool_resp = _make_groq_tool_response("list_reminders")
    # LLM generates follow-up after seeing {"status": "success"}
    followup_resp = _make_groq_text_response("Aqui estão seus lembretes!")

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(
        side_effect=[tool_resp, followup_resp]
    )

    with patch.object(agent, "_get_groq_client", return_value=mock_client):
        result = await agent.process(
            "lista meus lembretes",
            {},
            on_direct_reply=mock_direct_reply,
        )

    # direct_html was sent
    assert direct_reply_calls == ["<b>Nenhum lembrete.</b>"]
    # process() must suppress the LLM follow-up
    assert result is None


@pytest.mark.asyncio
async def test_process_returns_text_when_no_direct_html(agent):
    """
    When the tool does NOT use direct_html, process() returns the LLM text normally.
    """
    mock_skill = AsyncMock()
    mock_skill.name = "get_time"
    mock_skill.description = "get time"
    mock_skill.parameters = {}
    mock_skill.execute.return_value = {"time": "10:45", "status": "success"}
    agent.register_skill(mock_skill)

    tool_resp = _make_groq_tool_response("get_time")
    text_resp = _make_groq_text_response("São 10:45.")

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(
        side_effect=[tool_resp, text_resp]
    )

    with patch.object(agent, "_get_groq_client", return_value=mock_client):
        result = await agent.process("que horas são?", {})

    assert result == "São 10:45."


@pytest.mark.asyncio
async def test_process_returns_text_when_direct_html_dispatch_fails(agent):
    """
    When on_direct_reply raises (Telegram error), dispatched=False, so
    process() falls back and returns the LLM text (not None).
    """
    async def failing_direct_reply(html: str):
        raise Exception("Telegram timeout")

    mock_skill = AsyncMock()
    mock_skill.name = "list_reminders"
    mock_skill.description = "list"
    mock_skill.parameters = {}
    mock_skill.execute.return_value = {
        "status": "success",
        "data": [],
        "direct_html": "<b>Lista</b>",
    }
    agent.register_skill(mock_skill)

    tool_resp = _make_groq_tool_response("list_reminders")
    text_resp = _make_groq_text_response("Você tem 0 lembretes.")

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(
        side_effect=[tool_resp, text_resp]
    )

    with patch.object(agent, "_get_groq_client", return_value=mock_client):
        result = await agent.process(
            "lista meus lembretes",
            {},
            on_direct_reply=failing_direct_reply,
        )

    # Dispatch failed → LLM text should be returned, not None
    assert result is not None
    assert "lembrete" in result.lower()


@pytest.mark.asyncio
async def test_process_returns_text_when_on_direct_reply_is_none(agent):
    """
    When on_direct_reply is not provided (e.g. execute_reminder task path),
    dispatched is always False → process() returns LLM text.
    """
    mock_skill = AsyncMock()
    mock_skill.name = "list_reminders"
    mock_skill.description = "list"
    mock_skill.parameters = {}
    mock_skill.execute.return_value = {
        "status": "success",
        "data": [],
        "direct_html": "<b>Lista</b>",
    }
    agent.register_skill(mock_skill)

    tool_resp = _make_groq_tool_response("list_reminders")
    text_resp = _make_groq_text_response("Nenhum lembrete encontrado.")

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(
        side_effect=[tool_resp, text_resp]
    )

    with patch.object(agent, "_get_groq_client", return_value=mock_client):
        # No on_direct_reply — simulates execute_reminder task path
        result = await agent.process("lista lembretes", {})

    assert result is not None
    assert result != ""


@pytest.mark.asyncio
async def test_process_returns_text_with_mixed_tools(agent):
    """
    When one tool uses direct_html and another does not,
    _direct_html_count < _tool_call_count → process() returns LLM text.
    """
    direct_reply_calls = []

    async def mock_direct_reply(html: str):
        direct_reply_calls.append(html)

    # Skill 1: uses direct_html
    remind_skill = AsyncMock()
    remind_skill.name = "list_reminders"
    remind_skill.description = "list"
    remind_skill.parameters = {}
    remind_skill.execute.return_value = {
        "status": "success",
        "data": [],
        "direct_html": "<b>0 lembretes</b>",
    }
    agent.register_skill(remind_skill)

    # Skill 2: does NOT use direct_html
    time_skill = AsyncMock()
    time_skill.name = "get_time"
    time_skill.description = "time"
    time_skill.parameters = {}
    time_skill.execute.return_value = {"time": "10:45", "status": "success"}
    agent.register_skill(time_skill)

    # LLM calls both tools in sequence
    tool_resp_1 = _make_groq_tool_response("list_reminders", "call_1")
    tool_resp_2 = _make_groq_tool_response("get_time", "call_2")
    final_resp = _make_groq_text_response("Você tem 0 lembretes e são 10:45.")

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(
        side_effect=[tool_resp_1, tool_resp_2, final_resp]
    )

    with patch.object(agent, "_get_groq_client", return_value=mock_client):
        result = await agent.process(
            "lista lembretes e que horas são",
            {},
            on_direct_reply=mock_direct_reply,
        )

    # direct_html was sent for the first tool
    assert len(direct_reply_calls) == 1
    # But LLM text should NOT be suppressed (mixed case)
    assert result is not None

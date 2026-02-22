"""
Tests for SaveFactSkill and user_facts injection into agent context.
Issue #88 — Facts Injection: https://github.com/felipefernandes/curupira/issues/88
"""

import pytest
import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from skills.memory import MemoryManager, SaveFactSkill


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_memory():
    """Returns a MemoryManager with its async methods mocked."""
    mgr = MagicMock(spec=MemoryManager)
    mgr.save_fact = AsyncMock(return_value=None)
    mgr.get_fact_value = AsyncMock(return_value=None)
    return mgr


@pytest.fixture
def skill(mock_memory):
    return SaveFactSkill(mock_memory)


@pytest.fixture
def valid_context():
    return {"user_id": 12345}


# ---------------------------------------------------------------------------
# SaveFactSkill — execute()
# ---------------------------------------------------------------------------

class TestSaveFactSkill:

    @pytest.mark.asyncio
    async def test_execute_success(self, skill, mock_memory, valid_context):
        """Deve salvar o fato e retornar status ok."""
        result = await skill.execute(valid_context, key="city", value="São Paulo")

        assert result["status"] == "ok"
        assert result["saved"] == {"city": "São Paulo"}
        mock_memory.save_fact.assert_awaited_once_with(12345, "city", "São Paulo")

    @pytest.mark.asyncio
    async def test_execute_missing_user_id(self, skill, mock_memory):
        """Deve retornar erro quando user_id não está no contexto."""
        result = await skill.execute({}, key="city", value="São Paulo")

        assert "error" in result
        assert "user_id" in result["error"]
        mock_memory.save_fact.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_execute_empty_key(self, skill, mock_memory, valid_context):
        """Deve retornar erro quando key é vazio."""
        result = await skill.execute(valid_context, key="", value="São Paulo")

        assert "error" in result
        assert "key" in result["error"]
        mock_memory.save_fact.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_execute_empty_value(self, skill, mock_memory, valid_context):
        """Deve retornar erro quando value é vazio."""
        result = await skill.execute(valid_context, key="city", value="")

        assert "error" in result
        assert "value" in result["error"]
        mock_memory.save_fact.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_execute_strips_whitespace(self, skill, mock_memory, valid_context):
        """Deve fazer strip de espaços em key e value."""
        result = await skill.execute(valid_context, key="  city  ", value="  São Paulo  ")

        assert result["status"] == "ok"
        mock_memory.save_fact.assert_awaited_once_with(12345, "city", "São Paulo")

    def test_skill_name(self, skill):
        assert skill.name == "save_user_fact"

    def test_skill_parameters_has_required_fields(self, skill):
        params = skill.parameters
        assert "key" in params["properties"]
        assert "value" in params["properties"]
        assert "key" in params["required"]
        assert "value" in params["required"]


# ---------------------------------------------------------------------------
# user_facts injection into AgentBrain system prompt
# ---------------------------------------------------------------------------

class TestUserFactsInjection:

    @pytest.fixture
    def agent(self):
        with patch("core.agent.config.GROQ_API_KEY", "fake_key"):
            from core.agent import AgentBrain
            return AgentBrain("groq", "fake_model")

    @pytest.mark.asyncio
    async def test_user_facts_appear_in_system_prompt(self, agent):
        """user_facts do contexto deve aparecer no prompt enviado ao modelo."""
        # Mock do cliente Groq
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Resposta do agente"
        mock_response.choices[0].message.tool_calls = None

        mock_client = AsyncMock()
        mock_client.chat.completions.create.return_value = mock_response
        agent.client = mock_client

        context = {
            "user_name": "Felipe",
            "user_facts": "- city: São Paulo\n- wake_up_time: 07:00",
        }

        await agent.process("Qual o tempo?", context)

        # Verificar que o system prompt contém os fatos
        call_args = mock_client.chat.completions.create.call_args
        messages = call_args.kwargs.get("messages") or call_args.args[0] if call_args.args else []
        # messages é passado como keyword arg
        if not messages:
            messages = call_args[1].get("messages", [])

        system_content = messages[0]["content"]
        assert "São Paulo" in system_content
        assert "07:00" in system_content
        assert "FATOS PERSISTENTES" in system_content

    @pytest.mark.asyncio
    async def test_no_facts_section_when_empty(self, agent):
        """Quando user_facts é vazio, a seção não deve aparecer no prompt."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Resposta"
        mock_response.choices[0].message.tool_calls = None

        mock_client = AsyncMock()
        mock_client.chat.completions.create.return_value = mock_response
        agent.client = mock_client

        context = {"user_name": "Felipe", "user_facts": ""}
        await agent.process("Olá", context)

        call_args = mock_client.chat.completions.create.call_args
        messages = call_args.kwargs.get("messages", [])
        system_content = messages[0]["content"] if messages else ""

        assert "Fatos persistentes" not in system_content

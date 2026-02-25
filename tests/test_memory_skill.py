"""
Tests for SaveFactSkill and user_facts injection into agent context.
Issue #88 — Facts Injection: https://github.com/felipefernandes/curupira/issues/88
"""

import pytest
import sys
import os
import tempfile
import aiosqlite
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

        assert result["status"] == "success"
        assert result["data"] == {"key": "city", "value": "São Paulo"}
        mock_memory.save_fact.assert_awaited_once_with(12345, "city", "São Paulo")

    @pytest.mark.asyncio
    async def test_execute_missing_user_id(self, skill, mock_memory):
        """Deve retornar erro quando user_id não está no contexto."""
        result = await skill.execute({}, key="city", value="São Paulo")

        assert result["status"] == "error"
        assert "user_id" in result["error"]
        mock_memory.save_fact.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_execute_empty_key(self, skill, mock_memory, valid_context):
        """Deve retornar erro quando key é vazio."""
        result = await skill.execute(valid_context, key="", value="São Paulo")

        assert result["status"] == "error"
        assert "key" in result["error"]
        mock_memory.save_fact.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_execute_empty_value(self, skill, mock_memory, valid_context):
        """Deve retornar erro quando value é vazio."""
        result = await skill.execute(valid_context, key="city", value="")

        assert result["status"] == "error"
        assert "value" in result["error"]
        mock_memory.save_fact.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_execute_strips_whitespace(self, skill, mock_memory, valid_context):
        """Deve fazer strip de espaços em key e value."""
        result = await skill.execute(valid_context, key="  city  ", value="  São Paulo  ")

        assert result["status"] == "success"
        mock_memory.save_fact.assert_awaited_once_with(12345, "city", "São Paulo")

    def test_skill_metadata(self, skill):
        assert skill.name == "save_user_fact"
        assert "Salvar Fato" in skill.display_name
        assert "Persiste um fato" in skill.description

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


# ---------------------------------------------------------------------------
# MemoryManager DB migration — reminders table columns
# ---------------------------------------------------------------------------

class TestMemoryManagerMigration:

    @pytest.mark.asyncio
    async def test_init_db_creates_recurrence_and_is_task_columns(self):
        """init_db adds recurrence and is_task columns to the reminders table."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            mm = MemoryManager(db_path=db_path)
            await mm.init_db()

            async with aiosqlite.connect(db_path) as db:
                async with db.execute("PRAGMA table_info(reminders)") as cursor:
                    columns = [row[1] for row in await cursor.fetchall()]

            assert "recurrence" in columns
            assert "is_task" in columns
        finally:
            os.unlink(db_path)

    @pytest.mark.asyncio
    async def test_init_db_migration_idempotent(self):
        """Calling init_db twice does not raise (columns already exist)."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            mm = MemoryManager(db_path=db_path)
            await mm.init_db()
            # Second call must not raise
            await mm.init_db()
        finally:
            os.unlink(db_path)

# ---------------------------------------------------------------------------
# MemoryManager get_context session memory (Issue #70)
# ---------------------------------------------------------------------------

from datetime import datetime, timedelta

class TestGetContextSessionMemory:
    @pytest.mark.asyncio
    async def test_get_context_filters_by_minutes_ago(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            mm = MemoryManager(db_path=db_path)
            await mm.init_db()
            
            await mm.add_user(user_id=1, username="test", full_name="Test User")
            
            now = datetime.now()
            
            async with aiosqlite.connect(db_path) as db:
                # 1 hour ago (should be excluded)
                await db.execute(
                    "INSERT INTO conversations (user_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
                    (1, "user", "Old message", now - timedelta(hours=1))
                )
                # 10 minutes ago (should be included)
                await db.execute(
                    "INSERT INTO conversations (user_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
                    (1, "model", "Recent reply", now - timedelta(minutes=10))
                )
                # Just now (should be included)
                await db.execute(
                    "INSERT INTO conversations (user_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
                    (1, "user", "Hello now", now)
                )
                await db.commit()

            # Retrieve with 30 minutes window
            context = await mm.get_context(user_id=1, limit=10, minutes_ago=30)
            
            assert "Old message" not in context
            assert "Recent reply" in context
            assert "Hello now" in context
            
            # Verify chronological order
            assert context.find("Recent reply") < context.find("Hello now")
            
        finally:
            os.unlink(db_path)
            
    @pytest.mark.asyncio
    async def test_get_context_respects_limit(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            mm = MemoryManager(db_path=db_path)
            await mm.init_db()
            await mm.add_user(user_id=1, username="test", full_name="Test User")
            
            now = datetime.now()
            async with aiosqlite.connect(db_path) as db:
                for i in range(5):
                    await db.execute(
                        "INSERT INTO conversations (user_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
                        (1, "user", f"Msg {i}", now)
                    )
                await db.commit()

            # Retrieve with limit 2
            context = await mm.get_context(user_id=1, limit=2, minutes_ago=30)
            
            assert "Msg 0" not in context
            assert "Msg 1" not in context
            assert "Msg 2" not in context
            assert "Msg 3" in context
            assert "Msg 4" in context
        finally:
            os.unlink(db_path)

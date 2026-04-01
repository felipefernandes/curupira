"""
Tests for PatternAnalyzer and run_pattern_check.

Cobre:
- MemoryManager.get_tool_usage_stats()
- PatternAnalyzer.get_pending_suggestions()
- PatternAnalyzer._extract_top_topic()
- PatternAnalyzer._build_message()
- run_pattern_check() — integração
"""

import json
import os
import sys
import tempfile
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import aiosqlite
import pytest
import pytest_asyncio

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from skills.memory import MemoryManager
from skills.pattern_analyzer import PatternAnalyzer, run_pattern_check, SUGGESTION_REGISTRY

USER_ID = 42


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_metadata(tool_name: str, tool_args: dict) -> str:
    return json.dumps({"tool_name": tool_name, "tool_args": tool_args, "tool_call_id": "x"})


def _mock_config(
    threshold_days=7,
    threshold_count=3,
    cooldown_days=30,
):
    cfg = MagicMock()
    cfg.PATTERN_THRESHOLD_DAYS = threshold_days
    cfg.PATTERN_THRESHOLD_COUNT = threshold_count
    cfg.PATTERN_SUGGESTION_COOLDOWN_DAYS = cooldown_days
    return cfg


async def _seed_tool_calls(db_path: str, tool_name: str, args: dict, count: int, days_ago: int = 0):
    """Insere N registros de tool call no banco."""
    ts = datetime.now() - timedelta(days=days_ago)
    metadata = _make_metadata(tool_name, args)
    async with aiosqlite.connect(db_path) as db:
        for _ in range(count):
            await db.execute(
                "INSERT INTO conversations (user_id, role, content, timestamp, metadata) VALUES (?, ?, ?, ?, ?)",
                (USER_ID, "assistant", None, ts, metadata),
            )
        await db.commit()


# ---------------------------------------------------------------------------
# Fixture: MemoryManager com DB temporário
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def memory(tmp_path):
    db_path = str(tmp_path / "test.db")
    mgr = MemoryManager(db_path=db_path)
    await mgr.init_db()
    # Garante que o usuário existe na tabela users
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id, username, full_name, first_seen) VALUES (?, ?, ?, ?)",
            (USER_ID, "testuser", "Test User", datetime.now()),
        )
        await db.commit()
    return mgr


# ---------------------------------------------------------------------------
# TestGetToolUsageStats
# ---------------------------------------------------------------------------

class TestGetToolUsageStats:

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_tool_calls(self, memory):
        result = await memory.get_tool_usage_stats(USER_ID, days=7)
        assert result == []

    @pytest.mark.asyncio
    async def test_counts_correctly_within_window(self, memory):
        await _seed_tool_calls(memory.db_path, "sports_manager", {"team": "botafogo"}, count=5)
        result = await memory.get_tool_usage_stats(USER_ID, days=7)
        assert len(result) == 1
        assert result[0]["tool_name"] == "sports_manager"
        assert result[0]["call_count"] == 5

    @pytest.mark.asyncio
    async def test_excludes_rows_outside_window(self, memory):
        # 3 calls dentro da janela, 5 fora
        await _seed_tool_calls(memory.db_path, "sports_manager", {"team": "botafogo"}, count=3, days_ago=0)
        await _seed_tool_calls(memory.db_path, "sports_manager", {"team": "botafogo"}, count=5, days_ago=10)
        result = await memory.get_tool_usage_stats(USER_ID, days=7)
        assert result[0]["call_count"] == 3

    @pytest.mark.asyncio
    async def test_groups_by_tool_name(self, memory):
        await _seed_tool_calls(memory.db_path, "sports_manager", {"team": "flamengo"}, count=4)
        await _seed_tool_calls(memory.db_path, "get_weather", {"city": "rio"}, count=2)
        result = await memory.get_tool_usage_stats(USER_ID, days=7)
        tool_names = [r["tool_name"] for r in result]
        assert "sports_manager" in tool_names
        assert "get_weather" in tool_names
        sports = next(r for r in result if r["tool_name"] == "sports_manager")
        assert sports["call_count"] == 4

    @pytest.mark.asyncio
    async def test_accumulates_args_samples(self, memory):
        await _seed_tool_calls(memory.db_path, "sports_manager", {"team": "vasco"}, count=3)
        result = await memory.get_tool_usage_stats(USER_ID, days=7)
        assert len(result[0]["args_samples"]) == 3
        assert all(s["team"] == "vasco" for s in result[0]["args_samples"])

    @pytest.mark.asyncio
    async def test_tolerates_null_metadata_rows(self, memory):
        # Insere uma row sem metadata — não deve quebrar
        async with aiosqlite.connect(memory.db_path) as db:
            await db.execute(
                "INSERT INTO conversations (user_id, role, content, timestamp, metadata) VALUES (?, ?, ?, ?, ?)",
                (USER_ID, "user", "oi", datetime.now(), None),
            )
            await db.commit()
        result = await memory.get_tool_usage_stats(USER_ID, days=7)
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_ordered_by_call_count_desc(self, memory):
        await _seed_tool_calls(memory.db_path, "get_weather", {"city": "sp"}, count=2)
        await _seed_tool_calls(memory.db_path, "sports_manager", {"team": "santos"}, count=5)
        result = await memory.get_tool_usage_stats(USER_ID, days=7)
        assert result[0]["tool_name"] == "sports_manager"
        assert result[1]["tool_name"] == "get_weather"


# ---------------------------------------------------------------------------
# TestPatternAnalyzer
# ---------------------------------------------------------------------------

class TestPatternAnalyzer:

    def _make_analyzer(self, memory, **cfg_overrides):
        cfg = _mock_config(**cfg_overrides)
        return PatternAnalyzer(memory, cfg)

    @pytest.mark.asyncio
    async def test_no_suggestion_when_count_below_threshold(self, memory):
        await _seed_tool_calls(memory.db_path, "sports_manager", {"team": "botafogo"}, count=2)
        analyzer = self._make_analyzer(memory, threshold_count=3)
        result = await analyzer.get_pending_suggestions(USER_ID)
        assert result == []

    @pytest.mark.asyncio
    async def test_returns_suggestion_when_threshold_met(self, memory):
        await _seed_tool_calls(memory.db_path, "sports_manager", {"team": "botafogo"}, count=3)
        analyzer = self._make_analyzer(memory, threshold_count=3)
        result = await analyzer.get_pending_suggestions(USER_ID)
        assert len(result) == 1
        assert result[0]["tool_name"] == "sports_manager"
        assert "Botafogo" in result[0]["message"]

    @pytest.mark.asyncio
    async def test_respects_cooldown(self, memory):
        await _seed_tool_calls(memory.db_path, "sports_manager", {"team": "botafogo"}, count=5)
        # Marca sugestão como enviada AGORA
        await memory.save_fact(
            USER_ID, "suggestion_sent:sports_manager", datetime.now().isoformat()
        )
        analyzer = self._make_analyzer(memory, threshold_count=3, cooldown_days=30)
        result = await analyzer.get_pending_suggestions(USER_ID)
        assert result == []

    @pytest.mark.asyncio
    async def test_allows_suggestion_after_cooldown_expired(self, memory):
        await _seed_tool_calls(memory.db_path, "sports_manager", {"team": "botafogo"}, count=5)
        # Marca sugestão como enviada 31 dias atrás
        old_ts = (datetime.now() - timedelta(days=31)).isoformat()
        await memory.save_fact(USER_ID, "suggestion_sent:sports_manager", old_ts)
        analyzer = self._make_analyzer(memory, threshold_count=3, cooldown_days=30)
        result = await analyzer.get_pending_suggestions(USER_ID)
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_skips_tools_not_in_registry(self, memory):
        await _seed_tool_calls(memory.db_path, "introspection", {}, count=10)
        analyzer = self._make_analyzer(memory, threshold_count=3)
        result = await analyzer.get_pending_suggestions(USER_ID)
        assert result == []

    @pytest.mark.asyncio
    async def test_allows_suggestion_when_stored_timestamp_is_invalid(self, memory):
        """ISO inválido em suggestion_sent deve ser ignorado e permitir re-sugestão."""
        await _seed_tool_calls(memory.db_path, "sports_manager", {"team": "botafogo"}, count=5)
        await memory.save_fact(USER_ID, "suggestion_sent:sports_manager", "not-a-valid-iso-date")
        analyzer = self._make_analyzer(memory, threshold_count=3, cooldown_days=30)
        result = await analyzer.get_pending_suggestions(USER_ID)
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_uses_generic_template_when_no_topic(self, memory):
        # sports_manager sem campo "team" nos args
        await _seed_tool_calls(memory.db_path, "sports_manager", {"action": "standings"}, count=5)
        analyzer = self._make_analyzer(memory, threshold_count=3)
        result = await analyzer.get_pending_suggestions(USER_ID)
        assert len(result) == 1
        assert SUGGESTION_REGISTRY["sports_manager"]["generic_template"] in result[0]["message"]

    def test_extract_top_topic_returns_most_common(self):
        analyzer = PatternAnalyzer(MagicMock(), _mock_config())
        samples = [
            {"team": "botafogo"},
            {"team": "botafogo"},
            {"team": "flamengo"},
        ]
        assert analyzer._extract_top_topic(samples, "team") == "botafogo"

    def test_extract_top_topic_returns_none_when_field_absent(self):
        analyzer = PatternAnalyzer(MagicMock(), _mock_config())
        samples = [{"action": "results"}, {"action": "standings"}]
        assert analyzer._extract_top_topic(samples, "team") is None

    def test_extract_top_topic_returns_none_on_empty_list(self):
        analyzer = PatternAnalyzer(MagicMock(), _mock_config())
        assert analyzer._extract_top_topic([], "team") is None

    def test_build_message_with_topic(self):
        analyzer = PatternAnalyzer(MagicMock(), _mock_config())
        msg = analyzer._build_message("sports_manager", "botafogo")
        assert msg is not None
        assert "Botafogo" in msg
        assert msg == SUGGESTION_REGISTRY["sports_manager"]["template"].format(topic="Botafogo")

    def test_build_message_generic_when_no_topic(self):
        analyzer = PatternAnalyzer(MagicMock(), _mock_config())
        msg = analyzer._build_message("sports_manager", None)
        assert msg == SUGGESTION_REGISTRY["sports_manager"]["generic_template"]

    def test_build_message_returns_none_for_unknown_tool(self):
        analyzer = PatternAnalyzer(MagicMock(), _mock_config())
        assert analyzer._build_message("unknown_skill", "topic") is None


# ---------------------------------------------------------------------------
# TestRunPatternCheck — integração
# ---------------------------------------------------------------------------

class TestRunPatternCheck:

    @pytest.mark.asyncio
    async def test_returns_list_of_strings(self, memory):
        await _seed_tool_calls(memory.db_path, "sports_manager", {"team": "botafogo"}, count=5)
        cfg = _mock_config(threshold_count=3)
        messages = await run_pattern_check(USER_ID, memory, cfg)
        assert isinstance(messages, list)
        assert all(isinstance(m, str) for m in messages)

    @pytest.mark.asyncio
    async def test_marks_suggestion_sent_in_facts(self, memory):
        await _seed_tool_calls(memory.db_path, "sports_manager", {"team": "botafogo"}, count=5)
        cfg = _mock_config(threshold_count=3)
        await run_pattern_check(USER_ID, memory, cfg)
        sent_at = await memory.get_fact_value(USER_ID, "suggestion_sent:sports_manager")
        assert sent_at is not None
        # Deve ser um ISO datetime válido
        datetime.fromisoformat(sent_at)

    @pytest.mark.asyncio
    async def test_no_double_suggestion_within_cooldown(self, memory):
        await _seed_tool_calls(memory.db_path, "sports_manager", {"team": "botafogo"}, count=5)
        cfg = _mock_config(threshold_count=3, cooldown_days=30)
        # Primeira execução
        msgs1 = await run_pattern_check(USER_ID, memory, cfg)
        # Segunda execução (dentro do cooldown)
        msgs2 = await run_pattern_check(USER_ID, memory, cfg)
        assert len(msgs1) == 1
        assert len(msgs2) == 0

    @pytest.mark.asyncio
    async def test_empty_when_count_below_threshold(self, memory):
        await _seed_tool_calls(memory.db_path, "sports_manager", {"team": "botafogo"}, count=1)
        cfg = _mock_config(threshold_count=3)
        messages = await run_pattern_check(USER_ID, memory, cfg)
        assert messages == []

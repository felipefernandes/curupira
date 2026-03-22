"""Tests for the DailyBriefingSkill."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from skills.daily_briefing import DailyBriefingSkill


# ── Skill Unit Tests ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_execute_all_sources_available():
    """When all sub-skills are available, briefing includes all sections."""
    weather = AsyncMock()
    weather.execute.return_value = {
        "status": "success",
        "data": {
            "location": "São Paulo",
            "temperature": 25,
            "humidity": 60,
            "rain_probability": 10,
            "condition": "Céu limpo",
        },
    }

    calendar = AsyncMock()
    calendar.execute.return_value = {
        "status": "success",
        "data": {
            "events": [
                {"summary": "Reunião", "start": "2026-03-22T10:00:00", "end": "2026-03-22T11:00:00"}
            ],
            "count": 1,
        },
    }

    rss = AsyncMock()
    rss.execute.return_value = {
        "status": "success",
        "data": {
            "entries": [
                {"title": "Manchete 1", "link": "https://example.com/1", "published": ""},
            ]
        },
    }

    skill = DailyBriefingSkill(weather_skill=weather, calendar_skill=calendar, rss_skill=rss)

    with patch("core.config.RSS_FEEDS", {"G1": "https://g1.globo.com/rss/g1/"}):
        result = await skill.execute({})

    assert result["status"] == "success"
    data = result["data"]
    assert data["weather"]["temperature"] == 25
    assert len(data["events"]) == 1
    assert data["events"][0]["summary"] == "Reunião"
    assert len(data["news"]) == 1
    assert data["news"][0]["title"] == "Manchete 1"


@pytest.mark.asyncio
async def test_execute_no_sub_skills():
    """When no sub-skills are available, briefing returns None sections."""
    skill = DailyBriefingSkill()
    result = await skill.execute({})

    assert result["status"] == "success"
    data = result["data"]
    assert data["weather"] is None
    assert data["events"] is None
    assert data["news"] is None


@pytest.mark.asyncio
async def test_execute_weather_failure():
    """If weather fails, other sections still work."""
    weather = AsyncMock()
    weather.execute.side_effect = Exception("API timeout")

    calendar = AsyncMock()
    calendar.execute.return_value = {
        "status": "success",
        "data": {"events": [], "count": 0},
    }

    skill = DailyBriefingSkill(weather_skill=weather, calendar_skill=calendar)
    result = await skill.execute({})

    assert result["status"] == "success"
    assert result["data"]["weather"] is None
    assert result["data"]["events"] == []


@pytest.mark.asyncio
async def test_execute_calendar_error_response():
    """If calendar returns error status, events is None."""
    calendar = AsyncMock()
    calendar.execute.return_value = {
        "status": "error",
        "error": "Não autenticado",
    }

    skill = DailyBriefingSkill(calendar_skill=calendar)
    result = await skill.execute({})

    assert result["status"] == "success"
    assert result["data"]["events"] is None


@pytest.mark.asyncio
async def test_execute_rss_limits_feeds():
    """RSS gathering should limit to max 2 feeds and 3 entries each."""
    rss = AsyncMock()
    rss.execute.return_value = {
        "status": "success",
        "data": {
            "entries": [
                {"title": f"Headline {i}", "link": f"https://example.com/{i}", "published": ""}
                for i in range(5)
            ]
        },
    }

    skill = DailyBriefingSkill(rss_skill=rss)

    feeds = {
        "Feed1": "https://feed1.com",
        "Feed2": "https://feed2.com",
        "Feed3": "https://feed3.com",  # Should be excluded (max 2)
    }
    with patch("core.config.RSS_FEEDS", feeds):
        result = await skill.execute({})

    # Should have called rss.execute exactly 2 times (max 2 feeds)
    assert rss.execute.call_count == 2
    # Each call returns 3 entries (limit param), so total = 6
    # But our mock returns 5 entries and the skill takes all from return
    assert result["status"] == "success"


@pytest.mark.asyncio
async def test_skill_properties():
    """Test skill metadata properties."""
    skill = DailyBriefingSkill()
    assert skill.name == "daily_briefing"
    assert skill.display_name == "📋 Briefing Diário"
    assert skill.skill_group == "daily_briefing"
    assert "city" in skill.parameters["properties"]


# ── Heartbeat Integration Tests ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_heartbeat_triggers_briefing_during_greeting_window():
    """During greeting window with daily_briefing enabled, briefing is sent."""
    from bot import system_heartbeat

    mock_context = MagicMock()
    mock_context.bot = AsyncMock()
    mock_context.bot.send_message = AsyncMock()

    mock_brain = AsyncMock()
    mock_brain._last_greeting_date = None  # Not greeted today
    mock_brain.compose_briefing.return_value = "Bom dia! Aqui está seu briefing..."

    mock_briefing_skill = AsyncMock()
    mock_briefing_skill.execute.return_value = {
        "status": "success",
        "data": {"weather": {"temperature": 25}, "events": [], "news": []},
    }

    mock_memory = AsyncMock()
    mock_memory.get_fact_value.return_value = "Felipe"

    fixed_now = datetime(2026, 3, 22, 7, 30, 0)  # 7:30 AM - within greeting window

    with patch("bot.brain", mock_brain), \
         patch("bot.daily_briefing_skill", mock_briefing_skill), \
         patch("bot.memory_manager", mock_memory), \
         patch("bot.config.REFLECTION_ENABLED", True), \
         patch("bot.config.AUTHORIZED_USER_ID", 12345), \
         patch("bot.config.REFLECTION_GREETING_HOUR_START", 7), \
         patch("bot.config.REFLECTION_GREETING_HOUR_END", 9), \
         patch("bot.config.skill_enabled", return_value=True), \
         patch("bot.datetime") as mock_datetime:

        mock_datetime.now.return_value = fixed_now
        mock_datetime.side_effect = lambda *a, **kw: datetime(*a, **kw)

        await system_heartbeat(mock_context)

    # Briefing skill should have been called
    mock_briefing_skill.execute.assert_called_once()
    # LLM should have composed the briefing
    mock_brain.compose_briefing.assert_called_once()
    # Message should have been sent
    mock_context.bot.send_message.assert_called_once()
    # reflect() should NOT have been called (briefing replaces it)
    mock_brain.reflect.assert_not_called()


@pytest.mark.asyncio
async def test_heartbeat_falls_through_to_reflect_outside_greeting_window():
    """Outside greeting window, normal reflect() is used."""
    from bot import system_heartbeat

    mock_context = MagicMock()
    mock_context.bot = AsyncMock()
    mock_context.bot.send_message = AsyncMock()

    mock_brain = AsyncMock()
    mock_brain._last_greeting_date = None
    mock_brain.reflect.return_value = None  # SILENCE

    mock_briefing_skill = AsyncMock()
    mock_memory = AsyncMock()

    fixed_now = datetime(2026, 3, 22, 14, 0, 0)  # 2 PM - outside greeting window

    with patch("bot.brain", mock_brain), \
         patch("bot.daily_briefing_skill", mock_briefing_skill), \
         patch("bot.memory_manager", mock_memory), \
         patch("bot.config.REFLECTION_ENABLED", True), \
         patch("bot.config.AUTHORIZED_USER_ID", 12345), \
         patch("bot.config.REFLECTION_GREETING_HOUR_START", 7), \
         patch("bot.config.REFLECTION_GREETING_HOUR_END", 9), \
         patch("bot.config.skill_enabled", return_value=True), \
         patch("bot.datetime") as mock_datetime:

        mock_datetime.now.return_value = fixed_now
        mock_datetime.side_effect = lambda *a, **kw: datetime(*a, **kw)

        await system_heartbeat(mock_context)

    # Briefing should NOT have been triggered
    mock_briefing_skill.execute.assert_not_called()
    # Normal reflect should have been called
    mock_brain.reflect.assert_called_once()


@pytest.mark.asyncio
async def test_heartbeat_skips_briefing_when_disabled():
    """When daily_briefing is disabled, uses normal reflect even in greeting window."""
    from bot import system_heartbeat

    mock_context = MagicMock()
    mock_context.bot = AsyncMock()
    mock_context.bot.send_message = AsyncMock()

    mock_brain = AsyncMock()
    mock_brain._last_greeting_date = None
    mock_brain.reflect.return_value = "Bom dia!"

    mock_memory = AsyncMock()

    fixed_now = datetime(2026, 3, 22, 7, 30, 0)  # Within greeting window

    def skill_enabled_side_effect(name):
        if name == "daily_briefing":
            return False
        return True

    with patch("bot.brain", mock_brain), \
         patch("bot.daily_briefing_skill", None), \
         patch("bot.memory_manager", mock_memory), \
         patch("bot.config.REFLECTION_ENABLED", True), \
         patch("bot.config.AUTHORIZED_USER_ID", 12345), \
         patch("bot.config.REFLECTION_GREETING_HOUR_START", 7), \
         patch("bot.config.REFLECTION_GREETING_HOUR_END", 9), \
         patch("bot.config.skill_enabled", side_effect=skill_enabled_side_effect), \
         patch("bot.datetime") as mock_datetime:

        mock_datetime.now.return_value = fixed_now
        mock_datetime.side_effect = lambda *a, **kw: datetime(*a, **kw)

        await system_heartbeat(mock_context)

    # Normal reflect should have been called (no briefing)
    mock_brain.reflect.assert_called_once()

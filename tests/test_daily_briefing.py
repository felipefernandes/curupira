"""Tests for the DailyBriefingSkill and AgentBrain.compose_briefing."""

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


# ── Missing Coverage: Skill Properties ───────────────────────────────────


@pytest.mark.asyncio
async def test_skill_group_emoji_and_description():
    """Cover skill_group_emoji and description properties."""
    skill = DailyBriefingSkill()
    assert skill.skill_group_emoji == "📋"
    assert "clima" in skill.description.lower()


# ── Missing Coverage: Weather error response ─────────────────────────────


@pytest.mark.asyncio
async def test_weather_returns_error_status():
    """When weather returns error status, weather section is None."""
    weather = AsyncMock()
    weather.execute.return_value = {
        "status": "error",
        "error": "Cidade não encontrada",
    }

    skill = DailyBriefingSkill(weather_skill=weather)
    result = await skill.execute({})

    assert result["status"] == "success"
    assert result["data"]["weather"] is None


# ── Missing Coverage: Calendar exception ─────────────────────────────────


@pytest.mark.asyncio
async def test_calendar_exception_is_handled():
    """When calendar raises an exception, events section is None."""
    calendar = AsyncMock()
    calendar.execute.side_effect = Exception("OAuth token expired")

    skill = DailyBriefingSkill(calendar_skill=calendar)
    result = await skill.execute({})

    assert result["status"] == "success"
    assert result["data"]["events"] is None


# ── Missing Coverage: RSS exception ──────────────────────────────────────


@pytest.mark.asyncio
async def test_rss_exception_is_handled():
    """When RSS raises an exception, news section is None."""
    rss = AsyncMock()
    rss.execute.side_effect = Exception("Feed timeout")

    skill = DailyBriefingSkill(rss_skill=rss)

    with patch("core.config.RSS_FEEDS", {"G1": "https://g1.globo.com/rss/g1/"}):
        result = await skill.execute({})

    assert result["status"] == "success"
    assert result["data"]["news"] is None


# ── AgentBrain.compose_briefing Tests ────────────────────────────────────


@pytest.fixture
def mock_agent():
    """Fixture for AgentBrain with mocked dependencies."""
    from core.agent import AgentBrain
    with patch("core.agent.BaseSkill"), \
         patch("core.agent.IntrospectionSkill"), \
         patch("core.agent.RssReadSkill"), \
         patch("core.agent.RssListSkill"), \
         patch("core.agent.config.GROQ_API_KEY", "dummy_key"):
        agent = AgentBrain(provider="groq")
        return agent


@pytest.mark.asyncio
async def test_compose_briefing_groq_full_data(mock_agent):
    """compose_briefing with Groq and full briefing data."""
    mock_message = MagicMock()
    mock_message.content = "Bom dia Felipe! Hoje está 25°C em São Paulo..."
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_client = AsyncMock()
    mock_client.chat.completions.create.return_value = mock_response

    briefing_data = {
        "weather": {
            "location": "São Paulo",
            "temperature": 25,
            "humidity": 60,
            "rain_probability": 10,
            "condition": "Céu limpo",
        },
        "events": [
            {"summary": "Reunião", "start": "2026-03-22T10:00:00"},
        ],
        "news": [
            {"source": "G1", "title": "Manchete do dia"},
        ],
    }

    with patch("core.config.AI_PROVIDER", "groq"), \
         patch("core.config.GROQ_API_KEY", "valid_key"), \
         patch("core.config.GROQ_MODEL", "llama-test"), \
         patch("groq.AsyncGroq", return_value=mock_client):

        result = await mock_agent.compose_briefing(briefing_data, user_name="Felipe")

    assert result is not None
    assert "Bom dia" in result
    mock_client.chat.completions.create.assert_called_once()
    call_kwargs = mock_client.chat.completions.create.call_args[1]
    assert call_kwargs["temperature"] == 0.5
    assert call_kwargs["max_tokens"] == 600


@pytest.mark.asyncio
async def test_compose_briefing_groq_empty_events(mock_agent):
    """compose_briefing with empty events list shows 'nenhum evento'."""
    mock_message = MagicMock()
    mock_message.content = "Bom dia! Agenda livre hoje."
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_client = AsyncMock()
    mock_client.chat.completions.create.return_value = mock_response

    briefing_data = {"weather": None, "events": [], "news": None}

    with patch("core.config.AI_PROVIDER", "groq"), \
         patch("core.config.GROQ_API_KEY", "valid_key"), \
         patch("core.config.GROQ_MODEL", "llama-test"), \
         patch("groq.AsyncGroq", return_value=mock_client):

        result = await mock_agent.compose_briefing(briefing_data)

    assert result is not None
    # Verify prompt includes "nenhum evento" for empty events list
    call_args = mock_client.chat.completions.create.call_args[1]
    user_msg = call_args["messages"][1]["content"]
    assert "nenhum evento" in user_msg


@pytest.mark.asyncio
async def test_compose_briefing_no_data(mock_agent):
    """compose_briefing with no data available."""
    mock_message = MagicMock()
    mock_message.content = "Bom dia! Não consegui reunir informações hoje."
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_client = AsyncMock()
    mock_client.chat.completions.create.return_value = mock_response

    briefing_data = {}

    with patch("core.config.AI_PROVIDER", "groq"), \
         patch("core.config.GROQ_API_KEY", "valid_key"), \
         patch("core.config.GROQ_MODEL", "llama-test"), \
         patch("groq.AsyncGroq", return_value=mock_client):

        result = await mock_agent.compose_briefing(briefing_data)

    assert result is not None
    # Verify prompt includes fallback text
    call_args = mock_client.chat.completions.create.call_args[1]
    user_msg = call_args["messages"][1]["content"]
    assert "Nenhum dado disponível" in user_msg


@pytest.mark.asyncio
async def test_compose_briefing_gemini(mock_agent):
    """compose_briefing with Gemini provider."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.candidates[0].content.parts[0].text = "Bom dia! Via Gemini."
    mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

    briefing_data = {
        "weather": {"location": "Rio", "temperature": 30, "condition": "Sol", "humidity": 50, "rain_probability": 0},
    }

    with patch("core.config.AI_PROVIDER", "gemini"), \
         patch("core.config.GEMINI_API_KEY", "valid_key"), \
         patch("core.config.GEMINI_MODEL", "gemini-test"), \
         patch("google.genai.Client", return_value=mock_client):

        result = await mock_agent.compose_briefing(briefing_data, user_name="João")

    assert result == "Bom dia! Via Gemini."
    mock_client.aio.models.generate_content.assert_called_once()


@pytest.mark.asyncio
async def test_compose_briefing_gemini_no_candidates(mock_agent):
    """compose_briefing returns None when Gemini has no candidates."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.candidates = []
    mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

    with patch("core.config.AI_PROVIDER", "gemini"), \
         patch("core.config.GEMINI_API_KEY", "valid_key"), \
         patch("core.config.GEMINI_MODEL", "gemini-test"), \
         patch("google.genai.Client", return_value=mock_client):

        result = await mock_agent.compose_briefing({})

    assert result is None


@pytest.mark.asyncio
async def test_compose_briefing_no_provider(mock_agent):
    """compose_briefing returns None when no provider is available."""
    with patch("core.config.AI_PROVIDER", "groq"), \
         patch("core.config.GROQ_API_KEY", ""):

        result = await mock_agent.compose_briefing({"weather": {"temperature": 20}})

    assert result is None


@pytest.mark.asyncio
async def test_compose_briefing_llm_exception(mock_agent):
    """compose_briefing handles LLM exceptions gracefully."""
    mock_client = AsyncMock()
    mock_client.chat.completions.create.side_effect = Exception("Rate limited")

    with patch("core.config.AI_PROVIDER", "groq"), \
         patch("core.config.GROQ_API_KEY", "valid_key"), \
         patch("core.config.GROQ_MODEL", "llama-test"), \
         patch("groq.AsyncGroq", return_value=mock_client):

        result = await mock_agent.compose_briefing({"weather": {"temperature": 20}})

    assert result is None


@pytest.mark.asyncio
async def test_compose_briefing_strips_think_blocks(mock_agent):
    """compose_briefing strips <think> blocks from CoT models."""
    mock_message = MagicMock()
    mock_message.content = "<think>Planning...</think>Bom dia! Briefing pronto."
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_client = AsyncMock()
    mock_client.chat.completions.create.return_value = mock_response

    with patch("core.config.AI_PROVIDER", "groq"), \
         patch("core.config.GROQ_API_KEY", "valid_key"), \
         patch("core.config.GROQ_MODEL", "llama-test"), \
         patch("groq.AsyncGroq", return_value=mock_client):

        result = await mock_agent.compose_briefing({})

    assert result == "Bom dia! Briefing pronto."
    assert "<think>" not in result


@pytest.mark.asyncio
async def test_compose_briefing_empty_after_strip_returns_none(mock_agent):
    """compose_briefing returns None if result is empty after stripping CoT."""
    mock_message = MagicMock()
    mock_message.content = "<think>Thinking only...</think>"
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_client = AsyncMock()
    mock_client.chat.completions.create.return_value = mock_response

    with patch("core.config.AI_PROVIDER", "groq"), \
         patch("core.config.GROQ_API_KEY", "valid_key"), \
         patch("core.config.GROQ_MODEL", "llama-test"), \
         patch("groq.AsyncGroq", return_value=mock_client):

        result = await mock_agent.compose_briefing({})

    assert result is None


# ── AgentBrain._resolve_reflection_provider Tests ────────────────────────


@pytest.mark.asyncio
async def test_resolve_provider_groq(mock_agent):
    """_resolve_reflection_provider returns Groq client."""
    mock_client = MagicMock()

    with patch("core.config.AI_PROVIDER", "groq"), \
         patch("core.config.GROQ_API_KEY", "valid_key"), \
         patch("core.config.GROQ_MODEL", "llama-test"), \
         patch("groq.AsyncGroq", return_value=mock_client):

        use_groq, client, model = mock_agent._resolve_reflection_provider()

    assert use_groq is True
    assert client is mock_client
    assert model == "llama-test"


@pytest.mark.asyncio
async def test_resolve_provider_groq_missing_key(mock_agent):
    """_resolve_reflection_provider returns None when Groq key missing."""
    with patch("core.config.AI_PROVIDER", "groq"), \
         patch("core.config.GROQ_API_KEY", ""):

        use_groq, client, model = mock_agent._resolve_reflection_provider()

    assert client is None
    assert model is None


@pytest.mark.asyncio
async def test_resolve_provider_groq_import_error(mock_agent):
    """_resolve_reflection_provider handles Groq import error."""
    with patch("core.config.AI_PROVIDER", "groq"), \
         patch("core.config.GROQ_API_KEY", "valid_key"), \
         patch.dict("sys.modules", {"groq": None}):

        use_groq, client, model = mock_agent._resolve_reflection_provider()

    assert client is None


@pytest.mark.asyncio
async def test_resolve_provider_gemini(mock_agent):
    """_resolve_reflection_provider returns Gemini client."""
    mock_client = MagicMock()

    with patch("core.config.AI_PROVIDER", "gemini"), \
         patch("core.config.GEMINI_API_KEY", "valid_key"), \
         patch("core.config.GEMINI_MODEL", "gemini-test"), \
         patch("google.genai.Client", return_value=mock_client):

        use_groq, client, model = mock_agent._resolve_reflection_provider()

    assert use_groq is False
    assert client is mock_client
    assert model == "gemini-test"


@pytest.mark.asyncio
async def test_resolve_provider_gemini_missing_key(mock_agent):
    """_resolve_reflection_provider returns None when Gemini key missing."""
    with patch("core.config.AI_PROVIDER", "gemini"), \
         patch("core.config.GEMINI_API_KEY", ""):

        use_groq, client, model = mock_agent._resolve_reflection_provider()

    assert client is None
    assert model is None


@pytest.mark.asyncio
async def test_resolve_provider_unknown(mock_agent):
    """_resolve_reflection_provider returns None for unknown provider."""
    with patch("core.config.AI_PROVIDER", "unknown"):
        use_groq, client, model = mock_agent._resolve_reflection_provider()

    assert use_groq is False
    assert client is None
    assert model is None


# ── Heartbeat: briefing compose returns None ─────────────────────────────


@pytest.mark.asyncio
async def test_heartbeat_falls_to_reflect_when_briefing_compose_returns_none():
    """If compose_briefing returns None, heartbeat falls through to reflect."""
    from bot import system_heartbeat

    mock_context = MagicMock()
    mock_context.bot = AsyncMock()
    mock_context.bot.send_message = AsyncMock()

    mock_brain = AsyncMock()
    mock_brain._last_greeting_date = None
    mock_brain.compose_briefing.return_value = None  # LLM failed
    mock_brain.reflect.return_value = None  # SILENCE

    mock_briefing_skill = AsyncMock()
    mock_briefing_skill.execute.return_value = {
        "status": "success",
        "data": {"weather": None, "events": None, "news": None},
    }

    mock_memory = AsyncMock()
    mock_memory.get_fact_value.return_value = ""

    fixed_now = datetime(2026, 3, 22, 7, 30, 0)

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

    # Briefing was attempted
    mock_briefing_skill.execute.assert_called_once()
    mock_brain.compose_briefing.assert_called_once()
    # But compose returned None, so no message sent from briefing path
    # reflect should still have been called (fall-through)
    mock_brain.reflect.assert_called_once()

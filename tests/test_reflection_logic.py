
import pytest
from core.agent import AgentBrain

# We can test the logic by mocking the class or just extracting the logic.
# Since the logic is inside reflect, we need to mock the dependencies to run reflect,
# OR we can just unit test the specific filtering logic if we extract it.
# However, to avoid refactoring right now, we will test `reflect` with mocked clients 
# and verify the output for different "silence" strings.

from unittest.mock import AsyncMock, patch, MagicMock
import datetime

@pytest.fixture
def mock_agent():
    with patch("core.agent.BaseSkill"), \
         patch("core.agent.IntrospectionSkill"), \
         patch("core.agent.RssReadSkill"), \
         patch("core.agent.RssListSkill"), \
         patch("core.agent.config.GROQ_API_KEY", "dummy_key"):
        agent = AgentBrain(provider="groq")
        return agent


def _make_groq_mock(content: str):
    """Helper: builds a mock Groq response with given content."""
    mock_message = MagicMock()
    mock_message.content = content
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_client = AsyncMock()
    mock_client.chat.completions.create.return_value = mock_response
    return mock_client


@pytest.mark.asyncio
@pytest.mark.parametrize("model_output,expected_result", [
    ("SILENCE", None),
    ("SIL", None),
    ("silence", None),
    ("SILENCE.", None),
    ("Sil", None),
    ("SILENCIO", None),
    ("NONE", None),
    ("NO", None),
    ("Nothing to report", "Nothing to report"),
    ("Hello user!", "Hello user!"),
])
async def test_reflection_filtering(mock_agent, model_output, expected_result):
    """Test that various 'silence' outputs are filtered correctly."""
    
    # Mock Config to ensure reflection is enabled and provider is set
    with patch("core.config.AI_PROVIDER", "groq"), \
         patch("core.config.GROQ_API_KEY", "valid_key"), \
         patch("core.config.GROQ_MODEL", "llama-test"), \
         patch("core.config.REFLECTION_ENABLED", True), \
         patch("core.config.REFLECTION_GREETING_HOUR_START", 7), \
         patch("core.config.REFLECTION_GREETING_HOUR_END", 9):
        
        mock_client = _make_groq_mock(model_output)

        # Mock groq.AsyncGroq
        with patch("groq.AsyncGroq", return_value=mock_client):
            result = await mock_agent.reflect({"context": "test", "hour": 8})
            assert result == expected_result


# ---------------------------------------------------------------------------
# NEW: Greeting deduplication tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_greeting_deduplication(mock_agent):
    """
    Second call with a greeting response on the SAME day must return None (SILENCE).
    """
    today = datetime.date.today()
    # Pre-seed: bot already sent a greeting today
    mock_agent._last_greeting_date = today

    mock_client = _make_groq_mock("Bom dia! Tudo bem?")

    with patch("core.config.AI_PROVIDER", "groq"), \
         patch("core.config.GROQ_API_KEY", "valid_key"), \
         patch("core.config.GROQ_MODEL", "llama-test"), \
         patch("core.config.REFLECTION_ENABLED", True), \
         patch("core.config.REFLECTION_GREETING_HOUR_START", 7), \
         patch("core.config.REFLECTION_GREETING_HOUR_END", 9), \
         patch("groq.AsyncGroq", return_value=mock_client):
        result = await mock_agent.reflect({"hour": 8})

    assert result is None, "Should be silenced because greeting was already sent today"


@pytest.mark.asyncio
async def test_greeting_outside_window_prompt(mock_agent):
    """
    When current hour is OUTSIDE the greeting window, the prompt should contain the
    FORBIDDEN clause so the LLM knows not to greet.
    """
    captured_calls = []

    async def capture_create(**kwargs):
        captured_calls.append(kwargs)
        mock_message = MagicMock()
        mock_message.content = "SILENCE"
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        return mock_response

    mock_client = AsyncMock()
    mock_client.chat.completions.create = capture_create

    with patch("core.config.AI_PROVIDER", "groq"), \
         patch("core.config.GROQ_API_KEY", "valid_key"), \
         patch("core.config.GROQ_MODEL", "llama-test"), \
         patch("core.config.REFLECTION_ENABLED", True), \
         patch("core.config.REFLECTION_GREETING_HOUR_START", 7), \
         patch("core.config.REFLECTION_GREETING_HOUR_END", 9), \
         patch("groq.AsyncGroq", return_value=mock_client):
        # hour=14 is outside 7-9 window
        await mock_agent.reflect({"hour": 14})

    assert captured_calls, "Model should have been called"
    system_msg = captured_calls[0]["messages"][0]["content"]
    assert "FORBIDDEN" in system_msg, (
        f"Prompt should mention FORBIDDEN for greetings outside the window, got: {system_msg[:300]}"
    )


@pytest.mark.asyncio
async def test_greeting_inside_window_prompt(mock_agent):
    """
    When current hour IS INSIDE the greeting window, the prompt should NOT contain
    FORBIDDEN and should allow a greeting.
    """
    captured_calls = []

    async def capture_create(**kwargs):
        captured_calls.append(kwargs)
        mock_message = MagicMock()
        mock_message.content = "SILENCE"
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        return mock_response

    mock_client = AsyncMock()
    mock_client.chat.completions.create = capture_create

    with patch("core.config.AI_PROVIDER", "groq"), \
         patch("core.config.GROQ_API_KEY", "valid_key"), \
         patch("core.config.GROQ_MODEL", "llama-test"), \
         patch("core.config.REFLECTION_ENABLED", True), \
         patch("core.config.REFLECTION_GREETING_HOUR_START", 7), \
         patch("core.config.REFLECTION_GREETING_HOUR_END", 9), \
         patch("groq.AsyncGroq", return_value=mock_client):
        # hour=8 is inside 7-9 window
        await mock_agent.reflect({"hour": 8})

    assert captured_calls, "Model should have been called"
    system_msg = captured_calls[0]["messages"][0]["content"]
    assert "FORBIDDEN" not in system_msg, (
        "Prompt should NOT mention FORBIDDEN when inside the greeting window"
    )
    assert "Bom dia" in system_msg, (
        "Prompt should mention 'Bom dia' as an allowed action inside the window"
    )


@pytest.mark.asyncio
async def test_greeting_resets_next_day(mock_agent):
    """
    Greeting should be allowed again on the NEXT calendar day.
    """
    yesterday = datetime.date.today() - datetime.timedelta(days=1)
    mock_agent._last_greeting_date = yesterday  # Greeted yesterday

    mock_client = _make_groq_mock("Bom dia! Nova manhã!")

    with patch("core.config.AI_PROVIDER", "groq"), \
         patch("core.config.GROQ_API_KEY", "valid_key"), \
         patch("core.config.GROQ_MODEL", "llama-test"), \
         patch("core.config.REFLECTION_ENABLED", True), \
         patch("core.config.REFLECTION_GREETING_HOUR_START", 7), \
         patch("core.config.REFLECTION_GREETING_HOUR_END", 9), \
         patch("groq.AsyncGroq", return_value=mock_client):
        result = await mock_agent.reflect({"hour": 8})

    assert result is not None, "Should allow greeting on a new day"
    assert "bom dia" in result.lower(), f"Expected a greeting, got: {result}"
    # State should now be updated to today
    assert mock_agent._last_greeting_date == datetime.date.today()

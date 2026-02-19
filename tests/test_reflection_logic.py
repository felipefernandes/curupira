
import pytest
from core.agent import AgentBrain

# We can test the logic by mocking the class or just extracting the logic.
# Since the logic is inside reflect, we need to mock the dependencies to run reflect,
# OR we can just unit test the specific filtering logic if we extract it.
# However, to avoid refactoring right now, we will test `reflect` with mocked clients 
# and verify the output for different "silence" strings.

from unittest.mock import AsyncMock, patch, MagicMock

@pytest.fixture
def mock_agent():
    with patch("core.agent.BaseSkill"), \
         patch("core.agent.IntrospectionSkill"), \
         patch("core.agent.RssReadSkill"), \
         patch("core.agent.RssListSkill"), \
         patch("core.agent.config.GROQ_API_KEY", "dummy_key"):
        agent = AgentBrain(provider="groq")
        return agent

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
         patch("core.config.REFLECTION_ENABLED", True):
        
        # Mock Client Response
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.choices[0].message.content = model_output
        mock_client.chat.completions.create.return_value = mock_response

        # Mock groq.AsyncGroq
        with patch("groq.AsyncGroq", return_value=mock_client):
            result = await mock_agent.reflect({"context": "test"})
            assert result == expected_result

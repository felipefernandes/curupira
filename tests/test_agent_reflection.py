import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from core.agent import AgentBrain
from core import config

@pytest.fixture
def mock_agent():
    """Fixture to create an AgentBrain instance with mocked dependencies."""
    with patch("core.agent.BaseSkill"), \
         patch("core.agent.IntrospectionSkill"), \
         patch("core.agent.RssReadSkill"), \
         patch("core.agent.RssListSkill"):
        agent = AgentBrain(provider="groq", api_key="dummy_key")
        agent._get_groq_client = MagicMock()
        agent._get_gemini_client = MagicMock()
        return agent

@pytest.mark.asyncio
async def test_reflect_groq_success(mock_agent):
    """Test reflect with Groq provider and valid key."""
    # Mock Config
    with patch("core.config.AI_PROVIDER", "groq"), \
         patch("core.config.GROQ_API_KEY", "valid_key"), \
         patch("core.config.GROQ_MODEL", "llama-test"), \
         patch("core.config.REFLECTION_ENABLED", True):
        
        # Mock Client Response
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "Hello Groq"
        mock_client.chat.completions.create.return_value = mock_response
        mock_agent._get_groq_client.return_value = mock_client

        # Execute
        result = await mock_agent.reflect({"context": "test"})

        # Assert
        assert result == "Hello Groq"
        mock_agent._get_groq_client.assert_called_once()
        mock_client.chat.completions.create.assert_called_once()
        assert mock_client.chat.completions.create.call_args[1]['model'] == "llama-test"

@pytest.mark.asyncio
async def test_reflect_groq_missing_key(mock_agent):
    """Test reflect with Groq provider but missing key."""
    with patch("core.config.AI_PROVIDER", "groq"), \
         patch("core.config.GROQ_API_KEY", ""):
        
        result = await mock_agent.reflect({})
        assert result is None
        # Verify no client was created
        mock_agent._get_groq_client.assert_not_called()

@pytest.mark.asyncio
async def test_reflect_gemini_success(mock_agent):
    """Test reflect with Gemini provider and valid key."""
    with patch("core.config.AI_PROVIDER", "gemini"), \
         patch("core.config.GEMINI_API_KEY", "valid_key"), \
         patch("core.config.GEMINI_MODEL", "gemini-test"), \
         patch("core.config.REFLECTION_ENABLED", True):
        
        # Mock Client Response
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.candidates[0].content.parts[0].text = "Hello Gemini"
        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)
        mock_agent._get_gemini_client.return_value = mock_client

        # Execute
        result = await mock_agent.reflect({"context": "test"})

        # Assert
        assert result == "Hello Gemini"
        mock_agent._get_gemini_client.assert_called_once()
        mock_client.aio.models.generate_content.assert_called_once()
        assert mock_client.aio.models.generate_content.call_args[1]['model'] == "gemini-test"

@pytest.mark.asyncio
async def test_reflect_gemini_missing_key(mock_agent):
    """Test reflect with Gemini provider but missing key."""
    with patch("core.config.AI_PROVIDER", "gemini"), \
         patch("core.config.GEMINI_API_KEY", ""):
        
        result = await mock_agent.reflect({})
        assert result is None
        mock_agent._get_gemini_client.assert_not_called()

@pytest.mark.asyncio
async def test_reflect_unknown_provider(mock_agent):
    """Test reflect with unknown provider."""
    with patch("core.config.AI_PROVIDER", "unknown_provider"):
        result = await mock_agent.reflect({})
        assert result is None

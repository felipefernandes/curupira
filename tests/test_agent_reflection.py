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
         patch("core.agent.RssListSkill"), \
         patch("core.agent.config.GROQ_API_KEY", "dummy_key"):
        agent = AgentBrain(provider="groq")
        # We don't need to mock _get_... anymore for reflect tests as reflect uses direct instantiation
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

        # Execute
        # Since it is a local import inside the function `from groq import AsyncGroq`, we must patch `groq.AsyncGroq`
        with patch("groq.AsyncGroq", return_value=mock_client) as MockGroqLib:
            result = await mock_agent.reflect({"context": "test"})

            # Assert
            assert result == "Hello Groq"
            MockGroqLib.assert_called_once_with(api_key="valid_key")
            mock_client.chat.completions.create.assert_called_once()
            assert mock_client.chat.completions.create.call_args[1]['model'] == "llama-test"

@pytest.mark.asyncio
async def test_reflect_groq_missing_key(mock_agent):
    """Test reflect with Groq provider but missing key."""
    with patch("core.config.AI_PROVIDER", "groq"), \
         patch("core.config.GROQ_API_KEY", ""):
        
        result = await mock_agent.reflect({})
        assert result is None

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

        # Mock google.genai.Client
        with patch("google.genai.Client", return_value=mock_client) as MockGenAI:
            # Execute
            result = await mock_agent.reflect({"context": "test"})

            # Assert
            assert result == "Hello Gemini"
            MockGenAI.assert_called_once_with(api_key="valid_key")
            mock_client.aio.models.generate_content.assert_called_once()
            assert mock_client.aio.models.generate_content.call_args[1]['model'] == "gemini-test"

@pytest.mark.asyncio
async def test_reflect_gemini_missing_key(mock_agent):
    """Test reflect with Gemini provider but missing key."""
    with patch("core.config.AI_PROVIDER", "gemini"), \
         patch("core.config.GEMINI_API_KEY", ""):
        
        result = await mock_agent.reflect({})
        assert result is None

@pytest.mark.asyncio
async def test_reflect_unknown_provider(mock_agent):
    """Test reflect with unknown provider."""
    with patch("core.config.AI_PROVIDER", "unknown_provider"):
        result = await mock_agent.reflect({})
        assert result is None

@pytest.mark.asyncio
async def test_reflect_cross_provider(mock_agent):
    """
    Test reflect when Agent is init with Gemini but Config wants to use Groq for reflection.
    Should use Groq Key, NOT Agent's Gemini Key.
    """
    # 1. Init agent with Gemini (so self.api_key = 'gemini_key')
    mock_agent.provider = 'gemini'
    mock_agent.api_key = 'gemini_key'

    # 2. Config says use Groq for reflection
    with patch("core.config.AI_PROVIDER", "groq"), \
         patch("core.config.GROQ_API_KEY", "groq_key_123"), \
         patch("core.config.GROQ_MODEL", "llama-test"), \
         patch("core.config.REFLECTION_ENABLED", True):
        
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "I am Groq"
        mock_client.chat.completions.create.return_value = mock_response

        # Mock groq.AsyncGroq
        with patch("groq.AsyncGroq", return_value=mock_client) as MockGroqLib:
            # Execute
            result = await mock_agent.reflect({"context": "test"})

            # Assert
            assert result == "I am Groq"
            
            # CRITICAL: Verify AsyncGroq was init with GROQ_API_KEY, not self.api_key
            # The assert_called_once_with checks the arguments passed to constructor
            MockGroqLib.assert_called_once_with(api_key="groq_key_123")

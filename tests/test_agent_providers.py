import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from core.agent import AgentBrain
import sys

@pytest.fixture
def agent():
    return AgentBrain("groq", "fake_key")

# --- Groq Client Tests ---

@pytest.mark.asyncio
async def test_get_groq_client_existing(agent):
    """Should return existing client if already set."""
    mock_client = AsyncMock()
    agent.client = mock_client
    assert agent._get_groq_client() == mock_client

@pytest.mark.asyncio
async def test_get_groq_client_new(agent):
    """Should create new AsyncGroq client if not set."""
    with patch("groq.AsyncGroq") as MockGroq:
        client = agent._get_groq_client()
        assert client is not None
        MockGroq.assert_called_once_with(api_key="fake_key")
        assert agent.client == client

@pytest.mark.asyncio
async def test_get_groq_client_import_error(agent):
    """Should handle ImportError gracefully."""
    with patch.dict(sys.modules, {"groq": None}):
        client = agent._get_groq_client()
        assert client is None

# --- Gemini Client Tests ---

@pytest.mark.asyncio
async def test_get_gemini_client_existing(agent):
    """Should return existing client if already set."""
    mock_client = MagicMock()
    agent.client = mock_client
    assert agent._get_gemini_client() == mock_client

@pytest.mark.asyncio
async def test_get_gemini_client_new(agent):
    """Should create new genai.Client if not set."""
    mock_genai = MagicMock()
    mock_client_cls = MagicMock()
    mock_genai.Client = mock_client_cls
    
    # Create a mock specifically for the google package that points to our mock_genai
    mock_google = MagicMock()
    mock_google.genai = mock_genai

    # We patch BOTH google and google.genai
    # This ensures 'from google import genai' works via sys.modules OR via updated google module
    with patch.dict(sys.modules, {"google": mock_google, "google.genai": mock_genai}):
        client = agent._get_gemini_client()
        
        assert client is not None
        # Verify constructor called with api_key
        mock_client_cls.assert_called_once_with(api_key="fake_key")
        # Verify agent.client updated
        assert agent.client == client

@pytest.mark.asyncio
async def test_get_gemini_client_import_error(agent):
    """Should handle ImportError gracefully."""
    with patch.dict(sys.modules, {"google.genai": None}):
        client = agent._get_gemini_client()
        assert client is None

# --- Tool Conversion Tests ---

def test_get_groq_tools(agent):
    """Should convert skills to Groq/OpenAI tool format."""
    mock_skill = MagicMock()
    mock_skill.name = "test_skill"
    mock_skill.description = "Test Description"
    mock_skill.parameters = {"param": "value"}
    
    agent.skills = {"test_skill": mock_skill}
    
    tools = agent._get_groq_tools()
    assert len(tools) == 1
    assert tools[0]["type"] == "function"
    assert tools[0]["function"]["name"] == "test_skill"
    assert tools[0]["function"]["description"] == "Test Description"
    assert tools[0]["function"]["parameters"] == {"param": "value"}

def test_get_gemini_tools_empty(agent):
    """Should return None if no skills."""
    agent.skills = {}
    assert agent._get_gemini_tools() is None

def test_get_gemini_tools_valid(agent):
    """Should convert skills to Gemini tool format."""
    mock_skill = MagicMock()
    mock_skill.name = "test_skill"
    mock_skill.description = "Test Description"
    mock_skill.parameters = {"param": "value"}
    agent.skills = {"test_skill": mock_skill}

    # Mock google.genai module and its types attribute
    mock_genai = MagicMock()
    mock_types = MagicMock()
    mock_genai.types = mock_types
    
    # Mock constructors
    mock_types.FunctionDeclaration = MagicMock()
    mock_types.Tool = MagicMock()

    # Pass the mock_genai as the module
    with patch.dict(sys.modules, {"google.genai": mock_genai}):
        tools = agent._get_gemini_tools()
        
        # Verify FunctionDeclaration called
        mock_types.FunctionDeclaration.assert_called_once_with(
            name="test_skill",
            description="Test Description",
            parameters={"param": "value"}
        )
        
        # Verify Tool initialized with declarations
        mock_types.Tool.assert_called_once()
        assert tools is not None
        assert len(tools) == 1

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from core.agent import AgentBrain
import sys

@pytest.fixture
def agent():
    with patch("core.agent.config.GROQ_API_KEY", "fake_key"):
        return AgentBrain("groq")

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
    
    # Create a mock specifically for the google package
    mock_google = MagicMock()
    # Assign genai as a child attribute (submodule)
    mock_google.genai = mock_genai

    # Patch only the top-level 'google' module. 
    # Python's import system will find 'genai' inside 'google' via the attribute lookup
    # or we can explicitly patch sys.modules['google'] and let it handle submodules.
    # Iara suggested patching 'google' and setting attribute.
    
    with patch.dict(sys.modules, {"google": mock_google}):
        client = agent._get_gemini_client()
        
        assert client is not None
        # Verify constructor called with api_key
        mock_client_cls.assert_called_once_with(api_key="fake_key")
        # Verify agent.client updated
        assert agent.client == client

@pytest.mark.asyncio
async def test_get_gemini_client_import_error(agent):
    """Should handle ImportError gracefully."""
    with patch.dict(sys.modules, {"google": None, "google.genai": None}):
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
    
    # Cleanup
    agent.skills = {}

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

    # Mock google package and genai submodule
    mock_google = MagicMock()
    mock_genai = MagicMock()
    
    # Link them
    mock_google.genai = mock_genai

    # Patch 'google' and 'google.genai'. 
    # This ensures consistent module resolution.
    with patch.dict(sys.modules, {"google": mock_google, "google.genai": mock_genai}):
        
        tools = agent._get_gemini_tools()
        
        # Access the auto-created 'types' mock from mock_genai
        mock_types = mock_genai.types

        # Verify FunctionDeclaration called on the auto-created mock
        mock_types.FunctionDeclaration.assert_called_once_with(
            name="test_skill",
            description="Test Description",
            parameters={"param": "value"}
        )
        
        # Verify Tool initialized with declarations
        mock_types.Tool.assert_called_once()
        assert tools is not None
        assert len(tools) == 1
        
        # Extra assertion for tool structure
        expected_declaration = mock_types.FunctionDeclaration.return_value
        args, kwargs = mock_types.Tool.call_args
        assert "function_declarations" in kwargs
        assert kwargs["function_declarations"] == [expected_declaration]
        
    # Validation: Reset skills to ensure isolation
    agent.skills = {}

# --- Audio Transcription Tests ---

@pytest.mark.asyncio
async def test_transcribe_audio_groq(agent):
    """Should successfully transcribe audio via Groq Whisper API."""
    mock_client = AsyncMock()
    mock_transcription = MagicMock()
    mock_transcription.text = "Transcrito com sucesso"
    
    # Mock nested client.audio.transcriptions.create
    mock_client.audio = MagicMock()
    mock_client.audio.transcriptions = MagicMock()
    mock_client.audio.transcriptions.create = AsyncMock(return_value=mock_transcription)
    
    agent.client = mock_client
    
    from unittest.mock import mock_open, ANY
    with patch("builtins.open", mock_open(read_data=b"audio_bytes")):
        with patch("core.agent.config.GROQ_WHISPER_MODEL", "whisper-large-v3-turbo"):
            text = await agent.transcribe_audio("dummy.ogg")
            assert text == "Transcrito com sucesso"
            mock_client.audio.transcriptions.create.assert_called_once_with(
                file=ANY,
                model="whisper-large-v3-turbo"
            )

@pytest.mark.asyncio
async def test_transcribe_audio_not_implemented():
    """Should raise NotImplementedError for non-groq providers."""
    with patch("core.agent.config.GEMINI_API_KEY", "fake_key"):
        gemini_agent = AgentBrain("gemini")
        with pytest.raises(NotImplementedError):
            await gemini_agent.transcribe_audio("dummy.ogg")

@pytest.mark.asyncio
async def test_transcribe_audio_groq_no_client(agent):
    """Should raise RuntimeError if Groq client cannot be initialized."""
    agent.client = None
    with patch.object(agent, "_get_groq_client", return_value=None):
        with pytest.raises(RuntimeError, match="Cliente Groq não inicializado"):
            await agent.transcribe_audio("dummy.ogg")

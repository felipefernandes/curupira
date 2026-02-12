import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from core.agent import AgentBrain

@pytest.fixture
def mock_groq_client():
    # Helper to ensure groq module exists for patching if not installed
    try:
        import groq
    except ImportError:
        # Create a mock groq module if it doesn't exist (though it should)
        import sys
        mock_groq = MagicMock()
        sys.modules["groq"] = mock_groq
    
    with patch("groq.AsyncGroq") as mock:
        client_instance = AsyncMock()
        mock.return_value = client_instance
        yield client_instance

@pytest.fixture
def agent():
    return AgentBrain("groq", "fake_key", "fake_model")

@pytest.mark.asyncio
async def test_agent_initialization(agent):
    assert agent.provider == "groq"
    assert agent.api_key == "fake_key"
    assert agent.model_name == "fake_model"
    assert agent.skills == {}

@pytest.mark.asyncio
async def test_register_skill(agent):
    mock_skill = MagicMock()
    mock_skill.name = "test_skill"
    
    agent.register_skill(mock_skill)
    assert "test_skill" in agent.skills
    assert agent.skills["test_skill"] == mock_skill

@pytest.mark.asyncio
async def test_process_message_empty(agent):
    """Test empty message returns ellipsis"""
    response = await agent.process("", {})
    assert response == "..."

@pytest.mark.asyncio
async def test_process_message_groq_flow(agent, mock_groq_client):
    """Test basic Groq optimization flow"""
    # Mock response
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Hello User"
    mock_response.choices[0].message.tool_calls = None
    
    # Mock client creation inside agent
    agent.client = mock_groq_client
    mock_groq_client.chat.completions.create.return_value = mock_response
    
    response = await agent.process("Hello", {"user_name": "TestUser"})
    
    assert response == "Hello User"
    mock_groq_client.chat.completions.create.assert_called_once()

@pytest.mark.asyncio
async def test_execute_tool_call_success(agent):
    """Test successful tool execution"""
    mock_skill = AsyncMock()
    mock_skill.name = "test_skill"
    mock_skill.execute.return_value = {"status": "ok"}
    
    agent.register_skill(mock_skill)
    
    result = await agent._execute_tool_call("test_skill", {"arg": 1}, {})
    
    assert '"status": "ok"' in result
    mock_skill.execute.assert_called_with({}, arg=1)

@pytest.mark.asyncio
async def test_execute_tool_call_not_found(agent):
    """Test execution of non-existent tool"""
    result = await agent._execute_tool_call("missing_tool", {}, {})
    assert "error" in result
    assert "not found" in result

@pytest.mark.asyncio
async def test_execute_tool_call_exception(agent):
    """Test handling of tool execution errors"""
    mock_skill = AsyncMock()
    mock_skill.name = "failing_tool"
    mock_skill.execute.side_effect = Exception("Boom")
    
    agent.register_skill(mock_skill)
@pytest.mark.asyncio
async def test_process_message_gemini_flow(agent):
    """Test basic Gemini flow"""
    # Switch provider
    agent.provider = "gemini"
    
    # Mock google.genai module
    mock_genai = MagicMock()
    mock_types = MagicMock()
    mock_genai.types = mock_types
    
    # Setup mock Part.from_text to return a mock part
    mock_part_instance = MagicMock()
    mock_types.Part.from_text.return_value = mock_part_instance
    
    # Setup mock Content
    mock_content_instance = MagicMock()
    mock_types.Content.return_value = mock_content_instance
    
    # Patch sys.modules to return our mock for google.genai
    with patch.dict("sys.modules", {"google.genai": mock_genai}):
        # Mock GenAI client
        mock_genai_client = MagicMock()
        mock_genai_client.aio.models.generate_content = AsyncMock()
        
        # Mock response
        mock_response = MagicMock()
        mock_candidate = MagicMock()
        mock_resp_part = MagicMock()
        mock_resp_part.text = "Hello from Gemini"
        mock_resp_part.function_call = None
        mock_candidate.content.parts = [mock_resp_part]
        mock_response.candidates = [mock_candidate]
        
        mock_genai_client.aio.models.generate_content.return_value = mock_response
        
        # Patch the _get_gemini_client method to return our mock
        with patch.object(agent, "_get_gemini_client", return_value=mock_genai_client):
            with patch.object(agent, "_get_gemini_tools", return_value=None):
                 response = await agent.process("Hello", {"user_name": "TestUser"})
        
        assert response == "Hello from Gemini"

@pytest.mark.asyncio
async def test_process_message_tool_execution(agent, mock_groq_client):
    """Test tool execution flow in Groq"""
    # Valid tool call
    mock_tool_call = MagicMock()
    mock_tool_call.id = "call_123"
    mock_tool_call.function.name = "test_skill"
    mock_tool_call.function.arguments = '{"arg": 1}'
    
    # Valid response message with tool call
    msg_with_tool = MagicMock()
    msg_with_tool.role = "assistant"
    msg_with_tool.content = None
    msg_with_tool.tool_calls = [mock_tool_call]
    
    # Final response message
    msg_final = MagicMock()
    msg_final.role = "assistant"
    msg_final.content = "Tool executed."
    msg_final.tool_calls = None
    
    # Mock client sequence: first returns tool call, then final response
    mock_response_1 = MagicMock()
    mock_response_1.choices = [MagicMock(message=msg_with_tool)]
    
    mock_response_2 = MagicMock()
    mock_response_2.choices = [MagicMock(message=msg_final)]
    
    # Mock skill
    mock_skill = AsyncMock()
    mock_skill.name = "test_skill"
    mock_skill.execute.return_value = {"status": "ok"}
    agent.register_skill(mock_skill)
    
    agent.client = mock_groq_client
    mock_groq_client.chat.completions.create.side_effect = [mock_response_1, mock_response_2]
    
    response = await agent.process("Run tool", {})
    
    assert response == "Tool executed."
    mock_skill.execute.assert_called_with({}, arg=1)


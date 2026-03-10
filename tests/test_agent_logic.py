import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
import sys
import os

# Add parent directory to path to import core
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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
    with patch("core.agent.config.GROQ_API_KEY", "fake_key"):
        return AgentBrain("groq", "fake_model")

@pytest.mark.asyncio
async def test_agent_initialization(agent):
    assert agent.provider == "groq"
    assert agent.api_key == "fake_key"
    assert agent.model_name == "fake_model"
    assert agent.skills == {} or "describe_capabilities" in agent.skills

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
async def test_groq_call_includes_temperature(agent, mock_groq_client):
    """temperature deve ser passado à API Groq com valor entre 0.0 e 1.0."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Olá!"
    mock_response.choices[0].message.tool_calls = None

    agent.client = mock_groq_client
    mock_groq_client.chat.completions.create.return_value = mock_response

    await agent.process("Olá", {"user_name": "TestUser"})

    call_kwargs = mock_groq_client.chat.completions.create.call_args.kwargs
    assert "temperature" in call_kwargs, "temperature deve ser passado à API"
    assert 0.0 <= call_kwargs["temperature"] <= 1.0, "temperature deve estar entre 0.0 e 1.0"

@pytest.mark.asyncio
async def test_execute_tool_call_success(agent):
    """Test successful tool execution"""
    mock_skill = AsyncMock()
    mock_skill.name = "test_skill"
    mock_skill.execute.return_value = {"status": "success", "data": {"status": "ok"}}
    
    agent.register_skill(mock_skill)
    
    result = await agent._execute_tool_call("test_skill", {"arg": 1}, {})
    
    assert '"status": "success"' in result
    assert '"data": {"status": "ok"}' in result
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
    
    # Create a dummy class for GenerateContentConfig so isinstance works
    class MockGenerateContentConfig:
        def __init__(self, tools=None, temperature=None, max_output_tokens=None):
            pass
            
    mock_types.GenerateContentConfig = MockGenerateContentConfig
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
    mock_skill.execute.return_value = {"data": {"status": "ok"}, "status": "success"}
    agent.register_skill(mock_skill)
    
    agent.client = mock_groq_client
    mock_groq_client.chat.completions.create.side_effect = [mock_response_1, mock_response_2]
    
    response = await agent.process("Run tool", {})
    
    assert response == "Tool executed."
    mock_skill.execute.assert_called_with({}, arg=1)


# --- _parse_failed_generation tests ---

class TestParseFailedGeneration:
    """Tests for AgentBrain._parse_failed_generation."""

    def test_parens_format(self):
        """Match <function=name(args)></function>."""
        gen = '<function=rss_read({"url": "https://example.com/feed", "limit": 5})></function>'
        result = AgentBrain._parse_failed_generation(gen)
        assert result is not None
        fn_name, fn_args = result
        assert fn_name == "rss_read"
        assert fn_args == {"url": "https://example.com/feed", "limit": 5}

    def test_angle_bracket_format(self):
        """Match <function=name>args</function>."""
        gen = '<function=get_weather>{"city": "SP"}</function>'
        result = AgentBrain._parse_failed_generation(gen)
        assert result is not None
        fn_name, fn_args = result
        assert fn_name == "get_weather"
        assert fn_args == {"city": "SP"}

    def test_colon_quote_format(self):
        """Match <function=name":args</function> (Llama colon-quote variant)."""
        gen = '<function=add_reminder":{"message": "Notícias", "when": "08:00"}</function>'
        result = AgentBrain._parse_failed_generation(gen)
        assert result is not None
        fn_name, fn_args = result
        assert fn_name == "add_reminder"
        assert fn_args == {"message": "Notícias", "when": "08:00"}

    def test_slash_format(self):
        """Match <function/name{args}></function> (novo formato)."""
        gen = '<function/google_calendar{"action": "add_calendar_event", "summary": "Teste"}></function>'
        result = AgentBrain._parse_failed_generation(gen)
        assert result is not None
        fn_name, fn_args = result
        assert fn_name == "google_calendar"
        assert fn_args == {"action": "add_calendar_event", "summary": "Teste"}

    def test_direct_json_format(self):
        """Match <function=name{"args"...}> (nome colado direto no JSON)."""
        gen = '<function=google_calendar{"action": "list_calendar_events", "time_range": "tomorrow"}</function>'
        result = AgentBrain._parse_failed_generation(gen)
        assert result is not None
        fn_name, fn_args = result
        assert fn_name == "google_calendar"
        assert fn_args == {"action": "list_calendar_events", "time_range": "tomorrow"}

    def test_double_equals_format(self):
        """Match <function=name={"args"...}> (dois sinais de igual)."""
        gen = '<function=google_calendar={"action": "setup_calendar", "auth_code": "4/0AX4XfWi9LfV4j8x8j8xj8"}</function>'
        result = AgentBrain._parse_failed_generation(gen)
        assert result is not None
        fn_name, fn_args = result
        assert fn_name == "google_calendar"
        assert fn_args == {"action": "setup_calendar", "auth_code": "4/0AX4XfWi9LfV4j8x8j8xj8"}

    def test_invalid_json_args(self):
        """Falls back to empty dict when args are not valid JSON."""
        gen = '<function=test(not-json)></function>'
        result = AgentBrain._parse_failed_generation(gen)
        assert result is not None
        fn_name, fn_args = result
        assert fn_name == "test"
        assert fn_args == {}

    def test_no_function_tag(self):
        """Returns None when string has no function tag."""
        assert AgentBrain._parse_failed_generation("just a normal error") is None

    def test_empty_string(self):
        assert AgentBrain._parse_failed_generation("") is None

    def test_none_input(self):
        assert AgentBrain._parse_failed_generation(None) is None


class TestSanitizeText:
    """Tests for AgentBrain._sanitize_text."""

    def test_sanitize_empty_string(self):
        """Testa o tratamento de strings vazias ou nulas."""
        assert AgentBrain._sanitize_text("") == ""
        assert AgentBrain._sanitize_text(None) == ""

    def test_sanitize_normal_text(self):
        """Testa o retorno inalterado de textos comuns."""
        assert AgentBrain._sanitize_text("Olá Curupira! Como você está?") == "Olá Curupira! Como você está?"

    def test_sanitize_with_newlines(self):
        """Testa a preservação de quebras de linha e tabs."""
        text = "Linha 1\nLinha 2\r\n\tTexto tabulado"
        assert AgentBrain._sanitize_text(text) == text

    def test_sanitize_removes_control_chars(self):
        """Testa a remoção de caracteres de controle invisíveis ou maliciosos."""
        text_with_null = "Texto\x00Com\x1b[31mLixo"
        # \x1b (ESC) e \x00 (NUL) não são imprimíveis nem \n, \r, \t
        sanitized = AgentBrain._sanitize_text(text_with_null)
        assert sanitized == "TextoCom[31mLixo"


@pytest.mark.asyncio
async def test_groq_failed_generation_recovery(agent, mock_groq_client):
    """Test that a Groq 400 with failed_generation recovers and retries."""
    # Simulate Groq 400 error with failed_generation
    error = Exception("tool_use_failed")
    error.body = {
        "error": {
            "message": "Failed to call a function.",
            "type": "invalid_request_error",
            "code": "tool_use_failed",
            "failed_generation": '<function=rss_read({"url": "https://example.com/feed", "limit": 5})></function>'
        }
    }

    # Second call succeeds with final text
    msg_final = MagicMock()
    msg_final.content = "Here are the latest articles."
    msg_final.tool_calls = None

    mock_response_ok = MagicMock()
    mock_response_ok.choices = [MagicMock(message=msg_final)]

    agent.client = mock_groq_client
    mock_groq_client.chat.completions.create.side_effect = [error, mock_response_ok]

    # Register the skill so _execute_tool_call works
    mock_skill = AsyncMock()
    mock_skill.name = "rss_read"
    mock_skill.description = "Read RSS"
    mock_skill.parameters = {"type": "object", "properties": {}, "required": []}
    mock_skill.execute.return_value = {"status": "success", "data": {"entries": []}}
    agent.register_skill(mock_skill)

    response = await agent.process("Read news", {})

    assert response == "Here are the latest articles."
    mock_skill.execute.assert_called_once_with({}, url="https://example.com/feed", limit=5)


@pytest.mark.asyncio
async def test_groq_generic_error_returns_fallback(agent, mock_groq_client):
    """Test that a generic Groq error (no failed_generation) returns the fallback message."""
    error = Exception("Network error")
    # No .body attribute → falls through to generic handler

    agent.client = mock_groq_client
    mock_groq_client.chat.completions.create.side_effect = error

    response = await agent.process("Hello", {})

    assert "problema" in response.lower() or "desculpe" in response.lower()


# --- bot_full_name identity tests (PR #99) ---

@pytest.mark.asyncio
async def test_process_uses_bot_full_name_with_surname(agent, mock_groq_client):
    """System prompt should include the full bot name when assistant_surname is set."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Sou o Curupira Prime."
    mock_response.choices[0].message.tool_calls = None

    agent.client = mock_groq_client
    mock_groq_client.chat.completions.create.return_value = mock_response

    await agent.process("Qual o seu nome?", {
        "user_name": "Felipe",
        "assistant_surname": "Prime",
    })

    call_kwargs = mock_groq_client.chat.completions.create.call_args.kwargs
    system_content = call_kwargs["messages"][0]["content"]
    assert "Curupira Prime" in system_content, (
        f"System prompt should contain 'Curupira Prime', got: {system_content[:300]}"
    )
    assert "Nunca diga que seu nome" in system_content


@pytest.mark.asyncio
async def test_process_uses_bot_name_without_surname(agent, mock_groq_client):
    """When assistant_surname is absent, bot identity should fall back to 'Curupira'."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Sou o Curupira."
    mock_response.choices[0].message.tool_calls = None

    agent.client = mock_groq_client
    mock_groq_client.chat.completions.create.return_value = mock_response

    await agent.process("Qual o seu nome?", {"user_name": "Felipe"})

    call_kwargs = mock_groq_client.chat.completions.create.call_args.kwargs
    system_content = call_kwargs["messages"][0]["content"]
    # Should say "Curupira" but NOT "Curupira " with a trailing space
    assert "Você é o Curupira," in system_content or 'é "Curupira"' in system_content, (
        f"System prompt should contain plain 'Curupira' identity, got: {system_content[:300]}"
    )


@pytest.mark.asyncio
async def test_process_facts_section_labels_user(agent, mock_groq_client):
    """FATOS section must state that the data describes the USER, not the bot."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "OK"
    mock_response.choices[0].message.tool_calls = None

    agent.client = mock_groq_client
    mock_groq_client.chat.completions.create.return_value = mock_response

    await agent.process("Olá", {"user_name": "Felipe", "user_facts": "- city: São Paulo"})

    call_kwargs = mock_groq_client.chat.completions.create.call_args.kwargs
    system_content = call_kwargs["messages"][0]["content"]
    assert "USUÁRIO" in system_content and "não você" in system_content, (
        "FATOS section should clarify that facts describe the USER, not the bot"
    )

# --- on_intermediate_reply tests (Issue #81) ---

@pytest.mark.asyncio
async def test_groq_intermediate_reply_is_called(agent, mock_groq_client):
    """Test that on_intermediate_reply is called when content is present alongside tool_calls in Groq."""
    
    mock_tool_call = MagicMock()
    mock_tool_call.id = "call_abc"
    mock_tool_call.function.name = "test_skill"
    mock_tool_call.function.arguments = '{"arg": 1}'
    
    msg_with_tool_and_content = MagicMock()
    msg_with_tool_and_content.role = "assistant"
    msg_with_tool_and_content.content = "I am doing that now..."
    msg_with_tool_and_content.tool_calls = [mock_tool_call]
    
    msg_final = MagicMock()
    msg_final.role = "assistant"
    msg_final.content = "Done!"
    msg_final.tool_calls = None
    
    mock_response_1 = MagicMock()
    mock_response_1.choices = [MagicMock(message=msg_with_tool_and_content)]
    
    mock_response_2 = MagicMock()
    mock_response_2.choices = [MagicMock(message=msg_final)]
    
    mock_skill = AsyncMock()
    mock_skill.name = "test_skill"
    mock_skill.execute.return_value = {"status": "ok"}
    agent.register_skill(mock_skill)
    
    agent.client = mock_groq_client
    mock_groq_client.chat.completions.create.side_effect = [mock_response_1, mock_response_2]
    
    mock_intermediate = AsyncMock()
    
    response = await agent.process("Do something", {}, on_intermediate_reply=mock_intermediate)
    
    assert response == "Done!"
    mock_intermediate.assert_called_once_with("I am doing that now...")

@pytest.mark.asyncio
async def test_gemini_intermediate_reply_is_called(agent):
    """Test that on_intermediate_reply is called when text is present alongside function_calls in Gemini."""
    agent.provider = "gemini"
    
    mock_genai = MagicMock()
    mock_types = MagicMock()
    
    class MockGenerateContentConfig:
        def __init__(self, tools=None, temperature=None, max_output_tokens=None):
            pass
            
    mock_types.GenerateContentConfig = MockGenerateContentConfig
    mock_types.Part.from_text.return_value = MagicMock()
    mock_types.Content.return_value = MagicMock()
    
    class MockGenerateContentResponse:
        @classmethod
        def from_function_response(cls, name, response):
            return MagicMock()
    
    mock_types.Part.from_function_response = MagicMock()    
    mock_genai.types = mock_types
    
    with patch.dict("sys.modules", {"google.genai": mock_genai}):
        mock_genai_client = MagicMock()
        mock_genai_client.aio.models.generate_content = AsyncMock()
        
        mock_response_1 = MagicMock()
        mock_candidate_1 = MagicMock()
        
        mock_part_text = MagicMock()
        mock_part_text.text = "Just a moment..."
        mock_part_text.function_call = None
        
        mock_part_fn = MagicMock()
        mock_part_fn.text = None
        mock_part_fn.function_call = MagicMock()
        mock_part_fn.function_call.name = "test_skill"
        mock_part_fn.function_call.args = {"arg": 1}
        
        mock_candidate_1.content.parts = [mock_part_text, mock_part_fn]
        mock_response_1.candidates = [mock_candidate_1]
        
        mock_response_2 = MagicMock()
        mock_candidate_2 = MagicMock()
        mock_final_part = MagicMock()
        mock_final_part.text = "Done Gemini!"
        mock_final_part.function_call = None
        mock_candidate_2.content.parts = [mock_final_part]
        mock_response_2.candidates = [mock_candidate_2]
        
        mock_genai_client.aio.models.generate_content.side_effect = [mock_response_1, mock_response_2]
        
        mock_skill = AsyncMock()
        mock_skill.name = "test_skill"
        mock_skill.execute.return_value = {"status": "ok"}
        agent.register_skill(mock_skill)
        
        with patch.object(agent, "_get_gemini_client", return_value=mock_genai_client):
            with patch.object(agent, "_get_gemini_tools", return_value=None):
                mock_intermediate = AsyncMock()
                response = await agent.process("Do Gemini", {}, on_intermediate_reply=mock_intermediate)
        
        assert response == "Done Gemini!"
        mock_intermediate.assert_called_once_with("Just a moment...")

@pytest.mark.asyncio
async def test_groq_intermediate_reply_exception(agent, mock_groq_client):
    """Test that if on_intermediate_reply raises an exception, the agent process continues."""
    mock_tool_call = MagicMock()
    mock_tool_call.id = "call_abc"
    mock_tool_call.function.name = "test_skill"
    mock_tool_call.function.arguments = '{"arg": 1}'
    
    msg_with_tool = MagicMock()
    msg_with_tool.role = "assistant"
    msg_with_tool.content = "Crash me"
    msg_with_tool.tool_calls = [mock_tool_call]
    
    msg_final = MagicMock()
    msg_final.role = "assistant"
    msg_final.content = "Done!"
    msg_final.tool_calls = None
    
    agent.client = mock_groq_client
    mock_groq_client.chat.completions.create.side_effect = [
        MagicMock(choices=[MagicMock(message=msg_with_tool)]),
        MagicMock(choices=[MagicMock(message=msg_final)])
    ]
    
    mock_skill = AsyncMock()
    mock_skill.name = "test_skill"
    mock_skill.execute.return_value = {"status": "ok"}
    agent.register_skill(mock_skill)
    
    mock_intermediate = AsyncMock(side_effect=Exception("UI error"))
    
    response = await agent.process("Do something", {}, on_intermediate_reply=mock_intermediate)
    
    assert response == "Done!"
    mock_intermediate.assert_called_once_with("Crash me")


@pytest.mark.asyncio
async def test_llama_xml_intermediate_reply_logic(agent, mock_groq_client):
    """Test the Llama-3 XML fallback logic and its interaction with on_intermediate_reply."""
    # Llama 3 style XML embedded in content with no tool_calls array
    msg_xml = MagicMock()
    msg_xml.role = "assistant"
    msg_xml.content = "Wait a second...\n<function=test_skill>{\"arg\": 1}</function>"
    msg_xml.tool_calls = None
    
    msg_final = MagicMock()
    msg_final.role = "assistant"
    msg_final.content = "Done XML!"
    msg_final.tool_calls = None
    
    agent.client = mock_groq_client
    mock_groq_client.chat.completions.create.side_effect = [
        MagicMock(choices=[MagicMock(message=msg_xml)]),
        MagicMock(choices=[MagicMock(message=msg_final)])
    ]
    
    mock_skill = AsyncMock()
    mock_skill.name = "test_skill"
    mock_skill.execute.return_value = {"status": "ok"}
    agent.register_skill(mock_skill)
    
    mock_intermediate = AsyncMock()
    
    response = await agent.process("Do XML", {}, on_intermediate_reply=mock_intermediate)

    assert response == "Done XML!"
    # It should extract the preamble before the <function=>
    mock_intermediate.assert_called_once_with("Wait a second...")


@pytest.mark.asyncio
async def test_llama_xml_slash_format_fallback(agent, mock_groq_client):
    """Test the <function/name{...}> fallback detection in Groq content."""
    # LLM returns malformed <function/name{...}> format in content
    msg_xml = MagicMock()
    msg_xml.role = "assistant"
    msg_xml.content = "Creating event...\n<function/google_calendar{\"action\": \"add_event\"}></function>"
    msg_xml.tool_calls = None

    msg_final = MagicMock()
    msg_final.role = "assistant"
    msg_final.content = "Event created!"
    msg_final.tool_calls = None

    agent.client = mock_groq_client
    mock_groq_client.chat.completions.create.side_effect = [
        MagicMock(choices=[MagicMock(message=msg_xml)]),
        MagicMock(choices=[MagicMock(message=msg_final)])
    ]

    mock_skill = AsyncMock()
    mock_skill.name = "google_calendar"
    mock_skill.execute.return_value = {"status": "ok"}
    agent.register_skill(mock_skill)

    mock_intermediate = AsyncMock()

    response = await agent.process("Add event", {}, on_intermediate_reply=mock_intermediate)

    assert response == "Event created!"
    # Should extract preamble before <function/
    mock_intermediate.assert_called_once_with("Creating event...")
    # Should execute the skill
    mock_skill.execute.assert_called_once()


@pytest.mark.asyncio
async def test_llama_xml_slash_format_with_invalid_json(agent, mock_groq_client):
    """Test <function/name{...}> with invalid JSON args - should fallback to empty dict."""
    msg_xml = MagicMock()
    msg_xml.role = "assistant"
    msg_xml.content = "<function/test_skill{not-valid-json}></function>"
    msg_xml.tool_calls = None

    msg_final = MagicMock()
    msg_final.role = "assistant"
    msg_final.content = "Done!"
    msg_final.tool_calls = None

    agent.client = mock_groq_client
    mock_groq_client.chat.completions.create.side_effect = [
        MagicMock(choices=[MagicMock(message=msg_xml)]),
        MagicMock(choices=[MagicMock(message=msg_final)])
    ]

    mock_skill = AsyncMock()
    mock_skill.name = "test_skill"
    mock_skill.execute.return_value = {"status": "ok"}
    agent.register_skill(mock_skill)

    response = await agent.process("Test", {})

    assert response == "Done!"
    # Should call with empty dict when JSON is invalid
    mock_skill.execute.assert_called_once_with({})


@pytest.mark.asyncio
async def test_llama_xml_slash_intermediate_reply_exception(agent, mock_groq_client):
    """Test that exception in on_intermediate_reply doesn't crash the agent (slash format)."""
    msg_xml = MagicMock()
    msg_xml.role = "assistant"
    msg_xml.content = "Preamble text\n<function/test_skill{\"arg\": 1}></function>"
    msg_xml.tool_calls = None

    msg_final = MagicMock()
    msg_final.role = "assistant"
    msg_final.content = "Done!"
    msg_final.tool_calls = None

    agent.client = mock_groq_client
    mock_groq_client.chat.completions.create.side_effect = [
        MagicMock(choices=[MagicMock(message=msg_xml)]),
        MagicMock(choices=[MagicMock(message=msg_final)])
    ]

    mock_skill = AsyncMock()
    mock_skill.name = "test_skill"
    mock_skill.execute.return_value = {"status": "ok"}
    agent.register_skill(mock_skill)

    # Callback that raises exception
    mock_intermediate = AsyncMock(side_effect=Exception("Callback crashed"))

    response = await agent.process("Test", {}, on_intermediate_reply=mock_intermediate)

    # Should continue despite callback exception
    assert response == "Done!"
    mock_skill.execute.assert_called_once()


@pytest.mark.asyncio
async def test_llama_xml_direct_json_format_fallback(agent, mock_groq_client):
    """Test the <function=name{"args"...}> fallback (nome colado direto no JSON)."""
    # LLM returns malformed <function=name{...}> format (no > between name and JSON)
    msg_xml = MagicMock()
    msg_xml.role = "assistant"
    msg_xml.content = '<function=google_calendar{"action": "list_events"}</function>'
    msg_xml.tool_calls = None

    msg_final = MagicMock()
    msg_final.role = "assistant"
    msg_final.content = "Events listed!"
    msg_final.tool_calls = None

    agent.client = mock_groq_client
    mock_groq_client.chat.completions.create.side_effect = [
        MagicMock(choices=[MagicMock(message=msg_xml)]),
        MagicMock(choices=[MagicMock(message=msg_final)])
    ]

    mock_skill = AsyncMock()
    mock_skill.name = "google_calendar"
    mock_skill.execute.return_value = {"status": "ok"}
    agent.register_skill(mock_skill)

    response = await agent.process("List events", {})

    assert response == "Events listed!"
    # Should execute the skill with parsed JSON args
    mock_skill.execute.assert_called_once_with({}, action="list_events")


@pytest.mark.asyncio
async def test_llama_xml_double_equals_format_fallback(agent, mock_groq_client):
    """Test the <function=name={"args"...}> fallback (dois sinais de igual)."""
    # LLM returns malformed <function=name={...}> format (double equals)
    msg_xml = MagicMock()
    msg_xml.role = "assistant"
    msg_xml.content = '<function=google_calendar={"action": "setup_calendar"}</function>'
    msg_xml.tool_calls = None

    msg_final = MagicMock()
    msg_final.role = "assistant"
    msg_final.content = "Calendar configured!"
    msg_final.tool_calls = None

    agent.client = mock_groq_client
    mock_groq_client.chat.completions.create.side_effect = [
        MagicMock(choices=[MagicMock(message=msg_xml)]),
        MagicMock(choices=[MagicMock(message=msg_final)])
    ]

    mock_skill = AsyncMock()
    mock_skill.name = "google_calendar"
    mock_skill.execute.return_value = {"status": "ok"}
    agent.register_skill(mock_skill)

    response = await agent.process("Setup calendar", {})

    assert response == "Calendar configured!"
    # Should execute the skill with parsed JSON args
    mock_skill.execute.assert_called_once_with({}, action="setup_calendar")


@pytest.mark.asyncio
async def test_gemini_intermediate_reply_exception(agent):
    """Test that if on_intermediate_reply raises an exception in Gemini, the process continues."""
    agent.provider = "gemini"
    
    mock_genai = MagicMock()
    mock_types = MagicMock()
    
    class MockGenerateContentConfig:
        def __init__(self, tools=None, temperature=None, max_output_tokens=None):
            pass
            
    mock_types.GenerateContentConfig = MockGenerateContentConfig
    mock_types.Part.from_text.return_value = MagicMock()
    mock_types.Content.return_value = MagicMock()
    
    mock_types.Part.from_function_response = MagicMock()    
    mock_genai.types = mock_types
    
    with patch.dict("sys.modules", {"google.genai": mock_genai}):
        mock_genai_client = MagicMock()
        mock_genai_client.aio.models.generate_content = AsyncMock()
        
        mock_candidate_1 = MagicMock()
        mock_part_text = MagicMock()
        mock_part_text.text = "Crash Gemini"
        mock_part_text.function_call = None
        
        mock_part_fn = MagicMock()
        mock_part_fn.text = None
        mock_part_fn.function_call = MagicMock()
        mock_part_fn.function_call.name = "test_skill"
        mock_part_fn.function_call.args = {"arg": 1}
        
        mock_candidate_1.content.parts = [mock_part_text, mock_part_fn]
        
        mock_candidate_2 = MagicMock()
        mock_final_part = MagicMock()
        mock_final_part.text = "Done Gemini!"
        mock_final_part.function_call = None
        mock_candidate_2.content.parts = [mock_final_part]
        
        mock_genai_client.aio.models.generate_content.side_effect = [
            MagicMock(candidates=[mock_candidate_1]),
            MagicMock(candidates=[mock_candidate_2])
        ]
        
        mock_skill = AsyncMock()
        mock_skill.name = "test_skill"
        mock_skill.execute.return_value = {"status": "ok"}
        agent.register_skill(mock_skill)
        
        with patch.object(agent, "_get_gemini_client", return_value=mock_genai_client):
            with patch.object(agent, "_get_gemini_tools", return_value=None):
                mock_intermediate = AsyncMock(side_effect=Exception("UI Error Gemini"))
                response = await agent.process("Do Gemini", {}, on_intermediate_reply=mock_intermediate)
        
        assert response == "Done Gemini!"
        mock_intermediate.assert_called_once_with("Crash Gemini")

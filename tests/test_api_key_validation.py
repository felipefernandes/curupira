import pytest
import os
import sys

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent import AgentBrain

def test_api_key_validation_empty_string():
    """Valida que API keys vazias são rejeitadas."""
    # Limpar ambiente primeiro
    if "GROQ_API_KEY" in os.environ:
        del os.environ["GROQ_API_KEY"]
        
    with pytest.raises(ValueError, match="API key inválida ou ausente"):
        AgentBrain("groq", api_key="")

def test_api_key_validation_whitespace():
    """Valida que API keys com apenas espaços são rejeitadas."""
    with pytest.raises(ValueError, match="API key inválida ou ausente"):
        AgentBrain("groq", api_key="   ")

def test_api_key_validation_none_no_env():
    """Valida que API key None sem variável de ambiente é rejeitada."""
    # Ensure env var is gone
    if "GROQ_API_KEY" in os.environ:
        del os.environ["GROQ_API_KEY"]
        
    with pytest.raises(ValueError, match="API key inválida ou ausente"):
        AgentBrain("groq", api_key=None)

def test_api_key_validation_success():
    """Valida que API key válida é aceita."""
    agent = AgentBrain("groq", api_key="valid_key")
    assert agent.api_key == "valid_key"


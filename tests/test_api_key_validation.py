import pytest
import os
import sys
from unittest.mock import patch

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.agent import AgentBrain


def test_api_key_validation_empty_string():
    """Valida que API keys vazias no ambiente são rejeitadas."""
    with patch.dict(os.environ, {"GROQ_API_KEY": ""}, clear=True):
        # Also need to patch config if it was already loaded
        with patch("core.agent.config.GROQ_API_KEY", ""):
            with pytest.raises(ValueError, match="API key inválida ou ausente"):
                AgentBrain("groq")

def test_api_key_validation_whitespace():
    """Valida que API keys com apenas espaços no ambiente são rejeitadas."""
    with patch.dict(os.environ, {"GROQ_API_KEY": "   "}, clear=True):
        with patch("core.agent.config.GROQ_API_KEY", "   "):
            with pytest.raises(ValueError, match="API key inválida ou ausente"):
                AgentBrain("groq")

def test_api_key_validation_none_no_env():
    """Valida que falta de variável de ambiente causa erro."""
    # Ensure env var is missing
    with patch.dict(os.environ, {}, clear=True):
         # We must ensure config doesn't have it either (mocking config import might be cleaner but this works)
         with patch("core.agent.config.GROQ_API_KEY", None):
            with pytest.raises(ValueError, match="API key inválida ou ausente"):
                AgentBrain("groq")

def test_api_key_validation_success():
    """Valida que API key válida no config é aceita."""
    fake_key = "sk-antigravity-test-key-123456789"
    
    # We need to patch the config module where AgentBrain imports it.
    # core.agent imports config. So we patch core.agent.config.GROQ_API_KEY
    with patch("core.agent.config.GROQ_API_KEY", fake_key):
        agent = AgentBrain("groq")
        assert agent.api_key == fake_key



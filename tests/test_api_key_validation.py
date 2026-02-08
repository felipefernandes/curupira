import pytest
import os
import sys

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent import AgentBrain


def test_api_key_validation_empty_string(monkeypatch):
    """Valida que API keys vazias são rejeitadas."""
    # Garante que não pega do ambiente
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
        
    with pytest.raises(ValueError, match="API key inválida ou ausente"):
        AgentBrain("groq", api_key="")

def test_api_key_validation_whitespace(monkeypatch):
    """Valida que API keys com apenas espaços são rejeitadas."""
    # Garante que não pega do ambiente
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    with pytest.raises(ValueError, match="API key inválida ou ausente"):
        AgentBrain("groq", api_key="   ")

def test_api_key_validation_none_no_env(monkeypatch):
    """Valida que API key None sem variável de ambiente é rejeitada."""
    # Simula ambiente limpo sem a chave
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
        
    with pytest.raises(ValueError, match="API key inválida ou ausente"):
        AgentBrain("groq", api_key=None)

def test_api_key_validation_success():
    """Valida que API key válida é aceita."""
    # Usa um padrão de chave realista (fictício) para evitar 'valid_key' genérico
    fake_key = "sk-antigravity-test-key-123456789"
    agent = AgentBrain("groq", api_key=fake_key)
    assert agent.api_key == fake_key



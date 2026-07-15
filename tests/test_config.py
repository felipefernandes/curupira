import os
import sys
import importlib
from unittest.mock import patch, mock_open

# Add parent directory to path to import core
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_config_defaults(monkeypatch):
    """Test default values when env vars are missing"""
    # Clear relevant env vars
    monkeypatch.delenv("TELEGRAM_TOKEN", raising=False)
    monkeypatch.delenv("AI_PROVIDER", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("AUTHORIZED_USER_ID", raising=False)
    monkeypatch.delenv("MCP_SERVERS_CONFIG", raising=False)
    
    # Reload config to apply env changes, but MOCK load_dotenv to avoid reading .env file
    # AND mock is_file to avoid loading mcp.json
    with patch("dotenv.load_dotenv"), patch("pathlib.Path.is_file", return_value=False):
        if 'core.config' in sys.modules:
            importlib.reload(sys.modules['core.config'])
        from core import config
    
    # Check defaults
    assert config.HEARTBEAT_INTERVAL == 1800 # 30 * 60
    assert config.AI_PROVIDER == 'groq' # Default
    assert config.AUTHORIZED_USER_ID == 0 
    assert config.MCP_SERVERS == {}

def test_config_env_vars(monkeypatch):
    """Test loading values from environment variables"""
    monkeypatch.setenv("TELEGRAM_TOKEN", "test_token")
    monkeypatch.setenv("AI_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "test_gemini_key")
    monkeypatch.setenv("AUTHORIZED_USER_ID", "12345")
    
    # Reload config
    if 'core.config' in sys.modules:
        importlib.reload(sys.modules['core.config'])
    from core import config
    
    assert config.TELEGRAM_TOKEN == "test_token"
    assert config.AI_PROVIDER == "gemini"
    assert config.GEMINI_API_KEY == "test_gemini_key"
    assert config.AUTHORIZED_USER_ID == 12345

def test_config_invalid_user_id(monkeypatch):
    """Test handling of invalid AUTHORIZED_USER_ID"""
    monkeypatch.setenv("AUTHORIZED_USER_ID", "invalid_int")
    
    if 'core.config' in sys.modules:
        importlib.reload(sys.modules['core.config'])
    from core import config
    
    assert config.AUTHORIZED_USER_ID == 0

def test_mcp_config_file_loading(monkeypatch):
    """Test loading MCP config from file"""
    mock_mcp_config = '{"server1": {"command": "echo", "args": ["hello"]}}'
    
    with patch("builtins.open", mock_open(read_data=mock_mcp_config)):
        with patch("pathlib.Path.is_file", return_value=True):
             if 'core.config' in sys.modules:
                importlib.reload(sys.modules['core.config'])
             from core import config
             
             assert "server1" in config.MCP_SERVERS
             assert config.MCP_SERVERS["server1"]["command"] == "echo"

def test_mcp_config_env_fallback(monkeypatch):
    """Test loading MCP config from env var when file is missing"""
    mock_env_config = '{"server2": {"command": "python"}}'
    monkeypatch.setenv("MCP_SERVERS_CONFIG", mock_env_config)

    with patch("pathlib.Path.is_file", return_value=False):
        if 'core.config' in sys.modules:
            importlib.reload(sys.modules['core.config'])
        from core import config

        assert "server2" in config.MCP_SERVERS
        assert config.MCP_SERVERS["server2"]["command"] == "python"


# --- RSS Configuration Tests ---

def test_rss_feeds_defaults(monkeypatch):
    """Test RSS_FEEDS uses defaults when env var is not set."""
    monkeypatch.delenv("RSS_FEEDS_JSON", raising=False)

    with patch("dotenv.load_dotenv"), patch("pathlib.Path.is_file", return_value=False):
        if 'core.config' in sys.modules:
            importlib.reload(sys.modules['core.config'])
        from core import config

    assert "G1" in config.RSS_FEEDS
    assert "TechCrunch" in config.RSS_FEEDS
    assert "Hacker News" in config.RSS_FEEDS


def test_rss_feeds_from_env(monkeypatch):
    """Test RSS_FEEDS loads from RSS_FEEDS_JSON env var."""
    custom = '{"MyBlog": "https://myblog.com/feed"}'
    monkeypatch.setenv("RSS_FEEDS_JSON", custom)

    with patch("dotenv.load_dotenv"), patch("pathlib.Path.is_file", return_value=False):
        if 'core.config' in sys.modules:
            importlib.reload(sys.modules['core.config'])
        from core import config

    assert config.RSS_FEEDS == {"MyBlog": "https://myblog.com/feed"}


def test_rss_feeds_invalid_json(monkeypatch):
    """Test RSS_FEEDS falls back to defaults on invalid JSON."""
    monkeypatch.setenv("RSS_FEEDS_JSON", "not-json{{{")

    with patch("dotenv.load_dotenv"), patch("pathlib.Path.is_file", return_value=False):
        if 'core.config' in sys.modules:
            importlib.reload(sys.modules['core.config'])
        from core import config

    assert "G1" in config.RSS_FEEDS


def test_rss_feeds_wrong_type(monkeypatch):
    """Test RSS_FEEDS falls back to defaults when JSON is not a dict."""
    monkeypatch.setenv("RSS_FEEDS_JSON", '["a", "b"]')

    with patch("dotenv.load_dotenv"), patch("pathlib.Path.is_file", return_value=False):
        if 'core.config' in sys.modules:
            importlib.reload(sys.modules['core.config'])
        from core import config

    assert "G1" in config.RSS_FEEDS


def test_ai_news_config_from_env(monkeypatch):
    """Test AI_NEWS settings load from env variables."""
    monkeypatch.setenv("AI_NEWS_API_URL", "https://custom-ai-news.com/")
    monkeypatch.setenv("AI_NEWS_FETCH_SOURCES", "news,github")
    monkeypatch.setenv("AI_NEWS_LIMIT_PER_SOURCE", "5")
    monkeypatch.setenv("AI_NEWS_TIMEOUT", "45.0")

    with patch("dotenv.load_dotenv"), patch("pathlib.Path.is_file", return_value=False):
        if 'core.config' in sys.modules:
            importlib.reload(sys.modules['core.config'])
        from core import config

    assert config.AI_NEWS_API_URL == "https://custom-ai-news.com"
    assert config.AI_NEWS_FETCH_SOURCES == ["news", "github"]
    assert config.AI_NEWS_LIMIT_PER_SOURCE == 5
    assert config.AI_NEWS_TIMEOUT == 45.0


def test_ai_news_config_invalid_limit(monkeypatch):
    """Test AI_NEWS settings fallback on invalid limit and timeout."""
    monkeypatch.setenv("AI_NEWS_LIMIT_PER_SOURCE", "invalid_int")
    monkeypatch.setenv("AI_NEWS_TIMEOUT", "invalid_float")

    with patch("dotenv.load_dotenv"), patch("pathlib.Path.is_file", return_value=False):
        if 'core.config' in sys.modules:
            importlib.reload(sys.modules['core.config'])
        from core import config

    assert config.AI_NEWS_LIMIT_PER_SOURCE == 3
    assert config.AI_NEWS_TIMEOUT == 60.0

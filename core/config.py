import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Heartbeat Interval (in seconds) - Default: 30 minutes
HEARTBEAT_INTERVAL = 30 * 60

# Telegram Configuration
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')

# AI Provider Configuration
# Options: 'gemini', 'groq'
AI_PROVIDER = os.getenv('AI_PROVIDER', 'groq').lower()

# Gemini Configuration
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# Groq Configuration
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
# GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

# Retry Configuration
# Maximum number of retries for 429/ResourceExhausted errors
RETRY_ATTEMPTS = int(os.getenv("RETRY_ATTEMPTS", 3))
# Initial delay in seconds for exponential backoff (jitter is added automatically)
RETRY_INITIAL_DELAY = float(os.getenv("RETRY_INITIAL_DELAY", 2.0))

# Security Configuration
try:
    AUTHORIZED_USER_ID = int(os.getenv('AUTHORIZED_USER_ID', 0))
except ValueError:
    AUTHORIZED_USER_ID = 0

# Validation
if not TELEGRAM_TOKEN:
    print("WARNING: TELEGRAM_TOKEN is missing!")

if AUTHORIZED_USER_ID == 0:
    print("WARNING: AUTHORIZED_USER_ID is not set!")

if AI_PROVIDER == 'gemini' and not GEMINI_API_KEY:
    print("WARNING: GEMINI_API_KEY is missing but provider is set to 'gemini'!")

if AI_PROVIDER == 'groq' and not GROQ_API_KEY:
    print("WARNING: GROQ_API_KEY is missing but provider is set to 'groq'!")

# MCP Configuration
import json
import logging
from pathlib import Path
from typing import Dict, Any

# Configure logger for this module
logger = logging.getLogger(__name__)

# Define path for mcp.json in the project root (one level up from core/)
BASE_DIR = Path(__file__).resolve().parent.parent
MCP_CONFIG_FILE = BASE_DIR / "mcp.json"

MCP_SERVERS: Dict[str, Any] = {}

if MCP_CONFIG_FILE.is_file():
    try:
        with open(MCP_CONFIG_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, dict):
                MCP_SERVERS = data
                logger.info(f"Loaded MCP configuration from {MCP_CONFIG_FILE}")
            else:
                logger.error(f"{MCP_CONFIG_FILE} content must be a dictionary, got {type(data).__name__}")
    except json.JSONDecodeError:
        logger.error(f"{MCP_CONFIG_FILE} is not valid JSON!")
    except Exception as e:
        logger.error(f"Error loading {MCP_CONFIG_FILE}: {e}")
else:
    # Fallback to current Env Var method
    MCP_SERVERS_CONFIG = os.getenv('MCP_SERVERS_CONFIG', '{}')
    try:
        data = json.loads(MCP_SERVERS_CONFIG)
        if isinstance(data, dict):
            MCP_SERVERS = data
        else:
             logger.warning("MCP_SERVERS_CONFIG must be a dictionary! Defaulting to empty.")
    except json.JSONDecodeError:
        logger.warning("MCP_SERVERS_CONFIG is not valid JSON!")
    except Exception as e:
        logger.error(f"Error parsing MCP_SERVERS_CONFIG: {e}")

# RSS Configuration
RSS_FEEDS_DEFAULT: Dict[str, str] = {
    "G1": "https://g1.globo.com/rss/g1/",
    "G1 Brasil": "https://g1.globo.com/rss/g1/brasil/",
    "G1 Tecnologia": "https://g1.globo.com/rss/g1/tecnologia/",
    "Folha de São Paulo": "https://feeds.folha.uol.com.br/emcimadahora/rss091.xml",
    "TechCrunch": "https://techcrunch.com/feed/",
    "Hacker News": "https://hnrss.org/frontpage",
}

_rss_env = os.getenv("RSS_FEEDS_JSON", "")
if _rss_env.strip():
    try:
        _parsed = json.loads(_rss_env)
        if isinstance(_parsed, dict):
            RSS_FEEDS = _parsed
        else:
            logger.warning("RSS_FEEDS_JSON must be a dict. Using defaults.")
            RSS_FEEDS = RSS_FEEDS_DEFAULT.copy()
    except json.JSONDecodeError:
        logger.warning("RSS_FEEDS_JSON is not valid JSON. Using defaults.")
        RSS_FEEDS = RSS_FEEDS_DEFAULT.copy()
    except Exception as e:
        logger.error(f"Error parsing RSS_FEEDS_JSON: {e}. Using defaults.")
        RSS_FEEDS = RSS_FEEDS_DEFAULT.copy()
else:
    RSS_FEEDS = RSS_FEEDS_DEFAULT.copy()

# Heartbeat Reflection Configuration
REFLECTION_ENABLED = os.getenv("REFLECTION_ENABLED", "true").lower() == "true"
REFLECTION_MODEL = os.getenv("REFLECTION_MODEL", "llama-3.3-70b-versatile") # Default to fast/smart Groq model

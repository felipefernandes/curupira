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
GEMINI_MODEL = "gemini-2.0-flash"

# Groq Configuration
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
GROQ_MODEL = "llama-3.3-70b-versatile"

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
from pathlib import Path

# Define path for mcp.json in the project root (one level up from core/)
BASE_DIR = Path(__file__).resolve().parent.parent
MCP_CONFIG_FILE = BASE_DIR / "mcp.json"

MCP_SERVERS = {}

if MCP_CONFIG_FILE.is_file():
    try:
        with open(MCP_CONFIG_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, dict):
                MCP_SERVERS = data
                print(f"Loaded MCP configuration from {MCP_CONFIG_FILE}")
            else:
                print(f"ERROR: {MCP_CONFIG_FILE} content must be a dictionary, got {type(data).__name__}")
    except json.JSONDecodeError:
        print(f"ERROR: {MCP_CONFIG_FILE} is not valid JSON!")
    except Exception as e:
        print(f"ERROR loading {MCP_CONFIG_FILE}: {e}")
else:
    # Fallback to current Env Var method
    MCP_SERVERS_CONFIG = os.getenv('MCP_SERVERS_CONFIG', '{}')
    try:
        MCP_SERVERS = json.loads(MCP_SERVERS_CONFIG)
        if not isinstance(MCP_SERVERS, dict):
            print("WARNING: MCP_SERVERS_CONFIG must be a dictionary! Defaulting to empty.")
            MCP_SERVERS = {}
    except json.JSONDecodeError:
        print("WARNING: MCP_SERVERS_CONFIG is not valid JSON!")


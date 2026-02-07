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

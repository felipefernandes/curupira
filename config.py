import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Telegram Configuration
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')

# Gemini Configuration
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# Security Configuration
try:
    AUTHORIZED_USER_ID = int(os.getenv('AUTHORIZED_USER_ID', 0))
except ValueError:
    AUTHORIZED_USER_ID = 0

if not TELEGRAM_TOKEN or not GEMINI_API_KEY or AUTHORIZED_USER_ID == 0:
    print("WARNING: Missing required environment variables. Please check .env file.")

import os

# Set dummy environment variables to prevent module-level code (like AgentBrain
# instantiation in bot.py) from crashing during pytest collection on CI environments.
os.environ["GROQ_API_KEY"] = "dummy_groq_key_for_tests"
os.environ["GEMINI_API_KEY"] = "dummy_gemini_key_for_tests"
os.environ["TELEGRAM_TOKEN"] = "dummy_telegram_token_for_tests"

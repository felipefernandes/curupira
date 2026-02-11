
import asyncio
import logging
import sys
import os

# Add parent directory to path (curupira root)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import directly since we are running from project root context in sys.path
from core.agent import AgentBrain
from skills.reminders import ReminderManager, AddReminderSkill
from skills.memory import MemoryManager
from core import config

# Setup Mock Logger
logging.basicConfig(level=logging.INFO)

async def main():
    print("--- Starting AgentBrain Test ---")
    await MemoryManager().init_db()
    
    # Init Brain
    print(f"Provider: {config.AI_PROVIDER}")
    brain = AgentBrain(config.AI_PROVIDER, config.GEMINI_API_KEY if config.AI_PROVIDER == 'gemini' else config.GROQ_API_KEY, config.GEMINI_MODEL if config.AI_PROVIDER == 'gemini' else config.GROQ_MODEL)
    
    # Init Skills
    # Mock ReminderManager if needed, or use real one (sqlite file will be created)
    rm = ReminderManager() # Uses memory/db
    brain.register_skill(AddReminderSkill(rm))
    
    # Test 1: Simple Chat
    context = {"user_id": 123, "user_name": "Tester", "job_queue": None}
    print("\n--- Test 1: Chat ---")
    print("User: Olá, quem é você?")
    response = await brain.process("Olá, quem é você?", context)
    print(f"Agent: {response}")
    
    # Test 2: Tool Call (Reminder)
    print("\n--- Test 2: Reminder Tool ---")
    print("User: Me lembre de beber água em 10 minutos.")
    response = await brain.process("Me lembre de beber água em 10 minutos.", context)
    print(f"Agent: {response}")

if __name__ == "__main__":
    asyncio.run(main())

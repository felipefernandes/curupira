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
from dotenv import load_dotenv

# Load environment variables (crucial for MCP server token)
load_dotenv()


# Setup logging
logging.basicConfig(level=logging.INFO)
# Enable DEBUG for MCP Client to trace connection issues
logging.getLogger("MCPClient").setLevel(logging.DEBUG)


async def main():
    print("--- Starting AgentBrain Test ---")
    await MemoryManager().init_db()
    
    # Init Brain
    print(f"Provider: {config.AI_PROVIDER}")
    
    # Use explicit groq for consistency in manual test
    agent = AgentBrain(provider="groq", model_name="llama3-8b-8192")
    
    # Initialize MCP Clients (CRITICAL for verifying MCP Server)
    await agent.start_mcp_clients()
    
    # Register Mock Skills
    rm = ReminderManager() # Uses memory/db
    agent.register_skill(AddReminderSkill(rm))
    
    # Test 1: Simple Chat
    context = {"user_id": 123, "user_name": "Tester", "job_queue": None}
    try:
        response = await agent.process("Olá, quem é você?", context)
        print(f"Agent: {response}")
    except Exception as e:
        print(f"Error in chat processing: {e}")

    # Verify Skills
    print(f"\nRegistered Skills: {list(agent.skills.keys())}")

    
    # Optional: Test detailed tool call if needed, but chat covers tool injection
    
    # Cleanup
    await agent.shutdown()

if __name__ == "__main__":
    asyncio.run(main())

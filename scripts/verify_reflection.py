import asyncio
import os
import sys
import json
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from core import config, agent

async def main():
    print("🧪 Testing Reflection Logic...")
    
    # Force Enable
    config.REFLECTION_ENABLED = True
    
    # Initialize Brain (Mocking provider if needed, but we want real API test)
    print(f"Provider: {config.AI_PROVIDER}")
    brain = agent.AgentBrain(config.AI_PROVIDER)
    
    # Case 1: Normal Context (Should be SILENT)
    print("\n[Case 1] Normal Context")
    ctx_normal = {
        "time": "10:00:00",
        "hardware": {"cpu_percent": 10, "ram_percent": 20, "temp": 45}
    }
    res_normal = await brain.reflect(ctx_normal)
    print(f"Result: {res_normal}")
    
    # Case 2: Critical Context (Should TRIGGER)
    print("\n[Case 2] Critical Context")
    ctx_critical = {
        "time": "10:00:00",
        "hardware": {"cpu_percent": 95, "ram_percent": 98, "temp": 85} # High Temp
    }
    res_critical = await brain.reflect(ctx_critical)
    print(f"Result: {res_critical}")

    if res_normal is None and res_critical is not None:
        print("\n✅ Verification PASSED: Silence maintained for normal, Alert triggered for critical.")
    else:
        print("\n❌ Verification FAILED: Logic did not behave as expected.")

if __name__ == "__main__":
    asyncio.run(main())

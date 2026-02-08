import asyncio
import sys
import os

# Ensure we can import from project root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from skills.hardware import HardwareMonitoringSkill

async def test_hardware_skill():
    print("Testing HardwareMonitoringSkill...")
    skill = HardwareMonitoringSkill()
    
    # Context mimicking AgentBrain
    context = {"user_id": 12345}
    
    try:
        result = await skill.execute(context)
        print("\n--- Result ---")
        print(result.get('summary'))
        print("\n--- Raw Metrics ---")
        print(result.get('metrics'))
        
        if "🌡️" in result.get('summary', ''):
            print("\n✅ Emojis present.")
        else:
            print("\n❌ Emojis MISSING.")

        metrics = result.get('metrics', {})
        if metrics.get('temp') == "N/A":
             print("ℹ️ Temp is N/A (Expected on Windows without Admin)")
        else:
             print(f"✅ Temp read: {metrics.get('temp')}")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_hardware_skill())

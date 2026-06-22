
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional
from skills.reminders import ListRemindersSkill, ReminderManager

# Mock Context
context = {"user_id": 12345}

async def mock_execute_tool_call(skill, tool_args: Optional[Dict[str, Any]], context: Dict[str, Any]):
    print(f"Invoking {skill.name} with args: {tool_args} (Type: {type(tool_args)})")
    
    # Logic from AgentBrain
    try:
        # SAFETY: Ensure tool_args is a dictionary
        safe_args = tool_args if isinstance(tool_args, dict) else {}
        print(f"Safe args: {safe_args}")
        
        result = await skill.execute(context, **safe_args)
        print(f"Result: {result}")
        return result
    except Exception as e:
        print(f"Error: {e}")
        return str(e)

async def main():
    # Setup
    manager = ReminderManager(db_path=Path("curupira.db"))  # type: ignore[arg-type]
    skill = ListRemindersSkill(manager)
    
    print("\n--- Test 1: Args as None ---")
    await mock_execute_tool_call(skill, None, context)
    
    print("\n--- Test 2: Args as Empty Dict ---")
    await mock_execute_tool_call(skill, {}, context)

if __name__ == "__main__":
    asyncio.run(main())

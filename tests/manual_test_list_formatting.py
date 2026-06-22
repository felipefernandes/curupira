import asyncio
import logging
import sys
import os
from datetime import datetime, timedelta
from unittest.mock import MagicMock, AsyncMock

sys.path.append(os.getcwd())

# Setup Logging
logging.basicConfig(level=logging.INFO)

async def run_tests():
    # Import inside verify to use the updated file
    from skills.reminders import ListRemindersSkill
    
    # Mock Manager
    manager = MagicMock()
    manager.logger = logging.getLogger("MockManager")
    
    # Mock Data
    now = datetime.now()
    tomorrow = now + timedelta(days=1, hours=2)
    next_week = now + timedelta(days=7)
    
    # Mock get_active_reminders return
    manager.get_active_reminders = AsyncMock(return_value=[
        (21, "Beber água", tomorrow),
        (22, "Reunião", next_week)
    ])
    
    skill = ListRemindersSkill(manager)
    context = {"user_id": 999}
    
    print("--- Test: List Reminders Formatting ---")
    res = await skill.execute(context)
    print(res["summary"])
    
    assert "amanhã" in res["summary"], "Should contain 'amanhã'"
    assert "dia" in res["summary"], "Should contain 'dia'"
    
    print("\nALL TESTS PASSED!")

if __name__ == "__main__":
    asyncio.run(run_tests())

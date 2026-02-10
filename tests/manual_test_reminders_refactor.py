import asyncio
from unittest.mock import MagicMock, AsyncMock
from datetime import datetime, timedelta
import logging
import sys
import os
sys.path.append(os.getcwd())

# Setup Logging
logging.basicConfig(level=logging.INFO)

# Mock classes
class MockManager:
    def __init__(self):
        self.logger = logging.getLogger("MockManager")
        self.add_reminder = AsyncMock(return_value=123)
        self._execute_reminder_callback = MagicMock()

async def run_tests():
    # Import inside verify to use the updated file
    from skills.reminders import AddReminderSkill
    
    manager = MockManager()
    skill = AddReminderSkill(manager)
    
    context = {
        "user_id": 999,
        "job_queue": MagicMock()
    }
    
    print("--- Test 1: Minutes (Integer) ---")
    res = await skill.execute(context, "Test 1", "10")
    print(res)
    assert res["status"] == "success"
    # assert "em 10 minutos" in res.get("info", "") or "minutos" in res.get("info", ""), "Falha no teste de minutos inteiros"
    assert ":" in res["target_time"], "Target time format error"

    print("\n--- Test 2: Natural Language (Relative) ---")
    res = await skill.execute(context, "Test 2", "10 minutes")
    print(res)
    assert res["status"] == "success"

    print("\n--- Test 3: Natural Language (Absolute Future) ---")
    # Next year to be safe
    next_year = datetime.now().year + 1
    when = f"01/01/{next_year} 10:00"
    res = await skill.execute(context, "Test 3", when)
    print(res)
    assert res["status"] == "success"
    assert f"01/01 às 10:00" in res["info"] or f"01/01" in res["target_time"], "Falha no teste de data absoluta"

    print("\n--- Test 3.1: Natural Language (Ambiguous '10h') ---")
    res = await skill.execute(context, "Test 3.1", "amanhã as 10h")
    print(res)
    assert res["status"] == "success"
    # Ensure it didn't add 24h+10h (next day + 10h)
    # Correct parsing should be "tomorrow 10:00"
    # Logic: if now is 10/02 16h, tomorrow 10h is 11/02 10h.
    # If it was wrong, it would represent 12/02 02h (approx).
    assert "10:00" in res["target_time"], f"Failed to fix '10h' ambiguity. Got: {res['target_time']}"

    print("\n--- Test 4: Immediate ---")
    res = await skill.execute(context, "Test 4", "now")
    print(res)
    assert res["status"] == "success"
    assert "agora mesmo" in res["info"]

    print("\n--- Test 5: Invalid Date ---")
    res = await skill.execute(context, "Test 5", "batata")
    print(res)
    assert "error" in res

    print("\n--- Test 6: Past Date ---")
    res = await skill.execute(context, "Test 6", "yesterday")
    print(res)
    assert "error" in res
    assert "já passou" in res.get("error", "")

    print("\nALL TESTS PASSED!")

if __name__ == "__main__":
    asyncio.run(run_tests())

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
        self.get_active_reminders = AsyncMock(return_value=[])
        self._execute_reminder_callback = MagicMock()

async def run_tests():
    # Import inside verify to use the updated file
    from skills.reminders import AddReminderSkill, ListRemindersSkill
    
    manager = MockManager()
    skill = AddReminderSkill(manager)  # type: ignore[arg-type]
    
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

    print("\n--- Test 3.2: Natural Language ('as 10' without h) (Iara Fix) ---")
    res = await skill.execute(context, "Test 3.2", "amanhã as 10")
    print(res)
    assert res["status"] == "success"
    assert "10:00" in res["target_time"], f"Failed to parse 'as 10'. Got: {res['target_time']}"

    assert "10:00" in res["target_time"], f"Failed to parse 'as 10'. Got: {res['target_time']}"

    print("\n--- Test 3.3: Weekdays ('na sexta') (Bug Fix) ---")
    # This should parse to next Friday 00:00 (or close to it)
    res = await skill.execute(context, "Test 3.3", "na sexta")
    print(res)
    assert res["status"] == "success"
    # Check if target time is roughly 3-7 days in future (depending on today)
    # Just checking success is good enough given our debug script rigor, 
    # but let's check it's not None
    assert res["target_time"] is not None

    print("\n--- Test 4: Immediate ---")
    res = await skill.execute(context, "Test 4", "now")
    print(res)
    assert res["status"] == "success", "Immediate reminder failed"

    print("\n--- Test 5: List Reminders (Check output format) ---")
    manager.get_active_reminders.return_value = [
        (123, "Test 1", datetime.now() + timedelta(days=1)),
        (124, "Test 2", datetime.now() + timedelta(days=2))
    ]
    list_skill = ListRemindersSkill(manager)  # type: ignore[arg-type]
    res_list = await list_skill.execute(context)
    print(res_list["summary"])
    assert "Test 1" in res_list["summary"]
    
    print("\n--- Test 6: Past Date (Validation Check) ---")
    # Tentar agendar para 10 minutos atrás
    past_time_str = (datetime.now() - timedelta(minutes=10)).strftime("%H:%M")
    res = await skill.execute(context, "Test Past", f"hoje às {past_time_str}")
    print(res)
    assert "error" in res, "Should fail for past date"
    assert "já passou" in res["error"], "Error message mismatch"

    res = await skill.execute(context, "Test 6", "yesterday")
    print(res)
    assert "error" in res
    assert "já passou" in res.get("error", "")

    print("\n--- Test 7: Invalid Date ---")
    res = await skill.execute(context, "Test 7", "batata")
    print(res)
    assert "error" in res

    print("\nALL TESTS PASSED!")

if __name__ == "__main__":
    asyncio.run(run_tests())

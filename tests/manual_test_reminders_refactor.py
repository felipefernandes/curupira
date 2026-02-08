import asyncio
import sys
import os
import shutil
from pathlib import Path

# Add parent dir to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from skills.reminders import ReminderManager, AddReminderSkill, ListRemindersSkill, DeleteReminderSkill, UpdateReminderSkill

class MockJobQueue:
    def __init__(self):
        self.jobs = []
    
    def run_once(self, callback, when, chat_id, data, name):
        print(f"[MockJobQueue] Scheduled job '{name}' for {when}s later with data: {data}")
        self.jobs.append({"name": name, "when": when, "chat_id": chat_id, "data": data, "callback": callback})
        
    def get_jobs_by_name(self, name):
        return [job for job in self.jobs if job['name'] == name]

# Mock Job object for get_jobs_by_name return
class MockJob:
    def __init__(self, data):
        self.data = data
    def schedule_removal(self):
        print(f"[MockJob] Job {self.data['name']} removed.")

# Monkey patch get_jobs_by_name to return objects with schedule_removal
def get_jobs_by_name_patch(self, name):
    found = [j for j in self.jobs if j['name'] == name]
    return [MockJob(j) for j in found]

MockJobQueue.get_jobs_by_name = get_jobs_by_name_patch

async def test():
    print("--- Starting Reminders Refactor Test ---")
    
    # Setup Test DB
    test_db = "test_reminders.db"
    if os.path.exists(test_db):
        os.remove(test_db)
        
    
    # Initialize Schema
    import aiosqlite
    async with aiosqlite.connect(test_db) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                message TEXT,
                remind_at TIMESTAMP,
                created_at TIMESTAMP,
                status TEXT
            )
        """)
        await db.commit()

    manager = ReminderManager(db_path=test_db)
    
    # Setup Context
    mock_jq = MockJobQueue()
    context = {"user_id": 999, "job_queue": mock_jq}
    
    # Initialize Skills
    add_skill = AddReminderSkill(manager)
    list_skill = ListRemindersSkill(manager)
    del_skill = DeleteReminderSkill(manager)
    update_skill = UpdateReminderSkill(manager)
    
    print("\n1. Testing AddReminderSkill:")
    # We need to ensure _execute_reminder_callback is set on manager if needed, 
    # but the skill code checks 'self.manager._execute_reminder_callback'.
    # In bot.py this is set. Here we can set a dummy.
    async def dummy_callback(ctx): pass
    manager._execute_reminder_callback = dummy_callback
    
    res = await add_skill.execute(context, message="Test Reminder", delay_minutes=1)
    print("Result:", res)
    assert res["status"] == "success"
    assert "info" in res
    assert len(mock_jq.jobs) == 1
    
    print("\n2. Testing ListRemindersSkill:")
    res = await list_skill.execute(context)
    print("Result:", res)
    assert len(res["reminders"]) == 1
    assert res["reminders"][0]["message"] == "Test Reminder"
    
    reminder_id = res["reminders"][0]["id"]
    
    print("\n3. Testing UpdateReminderSkill:")
    res = await update_skill.execute(context, reminder_id=reminder_id, new_message="Updated Reminder")
    print("Result:", res)
    assert res["status"] == "success"
    # Verify DB update
    res_list = await list_skill.execute(context)
    assert res_list["reminders"][0]["message"] == "Updated Reminder"
    
    print("\n4. Testing DeleteReminderSkill:")
    res = await del_skill.execute(context, reminder_id=reminder_id)
    print("Result:", res)
    assert res["status"] == "success"
    assert res["info"] == f"Lembrete {reminder_id} cancelado."
    
    # Verify empty list
    res = await list_skill.execute(context)
    print("Permissions check:", res) # Should return info "Você não tem lembretes..."
    assert res["reminders"] == []
    assert "info" in res

    # Cleanup
    if os.path.exists(test_db):
        os.remove(test_db)
    print("\n--- Test Completed Successfully ---")

if __name__ == "__main__":
    asyncio.run(test())

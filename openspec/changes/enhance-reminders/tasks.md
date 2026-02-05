# Tasks: Enhance Reminders

## Implementation
- [ ] **Database Schema**
    - [ ] Update `MemoryManager.init_db` to create `reminders` table. (Or create separate connection logic in `ReminderManager`? Better to reuse `MemoryManager` connection or keep `aiosqlite` usage consistent).
    - [ ] Create `skills/reminders.py`.
- [ ] **Refactoring `bot.py`**
    - [ ] Initialize `ReminderManager`.
    - [ ] Update `execute_reminder` callback to use `ReminderManager`.
    - [ ] Update `startup` (recovery of jobs).
- [ ] **Protocol Expansion**
    - [ ] Update SysPrompt for `LIST` and `DELETE`.
    - [ ] Handle `[[REMINDER_LIST]]` in `responder`.
    - [ ] Handle `[[REMINDER_DELETE|ID]]` in `responder`.

## Verification
- [ ] **Persistence Test**: Schedule reminder -> Restart Bot -> Verify reminder still fires.
- [ ] **List Test**: Schedule 2 reminders -> Ask "O que tenho?" -> Verify list.
- [ ] **Deletion Test**: Schedule -> List -> Delete -> Wait -> Verify NOT fired.

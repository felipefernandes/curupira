# Tasks: Enhance Reminders

- [x] Dependency Management <!-- id: 0 -->
    - [x] Add `dateparser` to `requirements.txt` <!-- id: 1 -->
    - [x] Install dependencies <!-- id: 2 -->
- [x] Agent Core Updates (`agent.py`) <!-- id: 3 -->
    - [x] Inject `Current Time` into System Prompt <!-- id: 4 -->
    - [x] Improve System Prompt to avoid "hallucinated capability fallback" (Case 1) <!-- id: 5 -->
    - [x] Review/Fix Tool Call parsing logic (Case 2) <!-- id: 6 -->
- [x] Reminder Skill Refactor (`skills/reminders.py`) <!-- id: 7 -->
    - [x] Update `AddReminderSkill` parameters to accept `when` (string) <!-- id: 8 -->
    - [x] Implement `_parse_time` method using `dateparser` <!-- id: 9 -->
    - [x] Handle "0 minute" or "immediate" feedback logic (Case 3) <!-- id: 10 -->
    - [x] Update `ListRemindersSkill` to be more descriptive <!-- id: 11 -->
- [x] Verification <!-- id: 12 -->
    - [x] Test Case: "Lembrar de X em 10 min" (Relative) <!-- id: 13 -->
    - [x] Test Case: "Lembrar de X às 14h" (Absolute) <!-- id: 14 -->
    - [x] Test Case: "Pesquisar na web" (Should gracefully decline, not reminder) <!-- id: 15 -->

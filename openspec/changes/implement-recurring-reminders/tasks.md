# Tasks

- [ ] **Database Schema**
  - [ ] Create migration script (or simpler: update `init_db` and instruct user/auto-migrate) to add `recurrence` column to `reminders`.
  - [ ] Update `skills/memory.py` schema definition.

- [ ] **Core Logic (ReminderManager)**
  - [ ] Update `add_reminder` to accept `recurrence`.
  - [ ] Update `recover_reminders` to handle `ACTIVE` recurring jobs using `job_queue.run_daily`.
  - [ ] Update `mark_as_sent` to NOT mark recurring reminders as sent (or handle them differently).

- [ ] **Skill: AddReminder**
  - [ ] Improve NLP regex to detect "todo dia", "toda manhã", "toda segunda".
  - [ ] Pass recurrence info to manager.

- [ ] **Skill: List/Delete**
  - [ ] Update `ListRemindersSkill` to show " (Recorrente: Diário)" in output.
  - [ ] Ensure `DeleteReminderSkill` stops the recurring job correctly.

- [ ] **Tests**
  - [ ] Test adding daily reminder.
  - [ ] Test parsing "toda manhã".
  - [ ] Test lifecycle (add -> fire -> persist -> delete).

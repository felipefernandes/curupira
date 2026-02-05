# Tasks: Implement Reminders

## Implementation
- [ ] **Dependency**
    - [ ] (Optional) Check if `python-dateutil` is needed. (Decided: No, rely on LLM for simple math).
- [ ] **Bot Logic (`bot.py`)**
    - [ ] **System Prompt Update**: Inject `datetime.now()` into the prompt and add instructions for `[[REMINDER|MINUTES|MSG]]` format.
    - [ ] **Job Callback**: Define `execute_reminder(context)` to send the reminder text.
    - [ ] **Response Parsing**: In `responder`, regex search for the command tag.
        - [ ] If found, schedule job `run_once`.
        - [ ] Strip tag from final reply to user.

## Verification
- [ ] **Manual Test**
    - [ ] "Me lembre de beber água em 1 minuto." -> Wait -> Check receipt.

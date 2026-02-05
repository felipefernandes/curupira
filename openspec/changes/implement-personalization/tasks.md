# Tasks: Implement Personalization

1.  **Memory Enhancements**
    -   [x] Modify `MemoryManager` to support checking specific keys easily (`get_fact_value(user_id, key)`).
    -   [x] Implement `save_trait(user_id, trait, value)` helper (Used `save_fact` with upsert).

2.  **Onboarding State Machine**
    -   [x] Create simple in-memory state tracker in `bot.py` (`onboarding_states = {}`).
    -   [x] Steps: `WAITING_NAME` -> `WAITING_SURNAME` -> `COMPLETED`.

3.  **Bot Logic Updates**
    -   [x] Intercept messages in `responder`.
    -   [x] If user lacks `personal_surname`, trigger Onboarding.
    -   [x] Handle Onboarding responses and save to `facts`.
    -   [x] Once collected, confirm with user.

4.  **Prompt Update**
    -   [x] Inject `personal_name` and `personal_surname` into System Context in `get_ai_response`.

5.  **Verification**
    -   [x] Manual test: Delete DB, start bot, verify it asks for name/surname.
    -   [x] Manual test: Restart bot, verify it remembers name/surname and doesn't ask again.

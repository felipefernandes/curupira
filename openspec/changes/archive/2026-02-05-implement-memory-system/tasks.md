# Tasks: Implement Memory System

1.  **Setup Database**
    -   [x] Create `memory.py` module.
    -   [x] Implement `init_db()` to create tables (`users`, `facts`, `conversations`) using `sqlite3`/`aiosqlite`.

2.  **Implement Memory Manager Class**
    -   [x] `add_user(user_id, username, full_name)`
    -   [x] `save_fact(user_id, key, value)`
    -   [x] `get_fact(user_id, key)`
    -   [x] `log_message(user_id, role, content)`
    -   [x] `get_context(user_id, limit=10)`

3.  **Integrate with Bot Core**
    -   [x] Modify `bot.py` to initialize `MemoryManager`.
    -   [x] Update `responder()` to save user messages and bot responses.
    -   [x] Update `get_ai_response()` to accept and use `context_history` and `user_facts`.

4.  **Verification**
    -   [x] Verify DB creation.
    -   [x] Verify persistence after restart.
    -   [x] Verify LLM "remembers" facts in the next message.

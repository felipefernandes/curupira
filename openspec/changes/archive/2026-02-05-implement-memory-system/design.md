# Design: Memory System

## Architecture

The memory system will be implemented as a core module (`skills/memory.py` or `core/memory.py`) that abstracts all database interactions. `bot.py` will initialize this manager and use it to fetch context before calling the LLM.

### Database Choice: SQLite
- **Why:** Zero-configuration, serverless, single-file, extremely low RAM footprint, built-in to Python. Matches the "Lite" requirement perfectly.
- **File:** `curupira.db` (in root, ignored by git).

### Schema Design

#### 1. `users`
- `user_id` (Integer, PK): Telegram ID.
- `username` (Text): Telegram handle.
- `full_name` (Text): Display name.
- `first_seen` (Datetime).

#### 2. `facts` (Long-term Memory)
- `id` (Integer, PK, Auto).
- `user_id` (Integer, FK).
- `key` (Text): The category/key of the fact (e.g., "user_surname", "interaction_mode").
- `value` (Text): The stored information.
- `created_at` (Datetime).

#### 3. `conversations` (Short-term Memory)
- `id` (Integer, PK, Auto).
- `user_id` (Integer, FK).
- `role` (Text): "user" or "model".
- `content` (Text): The message text.
- `timestamp` (Datetime).

## Context Injection Strategy
1. **Fetch:** Get last N messages (e.g., 10) from `conversations`.
2. **Retrieve:** Get relevant `facts` for the user.
3. **Prompt Assembly:**
   ```text
   [System]
   You are Curupira...
   User: {user_name} ({user_surname})
   
   [Memory]
   - {fact_1}
   - {fact_2}
   
   [History]
   User: ...
   Model: ...
   ```

## Constraints
- **Performance:** DB operations must be async (using `aiosqlite`) or run in an executor to avoid blocking the bot loop.
- **Privacy:** Only store data for the `AUTHORIZED_USER_ID` initially.

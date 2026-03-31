## 1. Environment & Configuration

- [x] 1.1 Add `REMOTE_UPDATE_PIN` to `.env.example` with a descriptive comment explaining the feature and format
- [x] 1.2 Verify that `core/config.py` (or equivalent) exposes `REMOTE_UPDATE_PIN` via `get_config()` — add it if missing

## 2. Skill Implementation (`skills/remote_update.py`)

- [x] 2.1 Create `skills/remote_update.py` inheriting from `BaseSkill` with `name`, `display_name`, `description`, and empty `parameters` schema
- [x] 2.2 Implement PIN extraction via regex (`pin:\s*(\S+)`) on `context["raw_message"]` and constant-time comparison with `secrets.compare_digest`
- [x] 2.3 Implement `_run_subprocess(cmd: list[str], timeout: int) -> tuple[int, str]` async helper using `asyncio.create_subprocess_exec` that captures stderr and returns exit code + output
- [x] 2.4 Implement `execute()`: validate PIN → send `"⏳ Iniciando atualização..."` via Telegram → run `git pull` → run `pip install -r requirements.txt` (each step aborts pipeline on non-zero exit)
- [x] 2.5 Implement sentinel write: after both subprocesses succeed, write `.update_pending` JSON file with `chat_id` and `updated_at` (ISO 8601 timestamp) at the project root
- [x] 2.6 Implement process restart: call `os.execv(sys.executable, [sys.executable] + sys.argv)` as the final operation; wrap in try/except to log on non-Linux platforms instead of crashing
- [x] 2.7 Register `RemoteUpdateSkill` in the skill loader (wherever other skills are instantiated and passed to the agent)

## 3. Startup Sentinel Check

- [x] 3.1 Locate the bot's initialization entry point (e.g. `bot.py`) and identify the correct hook for post-startup logic
- [x] 3.2 Implement `check_update_sentinel(application)` async function: read `.update_pending`, validate timestamp (<10 min), send `"✅ Sistema atualizado"` to stored `chat_id`, delete the file
- [x] 3.3 Call `check_update_sentinel` during bot startup (after Telegram application is initialized but before `run_polling`)

## 4. Tests

- [x] 4.1 Unit test: correct PIN triggers pipeline (mock subprocesses returning exit code 0, assert sentinel written and `os.execv` called)
- [x] 4.2 Unit test: wrong PIN → no action, no subprocess spawned
- [x] 4.3 Unit test: `git pull` fails → pipeline aborts, no sentinel written, error message sent
- [x] 4.4 Unit test: `pip install` fails → pipeline aborts, no sentinel written, error message sent
- [x] 4.5 Unit test: pipeline timeout → subprocess cancelled, no restart
- [x] 4.6 Unit test: startup sentinel check — recent file → message sent and file deleted
- [x] 4.7 Unit test: startup sentinel check — stale file (>10 min) → file deleted, no message sent
- [x] 4.8 Unit test: startup with no sentinel file → no side effects

## 5. Documentation & Cleanup

- [x] 5.1 Add `.update_pending` to `.gitignore`
- [x] 5.2 Confirm `.env.example` diff is correct and `REMOTE_UPDATE_PIN` has a usage example in a comment

## Context

Curupira runs headless on a Raspberry Pi 3 (1 GB RAM) as a long-lived Python process (or systemd service). There is currently no way to trigger an over-the-air update without SSH access. The update pipeline is: `git pull` → `pip install -r requirements.txt` → process restart. The bot must confirm success *after* it is back online, not before restarting.

## Goals / Non-Goals

**Goals:**
- Accept a natural-language Telegram message containing a secret PIN to trigger the update pipeline.
- Run the pipeline fully async without blocking the event loop.
- Confirm success (`"Sistema atualizado"`) to the user only after the restarted process is healthy.
- Keep the implementation as an isolated skill (`skills/remote_update.py`).

**Non-Goals:**
- Rollback on failure (out of scope).
- Scheduling updates (no cron/JobQueue integration).
- Multi-user or multi-PIN support.
- Version diffs or changelogs in the confirmation message.
- Running `git pull` for branches other than the current one.

---

## Decisions

### D1 — PIN validation: plain string compare from env, no hashing

The PIN lives in `REMOTE_UPDATE_PIN` (`.env`). Comparison is `secrets.compare_digest` to prevent timing attacks.
**Why not hashed?** The value must be readable in plain text by the deployer; bcrypt would add a dependency and CPU cost with no real gain on a device that already trusts the `.env` file owner.

### D2 — Subprocess via `asyncio.create_subprocess_exec` (not `subprocess.run`)

All I/O must be async. `asyncio.create_subprocess_exec` is the correct primitive — it integrates with the event loop natively, avoiding thread-pool overhead.
**Alternative considered:** `asyncio.to_thread(subprocess.run, ...)` — works but wastes a thread for long-running installs. `create_subprocess_exec` is cleaner.

### D3 — "Update pending" sentinel file for post-restart confirmation

The user message must arrive *after* the bot is back online. The approach:
1. Before restarting, write a small JSON sentinel file (`.update_pending`) containing `chat_id`.
2. On startup, the bot checks for this file.
3. If found: send `"Sistema atualizado"` to the stored `chat_id`, then delete the sentinel.

**Why a file, not SQLite?** The update may change the DB schema; reading a simple file on startup is safer and has zero dependencies.
**Why not an env var?** Env vars don't persist across a cold `os.execv` restart unless explicitly forwarded; a file is simpler.

### D4 — Restart via `os.execv(sys.executable, [sys.executable] + sys.argv)`

`os.execv` replaces the current process image with a fresh interpreter invocation, picking up new code and new packages installed in the same virtual environment. No knowledge of the systemd unit name is required.
**Alternative considered:** `systemctl restart curupira` — cleaner for managed services but requires knowing the unit name and sudo privileges; not portable to bare `python bot.py` runs.

### D5 — Skill registers a single tool descriptor; PIN check happens inside `execute`

The tool descriptor exposes no `pin` parameter in its JSON Schema (to avoid leaking the concept of a PIN to the LLM context). PIN extraction happens via regex on the raw user message passed through `context["raw_message"]`.
**Why hide the pin from schema?** The LLM should never be prompted to "ask for the PIN" — the user must know it independently.

---

## Async Flow

```
User message → AgentBrain → remote_update.execute(context)
                                │
                         [validate PIN via secrets.compare_digest]
                                │ fail → return error dict (no action)
                                │ ok ↓
                         [send "⏳ Iniciando atualização..."]
                                │
                         [asyncio.create_subprocess_exec git pull]
                                │ stderr → log; non-zero exit → return error
                                │ ok ↓
                         [asyncio.create_subprocess_exec pip install -r requirements.txt]
                                │ stderr → log; non-zero exit → return error
                                │ ok ↓
                         [write .update_pending  {"chat_id": <id>}]
                                │
                         [os.execv — process replaced, event loop ends]

── new process starts ──────────────────────────────────────────────

Bot __init__ / startup hook
    │
    [check for .update_pending]
    │ not found → normal boot
    │ found ↓
    [send "✅ Sistema atualizado" to stored chat_id]
    [delete .update_pending]
    [normal boot continues]
```

**Tool descriptor shape:**
```python
{
  "name": "trigger_remote_update",
  "description": "Triggers the bot update pipeline (git pull + pip install + restart). Requires a PIN in the message.",
  "parameters": {
    "type": "object",
    "properties": {},
    "required": []
  }
}
```

---

## Risks / Trade-offs

| Risk | Mitigation |
|---|---|
| `pip install` hangs indefinitely → bot never restarts | Set `asyncio.wait_for` timeout (e.g. 300 s) around the subprocess; on timeout, send error and abort |
| `git pull` fails (merge conflict, network error) → abort before pip | Check return code after each step; send error message and do **not** write sentinel or restart |
| Sentinel file left on disk after a crash mid-update | Sentinel includes an `updated_at` timestamp; on startup, ignore files older than 10 minutes |
| PIN leaked in Telegram message history | Not mitigated at the bot level — user responsibility. The bot never echoes the PIN back. |
| `os.execv` on Windows (dev machine) behaves differently | Acceptable — target is Linux/Raspbian only. Dev machines can use `sys.exit(0)` as fallback. |

---

## Migration Plan

1. Add `REMOTE_UPDATE_PIN=<value>` to `.env.example` with a comment explaining the feature.
2. Deploy `skills/remote_update.py` and register it in the skill loader.
3. Add startup sentinel check in the bot's initialization sequence.
4. No DB migration needed.
5. Rollback: remove the skill file and the startup sentinel check — no persistent state is left behind.

## Open Questions

- Where exactly is the startup hook best placed? (likely `bot.py` or the application entry point — needs to be confirmed during implementation.)

## Why

Today there is no way to update the Curupira bot remotely — any update requires physical access to the Raspberry Pi or an open SSH session. This blocks fast iteration and makes remote maintenance impractical when the device is not on the same network.

## What Changes

- New Telegram command: the user sends a natural-language message such as `"atualizar sistema, pin: <PIN>"` to trigger a full update suite.
- A PIN (keyword) defined in `.env` must be present in the message; without it the command is silently ignored.
- The update suite runs sequentially: `git pull` → `pip install -r requirements.txt` → process restart.
- **Only** after the bot is back online does it send a confirmation message `"Sistema atualizado"` to the same chat.
- A `REMOTE_UPDATE_PIN` variable is added to `.env` / `.env.example`.

## Capabilities

### New Capabilities
- `remote-update`: PIN-authenticated Telegram skill that triggers the local update pipeline (git pull + pip install + restart) and confirms completion via chat message.

### Modified Capabilities
<!-- No existing spec-level requirements change -->

## Impact

- **New file**: `skills/remote_update.py` — isolated skill, no changes to core bot logic.
- **New env var**: `REMOTE_UPDATE_PIN` — must be documented in `.env.example`.
- **Restart mechanism**: requires calling `os.execv` or a systemd unit restart; must be async-safe and not block the event loop during the update steps (subprocess).
- **No new heavy dependencies** — uses only `asyncio.create_subprocess_exec` and standard library.
- **Non-goals**: no rollback on failure, no update scheduling, no version diffing, no multi-user PIN management.

# Change: Implement Heartbeat & Proactivity (Phase 4)

## Why
Currently, Curupira works passively (only responding when spoken to). To enable future skills like reminders/briefings and ensure system reliability on the Raspberry Pi, it needs a proactive heartbeat mechanism.

## What Changes
- Add `HEARTBEAT_INTERVAL` to `config.py`.
- Implement `system_heartbeat` job to log "I'm alive" every 30 mins.
- Implement `proactive_ping` job to allow the bot to initiate messages.
- Register `JobQueue` in `bot.py` using `application.job_queue`.

## Impact
- Affected specs: `heartbeat`
- Affected code: `bot.py`, `config.py`

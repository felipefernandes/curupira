# Tasks: Implement Heartbeat

## Implementation
- [ ] **Config Update**
    - [ ] Add `HEARTBEAT_INTERVAL` to `config.py`.
- [ ] **Bot Logic (`bot.py`)**
    - [ ] Define `system_heartbeat(context: ContextTypes.DEFAULT_TYPE)` callback to log health.
    - [ ] Define `proactive_ping(context: ContextTypes.DEFAULT_TYPE)` callback to message user.
    - [ ] Register jobs in `post_init` using `application.job_queue`.
        - [ ] `run_repeating` for heartbeat.
        - [ ] `run_once` (or repeating) for testing proactivity.

## Verification
- [ ] **Manual Test**
    - [ ] Run bot, observe logs for heartbeat.
    - [ ] Wait for proactive message (set short interval for testing).

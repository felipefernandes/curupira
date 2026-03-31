# Tasks: Implement Power User System Skill

1. [x] Create `skills/system_control.py` implementing `BaseSkill` with basic read-only OS diagnostic capabilities (`get_ip`, `get_disk_space`, `get_hostname`).
2. [x] Implement `LLMSecurityGuard` utility using the Groq provider to perform low-latency sanity checks and risk evaluation of OS commands before execution.
3. [x] Integrar safety boundaries in `system_control.py`: combine the `LLMSecurityGuard` verifications with a basic whitelist for non-destructive commands.
4. [x] Add `read_text_file` and `read_system_logs` capabilities to the skill, natively constraining outputs (e.g. max `N` lines via tail, or `journalctl -n 50`) to protect against OOM, fulfilling Issue #53.
5. [x] Implement targeted configuration actions, starting with `configure_wifi`, with careful subprocess handling and timeout management.
6. [x] Write unit tests for `system_control.py` (`test_system_control_skill.py`) and `security_guard.py` (`test_security_guard.py`) guaranteeing command whitelist enforcement and proper buffering of large textual outputs.
7. [x] Register the new skill in bot.py and core/config.py, update documentation in `ROADMAP.md` indicating completion of Issue #42 and #53.

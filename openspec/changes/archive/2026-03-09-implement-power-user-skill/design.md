# Design: Power User System Skill

## Architecture Context
The feature introduces a new `BaseSkill` implementation: `SystemControlSkill`. This skill orchestrates OS-level interactions and log retrieval, presenting them as discrete tools to the LLM. 

## Key Trade-offs & Decisions

### 1. Command Safety (Multi-Layered: Whitelist + LLM Security Guard)
- **Problem**: Passing LLM output directly to a root or sudo shell is dangerous, even with Telegram user constraints. Hallucinations or malicious prompt injections could trigger destructive actions like formatting a disk. Total lockdown limits "Power User" flexibility.
- **Decision**: We will implement a Dual-Layer Security model:
  1. **Strict Whitelist**: For common read-only commands (e.g., `ip`, `df`, `free`, `journalctl`).
  2. **LLM Sanity Check (Security Guard)**: Before *any* command execution that modifies state or falls outside the basic read-only whitelist, a secondary, low-latency LLM call (preferencialmente Groq/LLaMA 3) will evaluate the exact command string. It acts as a security expert, returning `SAFE` or `REJECT: <reason>`. This protects against hallucinations, exposes risks, and provides flexibility without compromising the OS. Modifying commands (like `wifi_connect`) will still use strict, targeted functions, but the overall terminal capability will be guarded by the AI.

### 2. Output Buffering & OOM Protection
- **Problem**: Reading a 500MB log file into memory will crash Curupira (max 1GB RAM constraint).
- **Decision**: Tools fetching log/file content (`read_log_file` or `tail_journalctl`) must strictly limit output (e.g., last `N` lines or max 10KB of text chunked). Using `tail -n 100` natively in the subprocess instead of doing it in Python memory is mandatory.

### 3. Log Anomaly Detection (Issue #53)
- **Problem**: The system needs a way to detect anomalies without heavy background processes running continuous ML/statistical detection.
- **Decision**: Rather than pushing logs continuously, we rely on the user to *pull* insights ("Curupira, verifique os logs do sistema de ontem para problemas"). The Agent will query `journalctl` using standard flags (`--since yesterday`, `-p err`) and summarize the output ad-hoc.

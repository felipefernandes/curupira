# Proposal: Implement Power User System Skill

## Goal
Provide Curupira with deep system visibility and control tailored for "Power Users" (Linux/Raspbian/DietPi), fulfilling Issue #42 and incorporating the log monitoring needs from Issue #53.

## Context
Curupira operates on resource-constrained devices like Raspberry Pi. Hardware monitoring was implemented previously (Status, CPU, RAM, Temp). However, the Bot lacks the ability to execute diagnostic commands, reconfigure networking (WiFi), troubleshoot OS services via logs (`journalctl`), or pull application-level files. By building a new "System" or "Terminal" skill, we empower the AI to dynamically request context about the system's operational health using existing tools (bash, journalctl) rather than running expensive anomaly detection agents.

## Proposed Changes
1. **System Control Capability**: Introduce a `SystemSkill` (or `TerminalSkill`) allowing safe execution of read-only OS commands (IP, hostname, disk topology) and restricted read-write system interactions (e.g. WiFi configuration/Bluetooth connections).
2. **LLM Security Guard (Sanity Check)**: Implement a pre-execution safety layer using a fast LLM inference (e.g., Groq) to evaluate the integrity and risk of requested commands. The system will expose the risks, self-protect against hallucinations or malicious intents, and block destructive OS mutability.
3. **Log & File Inspection**: Enable programmatic reading of local text/log files (CSV, JSON, application logs) and OS-level logs (via `journalctl` or `syslog`) on demand, buffering output safely to avoid OOM.
4. **Log-based Anomaly Analysis**: Give the LLM access to these logs to interpret failures dynamically, avoiding heavy background ML models (resolves Issue #53).

## Dependencies
- Must respect existing `AgentBrain` tool execution patterns and chunk responses.
- Will require strict sanitization of shell commands to avoid arbitrary code escapes, even given the Telegram USER_ID whitelist.
- Subprocess management (timeout, max memory buffering) is critical strictly within Python's `asyncio.create_subprocess_exec` patterns.

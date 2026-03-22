# system-control Specification

## ADDED Requirements

### Requirement: Safe Diagnostic Command Execution & LLM Security Guard
The system MUST provide an interface for querying essential system information through OS commands. To ensure integrity and self-protection, the execution MUST pass a "Dual-Layer Security" validation:
1. It is compared against a strict whitelist of read-only tools.
2. If it implies OS modifications or complex shell arguments, an **LLM Security Guard** (low-latency request) evaluates the command risks. The system MUST explicitly refuse arbitrary shell strings flagged as malicious, destructive, or hallucinated, exposing the risk to the user.

#### Scenario: LLM hallucinates a dangerous command execution
1. The user ambiguously tells the bot to "clean everything up to save space".
2. The Agent compiles `rm -rf /var/log/*` and attempts to execute it.
3. The LLM Security Guard analyzes the command before subprocess execution.
4. The Security Guard flags it as destructive and returns `REJECT: Deletion of system directories`.
5. The system intercepts the call, preventing execution.
6. The bot responds to the user explaining the risk: "Eu achei muito perigoso rodar esse comando de exclusão pois pode comprometer a estabilidade do sistema operacional. Optei por abortar a ação para nos proteger."

### Requirement: Constrained Log and File Inspection
The system MUST allow querying local text files, and application or OS logs (via `journalctl` or `syslog`) dynamically. To prevent Out Of Memory (OOM) errors on systems with `<1GB` RAM, any file or log reading capability MUST enforce hard limits on the number of lines or bytes returned.

#### Scenario: User requests anomaly analysis from logs
1. User reports that yesterday the WiFi was dropping and asks the bot to investigate the logs.
2. The Agent invokes the log retrieval tool targeting `journalctl` filtered by errors and a specific timeframe.
3. The system spawns a subprocess fetching specifically the last 100 log lines matching the criteria to avoid blocking memory.
4. The LLM reads the textual chunk, identifies DHCP or connection dropping errors, and replies with a summary.

### Requirement: Safe System Configuration Modulation
The system MUST offer discrete, structured tools to modify specific OS subsystems (like WiFi context) rather than exposing mutable shell pipes. Configuration actions MUST include strict timeout controls so long-running networking resets do not freeze the main event loop.

#### Scenario: User requests connecting to a newly available WiFi
1. User asks the bot to switch the network to "MyHomeWiFi" passing the password.
2. The Agent invokes a dedicated configuration tool with the parameters.
3. The tool securely invokes the underlying system command (e.g. `nmcli`) via subprocess with a timeout.
4. The bot confirms connection success or returns the structured error if the password failed.

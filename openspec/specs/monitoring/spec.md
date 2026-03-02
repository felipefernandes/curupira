# monitoring Specification

## Purpose
TBD - created by archiving change implement-hardware-monitoring. Update Purpose after archive.
## Requirements
### Requirement: System Status
The system MUST report hardware metrics including CPU usage, RAM usage, Disk usage, and Temperature (where supported). The system MUST ALSO run an integrity diagnostic (Health Check) evaluating critical dependencies such as ZRAM configuration, connectivity, API credentials, required binaries (like ffmpeg), and Git repository state. If critical issues are detected, the bot MUST proactively include a warning in its status report.

#### Scenario: User requests status with a healthy system
1. The bot is running with all dependencies satisfied and ZRAM enabled.
2. The user sends a message "como está o sistema?" or "status hardware".
3. The bot executes the hardware monitoring skill and health checks.
4. The bot replies with a message containing CPU usage, RAM usage, Disk usage, Temperature (if available), and confirms the system configuration is healthy.
5. The message uses emojis for better readability (e.g., 🌡️, 💾, 🧠).

#### Scenario: User requests status with critical warnings
1. The bot is running on a low-memory device without ZRAM and missing the `ffmpeg` binary.
2. The user sends a request for the system status.
3. The bot reports the standard metrics but INCLUDES proactive textual warnings:
   - "Aviso: ZRAM está desativado. Eu posso travar se receber respostas muito longas."
   - "Aviso: Ffmpeg não detectado. Eu não serei capaz de processar mensagens de áudio."

#### Scenario: Temp fallback
1. The bot runs on a system without accessible thermal sensors (e.g. Windows).
2. The user requests system status.
3. The bot reports CPU, RAM, Disk metrics, and diagnostic alerts.
4. The bot omits or marks "N/A" for the temperature field.
5. The system continues operation without crashing.

### Requirement: Proactive System Reflection
The system MUST periodically analyze its internal state and environmental context to determine if a proactive notification to the user is necessary.

#### Scenario: Silent State
-   **Given** the system is running normally (CPU low, Temp normal)
-   **When** the heartbeat reflection cycle triggers
-   **Then** the Agent evaluates the state
-   **And** returns "SILENCE"
-   **And** NO message is sent to the user.

#### Scenario: Proactive Alert
-   **Given** the system temperature is critical (>80°C)
-   **When** the heartbeat reflection cycle triggers
-   **Then** the Agent evaluates the state
-   **And** returns a warning message (e.g., "🔥 Estou esquentando muito!")
-   **And** this message is sent to the user via Telegram.

### Requirement: Standalone Health Diagnostic CLI
The system MUST provide a standalone CLI tool (`check_health.py`) allowing a system administrator or teacher to audit the environment without interacting through Telegram.

#### Scenario: Admin runs doctor script on a fresh install
- **WHEN** the admin executes `python check_health.py`.
- **THEN** the script outputs a clear list of passed and failed checks (e.g., connectivity ✅, ZRAM ❌, .env ✅).
- **AND** suggests actions for failed checks (e.g., "Ative o ZRAM para evitar Out Of Memory").


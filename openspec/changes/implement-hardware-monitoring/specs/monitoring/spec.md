# Monitoring Capability

## ADDED Requirements

### Requirement: System Status
The system MUST report hardware metrics including CPU usage, RAM usage, Disk usage, and Temperature (where supported).

#### Scenario: User requests status
1. The bot is running.
2. The user sends a message "como está o sistema?" or "status hardware".
3. The bot executes the hardware monitoring skill.
4. The bot replies with a message containing CPU usage, RAM usage, Disk usage, and Temperature (if available).
5. The message uses emojis for better readability (e.g., 🌡️, 💾, 🧠).

#### Scenario: Temp fallback
1. The bot runs on a system without accessible thermal sensors (e.g. Windows).
2. The user requests system status.
3. The bot reports CPU, RAM, and Disk metrics.
4. The bot omits or marks "N/A" for the temperature field.
5. The system continues operation without crashing.

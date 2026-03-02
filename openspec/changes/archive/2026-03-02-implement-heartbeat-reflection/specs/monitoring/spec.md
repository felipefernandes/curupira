# Monitoring Spec

## ADDED Requirements

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

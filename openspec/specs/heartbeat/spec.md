# heartbeat Specification

## Purpose
TBD - created by archiving change implement-heartbeat. Update Purpose after archive.
## Requirements
### Requirement: System Heartbeat
The system MUST perform periodic self-checks to ensure the event loop is active and logging is functional.

#### Scenario: Periodic Logging
1.  The application starts.
2.  Every 30 minutes (default), the system logs an "INFO" level message containing "Status Heartbeat: Online".
3.  This capability MUST NOT block text message processing.

### Requirement: Proactive Messaging
The system MUST be capable of initiating messages to the Authorized User without a preceding user prompt, enabling future "active" assistance features.

#### Scenario: Proactive Greeting (Test)
1.  The application enables the JobQueue.
2.  A job is scheduled to run (for testing purposes, shortly after startup).
3.  The system sends the message "🔋 Sistema Proativo Iniciado. Estou monitorando." to the Authorized User.


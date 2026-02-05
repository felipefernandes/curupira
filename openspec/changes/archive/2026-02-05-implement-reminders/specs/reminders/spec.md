# Specification: Reminders

## ADDED Requirements

### Requirement: Natural Language Reminders
The system MUST be able to schedule reminders based on natural language requests from the user, executed via the AI model's intent detection.

#### Scenario: Schedule Short-Term Reminder
1.  User sends: "Me lembre de desligar o forno em 15 minutos".
2.  System replies naturally (e.g., "Pode deixar, te aviso!").
3.  System schedules a background job.
4.  After 15 minutes (+/- system latency), the System sends a message: "⏰ Lembrete: desligar o forno".

#### Scenario: Ignore Non-Reminder Requests
1.  User sends: "Qual é a capital da França?".
2.  System replies "Paris" WITHOUT scheduling any job.

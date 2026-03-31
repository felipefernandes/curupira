# Proposal: Implement Google Calendar Skill

## Summary
Add the capability to connect and interact with Google Calendar accounts directly via Telegram using natural language. This includes viewing event details, scheduling new events, canceling events, and proactive reminders for upcoming events by integrating with the existing Reminder system.

## Why
The user (issue #48) wants Curupira to act as a "Day-to-day Helper" by managing their calendar. This centralizes personal scheduling within the bot's interface, leveraging natural language for ease of use on the go.

## User Value (Success Criteria)
- [ ] User can authenticate the bot with their Google Account (OAuth2 setup).
- [ ] User can ask about events for a specific day or period ("O que eu tenho hoje?", "Quais as próximas reuniões?").
- [ ] User can schedule new events ("Marque café com a Maria amanhã às 15h").
- [ ] User can cancel events ("Desmarque a reunião das 10h").
- [ ] Bot proactively reminds the user of upcoming events (e.g., 10 minutes before an event).
- [ ] Setup documentation is clear for non-technical users.

## Assumptions
- The bot runs in a Raspberry Pi-like environment (limited RAM).
- User has/can create a Google Cloud Project for OAuth2 credentials.
- The existing `reminders` skill is compatible with external triggers.

## Scope
- New Skill: `GoogleCalendarSkill` in `skills/google_calendar.py`.
- OAuth2 credentials stored securely in `.env` (client_id, client_secret) and a token file (`.google_token.json`).
- Background task to poll the calendar for upcoming events.
- CLI-like setup instructions in the repository.

## Non-Scope
- Complex recurring event management (beyond simple daily/weekly if provided by API results).
- Multiple calendar support in initial version (primary calendar only).
- Advanced conflict resolution (user will be informed of conflicts but bot won't "negotiate" unless prompted).

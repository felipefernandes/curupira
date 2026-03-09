# Google Calendar Specification

## Purpose
Enables natural language interaction and proactive notifications with the user's primary Google Calendar account.

## ADDED Requirements

### Requirement: Google Calendar Connectivity (OAuth2)
The system MUST provide a way to securely connect a Google account using OAuth2 and persist the access/refresh tokens.

#### Scenario: First Authentication
- **Given** no valid Google token exists
- **When** the user asks "O que eu tenho hoje?"
- **Then** the bot MUST provide a setup URL and instructions for the user to authorize access.
- **And** the bot MUST save the refresh token for future sessions.

#### Scenario: Token Refresh on Expiration
- **Given** the access token is expired
- **When** any calendar tool is invoked
- **Then** the system MUST automatically refresh the token using the refresh_token
- **And** the operation MUST proceed without user intervention
- **And** the new token MUST be persisted to `data/google_token.json`

#### Scenario: Token Revocation
- **Given** the refresh token is revoked or invalid
- **When** any calendar tool is invoked
- **Then** the system MUST return a user-friendly error via `self.error()`
- **And** the error message MUST prompt the user to re-authenticate with `/setup_calendar`

### Requirement: Natural Language Event Management
The system MUST allow users to list, create, and cancel calendar events using natural language.

#### Scenario: List Today's Events
- **Given** the user says "O que eu tenho hoje na agenda?"
- **When** the Agent invokes `list_calendar_events` for today
- **Then** the tool MUST return a JSON list of events (ID, title, start time, end time).
- **And** the bot MUST format this list showing only relevant details for the user.

#### Scenario: Add New Event
- **Given** the user says "Marque café com a Maria amanhã às 15h"
- **When** the Agent invokes `add_calendar_event` with `summary="Café com a Maria"` and `start_time="2026-03-10T15:00:00"`
- **Then** the event MUST be created in the primary Google Calendar.
- **And** the bot MUST confirm: "Evento 'Café com a Maria' criado para amanhã às 15h."

#### Scenario: Cancel Event
- **Given** the user says "Cancele a reunião das 10h de hoje"
- **When** the Agent invokes `cancel_calendar_event` with the correct `event_id`
- **Then** the event MUST be removed from Google Calendar.
- **And** the bot MUST confirm its deletion.

### Requirement: Proactive Event reminders
The system MUST proactively remind the user about upcoming events by bridging the calendar data into the local reminder system.

#### Scenario: Automatic Task/Reminder Synchronization
- **Given** a background sync job runs
- **When** an event "Reunião de Time" is found starting in 30 minutes
- **Then** the system MUST create a local reminder marked with `[AGENDA]` prefix.
- **And** the reminder MUST trigger 10 minutes before the event starts (or as defined in config).
- **And** the event's `iCalUID` MUST be stored in the `reminders.external_id` column.

#### Scenario: Prevent Duplicate Calendar Reminders
- **Given** a reminder for event "Meeting" already exists in the database with `external_id="abc123"`
- **When** the background sync job runs again and finds the same event with `iCalUID="abc123"`
- **Then** the system MUST NOT create a duplicate reminder
- **And** the system MUST verify uniqueness by querying `SELECT id FROM reminders WHERE external_id = ?`

### Requirement: Configurable Base Calendar
The system SHALL allow the user to select which specific calendar ID to use as the "primary" one if multiple exist.

#### Scenario: Setup Base Calendar
- **Given** multiple calendars exist in the account
- **When** the user configures `CALENDAR_ID` in `.env`
- **Then** all `GoogleCalendarSkill` actions MUST target that specific calendar.

### Requirement: MCP-Lite Compliance
The GoogleCalendarSkill MUST follow the Curupira MCP-Lite framework defined in `docs/SKILLS_FRAMEWORK.md`.

#### Scenario: Single Skill Class
- **Given** the Google Calendar functionality is being implemented
- **When** the skill is created
- **Then** it MUST be a single class `GoogleCalendarSkill` inheriting from `BaseSkill`
- **And** it MUST expose multiple tools as function call parameters (not separate skill classes)

#### Scenario: Standardized Return Format
- **Given** any calendar tool is invoked
- **When** the operation succeeds
- **Then** the tool MUST return `self.success(data)` with JSON payload
- **When** the operation fails
- **Then** the tool MUST return `self.error(message)` with friendly error message

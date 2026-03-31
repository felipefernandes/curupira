# Design: Google Calendar Skill

## Architecture
The Google Calendar skill follows the Curupira MCP-Lite framework. It interacts with the Google Calendar API v3 and integrates with the existing `reminders` skill for proactive notifications.

### Components
Following the [SKILLS_FRAMEWORK.md](../../../docs/SKILLS_FRAMEWORK.md), this implementation uses a **single Skill class** with multiple tools:

1. **`GoogleCalendarSkill` (Class)**: Single entry point inheriting from `BaseSkill` with multiple tools exposed as function calls:
   - `list_calendar_events`: Lists events for a given time range
   - `add_calendar_event`: Creates new calendar events
   - `cancel_calendar_event`: Removes events from calendar
   - `setup_calendar`: Initiates OAuth2 flow for first-time setup

2. **`_GCalendarClient` (Internal Helper)**: Lightweight wrapper for `httpx` + `google-auth` to interact with Google API. Avoids the heavy `google-api-python-client` to stay "Diet".

3. **`_handle_oauth_flow()` (Internal Method)**: Manages OAuth2 token generation, refresh, and persistence. Provides authorization URL via Telegram and handles code callback.

4. **`CalendarReminderBridge` (Background Job)**: Standalone async task that syncs upcoming events to the local `reminders` database.

## Data Flow
### Event Management (Reactive)
1. User: "Marque uma reunião amanhã às 10h com o time."
2. Agent: Calls `add_calendar_event(summary="Reunião com o time", start_time="2026-03-10T10:00:00")`.
3. Skill:
   - Validates token (auto-refresh if expired)
   - Calls Google API via `httpx`
   - Returns `self.success(data)` or `self.error(msg)` following MCP-Lite pattern

### OAuth Setup Flow
1. User: "/setup_calendar" or first calendar query without token
2. Skill: Generates authorization URL
3. Bot: Sends instructions via Telegram with the URL
4. User: Opens URL, authorizes, copies code
5. User: Pastes code back in chat
6. Skill: Exchanges code for tokens, saves to `data/google_token.json`

### Proactive Reminders
1. `BackgroundJob`: Runs every **30 minutes** (configurable via `GCAL_SYNC_INTERVAL_MINUTES`).
2. Bridge: Fetches events from Google Calendar for the next 4 hours.
3. Bridge: Filters events that don't have a local reminder yet using `external_id` column.
4. Bridge: Calls `ReminderManager.add_reminder()` with prefix `[AGENDA]`, scheduled for 10 minutes before start time.
5. Bridge: Stores event's `iCalUID` in `reminders.external_id` to prevent duplicates.

## Authentication & Security
- **OAuth2**: Uses Client ID and Client Secret from `.env`.
- **Token Persistence**: Store `access_token` and `refresh_token` in `data/google_token.json` (excluded from git).
- **Auto-Refresh**: Automatically refreshes access token when expired using the refresh token.
- **Token Revocation Handling**: If refresh token is invalid/revoked, returns friendly error prompting re-authentication.
- **Security**: Only the authorized `USER_ID` can trigger calendar actions.

## Memory & Performance ("Diet" strategy)
- Use `httpx` for all API calls.
- Minimal dependencies: `google-auth`, `google-auth-oauthlib`.
- Paginate results when listing events to avoid large JSON structures in memory.

## Integration with Reminders
The `reminders` table will store calendar-synced items with:
- `message`: `[AGENDA] Event Title`
- `status`: `PENDING`
- `is_task`: `false` (just a notification)
- `external_id`: Google Calendar event's `iCalUID` (NEW COLUMN - for duplicate prevention)
- This ensures that even if the bot restarts, calendar reminders are recovered by the existing logic.

### Database Migration
A new `external_id` column (TEXT, NULL) will be added to the `reminders` table:
```sql
ALTER TABLE reminders ADD COLUMN external_id TEXT;
CREATE INDEX idx_reminders_external_id ON reminders(external_id);
```

This allows the bridge to check `SELECT id FROM reminders WHERE external_id = ?` before creating duplicates.

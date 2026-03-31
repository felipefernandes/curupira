# Tasks: Implement Google Calendar Skill

## Task List
- [x] **Infrastructure: External Library Setup**
  - [x] Add `google-auth` and `google-auth-oauthlib` to `requirements.txt`.
  - [x] Configure `GCAL_CLIENT_ID`, `GCAL_CLIENT_SECRET`, and `GCAL_SYNC_INTERVAL_MINUTES` in `config.py` and `.env.example`.

- [x] **Database Migration**
  - [x] Add `external_id` column (TEXT, NULL) to `reminders` table.
  - [x] Create index on `external_id` for duplicate checking performance.
  - [x] Test migration on local database.

- [x] **Skill: GoogleCalendarSkill (Single Class)**
  - [x] Create `skills/google_calendar.py` inheriting from `BaseSkill`.
  - [x] Implement `name`, `display_name`, and `description` properties following MCP-Lite pattern.
  - [x] Implement `_get_client()` internal method using `httpx` for Google API calls.
  - [x] Implement `_load_token()` and `_save_token()` methods for `data/google_token.json`.
  - [x] Implement `_refresh_token()` with automatic refresh logic and error handling.

- [x] **Tool: `setup_calendar` (OAuth2 Flow)**
  - [x] Generate OAuth2 authorization URL.
  - [x] Send instructions to user via Telegram with clickable URL.
  - [x] Handle authorization code paste from user.
  - [x] Exchange code for access/refresh tokens.
  - [x] Save tokens to `data/google_token.json`.
  - [x] Confirm successful authentication.

- [x] **Tool: `list_calendar_events`**
  - [x] Add to `parameters` schema with `time_range` (string: "today", "tomorrow", "week").
  - [x] Parse time_range and convert to ISO8601 start/end times.
  - [x] Call Google Calendar API v3 events.list endpoint.
  - [x] Return formatted JSON with `self.success(events_data)`.
  - [x] Test listing for today, tomorrow, and current week.

- [x] **Tool: `add_calendar_event`**
  - [x] Add to `parameters` schema with `summary`, `start_time`, `end_time`, `description`.
  - [x] Call Google Calendar API v3 events.insert endpoint.
  - [x] Handle API errors gracefully with `self.error()`.
  - [x] Return `self.success()` with event confirmation.
  - [x] Test scheduling single events.

- [x] **Tool: `cancel_calendar_event`**
  - [x] Add to `parameters` schema with `event_id`.
  - [x] Call Google Calendar API v3 events.delete endpoint.
  - [x] Handle not found errors gracefully.
  - [x] Return `self.success()` confirmation.
  - [x] Test canceling events.

- [x] **Feature: Reminder Bridge (Background Job)**
  - [x] Create `calendar_reminder_bridge.py` in `skills/` directory.
  - [x] Implement async function to fetch upcoming events (next 4 hours).
  - [x] Check for existing reminders using `external_id` to prevent duplicates.
  - [x] Create reminders with `[AGENDA]` prefix and event's `iCalUID` as `external_id`.
  - [x] Schedule reminders for 10 minutes before event start time.
  - [x] Handle token expiration during background sync.

- [x] **Integration**
  - [x] Register `GoogleCalendarSkill()` in `core/agent.py`.
  - [x] Add calendar reminder bridge job to `bot.py`'s `JobQueue` (30-min interval).
  - [x] Ensure `.gitignore` includes `data/google_token.json`.

- [x] **Documentation**
  - [x] Create `docs/skills/GOOGLE_CALENDAR_SETUP.md` with:
    - [x] Step-by-step Google Cloud Console setup.
    - [x] Screenshots for OAuth consent screen configuration.
    - [x] How to obtain Client ID and Client Secret.
    - [x] How to run `/setup_calendar` in Telegram.
  - [x] Update `ROADMAP.md` marking Google Calendar skill as completed.
  - [x] Update `README.md` adding Google Calendar to features list.

- [ ] **Validation**
  - [x] Run `openspec validate implement-google-calendar-skill --strict`.
  - [ ] Functional test: OAuth flow with real Google account.
  - [ ] Functional test: List events, add event, cancel event.
  - [ ] Functional test: Verify background sync creates reminders correctly.
  - [ ] Functional test: Verify no duplicate reminders after multiple syncs.

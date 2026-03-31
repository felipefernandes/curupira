### Requirement: PIN-Authenticated Update Trigger
The system SHALL accept a Telegram message containing the phrase `"atualizar sistema"` (case-insensitive) and a secret keyword (`pin: <value>`) as a trigger for the update pipeline. The PIN value MUST be matched against the `REMOTE_UPDATE_PIN` environment variable using a constant-time comparison. If the PIN is absent or incorrect, the system MUST silently ignore the message with no response and no side effects.

#### Scenario: Correct PIN triggers the update pipeline
- **WHEN** the user sends a message matching `"atualizar sistema"` with a valid `pin: <PIN>` value
- **THEN** the bot sends a progress acknowledgement (`"⏳ Iniciando atualização..."`) and begins the update pipeline

#### Scenario: Wrong PIN is silently ignored
- **WHEN** the user sends a message matching `"atualizar sistema"` with an incorrect PIN
- **THEN** the bot sends no response and takes no action

#### Scenario: Update trigger without PIN is silently ignored
- **WHEN** the user sends a message matching `"atualizar sistema"` with no `pin:` present
- **THEN** the bot sends no response and takes no action

#### Scenario: REMOTE_UPDATE_PIN not configured
- **WHEN** `REMOTE_UPDATE_PIN` is not set in the environment
- **THEN** the skill MUST log a warning and return an error to the agent without exposing the missing configuration to the user

---

### Requirement: Sequential Async Update Pipeline
The system SHALL execute the update pipeline as a sequential chain of async subprocesses using `asyncio.create_subprocess_exec`. The pipeline steps MUST be: (1) `git pull`, (2) `pip install -r requirements.txt`. Each step MUST be awaited before the next begins. The combined pipeline MUST be wrapped in a configurable timeout (default: 300 seconds). If any step returns a non-zero exit code, the pipeline MUST abort and report the failure without restarting.

#### Scenario: Successful git pull and pip install
- **WHEN** both subprocesses exit with code 0 within the timeout
- **THEN** the pipeline proceeds to write the sentinel file and restart

#### Scenario: git pull fails (network error or merge conflict)
- **WHEN** `git pull` exits with a non-zero code
- **THEN** the bot sends an error message, aborts the pipeline, does NOT write the sentinel file, and does NOT restart

#### Scenario: pip install fails
- **WHEN** `git pull` succeeds but `pip install -r requirements.txt` exits with a non-zero code
- **THEN** the bot sends an error message, aborts the pipeline, does NOT write the sentinel file, and does NOT restart

#### Scenario: Pipeline exceeds timeout
- **WHEN** the combined pipeline duration exceeds 300 seconds
- **THEN** the bot cancels the subprocess, sends an error message, and does NOT restart

---

### Requirement: Sentinel-Based Post-Restart Confirmation
Before restarting, the system SHALL write a JSON sentinel file (`.update_pending`) at the project root containing at minimum `{"chat_id": <int>, "updated_at": <iso8601 timestamp>}`. On every startup, the bot SHALL check for this file. If found and the `updated_at` timestamp is less than 10 minutes old, the bot SHALL send `"✅ Sistema atualizado"` to the stored `chat_id` and delete the sentinel file. Sentinel files older than 10 minutes SHALL be deleted without sending any message.

#### Scenario: Bot restarts after successful update
- **WHEN** the bot starts and `.update_pending` exists with a recent timestamp
- **THEN** the bot sends `"✅ Sistema atualizado"` to the stored `chat_id` and deletes the file before entering normal operation

#### Scenario: Sentinel file is stale (bot crashed mid-update)
- **WHEN** the bot starts and `.update_pending` exists with a timestamp older than 10 minutes
- **THEN** the bot deletes the file and logs a warning, sending no message to the user

#### Scenario: Normal startup without sentinel
- **WHEN** the bot starts and no `.update_pending` file exists
- **THEN** the bot proceeds with normal initialization with no side effects

---

### Requirement: Process Restart via os.execv
After successfully writing the sentinel file, the system SHALL call `os.execv(sys.executable, [sys.executable] + sys.argv)` to replace the current process with a fresh interpreter instance. This MUST be the final operation in the `execute` coroutine — no code SHALL run after the `os.execv` call on success.

#### Scenario: Restart on Linux/Raspbian
- **WHEN** the update pipeline succeeds and the sentinel is written
- **THEN** the process image is replaced via `os.execv` and a new bot instance starts with the updated code

#### Scenario: Restart on non-Linux platforms (dev environment)
- **WHEN** the platform is not Linux and `os.execv` raises an exception
- **THEN** the bot logs the error and raises a descriptive exception; the sentinel file remains so the developer can inspect it

---

### Requirement: No Persistent State Added
The remote-update skill SHALL NOT add any rows to SQLite or modify any existing persistent storage. The only ephemeral file used is the `.update_pending` sentinel, which is always deleted on the next startup.

#### Scenario: Sentinel is cleaned up after use
- **WHEN** the post-restart confirmation is processed
- **THEN** the `.update_pending` file is deleted and no trace remains in SQLite

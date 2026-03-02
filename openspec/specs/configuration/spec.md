# configuration Specification

## Purpose
TBD - created by archiving change improve-user-config-maintenance. Update Purpose after archive.
## Requirements
### Requirement: Centralized Configuration File
The system MUST support a single configuration file in TOML format (`config.toml`) at the project root for centralized settings management.

#### Scenario: Loading from TOML
- **GIVEN** a `config.toml` file exists in the root directory
- **WHEN** the system initializes (`core.config`)
- **THEN** settings from the file MUST be loaded and made available as configuration constants.

#### Scenario: Fallback to Template
- **GIVEN** `config.toml` does NOT exist
- **WHEN** the system initializes
- **THEN** it MUST fall back to environment variables OR internal default values.
- **AND** it SHOULD log a warning to notify the user.

### Requirement: Priority Override Logic
The system MUST resolve configuration values using a hierarchical priority:
1. Environment Variables / OS Secrets (Highest)
2. `.env` file entries
3. `config.toml` entries
4. Hardcoded defaults (Lowest)

#### Scenario: Overriding TOML with ENV
- **GIVEN** `config.toml` has `ai_provider = "groq"`
- **AND** the environment variable `AI_PROVIDER` is set to `"gemini"`
- **WHEN** the configuration is loaded
- **THEN** `config.AI_PROVIDER` MUST be `"gemini"`.

### Requirement: Skill Feature Flipping
The system MUST allow users to selectively enable or disable bot skills via configuration flags.

#### Scenario: Disabling a Skill
- **GIVEN** the configuration has `skills.weather = false`
- **WHEN** the bot startsup (`bot.py`)
- **THEN** the `WeatherSkill` MUST NOT be registered with the `AgentBrain`.
- **AND** the bot MUST NOT attempt to use that skill during interaction.

### Requirement: Nested Preference Support
The system MUST support complex settings for specific skills (e.g., RSS feeds list, Job Hunter keywords) within the configuration file.

#### Scenario: Custom RSS Feeds
- **GIVEN** the configuration has a custom dictionary of RSS feeds under `skills.rss.feeds`
- **WHEN** the RSS skill is initialized
- **THEN** it MUST use the feeds defined in the configuration.
- **AND** ignore the hardcoded defaults.


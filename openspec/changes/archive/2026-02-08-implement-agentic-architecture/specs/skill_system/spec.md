# skill_system Specification

## Purpose
Standardize the implementation of bot capabilities (Skills) and future-proof the architecture for external tool integration (MCP).

## Requirements

### Requirement: Abstract Base Skill
The system MUST provide a `BaseSkill` abstract class that enforces a contract for all skills, ensuring they provide necessary metadata for LLM tool definitions.

#### Scenario: New Skill Implementation
1.  Developer creates a class inheriting from `BaseSkill`.
2.  Developer implements `name`, `description`, `parameters_schema`, and `execute`.
3.  The system automatically registers this skill and exposes it to the LLM without additional configuration code in `bot.py`.

### Requirement: JSON Schema Compatibility
The `BaseSkill` parameters schema MUST be compatible with the OpenAI JSON Schema format, which is the standard used by Gemini, Groq, and MCP.

#### Scenario: Schema Validation
1.  A skill defines its parameters using a standard dictionary format.
2.  The system successfully converts this into a tool definition payload accepted by the Gemini API.

### Requirement: Skill Registry
The system MUST maintain a central registry of available skills to dynamically generate the list of tools for the LLM.

#### Scenario: Dynamic loading
1.  System starts.
2.  `SkillRegistry` scans and loads enabled skills.
3.  The `AgentBrain` requests `get_all_tools()`.
4.  Registry returns the list of definitions for `WeatherSkill`, `ReminderSkill`, etc.

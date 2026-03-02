# introspection Specification

## Purpose
TBD - created by archiving change describe-capabilities. Update Purpose after archive.
## Requirements
### Requirement: List Available Skills
When requested without arguments, the introspection tool MUST return a list of all registered skills, including their names and brief descriptions.

#### Scenario: User asks "What can you do?"
- **GIVEN** the bot has registered skills "weather", "github", and "reminders"
- **WHEN** the user asks "Quais são suas habilidades?" or "O que você sabe fazer?"
- **THEN** the bot calls `describe_capabilities()`
- **AND** the tool returns a formatted list containing "weather", "github", and "reminders" with their descriptions.

### Requirement: Describe Specific Skill
When requested with a valid `skill_name`, the tool MUST return the full parameter schema and description for that skill.

#### Scenario: User asks for details heavily
- **GIVEN** the "github" skill has parameters `repo_name` and `action`
- **WHEN** the user asks "Como uso a skill do GitHub?" or "Quais parâmetros o GitHub aceita?"
- **THEN** the bot calls `describe_capabilities(skill_name="github")`
- **AND** the tool returns the text representation of the JSON schema for parameters.

#### Scenario: User asks for non-existent skill
- **WHEN** the user asks "Como voar?" and "fly" is not a skill
- **THEN** the bot calls `describe_capabilities(skill_name="fly")`
- **AND** the tool returns an informative error message listing available skills instead.

### Requirement: Token Usage Diagnostics
The system MUST be able to query its database and return an accumulated report of its API usage over time (such as prompt tokens vs completion tokens) categorized chronologically or by provider.

#### Scenario: User queries for bot token spendings
- **GIVEN** the bot has been interacting using Gemini and Groq, saving multiple usage logs
- **WHEN** the user asks "Qual foi meu custo até agora?", "Mostre o gasto de tokens"
- **THEN** the AgentBrain triggers the new `get_usage_report` introspection skill
- **AND** the tool queries `MemoryManager` to calculate the aggregate usage grouped by Provider and calculates an estimated price inside the output string to clearly inform the user.


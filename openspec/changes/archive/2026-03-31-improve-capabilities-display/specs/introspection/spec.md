## MODIFIED Requirements

### Requirement: List Available Skills
When requested without arguments, the introspection tool MUST return a grouped, emoji-annotated summary list — one entry per skill group — not a flat list of individual tools.

#### Scenario: User asks "What can you do?"
- **GIVEN** the bot has registered skills "weather", "github", and "reminders"
- **WHEN** the user asks "Quais são suas habilidades?" or "O que você sabe fazer?"
- **THEN** the bot calls `describe_capabilities()`
- **AND** the tool returns one line per skill in the format `[emoji] SkillName — resumo`
- **AND** the response does NOT enumerate individual tools

### Requirement: Describe Specific Skill
When requested with a valid `skill_name`, the tool MUST return the full list of individual tools for that skill, formatted as bullet points with their descriptions.

#### Scenario: User asks for details of a skill
- **GIVEN** the "github" skill has tools `list_repos`, `list_issues`, and `create_issue`
- **WHEN** the user asks "Me explica o GitHub" or "Como uso a skill do GitHub?"
- **THEN** the bot calls `describe_capabilities(skill_name="github")`
- **AND** the tool returns a bullet-point list of each tool with its description

#### Scenario: User asks for non-existent skill
- **WHEN** the user asks details about a skill that does not exist
- **THEN** the bot calls `describe_capabilities(skill_name="<unknown>")`
- **AND** the tool returns an informative error message
- **AND** the tool also returns the grouped summary list of available skills

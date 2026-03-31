# capabilities-display Specification

## Requirements

### Requirement: Grouped Skills Summary
When listing all capabilities without arguments, the system SHALL return a condensed list grouped by skill, with one line per skill containing an emoji, the skill name, and a short summary of what it does — not a flat enumeration of individual tools.

#### Scenario: User asks what the bot can do
- **WHEN** the user asks "O que você sabe fazer?" or "Quais são suas habilidades?"
- **THEN** the bot returns a list where each line represents one skill group
- **AND** each line follows the format: `[emoji] SkillName — resumo das capacidades`
- **AND** the total number of lines equals the number of registered skill groups (not the number of tools)

#### Scenario: Multiple tools from the same skill are condensed
- **WHEN** the GitHub skill has tools `list_repos`, `list_issues`, and `create_issue`
- **THEN** the response shows a single line: `🐙 GitHub — listar repositórios e gerenciar issues`
- **AND** the individual tool names are NOT listed

### Requirement: On-demand Skill Detail
When the user asks for details about a specific skill by name, the system SHALL return a bullet-point list of each individual tool that skill provides, with a short description per tool.

#### Scenario: User requests detail for a specific skill
- **WHEN** the user asks "Me explica o GitHub" or "O que o Git faz exatamente?"
- **THEN** the bot returns the detailed tool list for the GitHub skill
- **AND** each tool is listed as a bullet point with its description
- **AND** the response does NOT include tools from other skills

#### Scenario: User requests detail for a non-existent skill
- **WHEN** the user asks "Me explica o Spotify" and no Spotify skill is registered
- **THEN** the bot responds informing that the skill was not found
- **AND** the bot offers the grouped summary list so the user can pick a valid skill

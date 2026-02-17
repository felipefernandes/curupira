# Spec: Tool Execution Reliability

## ADDED Requirements

### Requirement: Prevent Malformed Tool Names
The AgentBrain system prompt MUST include explicit instructions prohibiting the LLM from embedding arguments in the function name field, ensuring only the exact tool identifier is used.

#### Scenario: Groq Llama 3 weather request with hardened prompt
- **WHEN** the user asks "Como está o tempo em São Paulo?" and the provider is Groq
- **THEN** the system prompt SHALL contain a negative constraint about tool call formatting
- **AND** the generated tool call name SHALL be exactly `get_weather` without any appended arguments

#### Scenario: Groq Llama 3 reminder list with hardened prompt
- **WHEN** the user asks to list reminders and the provider is Groq
- **THEN** the generated tool call name SHALL be exactly `list_reminders` without `={}` or similar suffixes

# agent_core Specification

## Purpose
Introduce a decision-making "Brain" that autonomously selects and executes tools based on user intent, replacing rigid regex pattern matching.

## Requirements

### Requirement: Native Function Calling
The system MUST utilize the Native Function Calling capabilities of the configured LLM provider (Gemini or Groq) to interpret user requests into actionable tool calls.

#### Scenario: Implicit Intent
1.  User sends "Preciso de um guarda-chuva hoje?".
2.  The LLM receives tool definitions including `get_weather`.
3.  The LLM responds with a tool call request for `get_weather(location=USER_LOCATION)`.
4.  The system executes the tool without regex parsing of the user message.

### Requirement: Multi-Turn Loop
The system MUST implement a loop that allows for tool execution results to be fed back into the LLM context to generate a final natural language response.

#### Scenario: Tool Execution & Response
1.  The system executes `get_weather` and receives JSON data.
2.  The system appends this data to the conversation history with role `tool`.
3.   The system calls the LLM again.
4.  The LLM generates "Sim, vai chover hoje em São Paulo. Leve o guarda-chuva!" based on the tool output.

### Requirement: Fallback to Text
If the LLM does not select any tool, the system MUST treat the response as a direct message to the user.

#### Scenario: Chit-chat
1.  User sends "Oi, tudo bem?".
2.  The LLM determines no tool is needed.
3.  The LLM returns text "Tudo ótimo! Como posso ajudar?".
4.  The system sends this text to the user.

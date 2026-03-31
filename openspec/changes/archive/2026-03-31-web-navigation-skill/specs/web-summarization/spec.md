## ADDED Requirements

### Requirement: Web Content Summarization
The system SHALL be able to provide a summary of the extracted text from a URL using an AI provider.

#### Scenario: Direct Summarization Request
- **GIVEN** a valid URL
- **WHEN** the `summarize` action is called
- **THEN** the system extracts the text and passes it to the LLM (Groq/Gemini) with a summarization prompt, returning the resulting summary.

### Requirement: Proactive Context Injection
The system SHALL allow the LLM to use the `WebNavigationSkill` as a tool when it needs current information from a website to answer a user's question.

#### Scenario: AI-initiated Web Search/Extraction
- **GIVEN** the user asks about a specific news item and provides a link
- **WHEN** the LLM decides to call the `web_navigation` tool
- **THEN** the tool returns the extracted text, which the LLM then uses to construct a final response in Portuguese.

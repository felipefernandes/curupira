# rss Specification

## Purpose
TBD - created by archiving change implement-rss-skill. Update Purpose after archive.
## Requirements
### Requirement: Read RSS Feed
The system MUST be able to fetch and parse an RSS or Atom feed from a given URL and return the latest entries.

#### Scenario: User asks for news from a specific topic
-   **Given** the user says "O que tem de novo no G1?"
-   **And** "G1" is a configured feed with URL "https://g1.globo.com/rss/g1/"
-   **When** the agent invokes `rss_read(url="https://g1.globo.com/rss/g1/")`
-   **Then** the tool MUST return a list of recent article titles and links.
-   **And** the agent summary MUST present these news items to the user.

### Requirement: List Configured Feeds
The system MUST provide a tool to list the pre-configured feeds so the user knows what sources are available.

#### Scenario: User asks what feeds are available
-   **Given** the user asks "Quais fontes de notícias você tem?"
-   **When** the agent invokes `rss_list()`

### Requirement: Auto-translation (Batching)
The system MUST be able to translate multiple RSS entry titles from a source language (e.g., EN, ES) to Brazilian Portuguese (PT-BR) using configured AI providers (Groq/Gemini).
-   **Given** a feed is in a foreign language.
-   **When** `rss_read` is executed with `auto_translate=True`.
-   **Then** titles SHOULD be translated in batches to optimize API usage.

### Requirement: Original Language Tags
Translated entries MUST include a tag indicating the original feed language.
-   **Given** a translated headline.
-   **When** presented to the user.
-   **Then** the title MUST include a suffix like ` (EN)` or ` (ES)`.

### Requirement: Feed Language Detection
Translation MUST be skipped for feeds already in Portuguese.
-   **Given** a feed configured as PT or PT-BR.
-   **When** `rss_read` processes the entries.
-   **Then** the translation step MUST be bypassed.

### Requirement: Error Fallback
The system MUST fallback to original titles if translation fails.
-   **Given** an API failure or timeout during translation.
-   **When** `rss_read` is processing.
-   **Then** the tool MUST return original titles and log a warning.


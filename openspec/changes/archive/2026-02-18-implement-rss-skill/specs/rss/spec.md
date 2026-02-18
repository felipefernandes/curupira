# RSS Spec

## ADDED Requirements

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
-   **Then** the tool returns a JSON of feed names and URLs.

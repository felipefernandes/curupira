# Design: RSS Skill

## Architecture
-   **Class**: `RssSkill(BaseSkill)` in `skills/rss.py`.
-   **Library**: `feedparser` (Standard for Python RSS/Atom parsing).
-   **State**: Stateless execution, but configuration-aware (reads `RSS_FEEDS`).

## Interface (Function Calling)

### `rss_read`
Reads the latest N entries from a feed URL.
```json
{
  "name": "rss_read",
  "description": "Reads the latest entries from a specific RSS/Atom feed URL. Use this to get news or updates.",
  "parameters": {
    "type": "object",
    "properties": {
      "url": { "type": "string", "description": "The URL of the RSS feed." },
      "limit": { "type": "integer", "description": "Number of entries to return (default 5)." }
    },
    "required": ["url"]
  }
}
```

### `rss_list`
Lists pre-configured feeds available in the system.
```json
{
  "name": "rss_list",
  "description": "Lists the names and URLs of pre-configured RSS feeds.",
  "parameters": { "type": "object", "properties": {}, "required": [] }
}
```

## Configuration
Feeds will be stored in `config.py` loaded from an environment variable `RSS_FEEDS_JSON` (serialized JSON) or a default dict if missing.
Structure:
```json
{
  "G1": "https://g1.globo.com/rss/g1/",
  "TechCrunch": "https://techcrunch.com/feed/"
}
```

## Security
-   `url` parameter in `rss_read` runs server-side `http` requests.
-   **Mitigation**: The skill serves verified feeds. If user inputs arbitrary URLs, `feedparser` is generally safe, but we should ensure we don't fetch internal/private IPs (SSRF protection not strictly required for personal bot but good practice). For V1, we allow any URL as it's a personal assistant.

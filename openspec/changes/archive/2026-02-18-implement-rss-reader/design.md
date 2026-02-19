# Design: RSS Reader Skill

## Architecture
- **Skill**: `RssReadSkill` (fetch) and `RssListSkill` (discovery).
- **Library**: `feedparser` (standard for Python RSS).
- **Security**: Whitelist enforcement via `config.RSS_FEEDS`.
- **Async**: Use `asyncio.to_thread` for `feedparser` (blocking I/O) with `asyncio.wait_for` timeout.

## Configuration
- `RSS_FEEDS_JSON`: Environment variable containing JSON mapping of Name -> URL.
- Defaults: G1, TechCrunch, Hacker News.

## Parameters
- `feed_identifier`: Name of the feed (case-insensitive key in config) or URL (if whitelisted).
- `limit`: Number of entries to return (default 5).

## Error Handling
- Timeout: 15 seconds.
- Invalid Feed: Catch and report.
- Unconfigured Feed: Return error listing available options (Anti-Hallucination).

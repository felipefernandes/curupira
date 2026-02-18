# Proposal: Implement RSS Skill

## Goal
Enable Curupira to fetch, parse, and summarize news and updates from RSS/Atom feeds, allowing the user to stay informed about their favorite topics (e.g., Tech, News, Dev) directly through the bot.

## Why
As a personal assistant, Curupira should proactively keep the user informed. RSS is a standard, decentralized way to consume content. This skill addresses **Issue #54** ("RSS Reader: Notícias e updates").

## Strategy
We will implement a **Native Python Skill** (`skills/rss.py`) using the `feedparser` library. This is chosen over an external MCP server to maintain low memory footprint (critical for Raspberry Pi 3) and reduce deployment complexity. Use of external MCP servers is reserved for complex tools (like Filesystem or GitHub) where the overhead is justified.

## What Changes
1.  **New Dependency**: `feedparser` added to `requirements.txt`.
2.  **New Skill**: `skills/rss.py` implementing `RssSkill`.
    -   `rss_read_feed(url)`: Fetches and parses a feed.
    -   `rss_list_feeds()`: Lists configured feeds (from env/config).
3.  **Configuration**: Add `RSS_FEEDS` (JSON/Dict) to `config.py` default or `.env` to store user's favorite feeds.

## User Review Required
-   **Dependency**: Is adding `feedparser` acceptable? (It's lightweight).
-   **Persistence**: For V1, we will store feeds in an environment variable or simple config file. Valid?

# Proposal: RSS Reader Skill

## Goal
Implement a skill to allow Curupira to read RSS/Atom feeds, enabling users to request news updates directly from the bot.

## Context
User requested a way to read news. We need a flexible RSS reader that can support configured feeds and arbitrary URLs (initially, later restricted for security).

## User Review Required
> [!IMPORTANT]
> **Security**: By default, we should restrict to a whitelist of feeds to prevent SSRF attacks if the bot runs in a privileged network.

## Proposed Changes
1.  Create `skills/rss.py` with `RssReadSkill` and `RssListSkill`.
2.  Update `core/config.py` to support `RSS_FEEDS_JSON`.
3.  Add tests in `tests/test_rss.py`.

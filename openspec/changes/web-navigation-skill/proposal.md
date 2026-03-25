## Why

This change introduces the `WebNavigationSkill` to CurupiraBOT, enabling it to access, extract, and summarize content from URLs provided by the user. Currently, the bot is limited to its internal knowledge and simple tool outputs. Web navigation is a fundamental capability for a personal assistant to provide up-to-date information, summarize articles, or research specific topics on the fly.

## What Changes

- **New Skill**: `WebNavigationSkill` in `skills/web_navigation.py`.
- **Extraction Logic**: Integration with `trafilatura` for high-quality text extraction and `httpx` for fetching content.
- **AI Integration**: The extracted text will be passed to Curupira's brain (Groq/Gemini) for summarization or analysis.
- **Dependencies**: Addition of `trafilatura` (and potentially `beautifulsoup4` as fallback) to `requirements.txt`.

## Capabilities

### New Capabilities
- `web-extraction`: Fetching HTML content from a URL and converting it to clean, readable text using `trafilatura`.
- `web-summarization`: Proactive or reactive summarization of web content to provide concise answers to the user.

### Modified Capabilities
- None.

## Impact

- **Affected code**: `core/agent.py` (to register the new skill).
- **APIs**: The bot will perform outbound HTTP requests to arbitrary URLs.
- **Dependencies**: `trafilatura` will be added.
- **Systems**: Slight increase in RAM usage during extraction, but `trafilatura` is relatively lightweight compared to a full browser engine.

## Non-goals
- Full browser rendering (JavaScript execution via Playwright/Selenium) due to Raspberry Pi 3 RAM constraints. This skill will be limited to static content and server-side rendered pages that `trafilatura` can handle.
- Periodic web scraping or monitoring (crawling). This is for on-demand information retrieval.

## Hardware Constraint Motivation
- **RAM**: By using `trafilatura` instead of a headless Chromium, we keep memory usage low enough for the RPi3 (1GB RAM).
- **CPU**: Extraction is computationally inexpensive compared to rendering.

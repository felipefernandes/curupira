## Context

CurupiraBOT currently lacks the ability to browse the web. Users often ask questions that require information from specific URLs or ask the bot to summarize articles. Following the "Diet" principle and RPi3 constraints, we need a lightweight way to extract content without a full browser engine.

## Goals / Non-Goals

**Goals:**
- Provide a `WebNavigationSkill` with `extract` and `summarize` actions.
- Use `trafilatura` for clean text extraction from HTML.
- Ensure all I/O is asynchronous using `httpx` and `asyncio.to_thread` where necessary.
- Limit extracted text size to avoid OOM or hitting LLM context limits prematurely.

**Non-Goals:**
- JavaScript execution (SPA support).
- Cookie/Session management for authenticated browsing.
- Image or media extraction.
- Automatic periodic scraping.

## Decisions

### 1. Library: Trafilatura
- **Rationale**: `trafilatura` is specifically designed for high-performance web scraping and text extraction. It is much more efficient than generic `BeautifulSoup` for cleaning article content and significantly lighter than Selenium/Playwright.
- **Alternatives**:
  - `BeautifulSoup4`: Requires more manual work to clean junk (menus, footers).
  - `Playwright`: Too heavy for RPi3 (requires Chromium/Webkit binaries).

### 2. Multi-Action Skill
- **Rationale**: Following `docs/SKILLS_FRAMEWORK.md`, we will implement a single `WebNavigationSkill` with an `action` parameter (`extract`, `summarize`).
- **Tool Descriptor**:
```python
{
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "enum": ["extract", "summarize"],
            "description": "Ação a executar: extrair texto puro ou resumir o conteúdo."
        },
        "url": {
            "type": "string",
            "description": "URL da página web."
        }
    },
    "required": ["action", "url"]
}
```

### 3. Async Extraction Flow
- **Rationale**: `httpx` will fetch the HTML. `trafilatura.extract()` is a CPU-bound operation. We should use `asyncio.to_thread` for the extraction part to avoid blocking the event loop.
- **Flow**:
  1. `httpx.get(url)` (async)
  2. `asyncio.to_thread(trafilatura.extract, html)`
  3. Return clean text or summary.

## Risks / Trade-offs

- **[Risk] OOM with Large Pages** -> **Mitigation**: Limit the `httpx` response size and truncate the extracted text to a reasonable limit (~10k characters).
- **[Risk] Blocked Requests** -> **Mitigation**: Use common User-Agent headers and handle 404/403 errors gracefully via `self.error()`.
- **[Risk] Anti-Scraping / JS Required** -> **Mitigation**: Documents clearly that SPAs/protected pages won't work.

## Open Questions
- Should we support basic search (e.g., via DuckDuckGo) in the same skill or a second one? (Decision: Separate skill for DuckDuckGo to keep `WebNavigationSkill` focused on direct URLs).

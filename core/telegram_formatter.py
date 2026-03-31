"""
TelegramFormatter — resilient LLM-output normalization for Telegram HTML mode.

Converts any LLM output (Markdown, HTML, mixed, plain) into text safe for
Telegram's HTML parse mode.  Pure stdlib: re + html — no heavy deps.

Designed to run on Raspberry Pi 3 (1 GB RAM).  All patterns are compiled
once at import time.
"""

import re
import html
from typing import Literal

# ── Telegram HTML allowlist ────────────────────────────────────────────────────

_ALLOWED_TAGS: frozenset = frozenset(
    {'b', 'i', 'u', 's', 'code', 'pre', 'a', 'tg-spoiler', 'tg-emoji'}
)

_TELEGRAM_MAX_LEN = 4096

# ── Compiled patterns ──────────────────────────────────────────────────────────

# Any HTML tag (for _strip_unsupported)
_RE_ANY_TAG = re.compile(r'<(/?)(\w[\w-]*)([^>]*)>')

# Allowed HTML tags (used as placeholders during Markdown pass)
_RE_ALLOWED_TAG = re.compile(
    r'</?(?:' + '|'.join(re.escape(t) for t in sorted(_ALLOWED_TAGS, key=len, reverse=True)) + r')(?:\s[^>]*)?>',
    re.IGNORECASE,
)

# <think>...</think> CoT blocks (Qwen3, DeepSeek-R1)
_RE_THINK_BLOCK = re.compile(r'<think>(?:.*?</think>|.*$)', re.DOTALL | re.IGNORECASE)

# HTML signal: at least one allowed tag present in the text
_RE_HTML_SIGNAL = re.compile(
    r'</?(?:' + '|'.join(re.escape(t) for t in _ALLOWED_TAGS) + r')(?:\s[^>]*)?>',
    re.IGNORECASE,
)

# Markdown signals (for format detection)
# Exclude < and > from italic/bold content to avoid false positives on HTML-like text
_RE_MD_BOLD   = re.compile(r'\*\*[^*\n<>]+\*\*|__[^_\n<>]+__')
_RE_MD_ITALIC = re.compile(
    r'(?<!\*)\*(?!\*)[^*\n<>]+(?<!\*)\*(?!\*)|(?<!_)_(?!_)[^_\n<>]+(?<!_)_(?!_)'
)
_RE_MD_HEADER  = re.compile(r'^#{1,6}\s', re.MULTILINE)
_RE_MD_FENCE   = re.compile(r'```')
_RE_MD_INLINE  = re.compile(r'`[^`]+`')
_RE_MD_LINK    = re.compile(r'\[[^\]]+\]\(https?://[^)]+\)')
_RE_MD_BULLET  = re.compile(r'^\s*[*-]\s+\S', re.MULTILINE)

# Markdown conversion patterns
# Exclude < and > from bold/italic to avoid mangling HTML-like text
_RE_CONV_FENCE  = re.compile(r'```[a-z]*\n?([\s\S]*?)```', re.IGNORECASE)
_RE_CONV_INLINE = re.compile(r'`([^`\n]+)`')
_RE_CONV_BOLD1  = re.compile(r'\*\*([^*\n<>]+?)\*\*')
_RE_CONV_BOLD2  = re.compile(r'__([^_\n<>]+?)__')
_RE_CONV_ITALIC1 = re.compile(r'(?<!\*)\*(?!\*)([^*\n<>]+?)(?<!\*)\*(?!\*)')
_RE_CONV_ITALIC2 = re.compile(r'(?<!_)_(?!_)([^_\n<>]+?)(?<!_)_(?!_)')
_RE_CONV_HEADER  = re.compile(r'^#{1,6}\s+(.+)$', re.MULTILINE)
_RE_CONV_LINK    = re.compile(r'\[([^\]]+)\]\((https?://[^)]+)\)')
_RE_CONV_BULLET  = re.compile(r'^[ \t]*[*-]\s+', re.MULTILINE)


class TelegramFormatter:
    """Converts any LLM output to Telegram-safe HTML.  All methods are static."""

    @staticmethod
    def normalize(text: str) -> str:
        """
        Main entry point.  Idempotent: calling twice is safe.

        Pipeline:
          1. Guard empty / None input
          2. Strip <think> CoT blocks
          3. Detect format (html | markdown | mixed | plain)
          4. Convert Markdown → HTML when needed
          5. Strip unsupported HTML tags
          6. Truncate to Telegram 4096-char limit
        """
        if not text:
            return text or ""

        text = _RE_THINK_BLOCK.sub('', text).strip()
        if not text:
            return ""

        fmt = TelegramFormatter._detect_format(text)

        if fmt == "plain":
            # Truncate even plain text to Telegram's limit
            if len(text) > _TELEGRAM_MAX_LEN:
                text = text[:_TELEGRAM_MAX_LEN - 3] + "..."
            return text

        if fmt in ("markdown", "mixed"):
            text = TelegramFormatter._markdown_to_html(text)

        text = TelegramFormatter._strip_unsupported(text)

        if len(text) > _TELEGRAM_MAX_LEN:
            text = text[:_TELEGRAM_MAX_LEN - 3] + "..."

        return text

    # ── Format Detection ───────────────────────────────────────────────────────

    @staticmethod
    def _detect_format(text: str) -> Literal["html", "markdown", "mixed", "plain"]:
        """Heuristically detect the text format."""
        has_html = bool(_RE_HTML_SIGNAL.search(text))

        md_score = 0
        if _RE_MD_BOLD.search(text):    md_score += 3
        if _RE_MD_FENCE.search(text):   md_score += 3
        if _RE_MD_HEADER.search(text):  md_score += 2
        if _RE_MD_LINK.search(text):    md_score += 2
        if _RE_MD_INLINE.search(text):  md_score += 1
        if _RE_MD_ITALIC.search(text):  md_score += 1
        if _RE_MD_BULLET.search(text):  md_score += 1

        has_markdown = md_score >= 1

        if has_html and has_markdown:
            return "mixed"
        if has_html:
            return "html"
        if has_markdown:
            return "markdown"
        return "plain"

    # ── Markdown → HTML ────────────────────────────────────────────────────────

    @staticmethod
    def _markdown_to_html(text: str) -> str:
        """
        Convert Markdown formatting to Telegram-compatible HTML.

        Uses a placeholder technique to protect existing HTML tags from being
        double-processed — critical for "mixed" format input.

        Conversion table:
          ```block```          → <pre>block</pre>
          `inline`             → <code>inline</code>
          **bold** / __bold__  → <b>bold</b>
          *italic* / _italic_  → <i>italic</i>
          # Header (1–6)       → <b>Header</b>
          [text](url)          → <a href="url">text</a>
          * item / - item      → • item
        """
        placeholders: dict = {}
        counter = [0]

        def _save_tag(m: re.Match) -> str:
            token = f"\x00TAG{counter[0]}\x00"
            placeholders[token] = m.group(0)
            counter[0] += 1
            return token

        # 1. Code fences FIRST — before protecting tags, so content inside
        #    fences gets html.escape()d rather than being treated as live HTML.
        text = _RE_CONV_FENCE.sub(
            lambda m: f"<pre>{html.escape(m.group(1).strip())}</pre>", text
        )

        # 2. Protect existing allowed HTML tags (after fences, so <pre> blocks
        #    created above are also shielded from further processing).
        text = _RE_ALLOWED_TAG.sub(_save_tag, text)

        # 3. Inline code
        text = _RE_CONV_INLINE.sub(
            lambda m: f"<code>{html.escape(m.group(1))}</code>", text
        )

        # 4. Bold
        text = _RE_CONV_BOLD1.sub(r'<b>\1</b>', text)
        text = _RE_CONV_BOLD2.sub(r'<b>\1</b>', text)

        # 5. Italic (after bold to avoid consuming ** as two *)
        text = _RE_CONV_ITALIC1.sub(r'<i>\1</i>', text)
        text = _RE_CONV_ITALIC2.sub(r'<i>\1</i>', text)

        # 6. Headers
        text = _RE_CONV_HEADER.sub(r'<b>\1</b>', text)

        # 7. Links
        text = _RE_CONV_LINK.sub(r'<a href="\2">\1</a>', text)

        # 8. Bullet list markers at line start
        text = _RE_CONV_BULLET.sub('• ', text)

        # 9. Restore placeholders
        for token, tag in placeholders.items():
            text = text.replace(token, tag)

        return text

    # ── Tag Stripping ──────────────────────────────────────────────────────────

    @staticmethod
    def _strip_unsupported(text: str) -> str:
        """Remove HTML tags not in Telegram's allowlist, keeping text content."""
        def _replace(m: re.Match) -> str:
            if m.group(2).lower() in _ALLOWED_TAGS:
                return m.group(0)
            return ''
        return _RE_ANY_TAG.sub(_replace, text)


# ── Module-level alias for backward compatibility ──────────────────────────────
# bot.py and tests can continue using _strip_unsupported_html without changes.

def _strip_unsupported_html(text: str) -> str:
    """Alias for TelegramFormatter._strip_unsupported (backward compat)."""
    return TelegramFormatter._strip_unsupported(text)

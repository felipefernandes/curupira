"""
Skill RSS: leitura e listagem de RSS/Atom feeds.
Ref: Issue #54 - https://github.com/felipefernandes/curupira/issues/54
"""

import asyncio
import logging
from typing import Any, Dict, List

import feedparser

_USER_AGENT = "Curupira-Bot/1.0 (RSS reader; +https://github.com/felipefernandes/curupira)"

from core import config
from skills.base import BaseSkill

logger = logging.getLogger(__name__)


class RssReadSkill(BaseSkill):
    """Reads the latest entries from an RSS/Atom feed URL."""

    @property
    def name(self) -> str:
        return "rss_read"

    @property
    def display_name(self) -> str:
        return "📰 Ler Feed RSS"

    @property
    def description(self) -> str:
        return (
            "Reads the latest entries from a specific RSS/Atom feed URL. "
            "Use this to get news or updates from a website."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The NAME of a configured feed (e.g. 'G1', 'TechCrunch'). Must be in config.py. Use 'rss_list' to see available options."
                },
                "limit": {
                    "type": "integer",
                    "description": (
                        "Maximum number of entries to return. Default is 5."
                    )
                }
            },
            "required": ["url"]
        }

    async def execute(self, context: Dict[str, Any], **kwargs) -> Any:
        url_or_name: str = kwargs.get("url", "").strip()
        limit: int = kwargs.get("limit", 5)

        # 1. Resolve URL from Config (Security: Whitelist Only)
        url = None
        
        # Check exact match
        if url_or_name in config.RSS_FEEDS:
            url = config.RSS_FEEDS[url_or_name]
            logger.info(f"Resolving feed name '{url_or_name}' to URL: {url}")
        else:
            # Check case-insensitive match
            for name, feed_url in config.RSS_FEEDS.items():
                if name.lower() == url_or_name.lower():
                    url = feed_url
                    logger.info(f"Resolving feed name '{url_or_name}' to URL: {url}")
                    break
        
        if not url:
            return {
                "error": f"Feed não configurado: '{url_or_name}'",
                "reason": "Security: Apenas feeds listados no 'config.py' são permitidos para evitar SSRF. Adicione a URL lá primeiro."
            }

        logger.info(f"Fetching RSS feed: {url} (limit={limit})")

        try:
            feed = await asyncio.wait_for(
                asyncio.to_thread(feedparser.parse, url, agent=_USER_AGENT),
                timeout=15,
            )
        except asyncio.TimeoutError:
            return {"error": f"Timeout ao buscar o feed: {url}"}

        if feed.bozo and not feed.entries:
            bozo_reason = str(getattr(feed, "bozo_exception", "unknown"))
            logger.warning(f"Feed inválido ou inacessível: {url} — {bozo_reason}")
            return {"error": f"Não foi possível ler o feed: {url}", "reason": bozo_reason}

        entries: List[Dict[str, str]] = []
        for entry in feed.entries[:limit]:
            entries.append({
                "title": entry.get("title", "Sem título"),
                "link": entry.get("link", ""),
                "published": entry.get("published", ""),
            })

        return {
            "feed_title": feed.feed.get("title", url),
            "total_available": len(feed.entries),
            "entries": entries,
        }


class RssListSkill(BaseSkill):
    """Lists pre-configured RSS feeds available in the system."""

    @property
    def name(self) -> str:
        return "rss_list"

    @property
    def display_name(self) -> str:
        return "📋 Listar Feeds RSS"

    @property
    def description(self) -> str:
        return (
            "Lists the names and URLs of pre-configured RSS feeds. "
            "Use this when the user wants to know available news sources."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {},
            "required": []
        }

    async def execute(self, context: Dict[str, Any], **kwargs) -> Any:
        feeds = config.RSS_FEEDS

        if not feeds:
            return {"message": "Nenhum feed RSS configurado.", "feeds": []}

        feeds_list = [
            {"name": name, "url": url}
            for name, url in feeds.items()
        ]

        return {
            "total": len(feeds_list),
            "feeds": feeds_list,
        }

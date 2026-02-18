"""
Skill RSS: leitura e listagem de RSS/Atom feeds.
Ref: Issue #54 - https://github.com/felipefernandes/curupira/issues/54
"""

import asyncio
import logging
from typing import Any, Dict, List

import feedparser

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
                    "description": "The URL of the RSS/Atom feed."
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
        url: str = kwargs["url"]
        limit: int = kwargs.get("limit", 5)

        logger.info(f"Fetching RSS feed: {url} (limit={limit})")

        try:
            feed = await asyncio.wait_for(
                asyncio.to_thread(feedparser.parse, url),
                timeout=15,
            )
        except asyncio.TimeoutError:
            return {"error": f"Timeout ao buscar o feed: {url}"}

        if feed.bozo and not feed.entries:
            return {"error": f"Não foi possível ler o feed: {url}"}

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

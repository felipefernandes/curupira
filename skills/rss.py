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
        return "Busca as últimas notícias/entradas de um feed RSS configurado."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "feed_identifier": {
                    "type": "string",
                    "description": "The NAME of a configured feed (e.g. 'G1', 'TechCrunch') or a whitelisted URL. Use 'rss_list' to see options."
                },
                "limit": {
                    "type": "integer",
                    "description": (
                        "Maximum number of entries to return. Default is 5."
                    )
                }
            },
            "required": ["feed_identifier"]
        }

    async def execute(self, context: Dict[str, Any], **kwargs) -> Any:
        feed_identifier: str = kwargs.get("feed_identifier", "").strip()
        try:
            limit = int(kwargs.get("limit", 5))
        except (ValueError, TypeError):
            limit = 5

        # Input Validation
        if not feed_identifier:
            return self.error("Nome do feed não fornecido.")

        if limit < 1:
            return self.error("Limite inválido.")

        # 1. Resolve URL from Config (Security: Whitelist Only)
        url = None
        
        # Check exact match
        if feed_identifier in config.RSS_FEEDS:
            url = config.RSS_FEEDS[feed_identifier]
            logger.info(f"Resolving feed '{feed_identifier}' to URL: {url}")
        else:
            # Check case-insensitive match (O(N) is fine for small config)
            for name, feed_url in config.RSS_FEEDS.items():
                if name.lower() == feed_identifier.lower():
                    url = feed_url
                    logger.info(f"Resolving feed '{feed_identifier}' to URL: {url}")
                    break
        
        if not url:
            available_feeds = ", ".join(config.RSS_FEEDS.keys())
            return self.error(f"Feed não configurado: '{feed_identifier}'. Opções disponíveis: {available_feeds}")

        logger.info(f"Fetching RSS feed: {url} (limit={limit})")

        try:
            feed = await asyncio.wait_for(
                asyncio.to_thread(feedparser.parse, url, agent=_USER_AGENT),
                timeout=15,
            )
        except asyncio.TimeoutError:
            return self.error(f"Timeout ao buscar o feed: {url}")

        if feed.bozo and not feed.entries:
            bozo_reason = str(getattr(feed, "bozo_exception", "unknown"))
            logger.warning(f"Feed inválido ou inacessível: {url} — {bozo_reason}")
            return self.error(f"Não foi possível ler o feed: {url} ({bozo_reason})")

        entries: List[Dict[str, str]] = []
        for entry in feed.entries[:limit]:
            entries.append({
                "title": entry.get("title", "Sem título"),
                "link": entry.get("link", ""),
                "published": entry.get("published", ""),
            })

        return self.success({
            "feed_title": feed.feed.get("title", url),
            "total_available": len(feed.entries),
            "entries": entries,
        })


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
        return "Lista os nomes e URLs dos feeds RSS pré-configurados."

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
            return self.success({"feeds": []}, message="Nenhum feed RSS configurado.")

        feeds_list = [
            {"name": name, "url": url}
            for name, url in feeds.items()
        ]

        return self.success({
            "total": len(feeds_list),
            "feeds": feeds_list,
        })

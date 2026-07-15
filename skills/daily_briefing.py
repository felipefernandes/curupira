"""
Skill Daily Briefing: agrega clima, agenda e notícias em um briefing matinal.

Substitui a saudação simples do heartbeat por um briefing completo
quando habilitada via config.toml ([skills] daily_briefing = true).
"""

import logging
from typing import Any, Dict, List, Optional

from skills.base import BaseSkill

logger = logging.getLogger(__name__)


class DailyBriefingSkill(BaseSkill):
    """Gathers weather, calendar events, and news for a daily briefing."""

    def __init__(
        self,
        weather_skill: Optional[BaseSkill] = None,
        calendar_skill: Optional[BaseSkill] = None,
        rss_skill: Optional[BaseSkill] = None,
        ai_news_skill: Optional[BaseSkill] = None,
    ):
        self._weather = weather_skill
        self._calendar = calendar_skill
        self._rss = rss_skill
        self._ai_news = ai_news_skill

    @property
    def name(self) -> str:
        return "daily_briefing"

    @property
    def display_name(self) -> str:
        return "📋 Briefing Diário"

    @property
    def skill_group(self) -> str:
        return "daily_briefing"

    @property
    def skill_group_emoji(self) -> str:
        return "📋"

    @property
    def description(self) -> str:
        return "Coleta dados de clima, agenda e notícias para montar um briefing diário."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "Cidade para previsão do tempo (opcional).",
                }
            },
            "required": [],
        }

    async def execute(self, context: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        city = kwargs.get("city", "São Paulo")
        briefing: Dict[str, Any] = {}

        # 1. Weather
        briefing["weather"] = await self._gather_weather(context, city)

        # 2. Calendar events for today
        briefing["events"] = await self._gather_events(context)

        # 3. News headlines
        briefing["news"] = await self._gather_news(context)

        return self.success(briefing)

    async def _gather_weather(
        self, context: Dict[str, Any], city: str
    ) -> Optional[Dict[str, Any]]:
        if self._weather is None:
            return None
        try:
            result = await self._weather.execute(context, city=city)
            if result.get("status") == "success":
                return result.get("data")
            logger.warning("Weather fetch failed: %s", result.get("error"))
        except Exception as e:
            logger.warning("Weather fetch error: %s", e)
        return None

    async def _gather_events(
        self, context: Dict[str, Any]
    ) -> Optional[List[Dict[str, Any]]]:
        if self._calendar is None:
            return None
        try:
            result = await self._calendar.execute(
                context, action="list_calendar_events", time_range="today"
            )
            if result.get("status") == "success":
                return result.get("data", {}).get("events", [])
            logger.warning("Calendar fetch failed: %s", result.get("error"))
        except Exception as e:
            logger.warning("Calendar fetch error: %s", e)
        return None

    async def _gather_news(
        self, context: Dict[str, Any]
    ) -> Optional[List[Dict[str, Any]]]:
        all_entries: List[Dict[str, Any]] = []

        # 1. RSS Feeds
        if self._rss is not None:
            from core import config

            feeds = list(config.RSS_FEEDS.keys())[:2]  # Max 2 feeds
            for feed_name in feeds:
                try:
                    result = await self._rss.execute(
                        context, feed_identifier=feed_name, limit=3
                    )
                    if result.get("status") == "success":
                        entries = result.get("data", {}).get("entries", [])
                        for entry in entries:
                            all_entries.append(
                                {
                                    "source": feed_name,
                                    "title": entry.get("title", ""),
                                    "link": entry.get("link", ""),
                                }
                            )
                except Exception as e:
                    logger.warning("RSS fetch error for %s: %s", feed_name, e)

        # 2. AI News API (mcp_ai_news)
        if self._ai_news is not None:
            try:
                result = await self._ai_news.execute(context, source="all")
                if result.get("status") == "success":
                    ai_entries = result.get("data", {}).get("entries", [])
                    for entry in ai_entries:
                        all_entries.append(
                            {
                                "source": entry.get("source", "IA News"),
                                "title": entry.get("title", ""),
                                "link": entry.get("link", ""),
                            }
                        )
            except Exception as e:
                logger.warning("AI News fetch error: %s", e)

        return all_entries if all_entries else None

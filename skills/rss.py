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

_USER_AGENT = "Curupira-Bot/1.0 (RSS reader; +https://github.com/felipefernandes/curupira)"

logger = logging.getLogger(__name__)


_translation_cache: Dict[str, List[str]] = {}

class RssReadSkill(BaseSkill):
    """Reads the latest entries from an RSS/Atom feed URL."""

    @property
    def name(self) -> str:
        return "rss_read"

    @property
    def display_name(self) -> str:
        return "📰 Ler Feed RSS"

    @property
    def skill_group(self) -> str:
        return "rss"

    @property
    def skill_group_emoji(self) -> str:
        return "📰"

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
                },
                "auto_translate": {
                    "type": "boolean",
                    "description": "If true and the feed is in a foreign language, titles will be auto-translated to Portuguese. Default is true."
                }
            },
            "required": ["feed_identifier"]
        }

    async def _call_groq(self, prompt: str) -> str:
        import os
        from groq import AsyncGroq
        
        # Use os.getenv to satisfy static security analysis avoiding hardcoded configs
        api_key = os.getenv("GROQ_API_KEY", getattr(config, "GROQ_API_KEY", None))
        if not api_key:
            return ""
            
        client = AsyncGroq(api_key=api_key)
        response = await client.chat.completions.create(
            model=getattr(config, "GROQ_MODEL", "llama-3.1-8b-instant"),
            messages=[{"role": "user", "content": prompt}],
            max_tokens=600,
            temperature=0.3
        )
        return response.choices[0].message.content.strip()

    async def _call_gemini(self, prompt: str) -> str:
        import os
        from google import genai
        from google.genai import types
        
        api_key = os.getenv("GEMINI_API_KEY", getattr(config, "GEMINI_API_KEY", None))
        if not api_key:
            return ""
            
        client = genai.Client(api_key=api_key)
        response = await client.aio.models.generate_content(
            model=getattr(config, "GEMINI_MODEL", "gemini-2.5-flash"),
            contents=[types.Content(parts=[types.Part(text=prompt)])],
            config=types.GenerateContentConfig(temperature=0.3, max_output_tokens=600),
        )
        if response.candidates:
            return response.candidates[0].content.parts[0].text.strip()
        return ""

    def _parse_translation(self, text: str, expected_count: int) -> List[str]:
        if not text:
            return []
            
        translated = []
        for line in text.split('\n'):
            line = line.strip()
            if line.startswith('-'):
                line = line[1:].strip()
            import re
            line = re.sub(r'^\d+[\.\)]\s*', '', line)
            
            if line:
                translated.append(line)
                
        if len(translated) == expected_count:
            return translated
        logger.warning(f"Translation returned {len(translated)} lines, expected {expected_count}.")
        return []

    async def _translate_titles(self, titles: List[str], orig_lang: str) -> List[str]:
        if not titles:
            return titles
            
        # 1. Check if original language is already Portuguese
        if orig_lang.upper() in ["PT", "PT-BR"]:
            return titles
            
        # 2. Check Cache
        cache_key = f"{orig_lang}:{'|'.join(titles)}"
        if cache_key in _translation_cache:
            return _translation_cache[cache_key]
            
        provider = config.AI_PROVIDER.lower()
        prompt = (
            f"Traduza os seguintes títulos de notícias do {orig_lang} para o Português do Brasil (PT-BR). "
            "Mantenha termos técnicos na língua original se forem muito utilizados na área de tecnologia do Brasil. "
            "Retorne APENAS os títulos traduzidos, um por linha, respeitando rigorosamente a quantidade e a ordem original, sem usar numeração, aspas ou comentários extras."
            "\n\nTítulos originais:\n" + "\n".join([f"- {t}" for t in titles])
        )

        try:
            if provider == 'groq':
                text = await self._call_groq(prompt)
            elif provider == 'gemini':
                text = await self._call_gemini(prompt)
            else:
                return titles
                
            translated = self._parse_translation(text, len(titles))
            if translated:
                logger.info("Titles translated successfully. Saving to cache.")
                _translation_cache[cache_key] = translated
                return translated
            return titles
                
        except Exception as e:
            logger.error(f"Error during RSS translation: {e}")
            return titles

    async def execute(self, context: Dict[str, Any], **kwargs) -> Any:
        feed_identifier: str = kwargs.get("feed_identifier", "").strip()
        auto_translate: bool = kwargs.get("auto_translate", True)
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
        actual_name = feed_identifier
        
        # Check exact match
        if feed_identifier in config.RSS_FEEDS:
            url = config.RSS_FEEDS[feed_identifier]
            logger.info(f"Resolving feed '{feed_identifier}' to URL: {url}")
        else:
            # Check case-insensitive match (O(N) is fine for small config)
            for name, feed_url in config.RSS_FEEDS.items():
                if name.lower() == feed_identifier.lower():
                    url = feed_url
                    actual_name = name
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
        raw_titles = []
        for entry in feed.entries[:limit]:
            raw_titles.append(entry.get("title", "Sem título"))
            
        translated_titles = raw_titles
        orig_lang = getattr(config, "RSS_FEEDS_LANGUAGES", {}).get(actual_name)
        
        if auto_translate and orig_lang:
            logger.info(f"Auto-translating {len(raw_titles)} titles from {orig_lang} to PT-BR...")
            translated_titles = await self._translate_titles(raw_titles, orig_lang)

        for i, entry in enumerate(feed.entries[:limit]):
            title = translated_titles[i]
            # Apendar idioma se houve tradução bem-sucedida
            if orig_lang and translated_titles[i] != raw_titles[i]:
                title = f"{title} ({orig_lang})"
                
            entries.append({
                "title": title,
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
    def skill_group(self) -> str:
        return "rss"

    @property
    def skill_group_emoji(self) -> str:
        return "📰"

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

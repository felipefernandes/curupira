import logging
import asyncio
from typing import Any, Dict, List, Optional
import httpx

from skills.base import BaseSkill
from core import config

logger = logging.getLogger(__name__)


class AINewsSkill(BaseSkill):
    """
    Skill to aggregate AI news, ArXiv papers, and trending GitHub repos
    by consuming the mcp_ai_news REST API.
    """

    def __init__(self, api_url: Optional[str] = None, timeout: Optional[float] = None):
        self.api_url = (api_url or config.AI_NEWS_API_URL).rstrip("/")
        self.default_sources = config.AI_NEWS_FETCH_SOURCES
        self.default_limit = config.AI_NEWS_LIMIT_PER_SOURCE
        self.timeout = timeout or config.AI_NEWS_TIMEOUT

    @property
    def name(self) -> str:
        return "ai_news"

    @property
    def display_name(self) -> str:
        return "🤖 Notícias de IA"

    @property
    def skill_group(self) -> str:
        return "ai_news"

    @property
    def skill_group_emoji(self) -> str:
        return "🤖"

    @property
    def description(self) -> str:
        return (
            "Obtém as últimas notícias sobre Inteligência Artificial, papers do ArXiv "
            "e repositórios em alta (trending) no GitHub."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "source": {
                    "type": "string",
                    "description": "Fonte a ser consultada: 'news', 'arxiv', 'github' ou 'all'.",
                    "enum": ["news", "arxiv", "github", "all"],
                },
                "limit": {
                    "type": "integer",
                    "description": "Número máximo de itens por fonte a retornar (padrão: 3).",
                },
            },
            "required": [],
        }

    async def execute(self, context: Dict[str, Any], **kwargs: Any) -> Dict[str, Any]:
        source = kwargs.get("source", "all")
        limit = kwargs.get("limit", self.default_limit)

        if not self.api_url:
            return self.error("URL da API mcp_ai_news não configurada.")

        # Determine which categories to fetch
        if source == "all":
            sources_to_fetch = self.default_sources
        else:
            sources_to_fetch = [source]

        tasks = []
        for src in sources_to_fetch:
            if src in ["news", "arxiv", "github"]:
                tasks.append(self._fetch_category(src, limit))

        if not tasks:
            return self.success({"entries": []})

        # Run requests concurrently to minimize latency (Render cold start handling)
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_entries: List[Dict[str, Any]] = []
        errors_occurred = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(
                    "Exceção capturada na execução concorrente do mcp_ai_news: %s",
                    result,
                    exc_info=result,
                )
                errors_occurred.append(str(result))
                continue
            if isinstance(result, list):
                all_entries.extend(result)

        # Se houveram erros de concorrência e nenhuma notícia foi obtida, reporta erro
        if errors_occurred and not all_entries:
            return self.error(f"Falha total ao buscar mcp_ai_news. Erros: {'; '.join(errors_occurred)}")

        return self.success({"entries": all_entries})

    async def _fetch_category(self, category: str, limit: int) -> List[Dict[str, Any]]:
        # Map category to corresponding endpoint and parameters based on mcp_ai_news design
        if category == "arxiv":
            endpoint = f"{self.api_url}/papers"
            params = {"max_results": limit}
        elif category == "github":
            endpoint = f"{self.api_url}/github"
            params = {"max_results": limit}
        else:
            endpoint = f"{self.api_url}/news"
            params = {"limit": limit}

        try:
            # Set a slightly longer timeout to handle Render cold start,
            # but avoid blocking the loop too much
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(endpoint, params=params)
                if response.status_code != 200:
                    logger.error(
                        "API mcp_ai_news retornou status %s para a categoria %s. Resposta: %s",
                        response.status_code,
                        category,
                        response.text[:200],
                    )
                    return []

                try:
                    data = response.json()
                except ValueError as exc:
                    logger.error(
                        "Falha ao decodificar JSON do mcp_ai_news para %s: %s. Resposta: %s",
                        category,
                        exc,
                        response.text[:200],
                    )
                    return []

                if not isinstance(data, list):
                    logger.error(
                        "Resposta inválida da API mcp_ai_news para %s (esperava lista, recebeu %s). Resposta: %s",
                        category,
                        type(data).__name__,
                        str(data)[:200],
                    )
                    return []

                # Normalize entries
                normalized = []
                for item in data[:limit]:
                    # Extract attributes based on endpoint-specific returns
                    title = item.get("title") or item.get("name") or "Sem título"
                    link = item.get("link") or item.get("url") or ""
                    summary = item.get("summary") or item.get("description") or ""

                    # Specific metadata to give context
                    source_label = "IA News"
                    if category == "arxiv":
                        source_label = "ArXiv Paper"
                        authors = item.get("authors")
                        if authors:
                            summary = f"Autores: {', '.join(authors)}. {summary}"
                    elif category == "github":
                        source_label = "GitHub Trending"
                        stars = item.get("stars")
                        lang = item.get("language")
                        meta = []
                        if stars:
                            meta.append(f"⭐ {stars}")
                        if lang:
                            meta.append(lang)
                        if meta:
                            summary = f"[{' | '.join(meta)}] {summary}"

                    normalized.append(
                        {
                            "source": source_label,
                            "title": title.strip(),
                            "link": link.strip(),
                            "summary": summary.strip(),
                        }
                    )
                return normalized

        except httpx.RequestError as exc:
            logger.error(
                "Falha na requisição HTTP ao mcp_ai_news (%s): %s", category, exc
            )
            raise exc
        except Exception as exc:
            logger.error("Erro inesperado ao buscar %s do mcp_ai_news: %s", category, exc)
            raise exc

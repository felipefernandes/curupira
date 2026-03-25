"""
Skill Web Navigation: extração e resumo de conteúdo web via URL.
Usa trafilatura para extração limpa de texto e httpx para fetch assíncrono.
"""

import asyncio
import logging
from typing import Any, Dict

import httpx
import trafilatura

from skills.base import BaseSkill

logger = logging.getLogger(__name__)

_USER_AGENT = (
    "Curupira-Bot/1.0 (+https://github.com/felipefernandes/curupira)"
)

# Safety limits for RPi3 (1GB RAM)
_MAX_HTML_BYTES = 500_000  # 500KB max HTML fetch
_MAX_TEXT_CHARS = 10_000   # 10k chars max extracted text
_HTTP_TIMEOUT = 15.0       # seconds


class WebNavigationSkill(BaseSkill):
    """Extracts or summarizes web page content from a given URL."""

    @property
    def name(self) -> str:
        return "web_navigation"

    @property
    def display_name(self) -> str:
        return "🌐 Navegação Web"

    @property
    def skill_group(self) -> str:
        return "web_navigation"

    @property
    def skill_group_emoji(self) -> str:
        return "🌐"

    @property
    def description(self) -> str:
        return (
            "Acessa uma URL e extrai o texto principal da página (sem menus, "
            "anúncios ou rodapés). Pode retornar o texto bruto ou pedir um "
            "resumo. Use a ação 'extract' para texto completo ou 'summarize' "
            "para obter um resumo conciso em português."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["extract", "summarize"],
                    "description": (
                        "Ação a executar: 'extract' retorna o texto limpo, "
                        "'summarize' retorna o texto com instrução de resumo."
                    ),
                },
                "url": {
                    "type": "string",
                    "description": "URL da página web.",
                },
            },
            "required": ["action", "url"],
        }

    async def execute(self, context: Dict[str, Any], **kwargs) -> Any:
        action: str = kwargs.get("action", "").strip()
        url: str = kwargs.get("url", "").strip()

        if action not in ("extract", "summarize"):
            return self.error(
                f"Ação inválida: '{action}'. Use 'extract' ou 'summarize'."
            )

        if not url:
            return self.error("URL não fornecida.")

        result = await self._extract(url)
        if isinstance(result, dict):
            return result  # _extract returned an error dict
        text = result

        if action == "extract":
            return self.success(
                {"url": url, "text": text, "length": len(text)},
                message="Texto extraído com sucesso.",
            )

        # summarize: return text with instruction for the LLM
        return self.success(
            {"url": url, "text": text, "length": len(text)},
            message=(
                "Resuma o conteúdo abaixo de forma concisa em português "
                "brasileiro, destacando os pontos principais."
            ),
        )

    async def _extract(self, url: str) -> Any:
        """Fetch URL and extract clean text. Returns text or error dict."""
        try:
            async with httpx.AsyncClient(
                follow_redirects=True,
                timeout=_HTTP_TIMEOUT,
                headers={"User-Agent": _USER_AGENT},
            ) as client:
                response = await client.get(url)
                response.raise_for_status()

                # RAM safety: limit the HTML we process
                html = response.text[:_MAX_HTML_BYTES]

        except httpx.TimeoutException:
            return self.error(f"Timeout ao acessar a URL: {url}")
        except httpx.HTTPStatusError as exc:
            code = exc.response.status_code
            return self.error(f"Erro HTTP {code} ao acessar: {url}")
        except httpx.RequestError as exc:
            return self.error(f"Erro de conexão ao acessar {url}: {exc}")

        # trafilatura.extract is CPU-bound; run in thread
        text = await asyncio.to_thread(trafilatura.extract, html)

        if not text:
            return self.error(
                "Não foi possível extrair texto da página. "
                "O site pode exigir JavaScript ou estar protegido."
            )

        # Truncate for RAM and LLM context safety
        if len(text) > _MAX_TEXT_CHARS:
            text = text[:_MAX_TEXT_CHARS] + "\n\n[...texto truncado...]"

        return text

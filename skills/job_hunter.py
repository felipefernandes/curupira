"""
Skill Job Hunter: busca de vagas de emprego via serviço externo.
Ref: Issue #95 - https://github.com/felipefernandes/curupira/issues/95
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

import requests

from core import config
from skills.base import BaseSkill

logger = logging.getLogger(__name__)


def _headers() -> Dict[str, str]:
    return {"Authorization": f"Bearer {config.JOB_HUNTER_TOKEN}"}


def _check_config() -> Optional[str]:
    """Returns an error message if required config is missing."""
    if not config.JOB_HUNTER_URL:
        return "JOB_HUNTER_URL não configurada."
    if not config.JOB_HUNTER_TOKEN:
        return "JOB_HUNTER_TOKEN não configurado."
    return None


class JobHunterRunSearchSkill(BaseSkill):
    """Executes a job search via the Job Hunter service."""

    @property
    def name(self) -> str:
        return "job_hunter_run_search"

    @property
    def display_name(self) -> str:
        return "🔍 Buscar Vagas"

    @property
    def skill_group(self) -> str:
        return "jobs"

    @property
    def skill_group_emoji(self) -> str:
        return "💼"

    @property
    def description(self) -> str:
        return "Busca, avalia via IA e notifica vagas de emprego baseadas nas configurações atuais."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "sources": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Lista de domínios para buscar vagas "
                        "(ex: ['gupy.io', 'lever.co']). "
                        "Se omitido, usa as configurações pessoais ou defaults do servidor."
                    ),
                },
                "keywords": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Lista de palavras-chave para a busca "
                        "(ex: ['Product Manager', 'Agente de IA']). "
                        "Se omitido, usa as configurações pessoais ou defaults do servidor."
                    ),
                },
                "prompt_override": {
                    "type": "string",
                    "description": (
                        "Prompt customizado para avaliação das vagas pela IA. "
                        "Se omitido, usa o prompt padrão do servidor."
                    ),
                },
                "score_cutoff": {
                    "type": "number",
                    "description": (
                        "Nota mínima (0-10) para uma vaga ser aprovada. "
                        "Se omitido, usa a configuração pessoal ou o default do servidor."
                    ),
                },
            },
            "required": [],
        }

    async def execute(self, context: Dict[str, Any], **kwargs) -> Any:
        err = _check_config()
        if err:
            return self.error(err)

        _kw_sources = kwargs.get("sources")
        _kw_keywords = kwargs.get("keywords")
        _kw_cutoff = kwargs.get("score_cutoff")

        # config.toml takes priority over LLM-provided kwargs to prevent
        # hallucinated values (e.g. from failed_generation recovery) from
        # overriding the user's personal preferences.
        sources: Optional[List[str]] = config.JOB_HUNTER_SOURCES if config.JOB_HUNTER_SOURCES is not None else _kw_sources
        keywords: Optional[List[str]] = config.JOB_HUNTER_KEYWORDS if config.JOB_HUNTER_KEYWORDS is not None else _kw_keywords
        prompt_override: Optional[str] = kwargs.get("prompt_override")
        score_cutoff: Optional[float] = config.JOB_HUNTER_SCORE_CUTOFF if config.JOB_HUNTER_SCORE_CUTOFF is not None else _kw_cutoff

        sources_origin = "config" if config.JOB_HUNTER_SOURCES is not None else "kwargs"
        keywords_origin = "config" if config.JOB_HUNTER_KEYWORDS is not None else "kwargs"
        cutoff_origin = "config" if config.JOB_HUNTER_SCORE_CUTOFF is not None else "kwargs"

        logger.info(
            "Job Hunter: valores efetivos — "
            "sources=%s [%s], keywords=%s [%s], score_cutoff=%s [%s]",
            sources, sources_origin,
            keywords, keywords_origin,
            score_cutoff, cutoff_origin,
        )

        if sources and not all(isinstance(s, str) for s in sources):
            return self.error("Fontes (sources) devem ser uma lista de strings.")
        if keywords and not all(isinstance(k, str) for k in keywords):
            return self.error("Palavras-chave (keywords) devem ser uma lista de strings.")

        body: Dict[str, Any] = {}
        if sources:
            body["sources"] = sources
        if keywords:
            body["keywords"] = keywords
        if prompt_override:
            body["prompt_override"] = prompt_override
        if score_cutoff is not None:
            body["score_cutoff"] = float(score_cutoff)

        logger.info("Job Hunter: iniciando busca com body_keys=%s", list(body.keys()))

        try:
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    requests.post,
                    f"{config.JOB_HUNTER_URL}/api/run_search",
                    headers=_headers(),
                    json=body,
                    timeout=90,
                ),
                timeout=95,
            )
            response.raise_for_status()
            result = response.json()
            logger.info(
                f"Job Hunter: busca concluída — fetched={result.get('fetched')}, "
                f"approved={result.get('approved')}"
            )
            return self.success({
                "search_results": result,
                "effective_criteria_used": {
                    "sources": sources,
                    "keywords": keywords,
                    "score_cutoff": score_cutoff,
                }
            })
        except asyncio.TimeoutError:
            return self.error("Timeout ao executar a busca de vagas (>95s).")
        except requests.HTTPError as e:
            return self.error(f"Erro HTTP {e.response.status_code}: {e.response.text}")
        except requests.RequestException as e:
            return self.error(f"Erro de conexão com o servidor de vagas: {e}")


class JobHunterGetDefaultsSkill(BaseSkill):
    """Returns the default configuration of the Job Hunter server."""

    @property
    def name(self) -> str:
        return "job_hunter_get_defaults"

    @property
    def display_name(self) -> str:
        return "⚙️ Config Padrão de Vagas"

    @property
    def skill_group(self) -> str:
        return "jobs"

    @property
    def skill_group_emoji(self) -> str:
        return "💼"

    @property
    def description(self) -> str:
        return "Retorna as configurações padrão do servidor de busca de vagas."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {},
            "required": [],
        }

    async def execute(self, context: Dict[str, Any], **kwargs) -> Any:
        err = _check_config()
        if err:
            return self.error(err)

        logger.info("Job Hunter: buscando configurações padrão do servidor.")

        try:
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    requests.get,
                    f"{config.JOB_HUNTER_URL}/api/config_endpoint",
                    headers=_headers(),
                    timeout=15,
                ),
                timeout=20,
            )
            response.raise_for_status()
            server_defaults = response.json()

            effective_sources = config.JOB_HUNTER_SOURCES if config.JOB_HUNTER_SOURCES is not None else server_defaults.get("sources")
            effective_keywords = config.JOB_HUNTER_KEYWORDS if config.JOB_HUNTER_KEYWORDS is not None else server_defaults.get("keywords")
            effective_score_cutoff = config.JOB_HUNTER_SCORE_CUTOFF if config.JOB_HUNTER_SCORE_CUTOFF is not None else server_defaults.get("score_cutoff")

            prompt_evaluation = (
                server_defaults.get("prompt_override")
                or server_defaults.get("evaluation_prompt")
                or ""
            )

            return self.success({
                "server_defaults": server_defaults,
                "local_overrides": {
                    "sources": config.JOB_HUNTER_SOURCES,
                    "keywords": config.JOB_HUNTER_KEYWORDS,
                    "score_cutoff": config.JOB_HUNTER_SCORE_CUTOFF,
                },
                "effective_criteria": {
                    "sources": effective_sources,
                    "keywords": effective_keywords,
                    "score_cutoff": effective_score_cutoff,
                    "prompt_evaluation": prompt_evaluation,
                }
            })
        except asyncio.TimeoutError:
            return self.error("Timeout ao buscar configurações do servidor (>20s).")
        except requests.HTTPError as e:
            return self.error(f"Erro HTTP {e.response.status_code}: {e.response.text}")
        except requests.RequestException as e:
            return self.error(f"Erro de conexão com o servidor de vagas: {e}")

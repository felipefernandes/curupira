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

        sources: Optional[List[str]] = kwargs.get("sources") or config.JOB_HUNTER_SOURCES
        keywords: Optional[List[str]] = kwargs.get("keywords") or config.JOB_HUNTER_KEYWORDS
        prompt_override: Optional[str] = kwargs.get("prompt_override")
        score_cutoff: Optional[float] = kwargs.get("score_cutoff") or config.JOB_HUNTER_SCORE_CUTOFF

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

        logger.info(f"Job Hunter: iniciando busca com overrides={list(body.keys())}")

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
            return self.success(result)
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
            return self.success(response.json())
        except asyncio.TimeoutError:
            return self.error("Timeout ao buscar configurações do servidor (>20s).")
        except requests.HTTPError as e:
            return self.error(f"Erro HTTP {e.response.status_code}: {e.response.text}")
        except requests.RequestException as e:
            return self.error(f"Erro de conexão com o servidor de vagas: {e}")

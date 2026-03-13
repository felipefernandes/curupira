"""
Skill: GitHub Integration

Integração com a API do GitHub para consultar repositórios,
issues e criar novas issues, seguindo o padrão BaseSkill multi-tool.

Ref: Issue #163 - Adequação para o SKILLS_FRAMEWORK.md
"""

import os
import re
import logging
from typing import Any, Dict

import httpx

from skills.base import BaseSkill

logger = logging.getLogger(__name__)

GITHUB_API_BASE = "https://api.github.com"
_REPO_RE = re.compile(r"^[\w.-]+/[\w.-]+$")

_ACTIONS_REQUIRING_REPO = {"list_issues", "create_issue"}


class GithubSkill(BaseSkill):
    """
    Skill multi-tool para integração com o GitHub.
    Actions disponíveis: list_repos, list_issues, create_issue.
    """

    def __init__(self):
        self.logger = logging.getLogger("GithubSkill")
        # Persistent client: reused across calls to leverage connection pooling.
        # Headers are rebuilt lazily when the token changes (supports token rotation).
        self._client: httpx.AsyncClient | None = None
        self._cached_token: str | None = None

    # ── Metadata ────────────────────────────────────────────────────────────

    @property
    def name(self) -> str:
        return "github"

    @property
    def display_name(self) -> str:
        return "🐙 Github"

    @property
    def skill_group(self) -> str:
        return "github"

    @property
    def skill_group_emoji(self) -> str:
        return "🐙"

    @property
    def description(self) -> str:
        return (
            "Interage com o GitHub: lista repositórios, consulta e cria issues. "
            "Actions disponíveis: list_repos, list_issues, create_issue."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["list_repos", "list_issues", "create_issue"],
                    "description": "Ação a executar no GitHub.",
                },
                "repo_name": {
                    "type": "string",
                    "description": (
                        "Repositório no formato 'owner/repo'. "
                        "Obrigatório para list_issues e create_issue."
                    ),
                },
                "state": {
                    "type": "string",
                    "enum": ["open", "closed", "all"],
                    "description": "Estado das issues (padrão: open). Usado com list_issues.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Número máximo de resultados (padrão: 10).",
                },
                "title": {
                    "type": "string",
                    "description": "Título da issue. Obrigatório para create_issue.",
                },
                "body": {
                    "type": "string",
                    "description": "Descrição da issue. Opcional para create_issue.",
                },
            },
            "required": ["action"],
        }

    # ── Entry point ──────────────────────────────────────────────────────────

    def _get_client(self, token: str) -> httpx.AsyncClient:
        """Returns a persistent AsyncClient, rebuilding it only if the token changed."""
        if self._client is None or self._cached_token != token:
            self._client = httpx.AsyncClient(
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github.v3+json",
                    "User-Agent": "CurupiraBot",
                },
                timeout=15.0,
            )
            self._cached_token = token
        return self._client

    async def execute(self, context: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        action = kwargs.get("action")
        if not action:
            return self.error("Parâmetro 'action' é obrigatório.")

        token = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")
        if not token:
            return self.error(
                "Token GitHub não configurado (GITHUB_PERSONAL_ACCESS_TOKEN ausente)."
            )

        # Early validation: repo_name is required for actions that target a repository
        repo_name = kwargs.get("repo_name", "")
        if action in _ACTIONS_REQUIRING_REPO and not repo_name:
            return self.error(
                f"Parâmetro 'repo_name' é obrigatório para a action '{action}'. "
                "Use o formato 'owner/repo'."
            )

        # Early validation: title is required to create an issue
        if action == "create_issue" and not kwargs.get("title", "").strip():
            return self.error("Parâmetro 'title' é obrigatório para a action 'create_issue'.")

        try:
            client = self._get_client(token)
            if action == "list_repos":
                return await self._list_repos(client, kwargs.get("limit", 10))
            elif action == "list_issues":
                return await self._list_issues(
                    client,
                    repo_name,
                    kwargs.get("state", "open"),
                    kwargs.get("limit", 10),
                )
            elif action == "create_issue":
                return await self._create_issue(
                    client,
                    repo_name,
                    kwargs.get("title", ""),
                    kwargs.get("body", ""),
                )
            else:
                return self.error(f"Action desconhecida: '{action}'.")
        except Exception as e:
            self.logger.error(f"Erro inesperado na GithubSkill [{action}]: {e}")
            return self.error(f"Falha ao comunicar com o GitHub: {str(e)}")

    # ── Private handlers ─────────────────────────────────────────────────────

    async def _list_repos(self, client: httpx.AsyncClient, limit: int) -> Dict[str, Any]:
        """Lista repositórios do usuário autenticado."""
        try:
            resp = await client.get(
                f"{GITHUB_API_BASE}/user/repos",
                params={"sort": "updated", "per_page": limit},
            )
            resp.raise_for_status()
            repos = resp.json()

            if not repos:
                return self.success({"repos": []}, message="Nenhum repositório encontrado.")

            result = [
                {"name": r["full_name"], "stars": r["stargazers_count"], "url": r["html_url"]}
                for r in repos
            ]
            return self.success({"repos": result, "total": len(result)})
        except httpx.HTTPStatusError as e:
            return self.error(f"Erro da API GitHub: {e.response.status_code}")

    async def _list_issues(
        self,
        client: httpx.AsyncClient,
        repo_name: str,
        state: str,
        limit: int,
    ) -> Dict[str, Any]:
        """Lista issues de um repositório."""
        if not repo_name or not _REPO_RE.match(repo_name):
            return self.error(
                f"Formato inválido para repo_name: '{repo_name}'. Use 'owner/repo'."
            )
        try:
            resp = await client.get(
                f"{GITHUB_API_BASE}/repos/{repo_name}/issues",
                params={"state": state, "per_page": limit},
            )
            resp.raise_for_status()
            issues = resp.json()

            # GitHub API returns PRs as issues too; filter them out
            real_issues = [i for i in issues if "pull_request" not in i]

            if not real_issues:
                return self.success(
                    {"issues": [], "repo": repo_name},
                    message=f"Nenhuma issue {state} encontrada em {repo_name}.",
                )

            result = [
                {
                    "number": i["number"],
                    "title": i["title"],
                    "author": i["user"]["login"],
                    "url": i["html_url"],
                }
                for i in real_issues
            ]
            return self.success({"issues": result, "repo": repo_name, "state": state})
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return self.error(f"Repositório '{repo_name}' não encontrado.")
            return self.error(f"Erro da API GitHub: {e.response.status_code}")

    async def _create_issue(
        self,
        client: httpx.AsyncClient,
        repo_name: str,
        title: str,
        body: str,
    ) -> Dict[str, Any]:
        """Cria uma nova issue em um repositório."""
        if not repo_name or not _REPO_RE.match(repo_name):
            return self.error(
                f"Formato inválido para repo_name: '{repo_name}'. Use 'owner/repo'."
            )
        if not title or not title.strip():
            return self.error("O título da issue é obrigatório.")

        # Sanitize: strip HTML tags to prevent injection
        clean_title = re.sub(r"<[^>]*>", "", title)
        clean_body = re.sub(r"<[^>]*>", "", body) if body else ""

        try:
            resp = await client.post(
                f"{GITHUB_API_BASE}/repos/{repo_name}/issues",
                json={"title": clean_title, "body": clean_body},
            )
            resp.raise_for_status()
            issue = resp.json()
            return self.success(
                {"number": issue["number"], "url": issue["html_url"], "title": issue["title"]},
                message=f"Issue #{issue['number']} criada com sucesso.",
            )
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return self.error(f"Repositório '{repo_name}' não encontrado.")
            if e.response.status_code == 403:
                return self.error("Sem permissão para criar issues nesse repositório.")
            return self.error(f"Erro da API GitHub: {e.response.status_code}")

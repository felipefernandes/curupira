"""Tests for skills/github_skill.py (GithubSkill).

Ref: Issue #163 — Adequação para o SKILLS_FRAMEWORK.md
"""

import os
import sys
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from skills.github_skill import GithubSkill


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def skill():
    return GithubSkill()


@pytest.fixture(autouse=True)
def mock_token(monkeypatch):
    """Ensure a valid token is set for most tests."""
    monkeypatch.setenv("GITHUB_PERSONAL_ACCESS_TOKEN", "ghp_test_token_123")


def _mock_response(json_data, status_code=200):
    """Helper to build a fake httpx Response-like object."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.raise_for_status = MagicMock()
    return resp


def _http_status_error(status_code, mock_client):
    """Configures the mock client to raise an HTTPStatusError."""
    import httpx
    err_response = MagicMock()
    err_response.status_code = status_code
    mock_client.get.side_effect = httpx.HTTPStatusError(
        "err", request=MagicMock(), response=err_response
    )
    mock_client.post.side_effect = httpx.HTTPStatusError(
        "err", request=MagicMock(), response=err_response
    )


# ---------------------------------------------------------------------------
# Metadata tests
# ---------------------------------------------------------------------------

class TestGithubSkillMetadata:
    def test_name(self, skill):
        assert skill.name == "github"

    def test_display_name(self, skill):
        assert skill.display_name == "🐙 Github"

    def test_skill_group(self, skill):
        assert skill.skill_group == "github"

    def test_skill_group_emoji(self, skill):
        assert skill.skill_group_emoji == "🐙"

    def test_description_is_short(self, skill):
        assert len(skill.description) <= 200
        # Must not contain docstring-style Args: blocks
        assert "Args:" not in skill.description

    def test_parameters_has_action(self, skill):
        params = skill.parameters
        assert "action" in params["properties"]
        assert "required" in params
        assert "action" in params["required"]


# ---------------------------------------------------------------------------
# Missing token
# ---------------------------------------------------------------------------

class TestGithubSkillMissingToken:
    @pytest.mark.asyncio
    async def test_error_when_token_missing(self, skill, monkeypatch):
        monkeypatch.delenv("GITHUB_PERSONAL_ACCESS_TOKEN", raising=False)
        result = await skill.execute({}, action="list_repos")
        assert result["status"] == "error"
        assert "Token" in result["error"] or "token" in result["error"].lower()


# ---------------------------------------------------------------------------
# Missing / invalid action
# ---------------------------------------------------------------------------

class TestGithubSkillInvalidAction:
    @pytest.mark.asyncio
    async def test_error_when_no_action(self, skill):
        result = await skill.execute({})
        assert result["status"] == "error"

    @pytest.mark.asyncio
    async def test_error_when_unknown_action(self, skill):
        result = await skill.execute({}, action="delete_everything")
        assert result["status"] == "error"
        assert "delete_everything" in result["error"]


# ---------------------------------------------------------------------------
# list_repos
# ---------------------------------------------------------------------------

class TestGithubListRepos:
    @pytest.mark.asyncio
    async def test_success(self, skill):
        fake_repos = [
            {"full_name": "user/repo1", "stargazers_count": 10, "html_url": "https://github.com/user/repo1"},
            {"full_name": "user/repo2", "stargazers_count": 3, "html_url": "https://github.com/user/repo2"},
        ]
        mock_resp = _mock_response(fake_repos)
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("skills.github_skill.httpx.AsyncClient", return_value=mock_client):
            result = await skill.execute({}, action="list_repos", limit=5)

        assert result["status"] == "success"
        assert len(result["data"]["repos"]) == 2
        assert result["data"]["repos"][0]["name"] == "user/repo1"

    @pytest.mark.asyncio
    async def test_empty_list(self, skill):
        mock_resp = _mock_response([])
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("skills.github_skill.httpx.AsyncClient", return_value=mock_client):
            result = await skill.execute({}, action="list_repos")

        assert result["status"] == "success"
        assert result["data"]["repos"] == []

    @pytest.mark.asyncio
    async def test_http_error(self, skill):
        import httpx
        mock_client = AsyncMock()
        _http_status_error(500, mock_client)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("skills.github_skill.httpx.AsyncClient", return_value=mock_client):
            result = await skill.execute({}, action="list_repos")

        assert result["status"] == "error"


# ---------------------------------------------------------------------------
# list_issues
# ---------------------------------------------------------------------------

class TestGithubListIssues:
    @pytest.mark.asyncio
    async def test_success(self, skill):
        fake_issues = [
            {"number": 1, "title": "Bug X", "user": {"login": "alice"}, "html_url": "https://github.com/u/r/issues/1"},
        ]
        mock_resp = _mock_response(fake_issues)
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("skills.github_skill.httpx.AsyncClient", return_value=mock_client):
            result = await skill.execute({}, action="list_issues", repo_name="user/repo")

        assert result["status"] == "success"
        assert result["data"]["issues"][0]["number"] == 1

    @pytest.mark.asyncio
    async def test_prs_are_excluded(self, skill):
        """pull_request items must be filtered out."""
        fake_issues = [
            {"number": 1, "title": "PR", "user": {"login": "bob"}, "html_url": "...", "pull_request": {}},
            {"number": 2, "title": "Real Issue", "user": {"login": "alice"}, "html_url": "..."},
        ]
        mock_resp = _mock_response(fake_issues)
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("skills.github_skill.httpx.AsyncClient", return_value=mock_client):
            result = await skill.execute({}, action="list_issues", repo_name="user/repo")

        assert result["status"] == "success"
        assert len(result["data"]["issues"]) == 1
        assert result["data"]["issues"][0]["number"] == 2

    @pytest.mark.asyncio
    async def test_invalid_repo_format(self, skill):
        result = await skill.execute({}, action="list_issues", repo_name="bad-format")
        assert result["status"] == "error"
        assert "owner/repo" in result["error"]

    @pytest.mark.asyncio
    async def test_repo_not_found(self, skill):
        import httpx
        mock_client = AsyncMock()
        _http_status_error(404, mock_client)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("skills.github_skill.httpx.AsyncClient", return_value=mock_client):
            result = await skill.execute({}, action="list_issues", repo_name="user/repo")

        assert result["status"] == "error"
        assert "não encontrado" in result["error"]


# ---------------------------------------------------------------------------
# create_issue
# ---------------------------------------------------------------------------

class TestGithubCreateIssue:
    @pytest.mark.asyncio
    async def test_success(self, skill):
        fake_issue = {"number": 42, "title": "New Bug", "html_url": "https://github.com/u/r/issues/42"}
        mock_resp = _mock_response(fake_issue, status_code=201)
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("skills.github_skill.httpx.AsyncClient", return_value=mock_client):
            result = await skill.execute(
                {}, action="create_issue", repo_name="user/repo", title="New Bug", body="Details"
            )

        assert result["status"] == "success"
        assert result["data"]["number"] == 42

    @pytest.mark.asyncio
    async def test_error_missing_title(self, skill):
        result = await skill.execute({}, action="create_issue", repo_name="user/repo", title="")
        assert result["status"] == "error"
        assert "título" in result["error"]

    @pytest.mark.asyncio
    async def test_error_invalid_repo(self, skill):
        result = await skill.execute({}, action="create_issue", repo_name="noslash", title="T")
        assert result["status"] == "error"

    @pytest.mark.asyncio
    async def test_html_tags_sanitized(self, skill):
        """Ensure HTML tags are stripped from title/body before sending."""
        fake_issue = {"number": 5, "title": "alert!", "html_url": "..."}
        mock_resp = _mock_response(fake_issue, status_code=201)
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("skills.github_skill.httpx.AsyncClient", return_value=mock_client):
            await skill.execute(
                {}, action="create_issue", repo_name="user/repo",
                title="<script>alert('xss')</script>", body="<b>bold</b>"
            )

        call_kwargs = mock_client.post.call_args.kwargs
        payload = call_kwargs["json"]
        assert "<script>" not in payload["title"]
        assert "<b>" not in payload["body"]

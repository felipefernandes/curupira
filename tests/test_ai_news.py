import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from skills.ai_news import AINewsSkill


@pytest.fixture
def ai_news_skill():
    return AINewsSkill(api_url="https://test-mcp-ai-news.com")


def test_ai_news_skill_properties(ai_news_skill):
    assert ai_news_skill.name == "ai_news"
    assert ai_news_skill.display_name == "🤖 Notícias de IA"
    assert ai_news_skill.skill_group == "ai_news"
    assert ai_news_skill.skill_group_emoji == "🤖"
    assert "Obtém as últimas notícias" in ai_news_skill.description
    assert "source" in ai_news_skill.parameters["properties"]


@pytest.mark.asyncio
async def test_execute_success_all_sources(ai_news_skill):
    """Test calling the skill with 'all' sources (the default) mock responses."""
    mock_news_response = MagicMock()
    mock_news_response.status_code = 200
    mock_news_response.json.return_value = [
        {
            "title": "Nova IA revolucionária",
            "link": "https://exemplo.com/news1",
            "summary": "Um resumo sobre a IA.",
        }
    ]

    mock_arxiv_response = MagicMock()
    mock_arxiv_response.status_code = 200
    mock_arxiv_response.json.return_value = [
        {
            "title": "Paper de LLM",
            "link": "https://arxiv.org/abs/1234",
            "summary": "Resumo do paper.",
            "authors": ["Autor Um", "Autor Dois"],
        }
    ]

    mock_github_response = MagicMock()
    mock_github_response.status_code = 200
    mock_github_response.json.return_value = [
        {
            "name": "repositorio-ia",
            "url": "https://github.com/repo",
            "description": "Um repositorio legal.",
            "stars": 100,
            "language": "Python",
        }
    ]

    # Mock client get to return consecutive responses
    async_mock_get = AsyncMock()
    async_mock_get.side_effect = [
        mock_news_response,
        mock_arxiv_response,
        mock_github_response,
    ]

    # Configure the mock default sources to make sure it tries all three
    ai_news_skill.default_sources = ["news", "arxiv", "github"]

    with patch("httpx.AsyncClient.get", async_mock_get):
        result = await ai_news_skill.execute({"user_id": 123}, source="all")

        assert result["status"] == "success"
        entries = result["data"]["entries"]
        assert len(entries) == 3

        # Validate News entry
        assert entries[0]["source"] == "IA News"
        assert entries[0]["title"] == "Nova IA revolucionária"
        assert entries[0]["link"] == "https://exemplo.com/news1"
        assert entries[0]["summary"] == "Um resumo sobre a IA."

        # Validate ArXiv entry
        assert entries[1]["source"] == "ArXiv Paper"
        assert entries[1]["title"] == "Paper de LLM"
        assert "Autores: Autor Um, Autor Dois" in entries[1]["summary"]

        # Validate GitHub entry
        assert entries[2]["source"] == "GitHub Trending"
        assert entries[2]["title"] == "repositorio-ia"
        assert "[⭐ 100 | Python]" in entries[2]["summary"]


@pytest.mark.asyncio
async def test_execute_single_source(ai_news_skill):
    """Test calling the skill with a single specific source."""
    mock_news_response = MagicMock()
    mock_news_response.status_code = 200
    mock_news_response.json.return_value = [
        {
            "title": "Somente Noticias",
            "link": "https://exemplo.com/only-news",
            "summary": "Um resumo.",
        }
    ]

    async_mock_get = AsyncMock(return_value=mock_news_response)

    with patch("httpx.AsyncClient.get", async_mock_get):
        result = await ai_news_skill.execute({"user_id": 123}, source="news", limit=1)

        assert result["status"] == "success"
        entries = result["data"]["entries"]
        assert len(entries) == 1
        assert entries[0]["source"] == "IA News"
        assert entries[0]["title"] == "Somente Noticias"
        # Verify call parameters
        async_mock_get.assert_called_once_with(
            "https://test-mcp-ai-news.com/api/news", params={"limit": 1}
        )


@pytest.mark.asyncio
async def test_execute_api_failures_gracefully(ai_news_skill):
    """Test that API failures (non-200 or exceptions) are handled gracefully."""
    # 1. Test non-200 response
    mock_fail_response = MagicMock()
    mock_fail_response.status_code = 500

    async_mock_get = AsyncMock(return_value=mock_fail_response)
    ai_news_skill.default_sources = ["news"]

    with patch("httpx.AsyncClient.get", async_mock_get):
        result = await ai_news_skill.execute({"user_id": 123}, source="news")
        assert result["status"] == "success"
        assert len(result["data"]["entries"]) == 0

    # 2. Test JSON parsing failure (ValueError)
    mock_bad_json = MagicMock()
    mock_bad_json.status_code = 200
    mock_bad_json.json.side_effect = ValueError("JSON inválido")
    async_mock_get_bad_json = AsyncMock(return_value=mock_bad_json)
    with patch("httpx.AsyncClient.get", async_mock_get_bad_json):
        result = await ai_news_skill.execute({"user_id": 123}, source="news")
        assert result["status"] == "success"
        assert len(result["data"]["entries"]) == 0

    # 3. Test Request exception (propagates exception via gather and returns error status)
    async_mock_get_exc = AsyncMock(side_effect=httpx.RequestError("Erro de Conexão"))
    with patch("httpx.AsyncClient.get", async_mock_get_exc):
        result = await ai_news_skill.execute({"user_id": 123}, source="news")
        assert result["status"] == "error"
        assert "Falha total" in result["error"]


@pytest.mark.asyncio
async def test_execute_no_api_url():
    """Test execute fails when api_url is empty."""
    skill = AINewsSkill(api_url="")
    skill.api_url = ""  # Force empty to test configuration error
    result = await skill.execute({"user_id": 123}, source="news")
    assert result["status"] == "error"
    assert "não configurada" in result["error"]


@pytest.mark.asyncio
async def test_execute_no_tasks(ai_news_skill):
    """Test execute returns success empty when source category is invalid."""
    result = await ai_news_skill.execute({"user_id": 123}, source="invalid_source")
    assert result["status"] == "success"
    assert len(result["data"]["entries"]) == 0


@pytest.mark.asyncio
async def test_execute_json_not_a_list(ai_news_skill):
    """Test execute returns success empty when API returns JSON that is not a list (e.g. dict)."""
    mock_dict_response = MagicMock()
    mock_dict_response.status_code = 200
    mock_dict_response.json.return_value = {"error": "API Key Expired"}

    async_mock_get = AsyncMock(return_value=mock_dict_response)
    with patch("httpx.AsyncClient.get", async_mock_get):
        result = await ai_news_skill.execute({"user_id": 123}, source="news")
        assert result["status"] == "success"
        assert len(result["data"]["entries"]) == 0


@pytest.mark.asyncio
async def test_execute_unexpected_exception(ai_news_skill):
    """Test execute propagates and handles unexpected exceptions correctly."""
    async_mock_get = AsyncMock(side_effect=Exception("Erro inesperado do host"))
    with patch("httpx.AsyncClient.get", async_mock_get):
        result = await ai_news_skill.execute({"user_id": 123}, source="news")
        assert result["status"] == "error"
        assert "Falha total" in result["error"]

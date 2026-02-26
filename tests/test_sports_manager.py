import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock
import sys
import os
import asyncio
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from skills.sports_manager import SportsManagerSkill, SportsCache
from skills.memory import MemoryManager


# ==================== FIXTURES ====================

@pytest.fixture
def mock_memory_manager():
    """Mock do MemoryManager para testes."""
    mock_mm = MagicMock(spec=MemoryManager)
    mock_mm.get_fact_value = AsyncMock(return_value=None)
    mock_mm.save_fact = AsyncMock()
    return mock_mm


@pytest.fixture
def sports_skill(mock_memory_manager):
    """Fixture da SportsManagerSkill com MemoryManager mockado."""
    return SportsManagerSkill(mock_memory_manager)


@pytest.fixture
def sports_cache():
    """Fixture do SportsCache."""
    return SportsCache(max_size=10)


# ==================== TESTES DE PROPERTIES ====================

def test_sports_skill_properties(sports_skill):
    """Testa propriedades básicas da skill."""
    assert sports_skill.name == "get_sports_info"
    assert sports_skill.display_name == "⚽ Resultados Esportivos"
    assert "Busca resultados" in sports_skill.description
    assert "action" in sports_skill.parameters["required"]
    assert sports_skill.parameters["type"] == "object"


def test_sports_skill_parameters_schema(sports_skill):
    """Testa schema de parâmetros."""
    params = sports_skill.parameters
    props = params["properties"]

    # Action
    assert "action" in props
    assert set(props["action"]["enum"]) == {
        "get_results", "get_schedule", "get_standings"
    }

    # Sport
    assert "sport" in props
    assert "football" in props["sport"]["enum"]
    assert "csgo" in props["sport"]["enum"]

    # Team name
    assert "team_name" in props
    assert "string" == props["team_name"]["type"]

    # Limit
    assert "limit" in props
    assert props["limit"]["minimum"] == 1
    assert props["limit"]["maximum"] == 10


# ==================== TESTES DE CACHE ====================

def test_cache_get_miss(sports_cache):
    """Testa cache miss (chave não existe)."""
    result = sports_cache.get("non_existent_key")
    assert result is None


def test_cache_set_and_get_hit(sports_cache):
    """Testa set e get de cache com hit."""
    test_data = {"team": "Flamengo", "score": "2-1"}
    sports_cache.set("test_key", test_data, "recent_results")

    result = sports_cache.get("test_key")
    assert result == test_data


def test_cache_expiration(sports_cache):
    """Testa expiração de cache por TTL."""
    # Sobrescrever TTL para teste rápido
    sports_cache.TTL_CONFIG["test_type"] = 0.1  # 100ms

    test_data = {"team": "Palmeiras"}
    sports_cache.set("test_key", test_data, "test_type")

    # Verifica imediatamente (deve estar no cache)
    result = sports_cache.get("test_key")
    assert result == test_data

    # Aguarda expiração
    time.sleep(0.15)

    # Cache deve estar expirado
    result = sports_cache.get("test_key")
    assert result is None


def test_cache_eviction_lru(sports_cache):
    """Testa eviction LRU quando cache atinge limite."""
    # Cache com max_size=10
    # Adicionar 11 entradas para forçar eviction
    for i in range(11):
        sports_cache.set(f"key_{i}", {"data": i}, "recent_results")

    # Após eviction, deve ter removido ~20% (2 entradas)
    # Então deve ter 9 entradas
    assert len(sports_cache._cache) == 9

    # As primeiras entradas (mais antigas) devem ter sido removidas
    assert sports_cache.get("key_0") is None
    assert sports_cache.get("key_1") is None

    # Entradas mais recentes devem existir
    assert sports_cache.get("key_10") is not None


def test_cache_invalidate_pattern(sports_cache):
    """Testa invalidação de cache por padrão."""
    sports_cache.set("flamengo:2024", {"data": 1}, "recent_results")
    sports_cache.set("flamengo:2023", {"data": 2}, "recent_results")
    sports_cache.set("palmeiras:2024", {"data": 3}, "recent_results")

    # Invalidar apenas entradas com "flamengo"
    sports_cache.invalidate_pattern("flamengo")

    assert sports_cache.get("flamengo:2024") is None
    assert sports_cache.get("flamengo:2023") is None
    assert sports_cache.get("palmeiras:2024") is not None


def test_cache_stats(sports_cache):
    """Testa estatísticas do cache."""
    sports_cache.set("key1", {"data": 1}, "recent_results")
    sports_cache.set("key2", {"data": 2}, "recent_results")

    stats = sports_cache.stats()
    assert stats["size"] == 2
    assert stats["max_size"] == 10
    assert stats["usage_percent"] == 20.0


# ==================== TESTES DE VALIDAÇÃO ====================

@pytest.mark.asyncio
async def test_execute_missing_user_id(sports_skill):
    """Testa erro quando user_id ausente."""
    context = {}  # Sem user_id
    result = await sports_skill.execute(context, action="get_results")

    assert result["status"] == "error"
    assert "user_id ausente" in result["error"]


@pytest.mark.asyncio
async def test_execute_missing_action(sports_skill):
    """Testa erro quando action ausente."""
    context = {"user_id": 123}
    result = await sports_skill.execute(context)

    assert result["status"] == "error"
    assert "obrigatório" in result["error"]


@pytest.mark.asyncio
async def test_execute_unsupported_action(sports_skill):
    """Testa erro para action não implementada (MVP)."""
    context = {"user_id": 123}
    result = await sports_skill.execute(
        context,
        action="get_schedule",  # Não implementado na Fase 1
        sport="football",
        team_name="Flamengo"
    )

    assert result["status"] == "error"
    assert "não implementada" in result["error"]
    assert "get_schedule" in result["error"]


@pytest.mark.asyncio
async def test_execute_missing_sport_no_preference(sports_skill, mock_memory_manager):
    """Testa erro quando sport ausente e sem preferência."""
    mock_memory_manager.get_fact_value.return_value = None

    context = {"user_id": 123}
    result = await sports_skill.execute(
        context,
        action="get_results",
        team_name="Flamengo"
    )

    assert result["status"] == "error"
    assert "Esporte não especificado" in result["error"]


@pytest.mark.asyncio
async def test_execute_missing_team_no_preference(sports_skill, mock_memory_manager):
    """Testa erro quando team_name ausente e sem preferência."""
    mock_memory_manager.get_fact_value.return_value = None

    context = {"user_id": 123}
    result = await sports_skill.execute(
        context,
        action="get_results",
        sport="football"
    )

    assert result["status"] == "error"
    assert "Time não especificado" in result["error"]


@pytest.mark.asyncio
async def test_execute_invalid_team_name_empty(sports_skill):
    """Testa validação de team_name vazio."""
    context = {"user_id": 123}
    result = await sports_skill.execute(
        context,
        action="get_results",
        sport="football",
        team_name="   "  # Apenas espaços
    )

    assert result["status"] == "error"
    assert "inválido" in result["error"]


@pytest.mark.asyncio
async def test_execute_invalid_team_name_too_short(sports_skill):
    """Testa validação de team_name muito curto."""
    context = {"user_id": 123}
    result = await sports_skill.execute(
        context,
        action="get_results",
        sport="football",
        team_name="A"  # 1 caractere
    )

    assert result["status"] == "error"
    assert "muito curto" in result["error"]


@pytest.mark.asyncio
async def test_execute_invalid_team_name_too_long(sports_skill):
    """Testa validação de team_name muito longo."""
    context = {"user_id": 123}
    result = await sports_skill.execute(
        context,
        action="get_results",
        sport="football",
        team_name="A" * 101  # 101 caracteres
    )

    assert result["status"] == "error"
    assert "muito longo" in result["error"]


@pytest.mark.asyncio
async def test_execute_unsupported_sport(sports_skill):
    """Testa erro para esporte não suportado (MVP)."""
    context = {"user_id": 123}
    result = await sports_skill.execute(
        context,
        action="get_results",
        sport="basketball",  # Não implementado na Fase 1
        team_name="Lakers"
    )

    assert result["status"] == "error"
    assert "não implementado" in result["error"]


@pytest.mark.asyncio
async def test_execute_missing_api_key(sports_skill):
    """Testa validação de API key ausente."""
    with patch("core.config.THESPORTSDB_KEY", ""):
        context = {"user_id": 123}
        result = await sports_skill.execute(
            context,
            action="get_results",
            sport="football",
            team_name="Flamengo"
        )

        assert result["status"] == "error"
        assert "THESPORTSDB_KEY não configurada" in result["error"]


# ==================== TESTES DE INTEGRAÇÃO COM API ====================

@pytest.mark.asyncio
async def test_fetch_thesportsdb_success(sports_skill):
    """Testa busca bem-sucedida no TheSportsDB."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"teams": [{"idTeam": "123"}]}
    mock_response.raise_for_status.return_value = None

    with patch("core.config.THESPORTSDB_KEY", "test_api_key_123"):
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            with patch("asyncio.sleep", new_callable=AsyncMock):  # Mock sleep para rate limiting
                result = await sports_skill._fetch_thesportsdb("searchteams.php?t=Flamengo")

                assert result == {"teams": [{"idTeam": "123"}]}
                mock_get.assert_called_once()


@pytest.mark.asyncio
async def test_fetch_thesportsdb_rate_limiting(sports_skill):
    """Testa rate limiting do TheSportsDB (1 req/s)."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"data": "test"}
    mock_response.raise_for_status.return_value = None

    with patch("core.config.THESPORTSDB_KEY", "test_api_key_123"):
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                # Primeira chamada
                await sports_skill._fetch_thesportsdb("endpoint1")

                # Segunda chamada imediatamente depois
                await sports_skill._fetch_thesportsdb("endpoint2")

                # Sleep deve ter sido chamado na segunda requisição
                assert mock_sleep.call_count >= 1


@pytest.mark.asyncio
async def test_fetch_thesportsdb_results_team_not_found(sports_skill):
    """Testa erro quando time não encontrado."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"teams": None}
    mock_response.raise_for_status.return_value = None

    with patch("core.config.THESPORTSDB_KEY", "test_api_key_123"):
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            with patch("asyncio.sleep", new_callable=AsyncMock):
                with pytest.raises(ValueError, match="não encontrado"):
                    await sports_skill._fetch_thesportsdb_results("NonExistentTeam", 5)


@pytest.mark.asyncio
async def test_fetch_thesportsdb_results_success(sports_skill):
    """Testa busca de resultados bem-sucedida."""
    # Mock search team response
    search_response = MagicMock()
    search_response.json.return_value = {
        "teams": [{
            "idTeam": "133604",
            "strTeam": "Flamengo"
        }]
    }
    search_response.raise_for_status.return_value = None

    # Mock results response
    results_response = MagicMock()
    results_response.json.return_value = {
        "results": [
            {
                "dateEvent": "2024-02-25",
                "strHomeTeam": "Flamengo",
                "strAwayTeam": "Palmeiras",
                "intHomeScore": "2",
                "intAwayScore": "1",
                "strLeague": "Brasileirão Série A",
                "strStatus": "Match Finished"
            }
        ]
    }
    results_response.raise_for_status.return_value = None

    with patch("core.config.THESPORTSDB_KEY", "test_api_key_123"):
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = [search_response, results_response]

            with patch("asyncio.sleep", new_callable=AsyncMock):
                result = await sports_skill._fetch_thesportsdb_results("Flamengo", 5)

                assert result["team_name"] == "Flamengo"
                assert result["team_id"] == "133604"
                assert result["matches_count"] == 1
                assert len(result["matches"]) == 1
                assert result["matches"][0]["home_team"] == "Flamengo"


# ==================== TESTES DE RETRY LOGIC ====================

@pytest.mark.asyncio
async def test_fetch_with_retry_success_first_attempt(sports_skill):
    """Testa retry com sucesso na primeira tentativa."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"data": "success"}
    mock_response.raise_for_status.return_value = None

    # Get HTTP client primeiro
    await sports_skill._get_http_client()

    with patch.object(sports_skill._http_client, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response

        result = await sports_skill._fetch_with_retry("http://test.com", retries=3)

        assert result == {"data": "success"}
        assert mock_get.call_count == 1


@pytest.mark.asyncio
async def test_fetch_with_retry_timeout_then_success(sports_skill):
    """Testa retry com timeout seguido de sucesso."""
    mock_success = MagicMock()
    mock_success.json.return_value = {"data": "success"}
    mock_success.raise_for_status.return_value = None

    await sports_skill._get_http_client()

    with patch.object(sports_skill._http_client, "get", new_callable=AsyncMock) as mock_get:
        # Primeira chamada timeout, segunda sucesso
        mock_get.side_effect = [
            httpx.TimeoutException("Timeout"),
            mock_success
        ]

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await sports_skill._fetch_with_retry("http://test.com", retries=3)

            assert result == {"data": "success"}
            assert mock_get.call_count == 2
            mock_sleep.assert_called_once()  # Backoff entre tentativas


@pytest.mark.asyncio
async def test_fetch_with_retry_rate_limit_429(sports_skill):
    """Testa retry com rate limit (429)."""
    mock_success = MagicMock()
    mock_success.json.return_value = {"data": "success"}
    mock_success.raise_for_status.return_value = None

    await sports_skill._get_http_client()

    with patch.object(sports_skill._http_client, "get", new_callable=AsyncMock) as mock_get:
        # Mock 429 response
        mock_429 = MagicMock()
        mock_429.status_code = 429
        error_429 = httpx.HTTPStatusError("Rate limit", request=MagicMock(), response=mock_429)

        mock_get.side_effect = [error_429, mock_success]

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await sports_skill._fetch_with_retry("http://test.com", retries=3)

            assert result == {"data": "success"}
            assert mock_get.call_count == 2
            mock_sleep.assert_called_once()


@pytest.mark.asyncio
async def test_fetch_with_retry_401_no_retry(sports_skill):
    """Testa que 401 (Unauthorized) não faz retry."""
    await sports_skill._get_http_client()

    with patch.object(sports_skill._http_client, "get", new_callable=AsyncMock) as mock_get:
        mock_401 = MagicMock()
        mock_401.status_code = 401
        error_401 = httpx.HTTPStatusError("Unauthorized", request=MagicMock(), response=mock_401)
        mock_get.side_effect = error_401

        with pytest.raises(ValueError, match="API key inválida"):
            await sports_skill._fetch_with_retry("http://test.com", retries=3)

        # Não deve fazer retry para 401
        assert mock_get.call_count == 1


# ==================== TESTES DE CACHE KEY ====================

def test_make_cache_key_basic(sports_skill):
    """Testa geração de chave de cache básica."""
    key = sports_skill._make_cache_key("get_results", "football", "Flamengo")
    assert key == "get_results:football:flamengo"


def test_make_cache_key_with_limit(sports_skill):
    """Testa geração de chave de cache com limit."""
    key = sports_skill._make_cache_key("get_results", "football", "Flamengo", limit=5)
    assert key == "get_results:football:flamengo:5"


def test_make_cache_key_different_limits(sports_skill):
    """Testa que limits diferentes geram chaves diferentes."""
    key1 = sports_skill._make_cache_key("get_results", "football", "Flamengo", limit=5)
    key2 = sports_skill._make_cache_key("get_results", "football", "Flamengo", limit=3)
    assert key1 != key2


def test_make_cache_key_with_league(sports_skill):
    """Testa geração de chave de cache com liga."""
    key = sports_skill._make_cache_key("get_standings", "football", league="Brasileirão")
    assert key == "get_standings:football:brasileirão"


# ==================== TESTES DE INTEGRAÇÃO END-TO-END ====================

@pytest.mark.asyncio
async def test_execute_with_cache_hit(sports_skill):
    """Testa execute com cache hit."""
    with patch("core.config.THESPORTSDB_KEY", "123"):
        context = {"user_id": 123}

        # Preencher cache manualmente
        cached_data = {
            "team_name": "Flamengo",
            "matches_count": 1,
            "matches": [{"home_team": "Flamengo"}]
        }
        cache_key = sports_skill._make_cache_key("get_results", "football", "Flamengo", limit=5)
        sports_skill.cache.set(cache_key, cached_data, "recent_results")

        result = await sports_skill.execute(
            context,
            action="get_results",
            sport="football",
            team_name="Flamengo",
            limit=5
        )

        assert result["status"] == "success"
        assert result["data"] == cached_data
        assert "cache" in result["message"].lower()


@pytest.mark.asyncio
async def test_execute_with_preferences(sports_skill, mock_memory_manager):
    """Testa execute usando preferências do usuário."""
    with patch("core.config.THESPORTSDB_KEY", "123"):
        # Mock preferências
        async def mock_get_fact(user_id, key):
            if key == "sports_favorite_sport":
                return "football"
            elif key == "sports_favorite_team":
                return "Palmeiras"
            return None

        mock_memory_manager.get_fact_value = mock_get_fact

        # Mock API responses
        search_response = MagicMock()
        search_response.json.return_value = {
            "teams": [{"idTeam": "456", "strTeam": "Palmeiras"}]
        }
        search_response.raise_for_status.return_value = None

        results_response = MagicMock()
        results_response.json.return_value = {"results": []}
        results_response.raise_for_status.return_value = None

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = [search_response, results_response]

            with patch("asyncio.sleep", new_callable=AsyncMock):
                context = {"user_id": 123}
                result = await sports_skill.execute(
                    context,
                    action="get_results"
                    # sport e team_name omitidos - devem vir das preferências
                )

                assert result["status"] == "success"
                assert "Palmeiras" in str(result["data"])

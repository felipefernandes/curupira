import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime
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


def test_cache_true_lru_behavior(sports_cache):
    """Testa que get() move entrada para o final (true LRU)."""
    # Adicionar 3 entradas
    sports_cache.set("key_0", {"data": 0}, "recent_results")
    sports_cache.set("key_1", {"data": 1}, "recent_results")
    sports_cache.set("key_2", {"data": 2}, "recent_results")

    # Acessar key_0 (deve mover para o final)
    assert sports_cache.get("key_0") == {"data": 0}

    # Adicionar mais entradas até forçar eviction (max_size=10)
    for i in range(3, 11):
        sports_cache.set(f"key_{i}", {"data": i}, "recent_results")

    # Após eviction, key_1 deve ter sido removida (era a mais antiga)
    # mas key_0 deve existir (foi acessada e movida para o final)
    assert sports_cache.get("key_1") is None  # Removida (mais antiga não acessada)
    assert sports_cache.get("key_0") is not None  # Preservada (foi acessada)


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
    """Testa erro para action não reconhecida."""
    context = {"user_id": 123}
    result = await sports_skill.execute(
        context,
        action="get_transfers",
        sport="football",
        team_name="Flamengo"
    )

    assert result["status"] == "error"
    assert "não reconhecida" in result["error"]


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
    assert "não suportado" in result["error"]


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


# ==================== TESTES DE FILTRAGEM DE JOGOS (Issue #117) ====================


@pytest.mark.asyncio
async def test_fetch_thesportsdb_results_filters_scheduled_matches(sports_skill):
    """Testa que jogos agendados (sem placar) são filtrados dos resultados."""
    search_response = MagicMock()
    search_response.json.return_value = {
        "teams": [{"idTeam": "133604", "strTeam": "Flamengo"}]
    }
    search_response.raise_for_status.return_value = None

    # API retorna mix de jogos finalizados e agendados
    # Inclui caso edge: away_score presente mas home_score ausente
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
                "strStatus": "Match Finished",
            },
            {
                "dateEvent": "2024-03-01",
                "strHomeTeam": "Flamengo",
                "strAwayTeam": "Vasco",
                "intHomeScore": None,
                "intAwayScore": None,
                "strLeague": "Brasileirão Série A",
                "strStatus": "Not Started",
            },
            {
                "dateEvent": "2024-02-28",
                "strHomeTeam": "Santos",
                "strAwayTeam": "Flamengo",
                "intHomeScore": "",
                "intAwayScore": "",
                "strLeague": "Copa do Brasil",
                "strStatus": "Postponed",
            },
            {
                "dateEvent": "2024-02-26",
                "strHomeTeam": "Flamengo",
                "strAwayTeam": "Grêmio",
                "intHomeScore": None,
                "intAwayScore": "3",
                "strLeague": "Copa do Brasil",
                "strStatus": "Match Finished",
            },
        ]
    }
    results_response.raise_for_status.return_value = None

    with patch("core.config.THESPORTSDB_KEY", "test_api_key_123"):
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = [search_response, results_response]

            with patch("asyncio.sleep", new_callable=AsyncMock):
                result = await sports_skill._fetch_thesportsdb_results("Flamengo", 5)

                # Jogos com pelo menos 1 score devem aparecer (2 de 4)
                assert result["matches_count"] == 2
                # Ordenado por data desc: 26 fev > 25 fev
                assert result["matches"][0]["date"] == "2024-02-26"
                assert result["matches"][1]["date"] == "2024-02-25"
                assert result["matches"][1]["home_score"] == "2"


@pytest.mark.asyncio
async def test_fetch_thesportsdb_results_all_scheduled_returns_message(sports_skill):
    """Testa mensagem quando API retorna apenas jogos agendados (sem placar)."""
    search_response = MagicMock()
    search_response.json.return_value = {
        "teams": [{"idTeam": "133604", "strTeam": "Flamengo"}]
    }
    search_response.raise_for_status.return_value = None

    # Todos os jogos sem placar
    results_response = MagicMock()
    results_response.json.return_value = {
        "results": [
            {
                "dateEvent": "2024-03-01",
                "strHomeTeam": "Flamengo",
                "strAwayTeam": "Vasco",
                "intHomeScore": None,
                "intAwayScore": None,
                "strLeague": "Brasileirão Série A",
                "strStatus": "Not Started",
            },
        ]
    }
    results_response.raise_for_status.return_value = None

    with patch("core.config.THESPORTSDB_KEY", "test_api_key_123"):
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = [search_response, results_response]

            with patch("asyncio.sleep", new_callable=AsyncMock):
                result = await sports_skill._fetch_thesportsdb_results("Flamengo", 5)

                assert result["matches_count"] == 0
                assert result["matches"] == []
                assert "agendados ou sem placar" in result["message"]


@pytest.mark.asyncio
async def test_fetch_thesportsdb_results_sorted_by_date_desc(sports_skill):
    """Testa que resultados são ordenados por data (mais recente primeiro)."""
    search_response = MagicMock()
    search_response.json.return_value = {
        "teams": [{"idTeam": "133604", "strTeam": "Flamengo"}]
    }
    search_response.raise_for_status.return_value = None

    # Jogos fora de ordem cronológica
    results_response = MagicMock()
    results_response.json.return_value = {
        "results": [
            {
                "dateEvent": "2024-02-20",
                "strHomeTeam": "Flamengo",
                "strAwayTeam": "Palmeiras",
                "intHomeScore": "1",
                "intAwayScore": "0",
                "strLeague": "Brasileirão",
                "strStatus": "Match Finished",
            },
            {
                "dateEvent": "2024-02-25",
                "strHomeTeam": "Santos",
                "strAwayTeam": "Flamengo",
                "intHomeScore": "0",
                "intAwayScore": "3",
                "strLeague": "Copa do Brasil",
                "strStatus": "Match Finished",
            },
            {
                "dateEvent": "2024-02-22",
                "strHomeTeam": "Flamengo",
                "strAwayTeam": "Botafogo",
                "intHomeScore": "2",
                "intAwayScore": "2",
                "strLeague": "Carioca",
                "strStatus": "Match Finished",
            },
        ]
    }
    results_response.raise_for_status.return_value = None

    with patch("core.config.THESPORTSDB_KEY", "test_api_key_123"):
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = [search_response, results_response]

            with patch("asyncio.sleep", new_callable=AsyncMock):
                result = await sports_skill._fetch_thesportsdb_results("Flamengo", 5)

                # Deve estar ordenado: 25 > 22 > 20
                assert result["matches_count"] == 3
                assert result["matches"][0]["date"] == "2024-02-25"
                assert result["matches"][1]["date"] == "2024-02-22"
                assert result["matches"][2]["date"] == "2024-02-20"


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


# ==================== TESTES DE _resolve_team_info ====================


@pytest.mark.asyncio
async def test_resolve_team_info_caches_result(sports_skill):
    """Testa que _resolve_team_info cacheia resultado (24h TTL)."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "teams": [{"idTeam": "133604", "strTeam": "Flamengo", "idLeague": "4351"}]
    }
    mock_response.raise_for_status.return_value = None

    with patch("core.config.THESPORTSDB_KEY", "test_key"):
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            with patch("asyncio.sleep", new_callable=AsyncMock):
                # Primeira chamada: API call
                team1 = await sports_skill._resolve_team_info("Flamengo")
                assert team1["idTeam"] == "133604"

                # Segunda chamada: cache hit (sem API call)
                team2 = await sports_skill._resolve_team_info("Flamengo")
                assert team2["idTeam"] == "133604"

                # Apenas 1 API call (segunda veio do cache)
                assert mock_get.call_count == 1


@pytest.mark.asyncio
async def test_resolve_team_info_not_found(sports_skill):
    """Testa erro quando time não encontrado no _resolve_team_info."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"teams": None}
    mock_response.raise_for_status.return_value = None

    with patch("core.config.THESPORTSDB_KEY", "test_key"):
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            with patch("asyncio.sleep", new_callable=AsyncMock):
                with pytest.raises(ValueError, match="não encontrado"):
                    await sports_skill._resolve_team_info("TimeInexistente")


# ==================== TESTES DE _determine_season ====================


def test_determine_season_brazilian_league(sports_skill):
    """Testa formato de season para liga brasileira (ano único)."""
    season = sports_skill._determine_season("Brasileirão Série A")
    # Deve retornar formato ano único
    assert "-" not in season
    assert len(season) == 4  # "2026"


def test_determine_season_european_league(sports_skill):
    """Testa formato de season para liga europeia (dois anos)."""
    season = sports_skill._determine_season("Premier League")
    # Deve retornar formato dois anos
    assert "-" in season
    assert len(season) == 9  # "2025-2026"


def test_determine_season_alternate_brazilian(sports_skill):
    """Testa formato alternativo para liga brasileira."""
    season = sports_skill._determine_season("Brasileirão Série A", alternate=True)
    # Alternate de brasileiro = formato europeu
    assert "-" in season


def test_determine_season_alternate_european(sports_skill):
    """Testa formato alternativo para liga europeia."""
    season = sports_skill._determine_season("Premier League", alternate=True)
    # Alternate de europeu = formato brasileiro (ano único)
    assert "-" not in season


def test_determine_season_none_league(sports_skill):
    """Testa season com league_name None (default europeu)."""
    season = sports_skill._determine_season(None)
    assert "-" in season  # Default é formato europeu


def test_determine_season_brazilian_month_before_july(sports_skill):
    """Testa season brasileira com month < 7 no alternate."""
    with patch("skills.sports_manager.datetime") as mock_datetime:
        mock_datetime.now.return_value = datetime(2026, 3, 15)  # Março
        season = sports_skill._determine_season("Brasileirão", alternate=True)
        assert "-" in season
        assert season == "2025-2026"


def test_determine_season_european_month_before_july(sports_skill):
    """Testa season europeia com month < 7."""
    with patch("skills.sports_manager.datetime") as mock_datetime:
        mock_datetime.now.return_value = datetime(2026, 3, 15)  # Março
        season = sports_skill._determine_season("Premier League")
        assert "-" in season
        assert season == "2025-2026"


# ==================== TESTES DE get_schedule ====================


@pytest.mark.asyncio
async def test_fetch_football_schedule_success(sports_skill):
    """Testa busca de próximos jogos bem-sucedida."""
    search_response = MagicMock()
    search_response.json.return_value = {
        "teams": [{"idTeam": "134141", "strTeam": "Botafogo"}]
    }
    search_response.raise_for_status.return_value = None

    schedule_response = MagicMock()
    schedule_response.json.return_value = {
        "events": [
            {
                "dateEvent": "2026-03-05",
                "strTime": "21:00:00",
                "strHomeTeam": "Botafogo",
                "strAwayTeam": "Flamengo",
                "strLeague": "Brasileirão Série A",
                "intRound": "5",
                "strVenue": "Estádio Nilton Santos",
            }
        ]
    }
    schedule_response.raise_for_status.return_value = None

    with patch("core.config.THESPORTSDB_KEY", "test_key"):
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = [search_response, schedule_response]
            with patch("asyncio.sleep", new_callable=AsyncMock):
                result = await sports_skill._fetch_football_schedule("Botafogo")

                assert result["team_name"] == "Botafogo"
                assert result["matches_count"] == 1
                assert result["upcoming_matches"][0]["date"] == "2026-03-05"
                assert result["upcoming_matches"][0]["venue"] == "Estádio Nilton Santos"
                assert result["free_tier_limited"] is True
                assert result["note"] is not None


@pytest.mark.asyncio
async def test_fetch_football_schedule_no_upcoming(sports_skill):
    """Testa quando não há próximos jogos."""
    search_response = MagicMock()
    search_response.json.return_value = {
        "teams": [{"idTeam": "134141", "strTeam": "Botafogo"}]
    }
    search_response.raise_for_status.return_value = None

    schedule_response = MagicMock()
    schedule_response.json.return_value = {"events": None}
    schedule_response.raise_for_status.return_value = None

    with patch("core.config.THESPORTSDB_KEY", "test_key"):
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = [search_response, schedule_response]
            with patch("asyncio.sleep", new_callable=AsyncMock):
                result = await sports_skill._fetch_football_schedule("Botafogo")

                assert result["matches_count"] == 0
                assert result["upcoming_matches"] == []
                assert "Nenhum" in result["message"]


@pytest.mark.asyncio
async def test_fetch_football_schedule_sorted_asc(sports_skill):
    """Testa que próximos jogos são ordenados por data ascendente."""
    search_response = MagicMock()
    search_response.json.return_value = {
        "teams": [{"idTeam": "134141", "strTeam": "Botafogo"}]
    }
    search_response.raise_for_status.return_value = None

    schedule_response = MagicMock()
    schedule_response.json.return_value = {
        "events": [
            {
                "dateEvent": "2026-03-10",
                "strTime": "20:00:00",
                "strHomeTeam": "Botafogo",
                "strAwayTeam": "Vasco",
                "strLeague": "Carioca",
                "intRound": "8",
                "strVenue": "Maracanã",
            },
            {
                "dateEvent": "2026-03-05",
                "strTime": "21:00:00",
                "strHomeTeam": "Flamengo",
                "strAwayTeam": "Botafogo",
                "strLeague": "Brasileirão",
                "intRound": "5",
                "strVenue": "Maracanã",
            },
        ]
    }
    schedule_response.raise_for_status.return_value = None

    with patch("core.config.THESPORTSDB_KEY", "test_key"):
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = [search_response, schedule_response]
            with patch("asyncio.sleep", new_callable=AsyncMock):
                result = await sports_skill._fetch_football_schedule("Botafogo")

                assert result["matches_count"] == 2
                # Mais próximo primeiro
                assert result["upcoming_matches"][0]["date"] == "2026-03-05"
                assert result["upcoming_matches"][1]["date"] == "2026-03-10"
                assert result["free_tier_limited"] is False


@pytest.mark.asyncio
async def test_execute_get_schedule_routes_correctly(sports_skill):
    """Testa que execute() roteia get_schedule corretamente."""
    with patch("core.config.THESPORTSDB_KEY", "123"):
        # Preencher cache para schedule
        cached_data = {
            "team_name": "Botafogo",
            "matches_count": 1,
            "upcoming_matches": [{"date": "2026-03-05"}],
        }
        cache_key = sports_skill._make_cache_key("get_schedule", "football", "Botafogo")
        sports_skill.cache.set(cache_key, cached_data, "schedule")

        context = {"user_id": 123}
        result = await sports_skill.execute(
            context,
            action="get_schedule",
            sport="football",
            team_name="Botafogo"
        )

        assert result["status"] == "success"
        assert result["data"]["team_name"] == "Botafogo"
        assert "upcoming_matches" in result["data"]


# ==================== TESTES DE get_standings ====================


@pytest.mark.asyncio
async def test_fetch_football_standings_via_team(sports_skill):
    """Testa busca de classificação via nome do time."""
    search_response = MagicMock()
    search_response.json.return_value = {
        "teams": [{
            "idTeam": "134141",
            "strTeam": "Botafogo",
            "idLeague": "4351",
            "strLeague": "Brasileirão Série A",
        }]
    }
    search_response.raise_for_status.return_value = None

    standings_response = MagicMock()
    standings_response.json.return_value = {
        "table": [
            {
                "intRank": "1",
                "strTeam": "Botafogo",
                "idTeam": "134141",
                "intPlayed": "10",
                "intWin": "8",
                "intDraw": "1",
                "intLoss": "1",
                "intGoalsFor": "22",
                "intGoalsAgainst": "8",
                "intGoalDifference": "14",
                "intPoints": "25",
            },
            {
                "intRank": "2",
                "strTeam": "Flamengo",
                "idTeam": "133604",
                "intPlayed": "10",
                "intWin": "7",
                "intDraw": "2",
                "intLoss": "1",
                "intGoalsFor": "20",
                "intGoalsAgainst": "10",
                "intGoalDifference": "10",
                "intPoints": "23",
            },
        ]
    }
    standings_response.raise_for_status.return_value = None

    with patch("core.config.THESPORTSDB_KEY", "test_key"):
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = [search_response, standings_response]
            with patch("asyncio.sleep", new_callable=AsyncMock):
                result = await sports_skill._fetch_football_standings("Botafogo", None)

                assert result["league"] == "Brasileirão Série A"
                assert result["entries_count"] == 2
                assert result["standings"][0]["position"] == "1"
                assert result["standings"][0]["team_name"] == "Botafogo"
                assert result["standings"][0]["points"] == "25"


@pytest.mark.asyncio
async def test_fetch_football_standings_via_league(sports_skill):
    """Testa busca de classificação via nome da liga (sem team_name)."""
    teams_response = MagicMock()
    teams_response.json.return_value = {
        "teams": [{"idLeague": "4351", "strTeam": "Botafogo"}]
    }
    teams_response.raise_for_status.return_value = None

    standings_response = MagicMock()
    standings_response.json.return_value = {
        "table": [
            {
                "intRank": "1",
                "strTeam": "Botafogo",
                "idTeam": "134141",
                "intPlayed": "10",
                "intWin": "8",
                "intDraw": "1",
                "intLoss": "1",
                "intGoalsFor": "22",
                "intGoalsAgainst": "8",
                "intGoalDifference": "14",
                "intPoints": "25",
            },
        ]
    }
    standings_response.raise_for_status.return_value = None

    with patch("core.config.THESPORTSDB_KEY", "test_key"):
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = [teams_response, standings_response]
            with patch("asyncio.sleep", new_callable=AsyncMock):
                result = await sports_skill._fetch_football_standings(
                    None, "Brasileirão Série A"
                )

                assert result["league"] == "Brasileirão Série A"
                assert result["entries_count"] == 1


@pytest.mark.asyncio
async def test_fetch_football_standings_league_not_found(sports_skill):
    """Testa erro quando liga não encontrada."""
    teams_response = MagicMock()
    teams_response.json.return_value = {"teams": None}
    teams_response.raise_for_status.return_value = None

    with patch("core.config.THESPORTSDB_KEY", "test_key"):
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = teams_response
            with patch("asyncio.sleep", new_callable=AsyncMock):
                with pytest.raises(ValueError, match="não encontrada"):
                    await sports_skill._fetch_football_standings(
                        None, "Liga Inexistente"
                    )


@pytest.mark.asyncio
async def test_fetch_football_standings_no_table(sports_skill):
    """Testa quando tabela não encontrada (retorna vazio com mensagem)."""
    search_response = MagicMock()
    search_response.json.return_value = {
        "teams": [{
            "idTeam": "134141",
            "strTeam": "Botafogo",
            "idLeague": "4351",
            "strLeague": "Brasileirão Série A",
        }]
    }
    search_response.raise_for_status.return_value = None

    empty_response = MagicMock()
    empty_response.json.return_value = {"table": None}
    empty_response.raise_for_status.return_value = None

    with patch("core.config.THESPORTSDB_KEY", "test_key"):
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            # search + 2x lookuptable (normal + fallback)
            mock_get.side_effect = [search_response, empty_response, empty_response]
            with patch("asyncio.sleep", new_callable=AsyncMock):
                result = await sports_skill._fetch_football_standings("Botafogo", None)

                assert result["entries_count"] == 0
                assert result["standings"] == []
                assert "não encontrada" in result["message"]


@pytest.mark.asyncio
async def test_fetch_football_standings_season_fallback(sports_skill):
    """Testa fallback de formato de season."""
    search_response = MagicMock()
    search_response.json.return_value = {
        "teams": [{
            "idTeam": "134141",
            "strTeam": "Botafogo",
            "idLeague": "4351",
            "strLeague": "Brasileirão Série A",
        }]
    }
    search_response.raise_for_status.return_value = None

    empty_response = MagicMock()
    empty_response.json.return_value = {"table": None}
    empty_response.raise_for_status.return_value = None

    standings_response = MagicMock()
    standings_response.json.return_value = {
        "table": [
            {
                "intRank": "1",
                "strTeam": "Botafogo",
                "idTeam": "134141",
                "intPlayed": "5",
                "intWin": "4",
                "intDraw": "1",
                "intLoss": "0",
                "intGoalsFor": "10",
                "intGoalsAgainst": "3",
                "intGoalDifference": "7",
                "intPoints": "13",
            },
        ]
    }
    standings_response.raise_for_status.return_value = None

    with patch("core.config.THESPORTSDB_KEY", "test_key"):
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            # search + empty (first season) + success (fallback season)
            mock_get.side_effect = [search_response, empty_response, standings_response]
            with patch("asyncio.sleep", new_callable=AsyncMock):
                result = await sports_skill._fetch_football_standings("Botafogo", None)

                # Fallback funcionou
                assert result["entries_count"] == 1
                assert result["standings"][0]["team_name"] == "Botafogo"


@pytest.mark.asyncio
async def test_fetch_football_standings_free_tier_note(sports_skill):
    """Testa nota de free tier quando <= 5 posições."""
    search_response = MagicMock()
    search_response.json.return_value = {
        "teams": [{
            "idTeam": "134141",
            "strTeam": "Botafogo",
            "idLeague": "4351",
            "strLeague": "Brasileirão Série A",
        }]
    }
    search_response.raise_for_status.return_value = None

    # 5 posições = limite free tier
    standings_response = MagicMock()
    table_entries = [
        {
            "intRank": str(i),
            "strTeam": f"Time {i}",
            "idTeam": str(i),
            "intPlayed": "10",
            "intWin": str(10 - i),
            "intDraw": "0",
            "intLoss": str(i),
            "intGoalsFor": str(20 - i),
            "intGoalsAgainst": str(i * 2),
            "intGoalDifference": str(20 - i * 3),
            "intPoints": str((10 - i) * 3),
        }
        for i in range(1, 6)
    ]
    standings_response.json.return_value = {"table": table_entries}
    standings_response.raise_for_status.return_value = None

    with patch("core.config.THESPORTSDB_KEY", "test_key"):
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = [search_response, standings_response]
            with patch("asyncio.sleep", new_callable=AsyncMock):
                result = await sports_skill._fetch_football_standings("Botafogo", None)

                assert result["free_tier_limited"] is True
                assert "5 posições" in result["note"]


@pytest.mark.asyncio
async def test_execute_get_standings_routes_correctly(sports_skill):
    """Testa que execute() roteia get_standings corretamente."""
    with patch("core.config.THESPORTSDB_KEY", "123"):
        # Preencher cache para standings
        cached_data = {
            "league": "Brasileirão Série A",
            "entries_count": 5,
            "standings": [{"position": "1", "team_name": "Botafogo"}],
        }
        cache_key = sports_skill._make_cache_key(
            "get_standings", "football", "Botafogo"
        )
        sports_skill.cache.set(cache_key, cached_data, "standings")

        context = {"user_id": 123}
        result = await sports_skill.execute(
            context,
            action="get_standings",
            sport="football",
            team_name="Botafogo"
        )

        assert result["status"] == "success"
        assert "standings" in result["data"]


@pytest.mark.asyncio
async def test_execute_get_standings_without_team_but_with_league(sports_skill):
    """Testa get_standings sem team_name mas com league (válido)."""
    with patch("core.config.THESPORTSDB_KEY", "123"):
        cached_data = {
            "league": "Premier League",
            "entries_count": 5,
            "standings": [{"position": "1"}],
        }
        cache_key = sports_skill._make_cache_key(
            "get_standings", "football", league="Premier League"
        )
        sports_skill.cache.set(cache_key, cached_data, "standings")

        context = {"user_id": 123}
        result = await sports_skill.execute(
            context,
            action="get_standings",
            sport="football",
            league="Premier League"
        )

        assert result["status"] == "success"


@pytest.mark.asyncio
async def test_fetch_football_standings_cannot_determine_league(sports_skill):
    """Testa erro quando não consegue determinar league_id."""
    with patch("core.config.THESPORTSDB_KEY", "test_key"):
        with pytest.raises(ValueError, match="determinar a liga"):
            await sports_skill._fetch_football_standings(None, None)


# ==================== TESTES DE shutdown ====================


@pytest.mark.asyncio
async def test_shutdown_closes_http_client(sports_skill):
    """Testa que shutdown() fecha o HTTP client."""
    # Simular que o client foi criado
    mock_client = AsyncMock()
    sports_skill._http_client = mock_client

    await sports_skill.shutdown()

    # Verifica que aclose() foi chamado
    mock_client.aclose.assert_called_once()


@pytest.mark.asyncio
async def test_shutdown_without_http_client(sports_skill):
    """Testa que shutdown() não falha sem HTTP client."""
    sports_skill._http_client = None

    # Não deve levantar exception
    await sports_skill.shutdown()

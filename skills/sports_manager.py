"""
Sports Manager Skill - Curupira Bot

Fornece resultados esportivos, calendário e classificação via TheSportsDB.
Suporta futebol com actions: get_results, get_schedule, get_standings.

Alinhamento ao Manifesto Curupira:
- Eficiência: Cache com TTL diferenciado, connection pooling
- Leveza: < 1MB RAM adicional
- Resiliência: Fallbacks automáticos, never crashes agent loop
"""

import time
import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, Optional
from collections import OrderedDict
from urllib.parse import quote
import httpx

from skills.base import BaseSkill
from core import config

# Constantes para inferência de season
BRAZILIAN_LEAGUE_KEYWORDS = [
    "brasileir", "serie", "carioca", "paulist", "copa do brasil",
    "paranaense", "gaucho", "mineiro", "baiano",
]


class SportsCache:
    """
    Cache em memória para resultados esportivos com TTL diferenciado.
    Implementa LRU implícito via timestamp e cleanup automático.
    """

    # TTL por tipo de dado (em segundos)
    TTL_CONFIG = {
        "recent_results": 300,  # 5 min para resultados recentes
        "schedule": 1800,  # 30 min para calendário
        "standings": 3600,  # 1h para tabelas de classificação
        "team_metadata": 86400,  # 24h para metadados (logos, nomes)
    }

    def __init__(self, max_size: int = 100):
        """
        Inicializa o cache com tamanho máximo definido.

        Args:
            max_size: Número máximo de entradas (~500KB com 100 entradas)
        """
        self._cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self._max_size = max_size
        self.logger = logging.getLogger("SportsCache")

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Retorna dado do cache se não expirado, senão None.
        Move a chave para o final (true LRU behavior).

        Args:
            key: Chave do cache

        Returns:
            Dados cacheados ou None se não encontrado/expirado
        """
        if key not in self._cache:
            return None

        entry = self._cache[key]
        age = time.time() - entry["timestamp"]

        if age > entry["ttl"]:
            # Cache expirado - cleanup lazy
            del self._cache[key]
            return None

        # Move para o final (marca como recentemente acessada - true LRU)
        self._cache.move_to_end(key)
        return entry["data"]

    def set(self, key: str, data: Dict[str, Any], cache_type: str = "recent_results"):
        """
        Armazena dado no cache com TTL apropriado.

        Args:
            key: Chave do cache
            data: Dados a armazenar
            cache_type: Tipo de cache (define TTL)
        """
        # Cleanup preventivo se cache muito grande
        if len(self._cache) >= self._max_size:
            self._evict_oldest()

        # Remove chave existente para reinseri-la no final (LRU behavior)
        if key in self._cache:
            del self._cache[key]

        self._cache[key] = {
            "data": data,
            "timestamp": time.time(),
            "ttl": self.TTL_CONFIG.get(cache_type, 300),
        }

    def _evict_oldest(self):
        """
        Remove 20% das entradas menos recentemente usadas (true LRU com OrderedDict).
        Complexidade: O(k) onde k = evict_count (melhor que O(n log n) do sorted).
        """
        if not self._cache:
            return

        evict_count = max(1, self._max_size // 5)

        # OrderedDict + move_to_end() implementa true LRU
        # Entradas no início = menos recentemente acessadas
        for _ in range(min(evict_count, len(self._cache))):
            self._cache.popitem(last=False)  # Remove do início (LRU)

        self.logger.info(f"Cache eviction: removidas {evict_count} entradas antigas")

    def invalidate_pattern(self, pattern: str):
        """
        Invalida todas as chaves que contenham o padrão.

        Args:
            pattern: String para buscar nas chaves
        """
        keys_to_delete = [k for k in self._cache if pattern in k]
        for key in keys_to_delete:
            del self._cache[key]

        if keys_to_delete:
            self.logger.info(f"Cache invalidation: {len(keys_to_delete)} entradas")

    def stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do cache."""
        return {
            "size": len(self._cache),
            "max_size": self._max_size,
            "usage_percent": (len(self._cache) / self._max_size) * 100,
        }


class SportsManagerSkill(BaseSkill):
    """
    Skill principal para resultados esportivos.
    TheSportsDB para futebol: get_results, get_schedule, get_standings.
    """

    SUPPORTED_ACTIONS = {"get_results", "get_schedule", "get_standings"}

    def __init__(self, memory_manager):
        """
        Inicializa a Sports Manager Skill.

        Args:
            memory_manager: Gerenciador de memória para persistência de preferências
        """
        self.logger = logging.getLogger("SportsManagerSkill")
        self.memory = memory_manager
        self.cache = SportsCache()

        # Cliente HTTP global (connection pooling)
        self._http_client: Optional[httpx.AsyncClient] = None

        # Rate limiting para TheSportsDB (1 req/s)
        self._last_thesportsdb_call: float = 0
        self._THESPORTSDB_MIN_INTERVAL = 1.0

    @property
    def name(self) -> str:
        return "get_sports_info"

    @property
    def display_name(self) -> str:
        return "⚽ Resultados Esportivos"

    @property
    def description(self) -> str:
        return "Busca resultados, calendário e classificação de esportes tradicionais e eSports"

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["get_results", "get_schedule", "get_standings"],
                    "description": (
                        "Ação a executar:\n"
                        "- get_results: Buscar resultados de jogos recentes\n"
                        "- get_schedule: Buscar próximos jogos agendados\n"
                        "- get_standings: Buscar tabela de classificação da liga"
                    ),
                },
                "sport": {
                    "type": "string",
                    "enum": [
                        "football",
                        "basketball",
                        "csgo",
                        "lol",
                        "dota2",
                        "valorant",
                    ],
                    "description": (
                        "Esporte a consultar. Se omitido, usa sports_favorite_sport dos fatos persistentes. "
                        "Valores: football (futebol), basketball, csgo, lol, dota2, valorant"
                    ),
                },
                "team_name": {
                    "type": "string",
                    "description": (
                        "Nome do time a buscar. Se omitido, usa sports_favorite_team dos fatos persistentes. "
                        "Exemplos: 'Flamengo', 'Real Madrid', 'FURIA', 'Cloud9'"
                    ),
                },
                "league": {
                    "type": "string",
                    "description": (
                        "Liga/campeonato a consultar (usado com get_standings). "
                        "Se omitido, tenta inferir pela preferência ou pelo time. "
                        "Exemplos: 'Brasileirão Série A', 'Premier League', 'LCS'"
                    ),
                },
                "limit": {
                    "type": "integer",
                    "description": "Número máximo de resultados a retornar. Padrão: 5. Máximo: 10.",
                    "minimum": 1,
                    "maximum": 10,
                },
            },
            "required": ["action"],
        }

    def _validate_and_sanitize_team_name(self, team_name: str) -> str:
        """
        Valida e sanitiza o nome do time para evitar injeção de caracteres especiais.

        Args:
            team_name: Nome do time fornecido pelo usuário

        Returns:
            Nome do time sanitizado

        Raises:
            ValueError: Se o nome for inválido
        """
        import re

        # Validação de tipo e conteúdo
        if not isinstance(team_name, str) or not team_name.strip():
            raise ValueError("Nome do time inválido. Forneça um nome válido.")

        # Sanitização: remove espaços extras
        team_name = team_name.strip()

        # Validação de comprimento
        if len(team_name) < 2:
            raise ValueError(
                "Nome do time muito curto. Forneça pelo menos 2 caracteres."
            )
        if len(team_name) > 100:
            raise ValueError("Nome do time muito longo. Máximo 100 caracteres.")

        # Sanitização de segurança: aceita apenas alfanuméricos, espaços, hífens e acentos
        # Padrão: letras (incluindo acentuadas), números, espaços, hífens, pontos
        if not re.match(r"^[\w\s\-\.]+$", team_name, re.UNICODE):
            raise ValueError(
                "Nome do time contém caracteres não permitidos. "
                "Use apenas letras, números, espaços, hífens e pontos."
            )

        return team_name

    async def execute(self, context: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        Ponto de entrada principal da skill.

        Args:
            context: Contexto do bot (user_id, job_queue, etc)
            **kwargs: Parâmetros da skill (action, sport, team_name, league, limit)

        Returns:
            Dict no formato MCP-Lite (success/error)
        """
        user_id = context.get("user_id")
        if not user_id:
            return self.error("user_id ausente no contexto.")

        action = kwargs.get("action")
        if not action:
            return self.error("Parâmetro 'action' é obrigatório.")

        if action not in self.SUPPORTED_ACTIONS:
            return self.error(
                f"Ação '{action}' não reconhecida. "
                f"Ações disponíveis: {', '.join(sorted(self.SUPPORTED_ACTIONS))}"
            )

        # Resolução de preferências (override > user facts)
        sport = kwargs.get("sport")
        team_name = kwargs.get("team_name")
        league = kwargs.get("league")
        limit = min(kwargs.get("limit", 5), 10)

        if not sport:
            sport = await self.memory.get_fact_value(user_id, "sports_favorite_sport")

        if not team_name:
            team_name = await self.memory.get_fact_value(
                user_id, "sports_favorite_team"
            )

        # Validação de parâmetros obrigatórios
        if not sport:
            return self.error(
                "Esporte não especificado e sem preferência salva. "
                "Pergunte ao usuário: 'Qual esporte você acompanha?' "
                "e use save_user_fact para persistir sports_favorite_sport."
            )

        # team_name obrigatório para results/schedule, opcional para standings se league fornecido
        if not team_name and not (action == "get_standings" and league):
            return self.error(
                "Time não especificado e sem preferência salva. "
                "Pergunte ao usuário: 'Qual time você torce?' "
                "e use save_user_fact para persistir sports_favorite_team."
            )

        # Validação e sanitização de team_name (segurança + clean code)
        if team_name:
            try:
                team_name = self._validate_and_sanitize_team_name(team_name)
            except ValueError as e:
                return self.error(str(e))

        # Apenas futebol suportado
        if sport != "football":
            return self.error(
                f"Esporte '{sport}' não suportado na versão atual. "
                f"Apenas 'football' está disponível."
            )

        # Validação explícita de API key (segurança)
        if not config.THESPORTSDB_KEY:
            return self.error(
                "THESPORTSDB_KEY não configurada. "
                "Configure a chave da API no arquivo .env (cadastro gratuito em thesportsdb.com)."
            )

        # Determinar cache_key e cache_type por action
        if action == "get_results":
            cache_key = self._make_cache_key(action, sport, team_name, limit=limit)
            cache_type = "recent_results"
        elif action == "get_schedule":
            cache_key = self._make_cache_key(action, sport, team_name)
            cache_type = "schedule"
        else:  # get_standings
            cache_key = self._make_cache_key(action, sport, team_name, league=league)
            cache_type = "standings"

        # Verificar cache
        cached = self.cache.get(cache_key)
        if cached:
            self.logger.info(f"Cache hit: {cache_key}")
            return self.success(
                cached, message="Dados do cache (atualizados recentemente)"
            )

        # Executar busca
        try:
            if action == "get_results":
                data = await self._handle_get_results(context, sport, team_name, limit)
            elif action == "get_schedule":
                data = await self._handle_get_schedule(context, sport, team_name)
            else:  # get_standings
                data = await self._handle_get_standings(context, sport, team_name, league)

            # Armazenar no cache
            self.cache.set(cache_key, data, cache_type)

            return self.success(data)

        except ValueError as e:
            return self.error(str(e))
        except Exception as e:
            self.logger.error(f"Erro inesperado na Sports Skill: {e}", exc_info=True)
            return self.error(f"Erro ao buscar dados esportivos: {e}")

    def _make_cache_key(
        self,
        action: str,
        sport: str,
        team: str = None,
        league: str = None,
        limit: int = None,
    ) -> str:
        """
        Gera chave de cache determinística.

        Args:
            action: Ação (get_results, get_schedule, get_standings)
            sport: Esporte
            team: Nome do time (opcional)
            league: Liga (opcional)
            limit: Número máximo de resultados (opcional)

        Returns:
            Chave de cache formatada
        """
        parts = [action, sport]
        if team:
            parts.append(team.lower().strip())
        if league:
            parts.append(league.lower().strip())
        if limit is not None:
            parts.append(str(limit))
        return ":".join(parts)

    async def _get_http_client(self) -> httpx.AsyncClient:
        """Lazy load do cliente HTTP global (connection pooling)."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(10.0),
                limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
            )
        return self._http_client

    async def _fetch_with_retry(
        self, url: str, headers: Dict = None, retries: int = 3
    ) -> Dict[str, Any]:
        """
        Executa requisição HTTP com retry exponencial.

        Args:
            url: URL completa da API
            headers: Headers HTTP (opcional)
            retries: Número de tentativas

        Returns:
            JSON parseado da resposta

        Raises:
            Exception: Se todas as tentativas falharem
        """
        client = await self._get_http_client()
        last_exception = None

        for attempt in range(retries):
            try:
                response = await client.get(url, headers=headers or {}, timeout=10.0)
                response.raise_for_status()
                return response.json()

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    # Rate limit - aguardar mais tempo
                    backoff = 2**attempt
                    self.logger.warning(
                        f"Rate limit hit, retrying in {backoff}s (attempt {attempt + 1}/{retries})..."
                    )
                    await asyncio.sleep(backoff)
                    last_exception = e
                elif e.response.status_code == 401:
                    # API key inválida - não adianta retry
                    raise ValueError("API key inválida. Verifique o .env.")
                else:
                    raise  # Outros erros HTTP não devem fazer retry

            except (httpx.TimeoutException, httpx.NetworkError) as e:
                last_exception = e
                backoff = 2**attempt
                self.logger.warning(
                    f"Network error (attempt {attempt + 1}/{retries}), retrying in {backoff}s..."
                )
                await asyncio.sleep(backoff)

        raise (
            last_exception if last_exception else Exception("Unknown error in _fetch_with_retry")
        )

    def _thesportsdb_url(self, endpoint: str) -> str:
        """
        Constrói URL completa do TheSportsDB com API key.

        Args:
            endpoint: Endpoint da API (ex: 'searchteams.php?t=Arsenal')

        Returns:
            URL completa

        Example:
            endpoint='searchteams.php?t=Arsenal'
            returns='https://www.thesportsdb.com/api/v1/json/123/searchteams.php?t=Arsenal'
        """
        if not config.THESPORTSDB_KEY:
            raise ValueError(
                "THESPORTSDB_KEY não configurada. "
                "Cadastre-se gratuitamente em thesportsdb.com"
            )

        base_url = "https://www.thesportsdb.com/api/v1/json"
        return f"{base_url}/{config.THESPORTSDB_KEY}/{endpoint}"

    async def _fetch_thesportsdb(self, endpoint: str) -> Dict[str, Any]:
        """
        Fetch do TheSportsDB com rate limiting local de 1 req/s.

        Args:
            endpoint: Endpoint da API

        Returns:
            JSON parseado da resposta
        """
        # Rate limiting: garantir 1s entre chamadas
        now = time.time()
        elapsed = now - self._last_thesportsdb_call

        if elapsed < self._THESPORTSDB_MIN_INTERVAL:
            sleep_time = self._THESPORTSDB_MIN_INTERVAL - elapsed
            self.logger.info(f"TheSportsDB throttle: aguardando {sleep_time:.2f}s...")
            await asyncio.sleep(sleep_time)

        url = self._thesportsdb_url(endpoint)
        data = await self._fetch_with_retry(url)

        self._last_thesportsdb_call = time.time()
        return data

    # ==================== RESOLUÇÃO DE TIME E SEASON ====================

    async def _resolve_team_info(self, team_name: str) -> Dict[str, Any]:
        """
        Resolve nome do time para dict completo via TheSportsDB.
        Usa cache team_metadata (24h TTL) para evitar chamadas repetidas.
        """
        cache_key = f"team_meta:{team_name.lower().strip()}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached

        endpoint = f"searchteams.php?t={team_name}"
        data = await self._fetch_thesportsdb(endpoint)

        if not data.get("teams"):
            raise ValueError(f"Time '{team_name}' não encontrado.")

        team = data["teams"][0]
        self.cache.set(cache_key, team, "team_metadata")
        return team

    def _determine_season(
        self, league_name: Optional[str] = None, alternate: bool = False
    ) -> str:
        """
        Determina string de season para TheSportsDB lookuptable.

        Ligas brasileiras usam formato ano único ("2026").
        Ligas europeias usam formato cruzado ("2025-2026").

        Args:
            league_name: Nome da liga (usado para inferir brasileiro vs europeu)
            alternate: Se True, retorna formato oposto (usado em fallback)

        Returns:
            String de season no formato correto
        """
        now = datetime.now()
        year = now.year
        month = now.month

        is_brazilian = False
        if league_name:
            lower_league = league_name.lower()
            is_brazilian = any(kw in lower_league for kw in BRAZILIAN_LEAGUE_KEYWORDS)

        if is_brazilian and not alternate:
            return str(year)
        elif is_brazilian and alternate:
            if month >= 7:
                return f"{year}-{year + 1}"
            else:
                return f"{year - 1}-{year}"
        elif not alternate:
            # Europeia / default
            if month >= 7:
                return f"{year}-{year + 1}"
            else:
                return f"{year - 1}-{year}"
        else:
            # Alternate europeia: tenta formato brasileiro
            return str(year)

    # ==================== HANDLERS POR ACTION ====================

    async def _handle_get_results(
        self, context: Dict[str, Any], sport: str, team_name: str, limit: int
    ) -> Dict[str, Any]:
        """Handler para action=get_results."""
        if sport == "football":
            return await self._fetch_thesportsdb_results(team_name, limit)
        else:
            raise ValueError(f"Esporte '{sport}' não suportado na versão atual.")

    async def _handle_get_schedule(
        self, context: Dict[str, Any], sport: str, team_name: str
    ) -> Dict[str, Any]:
        """Handler para action=get_schedule."""
        if sport == "football":
            return await self._fetch_football_schedule(team_name)
        else:
            raise ValueError(f"Esporte '{sport}' não suportado na versão atual.")

    async def _handle_get_standings(
        self, context: Dict[str, Any], sport: str,
        team_name: Optional[str], league: Optional[str]
    ) -> Dict[str, Any]:
        """Handler para action=get_standings."""
        if sport == "football":
            return await self._fetch_football_standings(team_name, league)
        else:
            raise ValueError(f"Esporte '{sport}' não suportado na versão atual.")

    # ==================== FETCH: RESULTADOS ====================

    async def _fetch_thesportsdb_results(
        self, team_name: str, limit: int
    ) -> Dict[str, Any]:
        """Busca últimos resultados de um time no TheSportsDB."""
        try:
            team = await self._resolve_team_info(team_name)
            team_id = team["idTeam"]
            team_full_name = team["strTeam"]

            results_endpoint = f"eventslast.php?id={team_id}"
            results_data = await self._fetch_thesportsdb(results_endpoint)

            if not results_data.get("results"):
                return {
                    "team_name": team_full_name,
                    "team_id": team_id,
                    "matches": [],
                    "matches_count": 0,
                    "message": f"Nenhum resultado recente encontrado para {team_full_name}.",
                }

            # Filtrar apenas jogos com placar (completed)
            # Usa OR: basta um dos scores existir para considerar finalizado
            completed_events = [
                event
                for event in results_data["results"]
                if (event.get("intHomeScore") not in (None, ""))
                or (event.get("intAwayScore") not in (None, ""))
            ]

            if not completed_events:
                return {
                    "team_name": team_full_name,
                    "team_id": team_id,
                    "matches": [],
                    "matches_count": 0,
                    "message": (
                        f"Nenhum jogo finalizado encontrado para {team_full_name}. "
                        f"A API retornou {len(results_data['results'])} jogo(s), "
                        f"mas todos estão agendados ou sem placar."
                    ),
                }

            # Ordenar por data decrescente (mais recente primeiro)
            completed_events.sort(
                key=lambda e: e.get("dateEvent", ""),
                reverse=True,
            )

            matches = []
            for event in completed_events[:limit]:
                matches.append({
                    "date": event.get("dateEvent"),
                    "home_team": event.get("strHomeTeam"),
                    "away_team": event.get("strAwayTeam"),
                    "home_score": event.get("intHomeScore"),
                    "away_score": event.get("intAwayScore"),
                    "league": event.get("strLeague"),
                    "status": event.get("strStatus"),
                })

            return {
                "team_name": team_full_name,
                "team_id": team_id,
                "matches_count": len(matches),
                "matches": matches,
            }

        except Exception as e:
            self.logger.error(f"Erro ao buscar resultados no TheSportsDB: {e}")
            raise

    # ==================== FETCH: SCHEDULE ====================

    async def _fetch_football_schedule(self, team_name: str) -> Dict[str, Any]:
        """Busca próximos jogos de um time no TheSportsDB."""
        team = await self._resolve_team_info(team_name)
        team_id = team["idTeam"]
        team_full_name = team["strTeam"]

        endpoint = f"eventsnext.php?id={team_id}"
        data = await self._fetch_thesportsdb(endpoint)

        events = data.get("events") or []

        if not events:
            return {
                "team_name": team_full_name,
                "team_id": team_id,
                "upcoming_matches": [],
                "matches_count": 0,
                "message": f"Nenhum próximo jogo encontrado para {team_full_name}.",
            }

        # Ordenar por data ascendente (mais próximo primeiro)
        events.sort(key=lambda e: e.get("dateEvent", ""))

        upcoming = []
        for event in events:
            upcoming.append({
                "date": event.get("dateEvent"),
                "time": event.get("strTime"),
                "home_team": event.get("strHomeTeam"),
                "away_team": event.get("strAwayTeam"),
                "league": event.get("strLeague"),
                "round": event.get("intRound"),
                "venue": event.get("strVenue"),
            })

        return {
            "team_name": team_full_name,
            "team_id": team_id,
            "matches_count": len(upcoming),
            "upcoming_matches": upcoming,
            "free_tier_limited": len(events) <= 1,
            "note": (
                "Plano gratuito da API retorna apenas 1 próximo jogo."
                if len(events) <= 1 else None
            ),
        }

    # ==================== FETCH: STANDINGS ====================

    async def _fetch_football_standings(
        self, team_name: Optional[str], league: Optional[str]
    ) -> Dict[str, Any]:
        """Busca classificação de uma liga no TheSportsDB."""
        league_id = None
        league_name = league

        # Resolver league_id via team ou via nome da liga
        if team_name:
            team_info = await self._resolve_team_info(team_name)
            league_id = team_info.get("idLeague")
            if not league_name:
                league_name = team_info.get("strLeague")

        if not league_id and league:
            # URL-encode league name para evitar problemas com caracteres especiais
            league_encoded = quote(league)
            endpoint = f"search_all_teams.php?l={league_encoded}"
            data = await self._fetch_thesportsdb(endpoint)
            teams = data.get("teams") or []
            if teams:
                league_id = teams[0].get("idLeague")
            else:
                raise ValueError(f"Liga '{league}' não encontrada no TheSportsDB.")

        if not league_id:
            raise ValueError(
                "Não foi possível determinar a liga. "
                "Forneça o nome do time ou da liga."
            )

        # Determinar season e buscar tabela
        season = self._determine_season(league_name)
        endpoint = f"lookuptable.php?l={league_id}&s={season}"
        data = await self._fetch_thesportsdb(endpoint)

        table = data.get("table") or []

        # Fallback: tentar formato de season alternativo
        if not table:
            alt_season = self._determine_season(league_name, alternate=True)
            if alt_season != season:
                endpoint = f"lookuptable.php?l={league_id}&s={alt_season}"
                data = await self._fetch_thesportsdb(endpoint)
                table = data.get("table") or []
                if table:
                    season = alt_season

        if not table:
            return {
                "league": league_name,
                "season": season,
                "standings": [],
                "entries_count": 0,
                "message": f"Classificação não encontrada para {league_name} ({season}).",
            }

        standings = []
        for entry in table:
            standings.append({
                "position": entry.get("intRank"),
                "team_name": entry.get("strTeam"),
                "team_id": entry.get("idTeam"),
                "played": entry.get("intPlayed"),
                "wins": entry.get("intWin"),
                "draws": entry.get("intDraw"),
                "losses": entry.get("intLoss"),
                "goals_for": entry.get("intGoalsFor"),
                "goals_against": entry.get("intGoalsAgainst"),
                "goal_difference": entry.get("intGoalDifference"),
                "points": entry.get("intPoints"),
            })

        return {
            "league": league_name,
            "season": season,
            "entries_count": len(standings),
            "standings": standings,
            "free_tier_limited": len(standings) <= 5,
            "note": (
                "Plano gratuito da API retorna apenas 5 posições da tabela."
                if len(standings) <= 5 else None
            ),
        }

    async def shutdown(self):
        """Fecha o cliente HTTP ao desligar o bot."""
        if self._http_client:
            await self._http_client.aclose()
            self.logger.info("HTTP client fechado.")

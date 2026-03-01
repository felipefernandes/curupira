"""
tests/test_config_toml.py
=========================
Testes de integração para o sistema de configuração TOML do Curupira.

Valida:
- Carregamento de config.toml (quando presente)
- Prioridade de overrides: ENV > TOML > Default
- skill_enabled() para feature flags
- Suporte a feeds RSS e job_hunter via TOML

Estratégia de isolamento:
- Cada teste usa importlib para criar uma instância fresh do módulo SEM
  alterar sys.modules permanentemente, prevenindo contaminação cross-test.
"""

import importlib
import importlib.util
import os
import sys
import textwrap
import pytest
from pathlib import Path
from unittest.mock import patch, mock_open

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

_CONFIG_MODULE_PATH = Path(__file__).resolve().parent.parent / "core" / "config.py"


# ── Helpers ────────────────────────────────────────────────────────────

def _load_config_isolated(toml_content: str = "", env_overrides: dict = None, monkeypatch=None):
    """
    Carrega core.config em um namespace isolado sem modificar sys.modules.
    Isso evita qualquer poluição de estado entre testes.
    """
    env_overrides = env_overrides or {}

    if monkeypatch:
        for k, v in env_overrides.items():
            monkeypatch.setenv(k, v)
        # Limpar vars que possam interferir
        for key in [
            "TELEGRAM_TOKEN", "AI_PROVIDER", "GROQ_API_KEY", "GEMINI_API_KEY",
            "AUTHORIZED_USER_ID", "HEARTBEAT_INTERVAL", "MCP_SERVERS_CONFIG",
            "RSS_FEEDS_JSON", "REFLECTION_ENABLED", "JOB_HUNTER_URL",
            "JOB_HUNTER_KEYWORDS", "JOB_HUNTER_SCORE_CUTOFF", "JOB_HUNTER_SOURCES",
            "SKILL_WEATHER_ENABLED", "SKILL_REMINDERS_ENABLED", "SKILL_SPORTS_ENABLED",
            "GROQ_MODEL", "GEMINI_MODEL", "GROQ_TEMPERATURE", "GROQ_TEMPERATURE_REFLECTION",
            "REFLECTION_GREETING_HOUR_START", "REFLECTION_GREETING_HOUR_END",
            "RETRY_ATTEMPTS", "RETRY_INITIAL_DELAY",
            "THESPORTSDB_KEY", "API_FOOTBALL_KEY", "PANDASCORE_KEY",
        ]:
            if key not in env_overrides:
                monkeypatch.delenv(key, raising=False)

    toml_bytes = toml_content.encode("utf-8") if toml_content else b""

    def _fake_is_file(self):
        path_str = str(self)
        if path_str.endswith("config.toml") and not path_str.endswith("default.config.toml"):
            return bool(toml_content)
        return False  # mcp.json e outros: não existem no teste

    m = mock_open(read_data=toml_bytes)
    m.return_value.read = lambda: toml_bytes

    # Cria um módulo isolado sem inserir em sys.modules
    spec = importlib.util.spec_from_file_location("_test_config_isolated", _CONFIG_MODULE_PATH)
    mod = importlib.util.module_from_spec(spec)

    with patch("pathlib.Path.is_file", _fake_is_file), \
         patch("builtins.open", m), \
         patch("dotenv.load_dotenv"):
        spec.loader.exec_module(mod)

    return mod


# ── Defaults ───────────────────────────────────────────────────────────

def test_defaults_sem_toml_e_sem_env(monkeypatch):
    """Sem config.toml e sem ENV, deve usar os valores padrão internos."""
    cfg = _load_config_isolated(toml_content="", monkeypatch=monkeypatch)

    assert cfg.AI_PROVIDER == "groq"
    assert cfg.HEARTBEAT_INTERVAL == 1800
    assert cfg.AUTHORIZED_USER_ID == 0
    assert cfg.MCP_SERVERS == {}
    assert "G1" in cfg.RSS_FEEDS
    assert cfg.REFLECTION_ENABLED is True


# ── Prioridade ENV > TOML ──────────────────────────────────────────────

def test_env_sobrescreve_toml_ai_provider(monkeypatch):
    """ENV AI_PROVIDER deve prevalecer sobre o valor no TOML."""
    toml = textwrap.dedent("""
        [bot]
        ai_provider = "groq"
    """)
    cfg = _load_config_isolated(toml_content=toml, env_overrides={"AI_PROVIDER": "gemini"}, monkeypatch=monkeypatch)
    assert cfg.AI_PROVIDER == "gemini"


def test_env_sobrescreve_toml_heartbeat(monkeypatch):
    """ENV HEARTBEAT_INTERVAL deve prevalecer sobre o valor no TOML."""
    toml = textwrap.dedent("""
        [bot]
        heartbeat_interval = 600
    """)
    cfg = _load_config_isolated(toml_content=toml, env_overrides={"HEARTBEAT_INTERVAL": "300"}, monkeypatch=monkeypatch)
    assert cfg.HEARTBEAT_INTERVAL == 300


# ── Carregamento de TOML ───────────────────────────────────────────────

def test_toml_carrega_ai_provider(monkeypatch):
    """Deve carregar ai_provider do config.toml."""
    toml = textwrap.dedent("""
        [bot]
        ai_provider = "gemini"
    """)
    cfg = _load_config_isolated(toml_content=toml, monkeypatch=monkeypatch)
    assert cfg.AI_PROVIDER == "gemini"


def test_toml_carrega_heartbeat_interval(monkeypatch):
    """Deve carregar heartbeat_interval do config.toml."""
    toml = textwrap.dedent("""
        [bot]
        heartbeat_interval = 900
    """)
    cfg = _load_config_isolated(toml_content=toml, monkeypatch=monkeypatch)
    assert cfg.HEARTBEAT_INTERVAL == 900


def test_toml_carrega_groq_model(monkeypatch):
    """Deve carregar o modelo Groq do config.toml."""
    toml = textwrap.dedent("""
        [ai.groq]
        model = "llama-3.3-70b-versatile"
    """)
    cfg = _load_config_isolated(toml_content=toml, monkeypatch=monkeypatch)
    assert cfg.GROQ_MODEL == "llama-3.3-70b-versatile"


def test_toml_carrega_reflection_settings(monkeypatch):
    """Deve carregar configurações da reflexão a partir do TOML."""
    toml = textwrap.dedent("""
        [reflection]
        enabled = false
        greeting_hour_start = 8
        greeting_hour_end = 10
    """)
    cfg = _load_config_isolated(toml_content=toml, monkeypatch=monkeypatch)
    assert cfg.REFLECTION_ENABLED is False
    assert cfg.REFLECTION_GREETING_HOUR_START == 8
    assert cfg.REFLECTION_GREETING_HOUR_END == 10


# ── skill_enabled() ────────────────────────────────────────────────────

def test_skill_enabled_padrao_true(monkeypatch):
    """Skills habilitadas por padrão retornam True sem configuração."""
    cfg = _load_config_isolated(toml_content="", monkeypatch=monkeypatch)
    assert cfg.skill_enabled("weather") is True
    assert cfg.skill_enabled("reminders") is True


def test_skill_enabled_padrao_false_github(monkeypatch):
    """A skill 'github' é desabilitada por padrão."""
    cfg = _load_config_isolated(toml_content="", monkeypatch=monkeypatch)
    assert cfg.skill_enabled("github") is False


def test_skill_desabilitada_via_toml(monkeypatch):
    """Deve desabilitar uma skill via config.toml."""
    toml = textwrap.dedent("""
        [skills]
        weather = false
        job_hunter = false
    """)
    cfg = _load_config_isolated(toml_content=toml, monkeypatch=monkeypatch)
    assert cfg.skill_enabled("weather") is False
    assert cfg.skill_enabled("job_hunter") is False
    assert cfg.skill_enabled("reminders") is True  # não alterado, usa padrão


def test_skill_env_sobrescreve_toml(monkeypatch):
    """Variável de ambiente SKILL_WEATHER_ENABLED deve prevalecer sobre TOML."""
    toml = textwrap.dedent("""
        [skills]
        weather = false
    """)
    cfg = _load_config_isolated(
        toml_content=toml,
        env_overrides={"SKILL_WEATHER_ENABLED": "true"},
        monkeypatch=monkeypatch,
    )
    assert cfg.skill_enabled("weather") is True


def test_skill_env_desabilita_skill(monkeypatch):
    """Variável SKILL_REMINDERS_ENABLED=false desabilita skill padrão."""
    cfg = _load_config_isolated(
        toml_content="",
        env_overrides={"SKILL_REMINDERS_ENABLED": "false"},
        monkeypatch=monkeypatch,
    )
    assert cfg.skill_enabled("reminders") is False


# ── RSS via TOML ───────────────────────────────────────────────────────

def test_rss_feeds_carregados_do_toml(monkeypatch):
    """Deve usar feeds definidos no TOML quando não há RSS_FEEDS_JSON no ENV."""
    toml = textwrap.dedent("""
        [skills.rss.feeds]
        MeuBlog = "https://meublog.com/feed"
        OutroFeed = "https://outro.com/rss"
    """)
    cfg = _load_config_isolated(toml_content=toml, monkeypatch=monkeypatch)
    assert "MeuBlog" in cfg.RSS_FEEDS
    assert cfg.RSS_FEEDS["MeuBlog"] == "https://meublog.com/feed"
    # Padrão G1 não deve estar presente (foi sobrescrito)
    assert "G1" not in cfg.RSS_FEEDS


def test_rss_feeds_env_sobrescreve_toml(monkeypatch):
    """RSS_FEEDS_JSON ENV deve prevalecer sobre feeds no TOML."""
    toml = textwrap.dedent("""
        [skills.rss.feeds]
        MeuBlog = "https://meublog.com/feed"
    """)
    env = '{"EnvFeed": "https://envfeed.com/rss"}'
    cfg = _load_config_isolated(
        toml_content=toml,
        env_overrides={"RSS_FEEDS_JSON": env},
        monkeypatch=monkeypatch,
    )
    assert "EnvFeed" in cfg.RSS_FEEDS
    assert "MeuBlog" not in cfg.RSS_FEEDS


# ── Job Hunter via TOML ────────────────────────────────────────────────

def test_job_hunter_keywords_do_toml(monkeypatch):
    """Deve carregar keywords do Job Hunter via TOML."""
    toml = textwrap.dedent("""
        [skills.job_hunter]
        keywords = ["Python", "AI", "Remote"]
    """)
    cfg = _load_config_isolated(toml_content=toml, monkeypatch=monkeypatch)
    assert cfg.JOB_HUNTER_KEYWORDS == ["Python", "AI", "Remote"]


def test_job_hunter_keywords_vazias_retorna_none(monkeypatch):
    """Lista vazia de keywords no TOML deve resultar em None."""
    toml = textwrap.dedent("""
        [skills.job_hunter]
        keywords = []
    """)
    cfg = _load_config_isolated(toml_content=toml, monkeypatch=monkeypatch)
    assert cfg.JOB_HUNTER_KEYWORDS is None


# ── _cfg_bool: fix do bug de string ───────────────────────────────────

def test_cfg_bool_toml_bool_false(monkeypatch):
    """_cfg_bool deve retornar False quando TOML entrega bool False (não string)."""
    toml = textwrap.dedent("""
        [reflection]
        enabled = false
    """)
    cfg = _load_config_isolated(toml_content=toml, monkeypatch=monkeypatch)
    assert cfg.REFLECTION_ENABLED is False


def test_cfg_bool_toml_int_zero(monkeypatch):
    """_cfg_bool deve retornar False quando TOML entrega 0 (fallback de tipo)."""
    toml = textwrap.dedent("""
        [reflection]
        enabled = 0
    """)
    cfg = _load_config_isolated(toml_content=toml, monkeypatch=monkeypatch)
    assert cfg.REFLECTION_ENABLED is False


def test_cfg_bool_toml_int_one(monkeypatch):
    """_cfg_bool deve retornar True quando TOML entrega 1."""
    toml = textwrap.dedent("""
        [reflection]
        enabled = 1
    """)
    cfg = _load_config_isolated(toml_content=toml, monkeypatch=monkeypatch)
    assert cfg.REFLECTION_ENABLED is True


# ── Retry via TOML ────────────────────────────────────────────────────

def test_retry_settings_do_toml(monkeypatch):
    """Deve carregar configurações de retry do TOML."""
    toml = textwrap.dedent("""
        [retry]
        attempts = 5
        initial_delay = 3.5
    """)
    cfg = _load_config_isolated(toml_content=toml, monkeypatch=monkeypatch)
    assert cfg.RETRY_ATTEMPTS == 5
    assert cfg.RETRY_INITIAL_DELAY == 3.5


# ── Sports via TOML ───────────────────────────────────────────────────

def test_sports_api_keys_do_toml(monkeypatch):
    """Deve carregar chaves das APIs de esportes do TOML."""
    toml = textwrap.dedent("""
        [skills.sports]
        thesportsdb_key = "abc123"
        api_football_key = "def456"
        pandascore_key = "ghi789"
    """)
    cfg = _load_config_isolated(toml_content=toml, monkeypatch=monkeypatch)
    assert cfg.THESPORTSDB_KEY == "abc123"
    assert cfg.API_FOOTBALL_KEY == "def456"
    assert cfg.PANDASCORE_KEY == "ghi789"


# ── Job Hunter score_cutoff via TOML ──────────────────────────────────

def test_job_hunter_score_cutoff_do_toml(monkeypatch):
    """Deve carregar score_cutoff do Job Hunter via TOML."""
    toml = textwrap.dedent("""
        [skills.job_hunter]
        score_cutoff = 0.75
    """)
    cfg = _load_config_isolated(toml_content=toml, monkeypatch=monkeypatch)
    assert cfg.JOB_HUNTER_SCORE_CUTOFF == 0.75


def test_job_hunter_score_cutoff_env_sobrescreve_toml(monkeypatch):
    """JOB_HUNTER_SCORE_CUTOFF ENV deve prevalecer sobre TOML."""
    toml = textwrap.dedent("""
        [skills.job_hunter]
        score_cutoff = 0.75
    """)
    cfg = _load_config_isolated(
        toml_content=toml,
        env_overrides={"JOB_HUNTER_SCORE_CUTOFF": "0.5"},
        monkeypatch=monkeypatch,
    )
    assert cfg.JOB_HUNTER_SCORE_CUTOFF == 0.5


# ── authorized_user_id negativo ───────────────────────────────────────

def test_authorized_user_id_negativo_fallback_zero(monkeypatch):
    """authorized_user_id < 0 no ENV deve resultar em 0 (fallback de segurança)."""
    cfg = _load_config_isolated(
        toml_content="",
        env_overrides={"AUTHORIZED_USER_ID": "-1"},
        monkeypatch=monkeypatch,
    )
    assert cfg.AUTHORIZED_USER_ID == 0


def test_authorized_user_id_invalido_fallback_zero(monkeypatch):
    """authorized_user_id não numérico deve resultar em 0."""
    cfg = _load_config_isolated(
        toml_content="",
        env_overrides={"AUTHORIZED_USER_ID": "nao_e_numero"},
        monkeypatch=monkeypatch,
    )
    assert cfg.AUTHORIZED_USER_ID == 0


# ── TOML inválido ─────────────────────────────────────────────────────

def test_toml_invalido_retorna_defaults(monkeypatch):
    """TOML com sintaxe inválida deve ser ignorado e usar defaults."""
    # Passamos conteúdo inválido, mas o mock abre como arquivo válido –
    # tomllib vai lançar TOMLDecodeError e _load_toml retorna {}.
    bad_toml = b"[bot\nai_provider = !!!invalid"

    def _fake_is_file(self):
        return str(self).endswith("config.toml") and not str(self).endswith("default.config.toml")

    m = mock_open(read_data=bad_toml)
    m.return_value.read = lambda: bad_toml

    for key in [
        "TELEGRAM_TOKEN", "AI_PROVIDER", "GROQ_API_KEY", "GEMINI_API_KEY",
        "AUTHORIZED_USER_ID", "HEARTBEAT_INTERVAL", "MCP_SERVERS_CONFIG",
        "RSS_FEEDS_JSON", "REFLECTION_ENABLED",
    ]:
        monkeypatch.delenv(key, raising=False)

    spec = importlib.util.spec_from_file_location("_test_config_isolated", _CONFIG_MODULE_PATH)
    mod = importlib.util.module_from_spec(spec)

    with patch("pathlib.Path.is_file", _fake_is_file), \
         patch("builtins.open", m), \
         patch("dotenv.load_dotenv"):
        spec.loader.exec_module(mod)

    # Com TOML inválido, deve usar defaults internos
    assert mod.AI_PROVIDER == "groq"
    assert mod.HEARTBEAT_INTERVAL == 1800
    assert "G1" in mod.RSS_FEEDS

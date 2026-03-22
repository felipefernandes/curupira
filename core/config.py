"""
core/config.py
==============
Carregamento unificado de configuração do Curupira.

Prioridade (maior → menor):
  1. Variáveis de Ambiente (OS / Docker / CI)
  2. Arquivo .env  (python-dotenv)
  3. config.toml   (arquivo de configuração do usuário)
  4. Valores padrão internos

Uso:
  from core import config
  print(config.AI_PROVIDER)
  if config.skill_enabled("weather"):
      ...
"""

import os
import json
import logging
import tomllib
from pathlib import Path
from typing import Any, Dict, Optional

from dotenv import load_dotenv

# ── Inicialização ──────────────────────────────────────────────────────
load_dotenv()

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent

# ── Carregamento do config.toml ────────────────────────────────────────

def _load_toml(path: Path) -> Dict[str, Any]:
    """Lê um arquivo TOML e retorna o dicionário. Retorna {} em caso de falha."""
    if not path.is_file():
        return {}
    try:
        with open(path, "rb") as f:
            data = tomllib.load(f)
        logger.info("Configuração carregada de %s", path)
        return data
    except tomllib.TOMLDecodeError as exc:
        logger.error("Erro ao ler %s (TOML inválido): %s", path, exc)
    except Exception as exc:  # pragma: no cover
        logger.error("Erro inesperado ao ler %s: %s", path, exc)
    return {}


_TOML: Dict[str, Any] = _load_toml(BASE_DIR / "config.toml")

if not _TOML:
    logger.warning(
        "config.toml não encontrado. "
        "Copie default.config.toml para config.toml para personalizar."
    )


def _toml_get(*keys: str, default: Any = None) -> Any:
    """Acessa um valor aninhado no TOML usando uma sequência de chaves."""
    node = _TOML
    for k in keys:
        if isinstance(node, dict):
            node = node.get(k)
        else:
            return default
        if node is None:
            return default
    return node


def _cfg(env_key: str, *toml_keys: str, default: Any = None) -> Any:
    """
    Resolve um valor de configuração respeitando a ordem de prioridade:
      ENV > TOML > default
    Retorna o valor como string raw (do ambiente) ou do tipo nativo do TOML.
    """
    env_val = os.getenv(env_key)
    if env_val is not None:
        return env_val
    toml_val = _toml_get(*toml_keys)
    if toml_val is not None:
        return toml_val
    return default


def _cfg_int(env_key: str, *toml_keys: str, default: int) -> int:
    val = _cfg(env_key, *toml_keys, default=default)
    try:
        return int(val)
    except (ValueError, TypeError):
        logger.error("Valor inválido para %s. Usando padrão: %s", env_key, default)
        return default


def _cfg_float(env_key: str, *toml_keys: str, default: float) -> float:
    val = _cfg(env_key, *toml_keys, default=default)
    try:
        return float(val)
    except (ValueError, TypeError):
        logger.error("Valor inválido para %s. Usando padrão: %s", env_key, default)
        return default


def _cfg_bool(env_key: str, *toml_keys: str, default: bool) -> bool:
    env_val = os.getenv(env_key)
    if env_val is not None:
        return env_val.lower() in ("true", "1", "yes")
    toml_val = _toml_get(*toml_keys)
    if toml_val is not None:
        if isinstance(toml_val, bool):
            return toml_val
        if isinstance(toml_val, str):
            return toml_val.lower() in ("true", "1", "yes")
        return bool(toml_val)  # fallback para int ou outros tipos
    return default


# ── Bot ────────────────────────────────────────────────────────────────

TELEGRAM_TOKEN: Optional[str] = _cfg("TELEGRAM_TOKEN", "bot", "telegram_token") or None

try:
    AUTHORIZED_USER_ID: int = _cfg_int(
        "AUTHORIZED_USER_ID", "bot", "authorized_user_id", default=0
    )
    if AUTHORIZED_USER_ID < 0:
        raise ValueError("AUTHORIZED_USER_ID deve ser um número positivo.")
except ValueError:
    AUTHORIZED_USER_ID = 0

HEARTBEAT_INTERVAL: int = _cfg_int(
    "HEARTBEAT_INTERVAL", "bot", "heartbeat_interval", default=30 * 60
)

# ── AI Provider ────────────────────────────────────────────────────────

AI_PROVIDER: str = (_cfg("AI_PROVIDER", "bot", "ai_provider", default="groq") or "groq").lower()

# ── Groq ───────────────────────────────────────────────────────────────

GROQ_API_KEY: Optional[str] = _cfg("GROQ_API_KEY", "ai", "groq", "api_key") or None
GROQ_MODEL: str = _cfg("GROQ_MODEL", "ai", "groq", "model", default="llama-3.1-8b-instant")
GROQ_TEMPERATURE: float = _cfg_float(
    "GROQ_TEMPERATURE", "ai", "groq", "temperature", default=0.7
)
GROQ_TEMPERATURE_REFLECTION: float = _cfg_float(
    "GROQ_TEMPERATURE_REFLECTION", "ai", "groq", "temperature_reflection", default=0.0
)

# ── Gemini ─────────────────────────────────────────────────────────────

GEMINI_API_KEY: Optional[str] = _cfg("GEMINI_API_KEY", "ai", "gemini", "api_key") or None
GEMINI_MODEL: str = _cfg("GEMINI_MODEL", "ai", "gemini", "model", default="gemini-2.5-flash")

# ── Retry ──────────────────────────────────────────────────────────────

RETRY_ATTEMPTS: int = _cfg_int("RETRY_ATTEMPTS", "retry", "attempts", default=3)
RETRY_INITIAL_DELAY: float = _cfg_float(
    "RETRY_INITIAL_DELAY", "retry", "initial_delay", default=2.0
)

# ── Skills (feature flags) ─────────────────────────────────────────────

_SKILLS_DEFAULTS: Dict[str, bool] = {
    "weather":    True,
    "reminders":  True,
    "time":       True,
    "hardware":   True,
    "memory":     True,
    "rss":        True,
    "job_hunter": True,
    "sports":     True,
    "github":     False,
    "usage_report": True,
    "system_control": True,
    "daily_briefing": True,
}

_toml_skills: Dict[str, Any] = _toml_get("skills") or {}


def skill_enabled(name: str) -> bool:
    """
    Retorna True se a skill estiver habilitada.

    Prioridade:
      1. Variável de ambiente: SKILL_<NAME>_ENABLED (ex: SKILL_WEATHER_ENABLED=false)
      2. config.toml: [skills] weather = true/false
      3. Padrão interno (_SKILLS_DEFAULTS)
    """
    env_key = f"SKILL_{name.upper()}_ENABLED"
    env_val = os.getenv(env_key)
    if env_val is not None:
        return env_val.lower() in ("true", "1", "yes")
    toml_val = _toml_skills.get(name)
    if toml_val is not None and isinstance(toml_val, bool):
        return toml_val
    return _SKILLS_DEFAULTS.get(name, True)


# ── MCP Configuration ──────────────────────────────────────────────────

MCP_CONFIG_FILE = BASE_DIR / "mcp.json"
MCP_SERVERS: Dict[str, Any] = {}

if MCP_CONFIG_FILE.is_file():
    try:
        with open(MCP_CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                MCP_SERVERS = data
                logger.info("MCP: configuração carregada de %s", MCP_CONFIG_FILE)
            else:
                logger.error("%s deve ser um dicionário JSON.", MCP_CONFIG_FILE)
    except json.JSONDecodeError:
        logger.error("%s não é um JSON válido!", MCP_CONFIG_FILE)
    except Exception as exc:
        logger.error("Erro ao carregar %s: %s", MCP_CONFIG_FILE, exc)
else:
    _mcp_env = os.getenv("MCP_SERVERS_CONFIG", "{}")
    try:
        data = json.loads(_mcp_env)
        if isinstance(data, dict):
            MCP_SERVERS = data
        else:
            logger.warning("MCP_SERVERS_CONFIG deve ser um dicionário. Usando {}.")
    except json.JSONDecodeError:
        logger.warning("MCP_SERVERS_CONFIG não é um JSON válido!")
    except Exception as exc:
        logger.error("Erro ao parsear MCP_SERVERS_CONFIG: %s", exc)

# ── Job Hunter ─────────────────────────────────────────────────────────

JOB_HUNTER_URL: str = (
    _cfg("JOB_HUNTER_URL", "skills", "job_hunter", "url", default="") or ""
).rstrip("/")
JOB_HUNTER_TOKEN: str = (
    _cfg("JOB_HUNTER_TOKEN", "skills", "job_hunter", "token", default="") or ""
)

_jh_sources_env = os.getenv("JOB_HUNTER_SOURCES")
_jh_keywords_env = os.getenv("JOB_HUNTER_KEYWORDS")
_jh_cutoff_env = os.getenv("JOB_HUNTER_SCORE_CUTOFF")

if _jh_sources_env:
    JOB_HUNTER_SOURCES = [s.strip() for s in _jh_sources_env.split(",") if s.strip()]
else:
    _toml_jh_sources = _toml_get("skills", "job_hunter", "sources")
    JOB_HUNTER_SOURCES = _toml_jh_sources if isinstance(_toml_jh_sources, list) else None

if _jh_keywords_env:
    JOB_HUNTER_KEYWORDS = [k.strip() for k in _jh_keywords_env.split(",") if k.strip()]
else:
    _toml_jh_kw = _toml_get("skills", "job_hunter", "keywords")
    JOB_HUNTER_KEYWORDS = _toml_jh_kw if isinstance(_toml_jh_kw, list) and _toml_jh_kw else None

if _jh_cutoff_env:
    try:
        JOB_HUNTER_SCORE_CUTOFF: Optional[float] = float(_jh_cutoff_env)
    except ValueError:
        logger.error("JOB_HUNTER_SCORE_CUTOFF inválido. Usando None.")
        JOB_HUNTER_SCORE_CUTOFF = None
else:
    _toml_cutoff = _toml_get("skills", "job_hunter", "score_cutoff")
    JOB_HUNTER_SCORE_CUTOFF = float(_toml_cutoff) if _toml_cutoff is not None else None

# ── RSS ────────────────────────────────────────────────────────────────

RSS_FEEDS_DEFAULT: Dict[str, str] = {
    "G1":                   "https://g1.globo.com/rss/g1/",
    "G1 Brasil":            "https://g1.globo.com/rss/g1/brasil/",
    "G1 Tecnologia":        "https://g1.globo.com/rss/g1/tecnologia/",
    "Folha de São Paulo":   "https://feeds.folha.uol.com.br/emcimadahora/rss091.xml",
    "TechCrunch":           "https://techcrunch.com/feed/",
    "Hacker News":          "https://hnrss.org/frontpage",
}

_rss_env = os.getenv("RSS_FEEDS_JSON", "")
if _rss_env.strip():
    try:
        _parsed = json.loads(_rss_env)
        RSS_FEEDS: Dict[str, str] = _parsed if isinstance(_parsed, dict) else RSS_FEEDS_DEFAULT.copy()
        if not isinstance(_parsed, dict):
            logger.warning("RSS_FEEDS_JSON deve ser um dict. Usando padrões.")
    except (json.JSONDecodeError, Exception) as exc:
        logger.warning("Erro ao parsear RSS_FEEDS_JSON: %s. Usando padrões.", exc)
        RSS_FEEDS = RSS_FEEDS_DEFAULT.copy()
else:
    _toml_rss_feeds = _toml_get("skills", "rss", "feeds")
    if isinstance(_toml_rss_feeds, dict) and _toml_rss_feeds:
        RSS_FEEDS = _toml_rss_feeds
    else:
        RSS_FEEDS = RSS_FEEDS_DEFAULT.copy()

# ── Reflection ─────────────────────────────────────────────────────────

REFLECTION_ENABLED: bool = _cfg_bool(
    "REFLECTION_ENABLED", "reflection", "enabled", default=True
)
REFLECTION_MODEL: str = _cfg(
    "REFLECTION_MODEL", "reflection", "model", default="llama-3.3-70b-versatile"
)
REFLECTION_GREETING_HOUR_START: int = _cfg_int(
    "REFLECTION_GREETING_HOUR_START", "reflection", "greeting_hour_start", default=7
)
REFLECTION_GREETING_HOUR_END: int = _cfg_int(
    "REFLECTION_GREETING_HOUR_END", "reflection", "greeting_hour_end", default=9
)

# ── Sports ─────────────────────────────────────────────────────────────

THESPORTSDB_KEY: str = (
    _cfg("THESPORTSDB_KEY", "skills", "sports", "thesportsdb_key", default="") or ""
)
API_FOOTBALL_KEY: str = (
    _cfg("API_FOOTBALL_KEY", "skills", "sports", "api_football_key", default="") or ""
)
PANDASCORE_KEY: str = (
    _cfg("PANDASCORE_KEY", "skills", "sports", "pandascore_key", default="") or ""
)

# ── Google Calendar ────────────────────────────────────────────────────

GCAL_CLIENT_ID: Optional[str] = _cfg(
    "GCAL_CLIENT_ID", "skills", "google_calendar", "client_id"
) or None

GCAL_CLIENT_SECRET: Optional[str] = _cfg(
    "GCAL_CLIENT_SECRET", "skills", "google_calendar", "client_secret"
) or None

GCAL_SYNC_INTERVAL_MINUTES: int = _cfg_int(
    "GCAL_SYNC_INTERVAL_MINUTES",
    "skills", "google_calendar", "sync_interval_minutes",
    default=30
)

GCAL_CALENDAR_ID: str = _cfg(
    "GCAL_CALENDAR_ID",
    "skills", "google_calendar", "calendar_id",
    default="primary"
)

# ── Validação e Avisos ─────────────────────────────────────────────────

if not TELEGRAM_TOKEN:
    logger.warning("TELEGRAM_TOKEN não configurado!")
if AUTHORIZED_USER_ID == 0:
    logger.warning("AUTHORIZED_USER_ID não configurado – nenhum usuário autorizado.")
if AI_PROVIDER == "gemini" and not GEMINI_API_KEY:
    logger.warning("GEMINI_API_KEY ausente mas provedor está como 'gemini'.")
if AI_PROVIDER == "groq" and not GROQ_API_KEY:
    logger.warning("GROQ_API_KEY ausente mas provedor está como 'groq'.")
if not THESPORTSDB_KEY:
    logger.warning("THESPORTSDB_KEY não configurada – cadastre-se em thesportsdb.com")
if API_FOOTBALL_KEY:
    logger.info("API-Football configurada (100 req/dia).")
if PANDASCORE_KEY:
    logger.info("PandaScore configurada para eSports (1000 req/mês).")

# ── System Control Skill (Power User) ──────────────────────────────────

SYSTEM_CONTROL_SECURITY_LEVEL: str = _cfg(
    "SYSTEM_CONTROL_SECURITY_LEVEL",
    "skills", "system_control", "security_level",
    default="normal"
)

SYSTEM_CONTROL_ALLOW_CUSTOM_COMMANDS: bool = _cfg_bool(
    "SYSTEM_CONTROL_ALLOW_CUSTOM_COMMANDS",
    "skills", "system_control", "allow_custom_commands",
    default=False
)

SYSTEM_CONTROL_ALLOW_FILE_WRITES: bool = _cfg_bool(
    "SYSTEM_CONTROL_ALLOW_FILE_WRITES",
    "skills", "system_control", "allow_file_writes",
    default=False
)

# ── Security & Audit ───────────────────────────────────────────────────

SECURITY_AUDIT_LOG_PATH: str = _cfg(
    "SECURITY_AUDIT_LOG_PATH",
    "security", "audit_log_path",
    default=str(BASE_DIR / "logs" / "security.log")
)

SECURITY_NOTIFY_EVENTS: bool = _cfg_bool(
    "SECURITY_NOTIFY_EVENTS",
    "security", "notify_security_events",
    default=False
)

# ── Config Class (for dependency injection compatibility) ──────────────

class Config:
    """Configuration class for accessing settings via properties."""

    @property
    def system_control_security_level(self) -> str:
        """Security level for system control skill: strict, normal, or permissive."""
        return SYSTEM_CONTROL_SECURITY_LEVEL

    @property
    def system_control_allow_custom_commands(self) -> bool:
        """Allow custom commands via LLM guard."""
        return SYSTEM_CONTROL_ALLOW_CUSTOM_COMMANDS

    @property
    def system_control_allow_file_writes(self) -> bool:
        """Allow file write operations (mv, cp, >)."""
        return SYSTEM_CONTROL_ALLOW_FILE_WRITES

    @property
    def security_audit_log_path(self) -> str:
        """Path to security audit log file."""
        return SECURITY_AUDIT_LOG_PATH

    @property
    def security_notify_events(self) -> bool:
        """Send Telegram notification when suspicious commands are blocked."""
        return SECURITY_NOTIFY_EVENTS


# Global singleton instance
_config_instance: Optional[Config] = None


def get_config() -> Config:
    """Get the global Config instance."""
    global _config_instance
    if _config_instance is None:
        _config_instance = Config()
    return _config_instance


# ── Sumário de configuração (startup debug) ────────────────────────────

def log_config_summary() -> None:
    """Loga um resumo da configuração carregada para facilitar o debugging."""
    source = "config.toml" if _TOML else "variáveis de ambiente / defaults"
    logger.info("─── Configuração do Curupira ───────────────────────────")
    logger.info("  Fonte principal : %s", source)
    logger.info("  Provedor IA     : %s", AI_PROVIDER.upper())
    logger.info("  Heartbeat       : %ds", HEARTBEAT_INTERVAL)
    logger.info("  Reflexão ativa  : %s", REFLECTION_ENABLED)

    enabled_skills  = [k for k in _SKILLS_DEFAULTS if skill_enabled(k)]
    disabled_skills = [k for k in _SKILLS_DEFAULTS if not skill_enabled(k)]
    logger.info("  Skills ativas   : %s", ", ".join(enabled_skills) or "nenhuma")
    if disabled_skills:
        logger.info("  Skills inativas : %s", ", ".join(disabled_skills))
    logger.info("────────────────────────────────────────────────────────")


log_config_summary()

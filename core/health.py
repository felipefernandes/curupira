import os
import shutil
import subprocess
import urllib.request
import logging
from typing import TypedDict, Dict, Any

from core import config

logger = logging.getLogger(__name__)

class HealthReport(TypedDict):
    status: str  # "ok", "warning", "critical"
    issues: list[str]
    details: Dict[str, Any]

_last_diagnostic: "HealthReport | None" = None
_last_diagnostic_time: float = 0
_CACHE_TTL = 60
MIN_RAM_KB = 2_000_000


def check_memory_zram() -> tuple[bool, str]:
    """
    Verifica se a memória é suficiente ou se o zram está ativo.
    """
    # Em sistemas Windows ou mac, /proc/meminfo não existe
    if not os.path.exists("/proc/meminfo"):
        logger.warning("Sistema operacional detectado como NÃO Linux. Validação de segurança de RAM pulada.")
        return True, "Sistema operacional não tem /proc/meminfo. Assumir RAM suficiente (Cuidado: Pode causar crashes em SBCs customizados)."
    
    try:
        total_mem_kb = 0
        with open("/proc/meminfo", "r") as f:
            # Lê apenas a primeira linha necessária ao invés de ler todo o arquivo
            first_line = f.readline()
            if first_line.startswith("MemTotal:"):
                total_mem_kb = int(first_line.split()[1])
        
        # Se MemTotal for maior que o mínimo (aprox 2000000 kB), assume que tá tranquilo
        if total_mem_kb > MIN_RAM_KB:
            return True, f"Memória total: {total_mem_kb // 1024} MB (OK)"

        # Verifica zram ou swap
        if os.path.exists("/proc/swaps"):
            with open("/proc/swaps", "r") as f:
                swaps = f.read()
                if "zram" in swaps:
                    return True, "Dispositivo com pouca RAM, mas zram está ativo (OK)."
                elif "file" in swaps or "partition" in swaps:
                    return True, "Dispositivo com pouca RAM, mas swap está ativo (OK)."
            
        return False, "Pouca RAM (< 2GB) e nenhum ZRAM/Swap detectado. Risco de Out Of Memory."
    except Exception as e:
        logger.warning(f"Erro ao ler informações de memória: {e}")
        return True, "Aviso: não foi possível validar a memória."

def check_env_secrets() -> tuple[bool, list[str]]:
    """
    Verifica a presença dos segredos obrigatórios baseados no provedor de IA atual com Regex.
    """
    import re
    missing = []
    
    # Valida presença e regex format compatível
    def is_valid_key(provider: str, val: str | None) -> bool:
        if not val:
            return False
        v = str(val).strip()
        if provider == "telegram":
            # API do telegram: numero_id:letrasnumeros
            return bool(re.match(r"^\d{8,10}:[a-zA-Z0-9_-]{35}$", v))
        elif provider == "groq":
            return v.startswith("gsk_") and len(v) > 20
        elif provider == "gemini":
            return v.startswith("AIza") and len(v) >= 30
        return len(v) > 10

    if not is_valid_key("telegram", config.TELEGRAM_TOKEN):
        missing.append("TELEGRAM_TOKEN (Token inválido ou ausente)")
    
    if config.AI_PROVIDER == "groq" and not is_valid_key("groq", config.GROQ_API_KEY):
        missing.append("GROQ_API_KEY (Formato inválido/ausente)")
    
    if config.AI_PROVIDER == "gemini" and not is_valid_key("gemini", config.GEMINI_API_KEY):
        missing.append("GEMINI_API_KEY (Formato inválido/ausente)")
    
    if missing:
        return False, missing
    return True, []

def check_system_dependencies() -> tuple[bool, list[str]]:
    """
    Verifica a presença de binários do sistema como ffmpeg.
    """
    missing = []
    if not shutil.which("ffmpeg"):
        missing.append("ffmpeg")
    
    if missing:
        return False, missing
    return True, []

def check_connectivity() -> tuple[bool, list[str]]:
    """
    Tenta se conectar e validar chaves com os serviços essenciais.
    """
    failures = []
    urls_to_check = []
    headers = {}

    if config.TELEGRAM_TOKEN:
        urls_to_check.append(("Telegram", f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/getMe"))
    else:
        urls_to_check.append(("Telegram", "https://api.telegram.org"))

    if config.AI_PROVIDER == "groq" and config.GROQ_API_KEY:
        urls_to_check.append(("Groq", "https://api.groq.com/openai/v1/models"))
        headers["Groq"] = {"Authorization": f"Bearer {config.GROQ_API_KEY}"}
    elif config.AI_PROVIDER == "gemini" and config.GEMINI_API_KEY:
        urls_to_check.append(("Gemini", f"https://generativelanguage.googleapis.com/v1beta/models?key={config.GEMINI_API_KEY}"))

    for name, url in urls_to_check:
        try:
            req_headers = headers.get(name, {})
            req = urllib.request.Request(url, headers=req_headers, method="GET")
            urllib.request.urlopen(req, timeout=5)
        except urllib.error.HTTPError as e:
            if e.code == 401:
                failures.append(f"Autenticação falhou em {name} (Chave de API inválida/401)")
            elif e.code == 403:
                failures.append(f"Acesso negado em {name} (403 Forbidden)")
            else:
                failures.append(f"Erro HTTP {e.code} ao conectar no {name}")
        except Exception as e:
            failures.append(f"Falha de rede ao conectar no {name}: {e}")
            
    if failures:
        return False, failures
    return True, []

def check_git() -> tuple[str, str]:
    """
    Verifica se existe um repositório git e o status atual.
    Retorna (status ("ok", "warning", "critical", "unknown"), msg)
    """
    try:
        # Pega a branch atual
        branch_res = subprocess.run(["git", "branch", "--show-current"], capture_output=True, text=True, check=True)
        branch = branch_res.stdout.strip()
        
        if not branch:
            return "unknown", "Repositório Git não detectado ou sem commits iniciais."
        
        commit_res = subprocess.run(["git", "log", "-1", "--format=%h"], capture_output=True, text=True, check=True)
        commit = commit_res.stdout.strip()
        
        # Tenta pegar status (modified, untracked)
        status_res = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, check=True)
        changes = status_res.stdout.strip()
        
        estado = "limpa" if not changes else "com arquivos modificados"
        return "ok", f"Branch: {branch} (Commit: {commit}) - Árvore {estado}."
        
    except FileNotFoundError:
        return "unknown", "Git não processado: Binário 'git' não instalado no PATH."
    except subprocess.CalledProcessError as e:
        return "unknown", f"Erro interno ao validar Git: {'Repositório vazio/corrompido' if not e.stderr else e.stderr.strip()}"
    except Exception as e:
        return "unknown", f"Erro de I/O inesperado ao verificar git: {e}"

def run_full_diagnostic(force: bool = False) -> HealthReport:
    """
    Executa todas as validações e retorna o relatório consolidado de saúde da instância.
    Utiliza um cache de 60 segundos para não onerar sistema em caso de spam.
    """
    global _last_diagnostic, _last_diagnostic_time
    import time
    
    now = time.time()
    if not force and _last_diagnostic and (now - _last_diagnostic_time < _CACHE_TTL):
        return _last_diagnostic

    issues = []
    details = {}
    
    # Memória
    mem_ok, mem_msg = check_memory_zram()
    details["memory"] = mem_msg
    if not mem_ok:
        issues.append(mem_msg)
        
    # Variáveis de ambiente
    env_ok, env_missing = check_env_secrets()
    if env_ok:
        details["env"] = "As credenciais e API Keys obrigatórias estão configuradas."
    else:
        msg = f"Credenciais/Variáveis ausentes: {', '.join(env_missing)}"
        details["env"] = msg
        issues.append(msg)
        
    # Dependências do OS
    deps_ok, deps_missing = check_system_dependencies()
    if deps_ok:
        details["dependencies"] = "Todas as dependências de sistema detectadas (ffmpeg)."
    else:
        msg = f"Dependências de sistema ausentes: {', '.join(deps_missing)}"
        details["dependencies"] = msg
        issues.append(msg)
        
    # Conectividade
    conn_ok, conn_failures = check_connectivity()
    if conn_ok:
        details["connectivity"] = "Conexão com internet e provedores OK."
    else:
        msg = f"Problemas de conexão detectados: {'; '.join(conn_failures)}"
        details["connectivity"] = msg
        issues.append(msg)
        
    # Git
    git_status, git_msg = check_git()
    details["git"] = git_msg
    if git_status == "critical":
        issues.append(git_msg)
        
    # Compila status
    status = "ok"
    if issues:
        if not env_ok or not deps_ok:
            status = "critical"
        else:
            status = "warning"
            
    report = HealthReport(status=status, issues=issues, details=details)
    _last_diagnostic = report
    _last_diagnostic_time = now
    
    return report

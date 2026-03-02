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

def check_memory_zram() -> tuple[bool, str]:
    """
    Verifica se a memória é suficiente ou se o zram está ativo.
    """
    # Em sistemas Windows ou mac, /proc/meminfo não existe
    if not os.path.exists("/proc/meminfo"):
        return True, "Sistema operacional não é Linux ou não tem /proc/meminfo. Assumindo RAM suficiente."
    
    try:
        total_mem_kb = 0
        with open("/proc/meminfo", "r") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    parts = line.split()
                    total_mem_kb = int(parts[1])
                    break
        
        # Se MemTotal for maior que 2GB (aprox 2000000 kB), assume que tá tranquilo
        if total_mem_kb > 2_000_000:
            return True, f"Memória total: {total_mem_kb // 1024} MB (OK)"

        # Verifica zram ou swap
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
    Verifica a presença dos segredos obrigatórios baseados no provedor de IA atual.
    """
    missing = []
    if not config.TELEGRAM_TOKEN:
        missing.append("TELEGRAM_TOKEN")
    
    if config.AI_PROVIDER == "groq" and not config.GROQ_API_KEY:
        missing.append("GROQ_API_KEY")
    
    if config.AI_PROVIDER == "gemini" and not config.GEMINI_API_KEY:
        missing.append("GEMINI_API_KEY")
    
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
    Tenta se conectar rapidamento aos serviços essenciais.
    """
    failures = []
    urls_to_check = [
        ("Telegram", "https://api.telegram.org"),
    ]

    if config.AI_PROVIDER == "groq":
        urls_to_check.append(("Groq", "https://api.groq.com/openai/v1/models"))
    elif config.AI_PROVIDER == "gemini":
        urls_to_check.append(("Gemini", "https://generativelanguage.googleapis.com"))

    for name, url in urls_to_check:
        try:
            # Apenas verificar se o host resolve e aceita requisição (timeout curto)
            req = urllib.request.Request(url, method="HEAD")
            urllib.request.urlopen(req, timeout=3)
        except urllib.error.HTTPError:
            # HTTP Error significa que conectou, só deu erro de autorização ou rota, o que indica network OK
            pass
        except Exception as e:
            failures.append(f"Falha ao conectar no {name} ({url}): {e}")
            
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
            return "unknown", "Repositório Git não detectado ou sem commits."
        
        # Tenta pegar status (modified, untracked)
        status_res = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, check=True)
        changes = status_res.stdout.strip()
        
        estado = "limpa" if not changes else "com arquivos modificados"
        
        # Tenta verificar se tem remote origin para pull (opicional, pode falhar timeout)
        # Não faremos fetch para não atrasar o bot, apenas vemos status local em relação ao upstream
        return "ok", f"Branch atual: {branch} ({estado})"
        
    except FileNotFoundError:
        return "unknown", "Git não instalado no sistema."
    except subprocess.CalledProcessError:
        return "unknown", "Pasta atual não é um repositório git válido."

def run_full_diagnostic() -> HealthReport:
    """
    Executa todas as validações e retorna o relatório consolidado de saúde da instância.
    """
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
        # Faltar token de apis obriga crítico. Faltar ffmpeg é apenas um aviso.
        if not env_ok:
            status = "critical"
        else:
            status = "warning"
            
    return HealthReport(status=status, issues=issues, details=details)

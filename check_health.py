#!/usr/bin/env python3
"""
check_health.py
===============
Script standalone (tipo "doctor") para diagnosticar a integridade do ambiente
onde o CurupiraBOT está executando.

Uso:
  python check_health.py
"""

import sys
from core.health import run_full_diagnostic

def print_status(name: str, status: str, details: str):
    icon = "❓"
    if status == "ok":
        icon = "✅"
    elif status == "warning":
        icon = "⚠️"
    elif status == "critical":
        icon = "❌"
    
    print(f"[{icon}] {name}:")
    print(f"    {details}")
    print()

def main():
    print("========================================")
    print("   🔥 CurupiraBOT - Diagnóstico (Health)  ")
    print("========================================")
    print()

    force_run = "--force" in sys.argv
    report = run_full_diagnostic(force=force_run)

    # 1. Memória & ZRAM
    mem_status_msg = report["details"].get("memory", "")
    mem_status = "ok" if mem_status_msg not in report["issues"] else "warning"
    print_status("Memória e ZRAM", mem_status, mem_status_msg)

    # 2. Variáveis e Segredos
    env_status_msg = report["details"].get("env", "")
    env_status = "ok" if env_status_msg not in report["issues"] else "critical"
    print_status("Segredos e Configuração", env_status, env_status_msg)

    # 3. Dependências (OS)
    deps_status_msg = report["details"].get("dependencies", "")
    deps_status = "ok" if deps_status_msg not in report["issues"] else "critical"
    print_status("Dependências de Sistema", deps_status, deps_status_msg)

    # 4. Conectividade
    conn_status_msg = report["details"].get("connectivity", "")
    conn_status = "ok" if conn_status_msg not in report["issues"] else "warning"
    print_status("Conectividade e Internet", conn_status, conn_status_msg)

    # 5. Git Status
    git_status_msg = report["details"].get("git", "")
    git_status = "ok"
    if git_status_msg in report["issues"]:
        git_status = "critical"
    elif "modificados" in git_status_msg or "não processado" in git_status_msg:
        git_status = "warning"
    elif "unknown" in git_status_msg:
        git_status = "warning"
    print_status("Repositório Git", git_status, git_status_msg)

    print("========================================")
    # Resultado Final Consolidado
    if report["status"] == "ok":
        print("🎉 STATUS GERAL: SAUDÁVEL. O bot está pronto para operar.")
        sys.exit(0)
    elif report["status"] == "warning":
        print("⚠️ STATUS GERAL: AVISO. O bot funcionará, mas há limitações (veja acima).")
        if report["issues"]:
            print("Problemas: \n - " + "\n - ".join(report["issues"]))
        sys.exit(0)
    else:
        print("❌ STATUS GERAL: CRÍTICO. O bot vai falhar ao rodar.")
        if report["issues"]:
            print("Problemas Críticos: \n - " + "\n - ".join(report["issues"]))
        sys.exit(1)

if __name__ == "__main__":
    main()

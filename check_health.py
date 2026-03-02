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
from core import health

def print_status(name: str, status: bool, details: str):
    icon = "✅" if status else "❌"
    print(f"[{icon}] {name}:")
    print(f"    {details}")
    print()

def main():
    print("========================================")
    print("   🔥 CurupiraBOT - Diagnóstico (Health)  ")
    print("========================================")
    print()

    report = health.run_full_diagnostic(force=True)

    # 1. Memória & ZRAM
    mem_msg = report["details"].get("memory", "")
    mem_ok = mem_msg not in report["issues"]
    print_status("Memória e ZRAM", mem_ok, mem_msg)

    # 2. Variáveis e Segredos
    env_msg = report["details"].get("env", "")
    env_ok = env_msg not in report["issues"]
    print_status("Segredos e Configuração", env_ok, env_msg)

    # 3. Dependências (OS)
    deps_msg = report["details"].get("dependencies", "")
    deps_ok = deps_msg not in report["issues"]
    icon_deps = "✅" if deps_ok else "⚠️"
    print(f"[{icon_deps}] Dependências de Sistema:")
    print(f"    {deps_msg}")
    print()

    # 4. Conectividade
    conn_msg = report["details"].get("connectivity", "")
    conn_ok = conn_msg not in report["issues"]
    print_status("Conectividade e Internet", conn_ok, conn_msg)

    # 5. Git Status
    git_msg = report["details"].get("git", "")
    git_ok = git_msg not in report["issues"]
    git_icon = "❓" if "Erro" in git_msg or "não instalado" in git_msg else ("✅" if "limpa" in git_msg else "⚠️")
    print(f"[{git_icon}] Repositório Git:")
    print(f"    {git_msg}")
    print()

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

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

    # 1. Memória & ZRAM
    mem_ok, mem_msg = health.check_memory_zram()
    print_status("Memória e ZRAM", mem_ok, mem_msg)

    # 2. Variáveis e Segredos
    env_ok, env_missing = health.check_env_secrets()
    if env_ok:
        env_msg = "Todas as chaves obrigatórias (Tokens e APIs LLM) estão configuradas."
    else:
        env_msg = f"Chaves ausentes no .env ou config.toml: {', '.join(env_missing)}"
    print_status("Segredos e Configuração", env_ok, env_msg)

    # 3. Dependências (OS)
    deps_ok, deps_missing = health.check_system_dependencies()
    if deps_ok:
        deps_msg = "ffmpeg detectado no sistema."
    else:
        deps_msg = f"Binários ausentes no PATH: {', '.join(deps_missing)}\n(Áudios não funcionarão sem ffmpeg)"
    # FFmpeg missing is a warning not a hard crash, but let's show an alert icon if missing
    icon_deps = "✅" if deps_ok else "⚠️"
    print(f"[{icon_deps}] Dependências de Sistema:")
    print(f"    {deps_msg}")
    print()

    # 4. Conectividade
    print("Testando conexões... (isso pode levar alguns segundos)")
    conn_ok, conn_failures = health.check_connectivity()
    if conn_ok:
        conn_msg = "Conexão com os provedores de API em perfeito estado."
    else:
        conn_msg = f"Falhas de conexão: {'; '.join(conn_failures)}"
    print_status("Conectividade e Internet", conn_ok, conn_msg)

    # 5. Git Status
    git_status, git_msg = health.check_git()
    # Se unknown, mostramos "?", se limpo "v", se modified "!"
    git_icon = "❓" if git_status == "unknown" else ("✅" if "limpa" in git_msg else "⚠️")
    print(f"[{git_icon}] Repositório Git:")
    print(f"    {git_msg}")
    print()

    print("========================================")
    # Resultado Final Consolidado
    report = health.run_full_diagnostic()
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

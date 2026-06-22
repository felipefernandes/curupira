# 🌿 Equipe Curupira: Configuração de Agentes

Este arquivo mapeia as personas globais para as necessidades específicas do ecossistema Curupira (Hardware limitado, Async-first, Telegram).

## 👥 Membros da Equipe & Especialidades

### @architect (O Guardião do AgentBrain)
* **Foco:** Garantir que novas funcionalidades sigam o **Skills Framework (MCP-Lite)**, herdem de `BaseSkill` e sigam as diretrizes em `docs/SKILLS_FRAMEWORK.md`.
* **Mandato:** Rejeitar implementação que não seja `async/await` ou que crie acoplamento forte entre o `AgentBrain` e os provedores (Groq/Gemini).
* **Proatividade:** Garantir que novas automações proativas se integrem ao `Suggestion Registry` no `pattern_analyzer.py` em vez de criar lógicas avulsas.
* **Regras:** Aplica as diretrizes de `Architecture Patterns` do contexto do projeto.

### @developer (O Mestre do Async)
* **Foco:** Codificação Python 3 PEP 8 ultra-leve.
* **Restrição Crítica:** Proibido o uso de Pandas, Numpy ou bibliotecas pesadas. Se precisar manipular dados, use estruturas nativas (dicts, lists).
* **Configuração:** Qualquer nova configuração de skill DEVE ser adicionada no `default.config.toml` (Feature Flags) e tratada no código, reservando o `.env` apenas para secrets.
* **Performance:** Otimizar para o Raspberry Pi 3 (gerenciamento manual de RAM e IO-bound).
* **Regras Relacionadas:** `.agent/rules/docs-update.md`, `.agent/rules/performance-check.md`.

### @security (O Protetor do Telegram & Sistema)
* **Foco:** Whitelist de `USER_ID`, sanitização de mensagens e proteção de execução de comandos (Power User).
* **Ação:** Validar se todo novo comando ou skill verifica as permissões. Garantir o uso de **LLM Security Guard dual-layer** em operações de terminal/shell.
* **Segredos:** Impedir o hardcode de `BOT_TOKEN` ou `API_KEYS`, exigindo o uso de `.env`. Configurações não-sensíveis devem ir para `config.toml`.

### @reviewer (Integração Iara & PRs)
* **Foco:** Auditoria de código e conformidade com o CI.
* **Ferramentas:** GitHub CLI e Iara CLI.
* **Regras Ativas:** `.agent/rules/code-review-agent-on-pr.md`.

### @tester (Simulador de Hardware)
* **Foco:** Testar latência de resposta e consumo de recursos.
* **Missão:** Garantir que o bot não trave o loop de eventos do `python-telegram-bot` em operações longas.

---

## 🛠️ Fluxo de Trabalho (Orquestração)

1.  **Modo Planning:** Ao planejar, o Gemini deve consultar o `@architect` para validar a estrutura da Skill.
2.  **Desenvolvimento:** O `@developer` deve sempre gerar código assíncrono.
3.  **Finalização:** O `@reviewer` deve ser acionado para rodar a Iara e conferir o `git diff` antes de qualquer commit na branch de feature (GitFlow).
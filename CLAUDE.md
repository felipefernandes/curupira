<!-- OPENSPEC:START -->
# OpenSpec Instructions

These instructions are for AI assistants working in this project.

Always open `@/openspec/AGENTS.md` when the request:
- Mentions planning or proposals (words like proposal, spec, change, plan)
- Introduces new capabilities, breaking changes, architecture shifts, or big performance/security work
- Sounds ambiguous and you need the authoritative spec before coding

Use `@/openspec/AGENTS.md` to learn:
- How to create and apply change proposals
- Spec format and conventions
- Project structure and guidelines

Keep this managed block so 'openspec update' can refresh the instructions.

<!-- OPENSPEC:END -->

Use o arquivo README.md e PROJECT.md para obter informações gerais sobre o projeto

* Contexto de Pull Request: Sempre que eu pedir para "corrigir o PR", "revisar os comentários da Iara" ou "ajustar o código com base no feedback", você deve usar o GitHub CLI ou Github MCP (se disponível) para obter o contexto atualizado.

**Ações Obrigatórias**:
1. Verifique se existe um PR aberto para a branch atual: gh pr view --web (ou apenas gh pr view).
2. Recupere os comentários e reviews usando: gh pr view --json reviews,comments --jq '.reviews[].body, .comments[].body'
3. Analise especificamente as sugestões da Iara (AI Code Review agent).
4. Aplique as correções sugeridas diretamente nos arquivos locais sem que eu precise copiar e colar as mensagens.




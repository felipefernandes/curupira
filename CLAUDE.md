Use o arquivo README.md e PROJECT.md para obter informações gerais sobre o projeto

* Contexto de Pull Request: Sempre que eu pedir para "corrigir o PR", "revisar os comentários da Iara" ou "ajustar o código com base no feedback", você deve usar o GitHub CLI ou Github MCP (se disponível) para obter o contexto atualizado.

**Ações Obrigatórias**:
1. Verifique se existe um PR aberto para a branch atual: gh pr view --web (ou apenas gh pr view).
2. Recupere os comentários e reviews usando: gh pr view --json reviews,comments --jq '.reviews[].body, .comments[].body'
3. Analise especificamente as sugestões da Iara (AI Code Review agent).
4. Aplique as correções sugeridas diretamente nos arquivos locais sem que eu precise copiar e colar as mensagens.




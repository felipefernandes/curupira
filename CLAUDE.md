
Use o arquivo README.md e PROJECT.md para obter informações gerais sobre o projeto

* **Contexto de Pull Request**: Sempre que eu pedir para "corrigir o PR", "revisar os comentários da Iara" ou "ajustar o código com base no feedback", você deve usar o GitHub CLI ou Github MCP (se disponível) para obter o contexto atualizado.

**Ações Obrigatórias**:
1. Verifique se existe um PR aberto para a branch atual: `gh pr view --web` (ou apenas `gh pr view`).
2. Recupere os comentários e reviews usando: `gh pr view --json reviews,comments,reviewThreads --jq '.reviewThreads[].comments[].body, .reviews[].body, .comments[].body'`
3. Analise especificamente as sugestões da Iara (AI Code Review agent).
4. Aplique as correções sugeridas diretamente nos arquivos locais sem que eu precise copiar e colar as mensagens.
5. Valide localmente as correções (testes e pyright) antes de pedir para comitar.

**Orientações Gerais**
- **Configurações vs Segredos**: O projeto utiliza `config.toml` para configurações gerais e `Feature Flags` das skills. O `.env` é ESTRITAMENTE reservado para chaves (Tokens, API Keys). Novas variáveis normais vão para `default.config.toml`.
- **Performance (Diet)**: Lembre-se do Raspberry Pi 3. Processamento em background, bibliotecas nativas e zero lock no event loop.
- Arquivos de logs, temporários (temps) e debugs devem ser adicionados à pasta `/logs`.

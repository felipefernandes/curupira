---
trigger: model_decision
description: Comandos como "corrigir PR", "revisar Iara", "feedbacks do GitHub" ou "ajustar código".
---

# Rule: Code Review & Iara Integration

## 1. Coleta de Contexto (Deep Context)
Sempre que acionado, você deve:
1. **Identificar a Branch**: Verifique se está na branch correta e se há um PR aberto usando `gh pr view`.
2. **Capturar Feedbacks Detalhados**: Use o comando abaixo para pegar não só os comentários gerais, mas também os comentários em linhas específicas (threads):
   `gh pr view --json reviews,comments,reviewThreads --jq '.reviewThreads[].comments[].body'`
3. **Filtro Iara**: Priorize mensagens que mencionem "Iara" ou que tenham o padrão de análise estática/IA.

## 2. Ações de Execução
Para cada sugestão encontrada:
1. **Análise de Impacto**: Antes de editar, verifique se a sugestão da Iara faz sentido no contexto atual do arquivo local (o código pode ter mudado desde o último push).
2. **Aplicação Silenciosa**: Aplique as correções diretamente. Se o comentário sugerir um bloco de código, implemente-o fielmente.
3. **Limpeza de Estilo**: Após aplicar, rode o `ruff check . --fix` (se disponível) para garantir que a correção segue o guia de estilo.

## 3. Protocolo de Fechamento (Verification)
Não considere a tarefa pronta apenas por editar o arquivo. Você deve:
1. **Validar Localmente**: Tente rodar o comando de teste do projeto (ex: `pytest`) ou a própria Iara local (`git diff main | iara`) para ver se o erro persiste.
2. **Resumo de Alterações**: Apresente um resumo curto: "Corrigi X na linha Y conforme solicitado pela Iara".
3. **Push Sugerido**: Pergunte ao usuário: "Deseja que eu suba essas correções para a branch agora?".
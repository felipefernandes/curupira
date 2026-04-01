---
trigger: model_decision
description: Sempre que houver alteração em arquivos .py ou comandos como "commit", "push", "abrir PR", "finalizar tarefa".
---

# Rule: Pyright Type Checking (Antigravity Hook)

Este arquivo implementa o equivalente aos hooks do Claude Code para o Antigravity, garantindo a integridade dos tipos no projeto CurupiraBOT.

## 1. Gatilhos de Verificação
Você deve acionar esta regra sempre que:
1.  **Alteração de Código**: Qualquer arquivo `.py` for modificado.
2.  **Preparação de Envio**: Antes de executar `git commit`, `git push` ou criar um Pull Request (`gh pr create`).
3.  **Finalização de Turno**: Antes de informar ao usuário que uma tarefa de codificação foi concluída.

## 2. Ação Requerida (@reviewer)
Sempre que acionado, o agente **@reviewer** deve:
1.  **Executar Validação**: Rodar o comando:
    `python3 .claude/hooks/pyright-check.py block`
2.  **Analisar Resultado**:
    -   Se o script retornar `{"continue": true}` (ou sucesso sem erros): Prossiga com a tarefa.
    -   Se o script retornar `{"continue": false}`: **PARE IMEDIATAMENTE**. 
    -   Você deve ler os erros apontados no `stopReason`, corrigi-los no código e rodar a validação novamente até que não restem erros de tipo.

## 3. Integração com outros Protocolos
-   Esta regra complementa o **Protocolo de Revisão Iara** definido nas `user_rules` globais.
-   O Pyright foca em **Segurança de Tipos**, enquanto a Iara foca em Lógica, Qualidade e Segurança Geral.

> [!IMPORTANT]
> Não ignore avisos ou erros do Pyright. A arquitetura do CurupiraBOT exige tipagem rigorosa para evitar falhas em tempo de execução no Raspberry Pi.

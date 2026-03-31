# Format Reminders List

## Context
Atualmente, o comando ou skill `list_reminders` retorna os lembretes do usuário em uma lista não ordenada (geralmente pela data de disparo `remind_at`). O formato em texto, embora funcional, pode ser confuso estruturalmente em listas longas ou quando tarefas automáticas se misturam com lembretes comuns. O usuário solicitou uma melhoria para formatar melhor a lista e ordená-la estritamente por ID, o que facilita operações subsequentes (como cancelar ou editar um lembrete pelo seu ID).

## Proposed Change
A alteração envolve modificar a lógica e a query SQL do skill `ListRemindersSkill` (e `ReminderManager.get_active_reminders` se necessário) para garantir que os resultados retornados estejam ordenados por `id` crescente. Além disso, o output em texto markdown deve ser reformatado para ser mais amigável, possivelmente adicionando indentação ou emojis padronizados para distinguir tarefas normais de automáticas, tudo dentro da restrição de "diet" e simplicidade da interface do Telegram.

## Impact
- **UX**: A lista de lembretes será mais limpa e ordenada pelo ID.
- **Performance**: Nenhuma penalidade significativa, apenas a alteração de um `ORDER BY` no SQL e pequenos ajustes na string formatting.
- **Retrocompatibilidade**: Mínimo impacto, não afeta o agente ou as assinaturas de chamadas de skills.

## Rationale
Ordenar por `id` facilita a vida do usuário ao rodar comandos de deleção/atualização, já que a leitura é feita de cima para baixo de forma incremental. Melhorar a apresentação evita confusão com links, metadados de agendamento, etc., melhorando a experiência no Telegram.

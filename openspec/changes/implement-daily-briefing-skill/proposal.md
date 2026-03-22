# Proposal: Implement Daily Briefing Skill

## Problem
O Curupira atualmente envia apenas um "Bom dia" simples via reflection no heartbeat.
O usuário gostaria de receber um briefing matinal completo ao invés de apenas uma saudação.

## Solution
Criar uma skill `DailyBriefingSkill` que agrega dados de clima, eventos do Google Calendar e
manchetes de RSS, e substitui a saudação simples por um briefing matinal formatado pelo LLM.

## Scope
- Nova skill: `skills/daily_briefing.py`
- Modificação do `system_heartbeat` em `bot.py` para disparar o briefing no horário de saudação
- Novo método `compose_briefing()` no `AgentBrain` para formatar o briefing via LLM
- Toggle on/off no `config.toml` (`[skills] daily_briefing = true`)
- Quando `daily_briefing = true`, o briefing substitui a saudação simples do reflect()
- Quando `daily_briefing = false`, comportamento original mantido (saudação simples)

## Out of Scope
- Evening briefing (futuro)
- Briefing customizável (escolher quais seções incluir)

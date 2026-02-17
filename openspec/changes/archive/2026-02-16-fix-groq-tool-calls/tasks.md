# Tasks: Fix Groq Tool Calls

## 1. Implementation
- [x] 1.1 Adicionar instrução negativa ao `system_prompt` em `core/agent.py:209-220` proibindo concatenação de argumentos no nome da função

## 2. Validation
- [x] 2.1 Criar e executar script de teste (`scripts/test_groq_tools.py`) comparando prompt fraco vs. prompt reforçado
- [x] 2.2 Confirmar que tool calls geradas têm nome exato (sem argumentos anexados)

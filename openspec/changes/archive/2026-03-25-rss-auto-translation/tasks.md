## 1. Preparation

- [x] 1.1 Mapear os feeds em `core/config.py` que não são PT-BR e necessitam de tradução (ex: BBC, TechCrunch).
- [x] 1.2 Estudar a melhor forma de acessar o cliente de IA (Groq/Gemini) a partir de uma Skill sem acoplamento forte (ex: via `context`).

## 2. Implementation: Tradução na Skill RSS

- [x] 2.1 Modificar a classe `RssReadSkill` em `skills/rss.py` para aceitar um parâmetro opcional no `parameters` (ex: `auto_translate`).
- [x] 2.2 Implementar a lógica de agrupamento de títulos para tradução em lote (batching).
- [x] 2.3 Implementar o prompt de sistema especializado para tradução de manchetes mantendo termos técnicos.
- [x] 2.4 Integrar a chamada da API de tradução (Groq ou Gemini) dentro do `execute` da skill caso o idioma do feed seja estrangeiro.

## 3. UI/UX & Fallbacks

- [x] 3.1 Adicionar sufixo de idioma original ao título traduzido (ex: `(EN)`).
- [x] 3.2 Implementar tratamento de exceções e timeout para a tradução: em caso de erro, retornar títulos originais.

## 4. Testing & QA

- [x] 4.1 Atualizar `tests/test_rss.py` para verificar se a tradução é invocada corretamente para feeds em inglês.
- [x] 4.2 Rodar `iara analyze` e ferramentas de linting para validar a qualidade do código.

## Why

Quando o usuário pergunta o que o Curupira pode fazer, a resposta atual lista cada tool individualmente — resultando em mais de 18 itens verbosos e sem estrutura visual. Isso dificulta a leitura e não representa bem a organização por Skills do bot. A resposta precisa ser condensada por skill e ter identidade visual com emojis.

## What Changes

- O comportamento de introspecção (`introspection`) passa a agrupar tools por skill e gerar uma resposta resumida, uma linha por skill com emoji
- Cada skill exibe apenas um resumo de suas capacidades (não lista cada tool)
- Quando o usuário solicitar detalhes de uma skill específica (ex: "me explica o Git"), o bot retorna os bullet points individuais daquela skill
- A lógica de formatação vive no handler de introspecção, sem alterar os tool descriptors das skills

## Capabilities

### New Capabilities

- `capabilities-display`: Formatação da lista de capacidades agrupada por skill com emojis e suporte a detalhamento por skill sob demanda

### Modified Capabilities

- `introspection`: Altera o requisito de resposta — de lista flat de tools para lista agrupada por skill, com dois modos: resumo e detalhamento

## Non-goals

- Não alterar os tool descriptors ou nomes das skills existentes
- Não adicionar novo comando `/skills` ou endpoint — apenas mudar a resposta do fluxo existente de "o que você faz"
- Não impactar o desempenho do Raspberry Pi (zero custo adicional de memória/CPU)

## Impact

- `skills/introspection.py` (ou equivalente): lógica de agrupamento e formatação
- Possível leitura de metadados de skill (nome, emoji, descrição) para montar o resumo
- Nenhuma mudança em banco de dados, dependências externas ou outras skills

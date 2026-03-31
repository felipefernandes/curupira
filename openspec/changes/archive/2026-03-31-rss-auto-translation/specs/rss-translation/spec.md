## ADDED Requirements

### Requirement: Tradução de Títulos em Lote
A skill `rss_read` deve agrupar todos os títulos (ex: 5 por vez) em uma única string estruturada e solicitar a tradução para PT-BR por meio do provedor de IA atual (Groq ou Gemini).
- **GIVEN** que o feed está em um idioma estrangeiro (como EN ou ES).
- **WHEN** a skill `rss_read` é executada com sucesso.
- **THEN** o resultado JSON deve conter os títulos já traduzidos substituindo os originais.

### Requirement: Tag de Idioma Original
Cada notícia traduzida deve conter um sufixo indicando o idioma original da fonte.
- **GIVEN** uma notícia traduzida do inglês.
- **WHEN** a skill retorna os títulos traduzidos.
- **THEN** o título deve terminar com ` (EN)`, ` (ES)` ou a tag correspondente.

### Requirement: Detecção de Idioma do Feed
O sistema deve ser capaz de distinguir feeds em português (como G1) daqueles em outros idiomas (como TechCrunch) para evitar traduções desnecessárias.
- **GIVEN** um feed configurado com URL de língua portuguesa ou títulos já em PT-BR.
- **WHEN** as notícias são extraídas.
- **THEN** o motor de tradução deve ser ignorado para economizar tokens e tempo.

### Requirement: Fallback em Erro
Se a chamada de tradução falhar (ex: timeout da API), a skill deve retornar os títulos originais sem interromper o fluxo total.
- **GIVEN** uma falha temporária no provedor de tradução.
- **WHEN** a skill tenta processar os títulos.
- **THEN** o bot ainda deve exibir as notícias nos idiomas originais normalmente.

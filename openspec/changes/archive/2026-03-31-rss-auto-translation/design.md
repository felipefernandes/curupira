## Context

Atualmente a skill `rss_read` em `skills/rss.py` extrai os títulos das notícias usando a biblioteca `feedparser` e os retorna "as-is". O usuário expressou na issue #109 a necessidade de que esses títulos sejam apresentados em Português Brasileiro (PT-BR) com uma indicação do idioma original da fonte.

## Goals

1.  **Tradução em Lote**: Garantir que todos os títulos extraídos (até o `limit` definido) sejam traduzidos em uma única operação de IA para minimizar latência e consumo de tokens.
2.  **Identificação de Idioma**: Adicionar o sufixo de idioma correspondente (ex: `(EN)`, `(ES)`, `(PT-BR)`) baseado no conteúdo original ou na URL do feed.
3.  **Fallback Seguro**: Se a tradução falhar, os títulos originais devem ser retornados normalmente, sem interromper o funcionamento da skill.
4.  **Integração Nativa**: Utilizar os provedores `Groq` ou `Gemini` já configurados no `AgentBrain`.

## Rationale

Para evitar o acoplamento forte desencorajado pelo `@architect`, a skill `RssReadSkill` continuará sendo uma unidade autônoma, mas poderá utilizar uma interface simplificada de tradução injetada ou acessível via `context`.

**Fluxo Técnico:**
1.  Extrair títulos originais via `feedparser`.
2.  Se o feed for reconhecidamente internacional:
    *   Formatar prompt para tradução múltipla: "Traduza os seguintes títulos de notícias para PT-BR: [Lista]"
    *   Chamar o modelo (`llama3-8b` por exemplo, por ser extremamente rápido e gratuito no Groq).
    *   Processar o retorno estruturado.
3.  Atualizar o objeto de resposta da skill.

## Risks / Trade-offs

-   **Ponto de Falha Extra**: Se a API da LLM estiver lenta ou indisponível, a busca de notícias ficará mais lenta. O timeout de 15s atual pode precisar de revisão, ou o processo de tradução deve ter seu próprio timeout curto.
-   **Hardware**: Como o bot roda em Raspberry Pi 3, chamadas de rede extras são preferíveis a processamento local pesado.
-   **Fidelidade da Tradução**: Nomes próprios e termos técnicos podem ser traduzidos incorretamente; o prompt deve ser instruído a manter termos técnicos comuns sem tradução literal excessiva.

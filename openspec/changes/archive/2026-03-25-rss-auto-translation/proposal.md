## Why

Atualmente, a skill `rss_read` extrai os títulos das notícias exatamente como estão no feed (frequentemente em inglês). Para usuários brasileiros, o consumo dessas informações é facilitado se os títulos já vierem traduzidos para o Português (PT-BR) na fonte. Além disso, a indicação do idioma original (ex: (EN), (PT-BR)) ajuda o usuário a saber o que esperar ao clicar no link da notícia.

Ter os dados pré-traduzidos na saída da ferramenta (`skill return`) garante que a informação esteja consistente independentemente de como o `AgentBrain` decide formatar a resposta final para o usuário.

## Impact

1.  **Skill `RssReadSkill`**: A lógica em `skills/rss.py` será alterada para processar a tradução antes de retornar os resultados.
2.  **LLM Integration**: A skill precisará de acesso a uma funcionalidade de tradução que utilize os provedores já existentes (Groq/Gemini), para evitar a adição de bibliotecas pesadas incompatíveis com Raspberry Pi.
3.  **Latência**: A execução da skill levará um pouco mais de tempo (tempo de uma chamada extra de IA para tradução). O uso de modelos rápidos (como Llama3-8b no Groq) minimiza esse impacto.
4.  **Daily Briefing**: A funcionalidade de resumo diário será beneficiada imediatamente com títulos em português sem esforço extra do gerador de briefing.

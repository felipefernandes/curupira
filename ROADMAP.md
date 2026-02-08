# [Fase 1 - SETUP] - Concluído
    [x] MVP, setup, arquivo de instalação amigável, fazer a primeira interação com o usuário via Telegram.

# [Fase 2 - MEMÓRIA] - Concluído
    [x] Adicionar camadas de memória (curto e longo prazo).
    [x] Memória de Longo prazo: usar um banco de dados para armazenar informações. Requisito importante: Precisa ser extremamente leve e não consumir muita memória RAM. (Ex: ChromaDB, SQLite, ou algo similar), a escolha deve ser feita de forma inteligente e com boa integração com Modelos de Linguagem Grandes (LLMs) escolhidas e usadas no projeto.
    [x] Memória de Curto prazo: Usar um arquivo JSON para armazenar informações ou algo similar, que seja leve e não consuma muita memória RAM.
    [x] Como produto final, é desejável que o Curupira tenha uma memória de longo prazo que permita que ele se lembre de informações sobre o usuário e sobre o sistema.

# [Fase 3 - Personalização] - Concluído
    [x] Na primeira interação que o Curupira tiver com o usuário, ele deve se apresentar e perguntar o nome do usuário. O curupira também deve perguntar ao usuário qual será o sobrenome que deseja que use, e esse sobrenome é o que o diferenciará dos outros Curupiras (deverá ser salvo em uma variável de ambiente persistente).
    [x] O nome do usuário deve ser armazenado em uma variável de ambiente persistente e usado em todas as interações futuras.
    [x] Curupira deverá se lembrar, resumidamente, de aspectos chaves da persolidade e da forma que o usuário gosta de interagir com ele.

# [Fase 4 - Heartbeat] - Concluído
    [x] Implementar um sistema de heartbeat enxuto e compatível com o hardware alvo (Raspberry Pi 3 Model B), considerando limitação de RAM e CPU ou algo similar.

# [Skill: Lembretes (Core)] - Concluído
    [x] Implementar um sistema de lembretes que permita ao usuário definir lembretes para serem enviados no futuro (MVP via JobQueue).

# [Skill: Lembretes (Gerenciamento Avançado)] - Concluído
    [x] Se o usuário perguntar algo do tipo "o que tem que fazer hoje?" ou "Quais são os meus lembretes de hoje | amanhã | semana | mes?", o Curupira deve responder com os lembretes que o usuário definiu.
    [x] O usuário pode definir lembretes com prazo definido, como "lembrete para amanhã" ou "lembrete para semana que vem".
    [x] O usuário pode pedir para remover lembretes existentes, como "remova lembrete de amanhã" ou "remova lembrete de semana que vem" ou "remova o lembrete sobre {assunto}" ou "remova todos os lembretes".
    [x] O usuário pode pedir para alterar alguma propriedade de algum lembrete existe: data, descrição e etc.

# [Skill: Previsão do Tempo / "Vai chover?"] - Concluído
    [x] O usuário pode perguntar algo do tipo "Vai chover hoje?" ou "Qual é a previsão do tempo para amanhã?".
    [x] O Curupira deve responder com a previsão do tempo para a localização do usuário.
    [x] O Curupira deve usar uma API de previsão do tempo para obter a previsão do tempo (exemplo: Open-Meteo ou wttr.in).
    [x] O curupira precisa perguntar ao usuário qual é a sua localização, caso ele não tenha informado anteriormente, e salvar essa informação em uma variável de ambiente persistente. Alternativamente, o curupira pode usar a localização do usuário obtida através do Telegram ou configurar o IP-API para descobrir a localização do usuário baseado no IP do dispositivo.

# [Skill: Monitoramento de Hardware]
    [ ] Adicionar monitoramento de hardware (temperatura, uso de CPU/RAM).

# [Skill: Gerenciamento de Arquivos]
    [ ] Adicionar gerenciamento de arquivos (criar, ler, escrever, deletar, mover, copiar, renomear, listar, etc.).

# [Skill: Integração com o Google Agenda]
    [ ] 

# [Skill: Integração com o Notion]
    [ ] 

# [Fase 5 - Arquitetura Agêntica Lightweight] - Em Progresso
    [x] Refatorar sistema de Skills para usar Function Calling (compatível com Gemini/Groq) ao invés de Regex.
    [x] Criação de classe base `BaseSkill` para padronizar novas habilidades e facilitar a extensão.
    [x] Implementar "Cérebro" de decisão (Loop de Agente) que escolhe qual skill usar baseado no contexto, mantendo baixo consumo de recursos.
    [ ] Implementar Cliente MCP (Model Context Protocol) para conectar nativamente a ferramentas externas e expandir o ecossistema de skills.

# [Skill: Navegação Web (Headless)]
    [ ] Implementar capacidade de acessar URLs e extrair conteúdo textual limpo (usando bibliotecas leves como `trafilatura` ou `beautifulsoup4`, evitando browsers completos devido à restrição de RAM do Raspberry Pi).
    [ ] Habilidade de resumir conteúdo de páginas web para o usuário.

# [Skill: Integração Vercel & Logs]
    [ ] Conectar à API da Vercel para baixar logs de deployments e runtime.
    [ ] Processamento de Logs: Implementar lógica de resumo com janelas de contexto para analisar logs extensos sem estourar limites de tokens.

# [Skill: Relatórios & Notificações (PDF/Email)]
    [ ] Gerar PDFs simples e leves (usando `fpdf2` ou similar).
    [ ] Enviar e-mails com anexos via SMTP ou API de terceiros (Resend/SendGrid).

# [Skill: Monitoramento & Google Analytics]
    [ ] Conectar API GA4 para extração de métricas diárias.
    [ ] Implementar análise de anomalias simples (comparação estatística local) para notificar o usuário sobre desvios padrão.

# [Skill: Terminal & Sistema (Power User)]
    [ ] Executar comandos de shell de forma segura (leitura de logs locais, verificação de disco, etc.).
    [ ] Expandir monitoramento de hardware (temperatura, CPU, RAM) com alertas proativos.


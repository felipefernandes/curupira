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

# [Fase 5 - Skill: Lembretes (Core)] - Concluído
[x] Implementar um sistema de lembretes que permita ao usuário definir lembretes para serem enviados no futuro (MVP via JobQueue).

# [Fase 5.5 - Skill: Lembretes (Gerenciamento Avançado)]
[x] Se o usuário perguntar algo do tipo "o que tem que fazer hoje?" ou "Quais são os meus lembretes de hoje | amanhã | semana | mes?", o Curupira deve responder com os lembretes que o usuário definiu.
[x] O usuário pode definir lembretes com prazo definido, como "lembrete para amanhã" ou "lembrete para semana que vem".
[x] O usuário pode pedir para remover lembretes existentes, como "remova lembrete de amanhã" ou "remova lembrete de semana que vem" ou "remova o lembrete sobre {assunto}" ou "remova todos os lembretes".
[ ] O usuário pode pedir para alterar alguma propriedade de algum lembrete existe: data, descrição e etc.

# [Fase 6 - Skill: Previsão do Tempo / "Vai chover?"]
[ ] O usuário pode perguntar algo do tipo "Vai chover hoje?" ou "Qual é a previsão do tempo para amanhã?".
[ ] O Curupira deve responder com a previsão do tempo para a localização do usuário.
[ ] O Curupira deve usar uma API de previsão do tempo para obter a previsão do tempo (exemplo: Open-Meteo ou wttr.in).
[ ] O curupira precisa perguntar ao usuário qual é a sua localização, caso ele não tenha informado anteriormente, e salvar essa informação em uma variável de ambiente persistente. Alternativamente, o curupira pode usar a localização do usuário obtida através do Telegram ou configurar o IP-API para descobrir a localização do usuário baseado no IP do dispositivo.

# [Fase 7 - Skill: Monitoramento de Hardware]
[ ] Adicionar monitoramento de hardware (temperatura, uso de CPU/RAM).

# [Fase 8 - Skill: Automação de Tarefas]
[ ] Adicionar automação de tarefas definidas pelo usuário.

# [Fase 9 - Skill: Gerenciamento de Arquivos]
[ ] Adicionar gerenciamento de arquivos (criar, ler, escrever, deletar, mover, copiar, renomear, listar, etc.).
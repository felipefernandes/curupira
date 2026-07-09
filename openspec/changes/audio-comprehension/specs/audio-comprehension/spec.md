## ADDED Requirements

### Requirement: Recebimento e Transcrição de Áudio
O sistema MUST receber mensagens de áudio (formato de voz do Telegram), baixá-las temporariamente, transcrevê-las usando a API do provedor LLM configurado (Groq Whisper) de forma estritamente assíncrona, e encaminhar o texto resultante para a engine de processamento de comandos. Não adiciona estado persistente (memory impact zero); o arquivo baixado MUST ser excluído imediatamente após a transcrição para evitar consumo de disco no hardware limitado (Raspberry Pi 3).

#### Scenario: Processamento bem-sucedido de áudio
- **GIVEN** que o provedor Groq está acessível
- **WHEN** o usuário enviar uma mensagem de voz no Telegram
- **THEN** o sistema baixará o áudio temporariamente
- **AND THEN** enviará para a API do Groq e receberá a transcrição
- **AND THEN** passará a transcrição textual para o fluxo do AgentBrain
- **AND THEN** apagará o arquivo de áudio temporário do disco local

#### Scenario: Falha na API de transcrição
- **GIVEN** que a API do Groq está inacessível ou retornando erro
- **WHEN** o usuário enviar uma mensagem de voz no Telegram
- **THEN** o sistema falhará ao transcrever o áudio
- **AND THEN** apagará o arquivo de áudio temporário do disco local para evitar vazamento de disco
- **AND THEN** informará ao usuário no Telegram que não foi possível processar o áudio no momento

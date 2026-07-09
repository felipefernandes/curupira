## Why

O assistente Curupira atualmente aceita apenas comandos de texto. No contexto de um assistente pessoal, o suporte a mensagens de áudio é fundamental para proporcionar uma interação mais natural e ágil, especialmente em dispositivos móveis. A restrição de hardware do Raspberry Pi 3 (CPU limitada e 1GB de RAM) inviabiliza o processamento local de modelos de transcrição (STT - Speech-to-Text). Portanto, a solução proposta aproveita a infraestrutura já existente do Groq para delegar a transcrição de áudio, utilizando modelos como `whisper-large-v3` ou `whisper-large-v3-turbo`.

## What Changes

- Adição de um manipulador de mensagens de voz (`MessageHandler(filters.VOICE)`) no Telegram.
- Implementação da lógica para realizar o download do arquivo de áudio recebido.
- Integração com a API do Groq (endpoint de transcrição de áudio) para converter o áudio baixado em texto.
- Encaminhamento do texto transcrito para o fluxo principal de processamento de comandos do bot (`AgentBrain`).
- Limpeza dos arquivos de áudio temporários após o processamento para não onerar o armazenamento do Raspberry Pi.

## Non-goals

- O bot não precisa responder com áudio (Text-to-Speech/TTS) neste primeiro momento. A resposta continuará sendo em texto.
- Não implementaremos reconhecimento de voz contínuo localmente ("wake word"); o bot apenas processará áudios enviados de forma explícita no chat do Telegram.

## Capabilities

### New Capabilities
- `audio-comprehension`: Capacidade de receber mensagens de voz no Telegram, baixar o áudio temporariamente, enviá-lo para transcrição na API do Groq usando o modelo Whisper e redirecionar o texto transcrito para o fluxo normal do assistente.

### Modified Capabilities
- Nenhuma capacidade existente tem seus requisitos modificados, essa é uma adição que alimenta o fluxo atual de processamento de mensagens.

## Impact

- **Core Bot Logic:** Esta alteração requer modificações no código principal de integração com o Telegram (adicionando suporte para lidar com mensagens de voz) e no cliente do provedor de LLM para incluir a chamada à API de transcrição do Groq.
- **Armazenamento:** Criação temporária de arquivos de áudio (`.ogg`) no disco do Raspberry Pi, que devem ser estritamente removidos após a transcrição para não esgotar o armazenamento SD.
- **Rede:** Aumento do consumo de rede, pois o bot precisará baixar o arquivo do Telegram e fazer o upload para a API do Groq.

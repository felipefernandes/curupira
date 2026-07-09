## Context

O Curupira Bot atualmente só recebe comandos em texto. Para se tornar um assistente pessoal mais completo, ele precisa entender mensagens de voz enviadas pelo Telegram. Como o Raspberry Pi 3 não tem recursos (RAM/CPU) suficientes para rodar um modelo de Speech-to-Text local (como Whisper local), devemos utilizar a API do provedor LLM configurado (neste caso, o Groq, que suporta o `whisper-large-v3` ou `whisper-large-v3-turbo`) para fazer a transcrição.

Esta alteração afeta principalmente a camada de interface do Telegram e os adaptadores de provedor de LLM, atuando como um pré-processamento antes que o prompt real seja enviado ao fluxo padrão do bot (AgentBrain).

## Goals / Non-Goals

**Goals:**
- Capturar mensagens de voz enviadas ao bot via Telegram.
- Baixar o áudio temporariamente de forma assíncrona.
- Enviar o áudio para a API do Groq e receber a transcrição textual de forma não bloqueante.
- Encaminhar a transcrição para o fluxo padrão do assistente como se fosse uma mensagem de texto.
- Limpar de forma agressiva os arquivos de áudio após o processamento.

**Non-Goals:**
- Implementação de funcionalidade Text-to-Speech (TTS).
- Transcrição local (sempre utilizaremos a API remota).
- Suporte para chamadas de voz ou ligações.

## Decisions

**1. Fluxo de Interceptação Assíncrona**
- **Decisão:** Criar um handler no `telegram_bot.py` dedicado a mensagens de voz: `MessageHandler(filters.VOICE, handle_voice_message)`.
- **Fluxo Assíncrono:** 
  1. A corrotina `handle_voice_message` intercepta a mensagem.
  2. Executa `await message.voice.get_file()` para obter o arquivo.
  3. Executa `await file.download_to_drive(custom_path)` no diretório de temporários.
  4. Chama o `provider` (ex: `GroqProvider`) passando o arquivo: `await provider.transcribe_audio(file_path)`.
  5. Após receber o texto transcrito, chama a corrotina padrão de processamento de texto `await agent_brain.process_message(texto)`.
  6. Finaliza com um bloco `finally:` para apagar o arquivo de áudio com `os.remove()`.
- **Alternativa Considerada:** Tentar rodar a transcrição num JobQueue. Descartado, pois a resposta precisa ser imediata ao usuário na conversa.

**2. Integração com a API do Groq**
- **Decisão:** Adicionar o método `transcribe_audio(file_path: str) -> str` no contrato de provedores (ex: interface base e `GroqProvider`). Utilizaremos a biblioteca oficial assíncrona do provedor ou requisições `aiohttp`.
- **Falhas e Fallback:** Se a API do Groq falhar (timeout ou erro 500), o bot responderá com uma mensagem de erro ("Desculpe, não consegui transcrever sua mensagem de áudio no momento."). Não há fallback imediato para outro provedor configurado para áudio no momento, mantendo a simplicidade.

**3. Gerenciamento de Armazenamento**
- **Decisão:** Os áudios baixados devem ser salvos numa pasta `/tmp` em memória (se disponível via tmpfs no Raspberry Pi) ou no diretório temporário do sistema operacional e excluídos imediatamente após a requisição ao Groq via bloco `try...finally`.

## Risks / Trade-offs

- **[Risco] Limite de tamanho de arquivo do Telegram:** O Telegram limita downloads de bots a 20MB. 
  - **Mitigação:** Para mensagens de áudio normais isso é mais do que suficiente. Pode-se validar o `file_size` antes de baixar e recusar arquivos muito grandes.
- **[Risco] Bloqueio do Event Loop:** O processo de ler o arquivo do disco ou fazer o request para a API HTTP de transcrição pode bloquear o event loop se for feito de forma síncrona.
  - **Mitigação:** Usar as bibliotecas estritamente assíncronas do `python-telegram-bot` (`download_to_drive` usa o event loop) e a versão `async` do cliente do Groq (ex: `AsyncGroq`).
- **[Risco] Consumo excessivo de espaço no cartão SD do Raspberry Pi:** Arquivos órfãos podem lotar o pequeno cartão SD.
  - **Mitigação:** Usar `tempfile` no Python com exclusão garantida no bloco `finally` e implementar um job periódico de limpeza (sanity check) na inicialização do bot para apagar qualquer resquício antigo na pasta de temp.

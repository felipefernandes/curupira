## 1. Provider Integration

- [x] 1.1 Atualizar a interface base de providers de LLM para incluir a assinatura assíncrona `async def transcribe_audio(self, file_path: str) -> str`.
- [x] 1.2 Implementar `transcribe_audio` no `GroqProvider`, utilizando o modelo `whisper-large-v3` ou `whisper-large-v3-turbo` via API (estritamente assíncrono).
- [x] 1.3 Adicionar implementação mock ou `NotImplementedError` para outros providers, garantindo compatibilidade da interface base.

## 2. Telegram Handler e Gerenciamento de Arquivos

- [x] 2.1 Criar a função assíncrona `handle_voice_message(update: Update, context: ContextTypes.DEFAULT_TYPE)` no módulo de interface do Telegram (`telegram_bot.py` ou equivalente).
- [x] 2.2 Registrar o novo handler no Dispatcher/Application: `MessageHandler(filters.VOICE, handle_voice_message)`.
- [x] 2.3 Implementar o download do arquivo de áudio utilizando `await update.message.voice.get_file()` e salvar em um diretório temporário (`tempfile`).
- [x] 2.4 Implementar a exclusão segura do arquivo de áudio (bloco `finally`) garantindo que ele não persista após o sucesso ou falha da operação.

## 3. Flow de Integração e UX

- [x] 3.1 Dentro de `handle_voice_message`, enviar feedback inicial ao usuário informando que o áudio está sendo processado (ex: ChatAction.TYPING ou mensagem de texto).
- [x] 3.2 Conectar a chamada ao `provider.transcribe_audio(file_path)` e obter o texto transcrito.
- [x] 3.3 Redirecionar o texto transcrito para o fluxo de conversação padrão (`agent_brain.process_message(text)` ou equivalente), garantindo que a resposta final seja enviada ao usuário.
- [x] 3.4 Adicionar tratamento de exceções (try/except) para falhas na API do Groq, notificando o usuário amigavelmente caso não seja possível transcrever o áudio.

## 4. Testes Manuais (Hardware & Software)

- [x] 4.1 Enviar mensagem de voz via cliente Telegram e verificar se a resposta gerada corresponde ao conteúdo falado.
- [x] 4.2 Verificar o diretório temporário após a execução para assegurar que os arquivos `.ogg` foram removidos.
- [x] 4.3 Simular falha de rede/API e certificar-se de que o arquivo ainda assim é removido localmente, prevenindo vazamento de espaço em disco no Raspberry Pi.

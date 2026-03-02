# Change: Diagnóstico de Integridade (Health Check)

## Why
Facilitar a configuração, contribuição e garantir que o ambiente do bot (especialmente para usuários não técnicos e instâncias pequenas, como Raspberry Pi/Celulares velhos) está operando de forma saudável. Falhas comuns (Falta de ZRAM gerando OOM, ausência do FFmpeg quebrando áudio, chaves de API faltando) podem gerar crashes silenciosos ou erros difíceis de depurar. Um diagnóstico ativo ("doctor") permite identificar e alertar o usuário preventivamente.

## What Changes
- Adicionar módulo `core/health.py` com validadores individuais (ZRAM/Memória, Segredos/ENV, FFmpeg, Conectividade, Git).
- Criar script standalone `check_health.py` (estilo "doctor" do Flutter/React Native) para rodar verificações de integridade via CLI.
- Atualizar a lógica do bot e o `system_prompt` para consumir os alertas do diagnóstico (ex: permitindo mensagens proativas ou respostas de status ricas em informações de problemas estruturais).
- Atualizar a documentação / README.md ensinando a rodar o script e explicando suas respostas.

## Impact
- Affected specs: `monitoring`
- Affected code: Criação de classes/módulos novos, leve injeção no contexto do Bot/Prompt sobre o status atual.
- Benefício chave: Diminuir erros de setup e facilitar suporte / troubleshooting para novos operadores do bot.

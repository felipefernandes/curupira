# Google Calendar - Guia de Configuração

Este guia explica como conectar o Curupira ao seu Google Calendar para gerenciar eventos via Telegram.

## 📋 Pré-requisitos

- Conta do Google
- Acesso ao [Google Cloud Console](https://console.cloud.google.com/)
- Curupira já instalado e funcionando

## 🔧 Configuração no Google Cloud Console

### Passo 1: Criar Projeto

1. Acesse o [Google Cloud Console](https://console.cloud.google.com/)
2. Clique em **"Select a project"** (topo da página)
3. Clique em **"NEW PROJECT"**
4. Nome do projeto: `Curupira Bot` (ou outro nome de sua preferência)
5. Clique em **"CREATE"**

### Passo 2: Habilitar Google Calendar API

1. No menu lateral, vá em **"APIs & Services"** → **"Library"**
2. Pesquise por `Google Calendar API`
3. Clique no resultado **"Google Calendar API"**
4. Clique em **"ENABLE"**

### Passo 3: Configurar Tela de Consentimento OAuth

1. No menu lateral, vá em **"APIs & Services"** → **"OAuth consent screen"**
2. Selecione **"External"** (para uso pessoal)
3. Clique em **"CREATE"**
4. Preencha os campos obrigatórios:
   - **App name**: `Curupira Bot`
   - **User support email**: Seu email
   - **Developer contact information**: Seu email
5. Clique em **"SAVE AND CONTINUE"**
6. Em **"Scopes"**, clique em **"ADD OR REMOVE SCOPES"**
7. Procure e selecione:
   - `https://www.googleapis.com/auth/calendar` (Manage your calendars)
8. Clique em **"UPDATE"** → **"SAVE AND CONTINUE"**
9. Em **"Test users"**, clique em **"ADD USERS"**
10. Adicione o email da sua conta Google que usará o calendário
11. Clique em **"SAVE AND CONTINUE"**
12. Revise e clique em **"BACK TO DASHBOARD"**

### Passo 4: Criar Credenciais OAuth 2.0

1. No menu lateral, vá em **"APIs & Services"** → **"Credentials"**
2. Clique em **"+ CREATE CREDENTIALS"** → **"OAuth client ID"**
3. **Application type**: Selecione **"Desktop app"**
4. **Name**: `Curupira Desktop Client`
5. Clique em **"CREATE"**
6. Uma janela mostrará:
   - **Client ID** (algo como `123456-abc.apps.googleusercontent.com`)
   - **Client secret** (algo como `GOCSPX-abc123def456`)
7. Clique em **"DOWNLOAD JSON"** (opcional, para backup)
8. Clique em **"OK"**

## ⚙️ Configuração no Curupira

### Passo 1: Adicionar Credenciais ao `.env`

Edite o arquivo `.env` na raiz do projeto e adicione:

```bash
# ── Google Calendar ────────────────────────────────────────────────
GCAL_CLIENT_ID=seu_client_id_aqui.apps.googleusercontent.com
GCAL_CLIENT_SECRET=seu_client_secret_aqui
GCAL_SYNC_INTERVAL_MINUTES=30
GCAL_CALENDAR_ID=primary
```

**⚠️ Importante:**
- Substitua `seu_client_id_aqui` e `seu_client_secret_aqui` pelos valores obtidos no Google Cloud Console
- `GCAL_CALENDAR_ID=primary` usa o calendário principal. Para usar outro calendário, obtenha o ID específico nas configurações do Google Calendar

### Passo 2: Reiniciar o Bot

```bash
# Pare o bot (Ctrl+C)
# Inicie novamente
python3 bot.py
```

## 🔐 Autenticação (Primeira Vez)

### Via Telegram

1. Envie para o Curupira: **"Configure o calendário"**
2. O bot responderá com uma URL de autenticação
3. **Abra a URL** no navegador
4. **Faça login** com sua conta Google
5. **Autorize** o Curupira a acessar seu calendário
6. O Google mostrará um **código de autorização**
7. **Copie o código**
8. Envie para o Curupira: **"Configure calendário com código: [SEU_CODIGO]"**
9. O bot confirmará: **"✅ Autenticação concluída com sucesso!"**

### Exemplo Prático

```
Você: Configure o calendário

Curupira: Autenticação necessária. Acesse:
https://accounts.google.com/o/oauth2/auth?...

Após autorizar, copie o código e envie:
'Configure calendário com código: [SEU_CODIGO]'

[Você abre o link, autoriza, e copia o código: 4/0AY0e-abc123...]

Você: Configure calendário com código: 4/0AY0e-abc123...

Curupira: ✅ Autenticação concluída com sucesso!
Você pode usar o Google Calendar agora.
```

## 📱 Usando o Google Calendar

### Listar Eventos

```
"O que eu tenho hoje?"
"Quais as próximas reuniões?"
"Me mostra a agenda de amanhã"
"Eventos da semana"
```

### Criar Eventos

```
"Marque café com a Maria amanhã às 15h"
"Crie uma reunião para segunda às 10h"
"Agende dentista na sexta 14h30"
```

### Cancelar Eventos

```
"Cancele a reunião das 10h"
"Desmarque o evento de amanhã"
```

## 🔔 Lembretes Automáticos

O Curupira **sincroniza automaticamente** seu calendário a cada 30 minutos (configurável via `GCAL_SYNC_INTERVAL_MINUTES`).

Para cada evento agendado nas **próximas 4 horas**, o bot cria um lembrete e te notifica **10 minutos antes** do evento:

```
Curupira: ⏰ Lembrete: [AGENDA] Reunião com o time
```

### Funcionamento
- **Sincronização**: A cada 30 minutos
- **Janela de busca**: Próximas 4 horas
- **Antecedência do lembrete**: 10 minutos antes
- **Sem duplicatas**: Usa o `iCalUID` do evento para evitar lembretes repetidos

## 🔧 Solução de Problemas

### "Não autenticado. Use 'Configure o calendário'"

**Causa**: Token OAuth expirado ou não configurado.

**Solução**: Refaça o processo de autenticação enviando "Configure o calendário" ao bot.

### "Google Calendar não configurado"

**Causa**: `GCAL_CLIENT_ID` ou `GCAL_CLIENT_SECRET` não estão no `.env`.

**Solução**:
1. Verifique se o arquivo `.env` contém as variáveis
2. Reinicie o bot após adicionar as variáveis

### "Erro 403: Access not configured"

**Causa**: Google Calendar API não foi habilitada no projeto.

**Solução**:
1. Acesse [Google Cloud Console](https://console.cloud.google.com/)
2. Vá em "APIs & Services" → "Library"
3. Procure "Google Calendar API" e clique em "ENABLE"

### "invalid_grant" ou "Token has been expired or revoked"

**Causa**: Refresh token inválido ou revogado.

**Solução**:
1. Delete o arquivo `data/google_token.json`
2. Refaça a autenticação via Telegram

### Lembretes não estão sendo criados

**Verificações**:
1. Confirme que o bot está rodando continuamente
2. Verifique os logs: `grep "calendar_sync" logs/curupira.log`
3. Confirme que há eventos nas próximas 4 horas no Google Calendar
4. Verifique se o intervalo de sync está configurado: `GCAL_SYNC_INTERVAL_MINUTES=30`

## 🔒 Segurança

- **Tokens**: Armazenados localmente em `data/google_token.json` (nunca no Git)
- **Escopo**: Acesso apenas ao calendário (não a emails ou outros dados)
- **Usuário único**: Apenas o `AUTHORIZED_USER_ID` pode usar a skill
- **Refresh automático**: Tokens são renovados automaticamente quando expiram

## 📚 Referências

- [Google Calendar API Documentation](https://developers.google.com/calendar/api/v3/reference)
- [OAuth 2.0 for Mobile & Desktop Apps](https://developers.google.com/identity/protocols/oauth2/native-app)
- [Curupira Skills Framework](../SKILLS_FRAMEWORK.md)

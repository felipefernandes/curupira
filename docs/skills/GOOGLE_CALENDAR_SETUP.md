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

## 🔒 Segurança OAuth2

A integração com Google Calendar usa **5 camadas de proteção** para garantir a segurança dos seus dados:

### Como Seus Dados São Protegidos

#### 1. **PKCE (Proof Key for Code Exchange)**
- Proteção contra ataques de interceptação de código de autorização
- Códigos temporários (10 minutos) que expiram automaticamente
- Uso único (deletados após autenticação bem-sucedida)
- Conformidade com RFC 7636 (padrão de indústria)

#### 2. **Tokens Criptografados em Disco**
- Tokens OAuth2 são criptografados antes de salvar em disco
- Algoritmo: Fernet (AES-128-CBC + HMAC-SHA256)
- Chave derivada via PBKDF2 com 100.000 iterações
- Proteção se backup for exposto acidentalmente

**⚠️ Importante**: Se você mudar `TELEGRAM_TOKEN` no `.env`, precisará re-autenticar o calendário.

#### 3. **Audit Logging**
- Todos os eventos OAuth2 são registrados em formato estruturado
- Log dedicado: `logs/security_audit.log`
- Rastreamento de autenticações, falhas e renovações de token
- Detecção de anomalias (múltiplas falhas = possível ataque)

#### 4. **Client Secret Seguro**
- Armazenado em `.env` (nunca no Git, protegido por .gitignore)
- Enviado apenas via HTTPS POST (criptografado em trânsito)
- Nunca aparece em URLs ou logs
- Conformidade com RFC 6749 (OAuth 2.0)

#### 5. **Escopo Mínimo**
- Permissão apenas para calendário: `https://www.googleapis.com/auth/calendar`
- Não acessa emails, contatos, drive ou outros dados
- Você pode revogar acesso a qualquer momento

### Revogando Acesso

Para revogar o acesso do Curupira ao seu Google Calendar:

1. Acesse [Google Account Permissions](https://myaccount.google.com/permissions)
2. Encontre "Curupira Bot" na lista
3. Clique em **"Remover Acesso"**
4. Delete `data/google_token.json` no servidor do Curupira
5. Pronto! O bot não terá mais acesso ao seu calendário

### Proteção de Dados

- **Armazenamento Local**: Tokens ficam no servidor do Curupira (`data/google_token.json`)
- **Nunca no Git**: `.gitignore` protege tokens, credenciais e logs de audit
- **Usuário Único**: Apenas `AUTHORIZED_USER_ID` (você) pode usar a skill
- **Refresh Automático**: Tokens são renovados quando expiram (sem interrupção)
- **Logging Sanitizado**: Erros de API nunca expõem informações sensíveis

### Compliance e Standards

A implementação segue rigorosamente:
- ✅ **RFC 6749**: OAuth 2.0 Authorization Framework
- ✅ **RFC 7636**: Proof Key for Code Exchange (PKCE)
- ✅ **NIST 800-111**: Guide to Storage Encryption
- ✅ **NIST 800-92**: Guide to Computer Security Log Management
- ✅ **OWASP OAuth Security Cheat Sheet**

### Documentação Técnica

Para detalhes técnicos completos sobre a arquitetura de segurança, veja:
- [GOOGLE_CALENDAR_OAUTH2_SECURITY.md](./GOOGLE_CALENDAR_OAUTH2_SECURITY.md)

## 📚 Referências

- [Google Calendar API Documentation](https://developers.google.com/calendar/api/v3/reference)
- [OAuth 2.0 for Mobile & Desktop Apps](https://developers.google.com/identity/protocols/oauth2/native-app)
- [Curupira Skills Framework](../SKILLS_FRAMEWORK.md)

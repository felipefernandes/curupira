import google.generativeai as genai
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import config
import logging

# Configure Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Gemini Setup
genai.configure(api_key=config.GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# Security Filter
def is_authorized(user_id):
    return user_id == config.AUTHORIZED_USER_ID

# Authorized Check Handler
async def acesso_negado(update: Update):
    await update.message.reply_text("⛔ Acesso negado. Este bot é privado.")

# Message Handler (AI)
async def responder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    
    if not is_authorized(user_id):
        await acesso_negado(update)
        return

    user_msg = update.message.text
    await update.message.reply_chat_action(action="typing")
    
    try:
        response = model.generate_content(user_msg)
        await update.message.reply_text(response.text)
    except Exception as e:
        error_msg = f"Erro ao processar: {str(e)}"
        logging.error(error_msg)
        await update.message.reply_text("Ocorreu um erro ao processar sua solicitação.")

# Status Command (Automation)
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.message.from_user.id):
        await acesso_negado(update)
        return

    await update.message.reply_text("✅ Sistema Online e você está autenticado!")

def main():
    if not config.TELEGRAM_TOKEN:
        print("Erro: TELEGRAM_TOKEN não configurado.")
        return

    app = ApplicationBuilder().token(config.TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler("status", status))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), responder))
    
    print("Bot Curupira iniciado com trava de segurança!")
    app.run_polling()

if __name__ == '__main__':
    main()

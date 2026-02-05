from google import genai
from groq import Groq
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, Application
import config
import logging
from skills.memory import MemoryManager

# Configure Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# AI Setup
gemini_client = None
groq_client = None
memory_manager = MemoryManager()

# Onboarding States
WAITING_NAME = 1
WAITING_SURNAME = 2
onboarding_states = {}

logging.info(f"Iniciando bot com provedor: {config.AI_PROVIDER}")

if config.AI_PROVIDER == 'gemini':
    if config.GEMINI_API_KEY:
        try:
            gemini_client = genai.Client(api_key=config.GEMINI_API_KEY)
            logging.info("Cliente Gemini inicializado.")
        except Exception as e:
            logging.error(f"Erro ao inicializar Gemini: {e}")
    else:
        logging.error("GEMINI_API_KEY não configurada.")

elif config.AI_PROVIDER == 'groq':
    if config.GROQ_API_KEY:
        try:
            groq_client = Groq(api_key=config.GROQ_API_KEY)
            logging.info("Cliente Groq inicializado.")
        except Exception as e:
            logging.error(f"Erro ao inicializar Groq: {e}")
    else:
        logging.error("GROQ_API_KEY não configurada.")

# Security Filter
def is_authorized(user_id):
    return user_id == config.AUTHORIZED_USER_ID

# Authorized Check Handler
async def acesso_negado(update: Update):
    await update.message.reply_text("⛔ Acesso negado. Este bot é privado.")

async def get_ai_response(user_msg, context_history="", facts=""):
    # Extract personal names from facts if available
    personal_name = "Usuário"
    assistant_surname = ""
    
    # Parse facts text to find names (simple parsing since get_facts returns "- key: value")
    if facts:
        for line in facts.split("\n"):
            if "personal_name" in line:
                personal_name = line.split(": ")[1].strip()
            elif "assistant_surname" in line:
                assistant_surname = line.split(": ")[1].strip()

    full_prompt = f"""
[System Context]
Persona: Curupira {assistant_surname} (Assistente Pessoal / Guardião do Sistema)
User Profile: {personal_name}
User Profile: {personal_name}
Fatos sobre o Usuário:
{facts}

[Instruções de Estilo]
1. Formatação: Use tags HTML para formatar a resposta (<b>negrito</b>, <i>itálico</i>, <pre>código</pre>). NÃO use Markdown (como **negrito**), pois o Telegram não renderiza corretamente neste modo.
2. Naturalidade: Seja natural e direto. Evite repetir o nome do usuário em toda frase. Aja como um amigo próximo que já conhece a pessoa, sem formalidades excessivas.

[Histórico da Conversa]
{context_history}

[Mensagem Atual]
User: {user_msg}
"""
    try:
        if config.AI_PROVIDER == 'groq':
            if not groq_client:
                return "Erro: Cliente Groq não inicializado. Verifique a chave de API."
            
            chat_completion = groq_client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": full_prompt,
                    }
                ],
                model="llama-3.3-70b-versatile",
            )
            return chat_completion.choices[0].message.content

        elif config.AI_PROVIDER == 'gemini':
            if not gemini_client:
                return "Erro: Cliente Gemini não inicializado. Verifique a chave de API."

            response = gemini_client.models.generate_content(
                model="gemini-2.0-flash", 
                contents=full_prompt
            )
            return response.text
        
        else:
            return f"Erro: Provedor '{config.AI_PROVIDER}' desconhecido."

    except Exception as e:
        logging.error(f"Erro na geração de IA: {e}")
        return f"Ocorreu um erro ao processar sua solicitação ({config.AI_PROVIDER}): {str(e)}"

# Message Handler (AI)
async def responder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    
    if not is_authorized(user_id):
        await acesso_negado(update)
        return

    user_msg = update.message.text
    user_name = update.message.from_user.username or "Unknown"
    full_name = update.message.from_user.full_name or "Unknown"
    
    await update.message.reply_chat_action(action="typing")
    
    # 1. Register User & Log Message
    await memory_manager.add_user(user_id, user_name, full_name)
    await memory_manager.log_message(user_id, "user", user_msg)

    # --- ONBOARDING FLOW START ---
    # Check if we know the user's chosen surname (identity marker for the BOT)
    has_surname = await memory_manager.get_fact_value(user_id, "assistant_surname")
    
    if not has_surname:
        state = onboarding_states.get(user_id)
        
        if state is None:
            # Start Onboarding
            await update.message.reply_text("Olá! Sou o Curupira. Antes de começarmos, como gostaria de ser chamado?")
            onboarding_states[user_id] = WAITING_NAME
            await memory_manager.log_message(user_id, "model", "Olá! Sou o Curupira. Antes de começarmos, como gostaria de ser chamado?")
            return

        elif state == WAITING_NAME:
            # Save Name, Ask Surname
            await memory_manager.save_fact(user_id, "personal_name", user_msg)
            reply_text = f"OK {user_msg}, como sou único, qual sobrenome devo usar para me diferenciar dos outros Curupiras?"
            await update.message.reply_text(reply_text)
            onboarding_states[user_id] = WAITING_SURNAME
            await memory_manager.log_message(user_id, "model", reply_text)
            return

        elif state == WAITING_SURNAME:
            # Save BOT Surname
            await memory_manager.save_fact(user_id, "assistant_surname", user_msg)
            del onboarding_states[user_id] # Clear state
            
            # Retrieve name for better UX
            name = await memory_manager.get_fact_value(user_id, "personal_name") or "Usuário"
            
            # Improved informal reply as requested:
            welcome_back = f"Entendido! Configuração concluída! Como posso ajudar hoje?"
            
            await update.message.reply_text(welcome_back)
            await memory_manager.log_message(user_id, "model", welcome_back)
            return
    # --- ONBOARDING FLOW END ---
    
    # 2. Retrieve Context
    context_history = await memory_manager.get_context(user_id)
    facts = await memory_manager.get_facts(user_id)
    
    # 3. Get AI Response
    response_text = await get_ai_response(user_msg, context_history, facts)
    
    # 4. Log Response
    await memory_manager.log_message(user_id, "model", response_text)
    
    try:
        await update.message.reply_text(response_text, parse_mode=ParseMode.HTML)
    except Exception as e:
        logging.error(f"Erro de parsing HTML: {e}")
        await update.message.reply_text(response_text)

# --- JOB QUEUE CALLBACKS ---
async def system_heartbeat(context: ContextTypes.DEFAULT_TYPE):
    """Logs a heartbeat message to ensure system is alive."""
    logging.info("💓 Status Heartbeat: Online. System is healthy.")

async def proactive_ping(context: ContextTypes.DEFAULT_TYPE):
    """Sends a proactive message to the user."""
    job = context.job
    chat_id = job.chat_id
    if chat_id:
        await context.bot.send_message(chat_id=chat_id, text="🔋 Sistema Proativo Iniciado. Estou monitorando.")
        logging.info("Proactive ping sent.")

async def post_init(application: Application):
    await memory_manager.init_db()
    
    # Register Jobs
    if application.job_queue:
        # System Heartbeat
        application.job_queue.run_repeating(system_heartbeat, interval=config.HEARTBEAT_INTERVAL, first=10, name="system_heartbeat")
        
        # Proactive Test (Runs once 30s after startup)
        if config.AUTHORIZED_USER_ID:
             application.job_queue.run_once(proactive_ping, when=30, chat_id=config.AUTHORIZED_USER_ID, name="proactive_test")
        
        logging.info("Jobs agendados: Heartbeat & Proactive Ping Stub")
    else:
        logging.error("JobQueue não está disponível!")

# Status Command (Automation)
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.message.from_user.id):
        await acesso_negado(update)
        return

    provider_status = f"IA: {config.AI_PROVIDER.upper()}"
    await update.message.reply_text(f"✅ Sistema Online e você está autenticado!\n{provider_status}")

def main():
    if not config.TELEGRAM_TOKEN:
        print("Erro: TELEGRAM_TOKEN não configurado.")
        return

    app = ApplicationBuilder().token(config.TELEGRAM_TOKEN).post_init(post_init).build()
    
    app.add_handler(CommandHandler("status", status))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), responder))
    
    print(f"Bot Curupira iniciado com trava de segurança! Provedor: {config.AI_PROVIDER}")
    app.run_polling()

if __name__ == '__main__':
    main()

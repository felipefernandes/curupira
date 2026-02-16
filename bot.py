from google import genai
from groq import Groq
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, Application
from core import config
import re
from datetime import datetime
import logging
from skills.memory import MemoryManager
from skills.reminders import ReminderManager, AddReminderSkill, ListRemindersSkill, DeleteReminderSkill, UpdateReminderSkill
from skills.weather_manager import WeatherSkill
from core.agent import AgentBrain
from skills.github import configure as configure_github

# Configure Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# AI Setup
memory_manager = MemoryManager()
reminder_manager = ReminderManager()
weather_skill = WeatherSkill()

# Agent Brain Setup
brain = AgentBrain(config.AI_PROVIDER, config.GEMINI_API_KEY if config.AI_PROVIDER == 'gemini' else config.GROQ_API_KEY, config.GEMINI_MODEL if config.AI_PROVIDER == 'gemini' else config.GROQ_MODEL)

# Configure MCP Skills (before start_mcp_clients)
configure_github()

# Register Skills
brain.register_skill(weather_skill)
brain.register_skill(AddReminderSkill(reminder_manager))
brain.register_skill(ListRemindersSkill(reminder_manager))
brain.register_skill(DeleteReminderSkill(reminder_manager))
brain.register_skill(UpdateReminderSkill(reminder_manager))

# Skill: Hardware Monitoring
# Skill: Hardware Monitoring
from skills.hardware import HardwareMonitoringSkill
brain.register_skill(HardwareMonitoringSkill())

# Skill: Time
from skills.time import GetTimeSkill
brain.register_skill(GetTimeSkill())

# Onboarding States
WAITING_NAME = 1
WAITING_SURNAME = 2
onboarding_states = {}

logging.info(f"Iniciando bot com provedor: {config.AI_PROVIDER}")

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
    # active_reminders = await reminder_manager.get_active_reminders(user_id) # Agent can fetch if needed via Skill
    
    # 3. Agent Brain Execution
    agent_context = {
        "user_id": user_id,
        "user_name": full_name,
        "job_queue": context.job_queue
    }
    
    try:
        response_text = await brain.process(user_msg, agent_context, chat_history=context_history)
    except Exception as e:
        logging.error(f"Brain Error: {e}")
        response_text = "Ocorreu um erro interno no meu cérebro. Tente novamente."

    # 4. Log Response
    await memory_manager.log_message(user_id, "model", response_text)
    
    try:
        await update.message.reply_text(response_text, parse_mode=ParseMode.HTML)
    except Exception as e:
        logging.error(f"Erro de parsing HTML: {e}")
        # Fallback to plain text if HTML fails
        await update.message.reply_text(response_text)

# --- JOB QUEUE CALLBACKS ---
async def execute_reminder(context: ContextTypes.DEFAULT_TYPE):
    """Executes a scheduled reminder after verifying DB status."""
    job = context.job
    # Data is now a dict {"id": id, "msg": msg}
    reminder_data = job.data 
    
    if not isinstance(reminder_data, dict):
        # Fallback for old jobs (memory only) - unlikely to happen if restarted
        await context.bot.send_message(chat_id=job.chat_id, text=f"⏰ Lembrete: {reminder_data}")
        return

    reminder_id = reminder_data["id"]
    # Single Source of Truth: Fetch latest message from DB
    db_message = await reminder_manager.get_reminder_message(reminder_id)
    message = db_message if db_message else reminder_data.get("msg", "Lembrete sem texto")

    # Check status in DB
    status = await reminder_manager.get_reminder_status(reminder_id)
    
    if status == 'PENDING':
        await context.bot.send_message(chat_id=job.chat_id, text=f"⏰ Lembrete: {message}")
        await reminder_manager.mark_as_sent(reminder_id)
    else:
        logging.info(f"Skipping reminder {reminder_id} (Status: {status})")

async def system_heartbeat(context: ContextTypes.DEFAULT_TYPE):
    """Logs a heartbeat message to ensure system is alive."""
    logging.info("💓 Status Heartbeat: Online. System is healthy.")

async def post_init(application: Application):
    await memory_manager.init_db()
    # Start MCP Clients
    await brain.start_mcp_clients()
    
    if application.job_queue:
        # System Heartbeat
        application.job_queue.run_repeating(system_heartbeat, interval=config.HEARTBEAT_INTERVAL, first=10, name="system_heartbeat")
        
        # Recover Persisted Reminders
        try:
            logging.info("Recuperando lembretes persistentes...")
            # Assign callback for recovery
            reminder_manager._execute_reminder_callback = execute_reminder 
            await reminder_manager.recover_reminders(application.job_queue)
        except Exception as e:
            logging.error(f"Erro ao recuperar lembretes: {e}")
        
        logging.info("Jobs agendados: Heartbeat + Lembretes Recuperados")
    else:
        logging.error("JobQueue não está disponível!")

# Status Command (Automation)
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.message.from_user.id):
        await acesso_negado(update)
        return

    provider_status = f"IA: {config.AI_PROVIDER.upper()}"
    await update.message.reply_text(f"✅ Sistema Online e você está autenticado! (Agentic Mode)\n{provider_status}")

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

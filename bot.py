from google import genai
from groq import Groq
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, Application
from core import config
import asyncio
import re
from datetime import datetime
import logging
from skills.memory import MemoryManager
from skills.reminders import ReminderManager, AddReminderSkill, ListRemindersSkill, DeleteReminderSkill, UpdateReminderSkill
from skills.weather_manager import WeatherSkill
from skills.memory import SaveFactSkill
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
brain = AgentBrain(config.AI_PROVIDER, config.GEMINI_MODEL if config.AI_PROVIDER == 'gemini' else config.GROQ_MODEL)

# Configure MCP Skills (before start_mcp_clients)
configure_github()

# Register Skills
brain.register_skill(weather_skill)
brain.register_skill(AddReminderSkill(reminder_manager))
brain.register_skill(ListRemindersSkill(reminder_manager))
brain.register_skill(DeleteReminderSkill(reminder_manager))
brain.register_skill(UpdateReminderSkill(reminder_manager))

# Skill: Hardware Monitoring
from skills.hardware import HardwareMonitoringSkill
hardware_skill = HardwareMonitoringSkill()
brain.register_skill(hardware_skill)

# Skill: Time
from skills.time import GetTimeSkill
brain.register_skill(GetTimeSkill())

# Skill: Save User Fact (long-term memory)
brain.register_skill(SaveFactSkill(memory_manager))

# Skill: Job Hunter
from skills.job_hunter import JobHunterRunSearchSkill, JobHunterGetDefaultsSkill
brain.register_skill(JobHunterRunSearchSkill())
brain.register_skill(JobHunterGetDefaultsSkill())

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
    
    # 2. Retrieve Context (Session Memory: Max 20 msgs in the last 30 minutes)
    context_history = await memory_manager.get_context(user_id, limit=20, minutes_ago=30)
    user_facts = await memory_manager.get_facts(user_id)
    assistant_surname = await memory_manager.get_fact_value(user_id, "assistant_surname") or ""

    # 3. Agent Brain Execution
    agent_context = {
        "user_id": user_id,
        "user_name": full_name,
        "user_facts": user_facts,
        "job_queue": context.job_queue,
        "assistant_surname": assistant_surname,
    }

    async def keep_typing():
        """Sends TYPING action every 4s while the agent processes."""
        try:
            while True:
                await update.effective_chat.send_action("typing")
                await asyncio.sleep(4)
        except asyncio.CancelledError:
            pass

    async def intermediate_reply(text: str):
        """Callback to send preamble text before tool execution."""
        if text and text.strip():
            try:
                await update.message.reply_text(text.strip(), parse_mode=ParseMode.HTML)
            except Exception as e:
                logging.error(f"Erro no intermediate_reply (HTML): {e}")
                try:
                    await update.message.reply_text(text.strip())
                except Exception as inner_e:
                    logging.error(f"Erro no intermediate_reply (Fallback): {inner_e}")

    typing_task = asyncio.create_task(keep_typing())
    try:
        response_text = await brain.process(
            user_msg, 
            agent_context, 
            chat_history=context_history, 
            on_intermediate_reply=intermediate_reply
        )
    except Exception as e:
        logging.error(f"Brain Error: {e}")
        response_text = "Ocorreu um erro interno no meu cérebro. Tente novamente."
    finally:
        typing_task.cancel()

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
    """Executes a scheduled reminder after verifying DB status.

    For recurring reminders: resets remind_at and reschedules instead of marking SENT.
    For is_task reminders: runs the message through the agent brain to trigger skills.
    """
    job = context.job
    reminder_data = job.data

    if not isinstance(reminder_data, dict):
        # Fallback for old plain-text jobs
        await context.bot.send_message(chat_id=job.chat_id, text=f"⏰ Lembrete: {reminder_data}")
        return

    reminder_id = reminder_data["id"]
    db_message = await reminder_manager.get_reminder_message(reminder_id)
    message = db_message if db_message else reminder_data.get("msg", "Lembrete sem texto")

    status = await reminder_manager.get_reminder_status(reminder_id)
    if status != 'PENDING':
        logging.info(f"Skipping reminder {reminder_id} (Status: {status})")
        return

    recurrence, is_task, remind_at = await reminder_manager.get_reminder_recurrence(reminder_id)

    # --- Execute the reminder action ---
    task_error = False
    if is_task:
        # Run message through the agent brain to trigger skills
        try:
            user_facts = await memory_manager.get_facts(job.chat_id)
            assistant_surname = await memory_manager.get_fact_value(job.chat_id, "assistant_surname") or ""
            agent_context = {
                "user_id": job.chat_id,
                "user_name": "Usuário",
                "user_facts": user_facts,
                "job_queue": context.job_queue,
                "assistant_surname": assistant_surname,
            }
            response_text = await brain.process(message, agent_context, chat_history=[])
            await context.bot.send_message(chat_id=job.chat_id, text=response_text)
        except Exception as e:
            task_error = True
            logging.error(f"Error executing task reminder {reminder_id}: {e}")
            try:
                await context.bot.send_message(chat_id=job.chat_id, text=f"⚠️ Erro ao executar tarefa agendada: {message}")
            except Exception as send_err:
                logging.error(f"Failed to notify user of task error for reminder {reminder_id}: {send_err}")
    else:
        await context.bot.send_message(chat_id=job.chat_id, text=f"⏰ Lembrete: {message}")

    # --- Reschedule or mark as sent ---
    if recurrence:
        next_time = reminder_manager._next_occurrence(recurrence, from_time=remind_at)
        await reminder_manager.reset_recurring_reminder(reminder_id, next_time)
        next_delay = (next_time - datetime.now()).total_seconds()
        context.job_queue.run_once(
            execute_reminder,
            when=max(next_delay, 1),
            chat_id=job.chat_id,
            data={"id": reminder_id, "msg": message},
            name=f"reminder_{reminder_id}",
        )
        logging.info(f"Recurring reminder {reminder_id} rescheduled → {next_time}")
    if not recurrence and not task_error:
        await reminder_manager.mark_as_sent(reminder_id)

async def system_heartbeat(context: ContextTypes.DEFAULT_TYPE):
    """
    Heartbeat + Reflection Loop.
    Logs status and checks if the Agent wants to speak proactively.
    """
    logging.info("💓 Status Heartbeat: Online.")
    
    if not config.REFLECTION_ENABLED:
        return

    try:
        # 1. Gather Context (Lightweight)
        hw_status = await hardware_skill.execute({})
        now = datetime.now()
        
        reflection_context = {
            "time": now.strftime("%Y-%m-%d %H:%M:%S"),
            "hour": now.hour,
            "hardware": hw_status.get("metrics", {}),
            # "reminders": await reminder_manager.get_active_count() # Future optimization
        }

        # 2. Reflect
        msg = await brain.reflect(reflection_context)

        # 3. Act
        if msg:
            logging.info(f"🔔 Proactive Reflection Triggered: {msg}")
            # Send to authorized user
            if config.AUTHORIZED_USER_ID != 0:
                await context.bot.send_message(
                    chat_id=config.AUTHORIZED_USER_ID, 
                    text=f"🧙‍♂️ *Curupira (Reflexão):*\n{msg}",
                    parse_mode=ParseMode.MARKDOWN
                )
        else:
            logging.info("🤫 Reflection: SILENCE")

    except Exception as e:
        logging.error(f"Heartbeat Reflection Error: {e}")

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

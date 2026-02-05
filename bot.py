from google import genai
from groq import Groq
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, Application
import config
import re
from datetime import datetime, timedelta
import logging
from skills.memory import MemoryManager
from skills.reminders import ReminderManager

# Configure Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# AI Setup
gemini_client = None
groq_client = None
memory_manager = MemoryManager()
reminder_manager = ReminderManager()

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
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

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
Current Time: {now}
Fatos sobre o Usuário:
{facts}

[Instruções de Estilo]
1. Formatação: Use tags HTML para formatar a resposta (<b>negrito</b>, <i>itálico</i>, <pre>código</pre>). NÃO use Markdown (como **negrito**), pois o Telegram não renderiza corretamente neste modo.
2. Naturalidade: Seja natural e direto. Evite repetir o nome do usuário em toda frase. Aja como um amigo próximo que já conhece a pessoa, sem formalidades excessivas.

[Ferramentas / Comandos]
1. Criar Lembrete:
Se o usuário pedir para ser lembrado, calcule o tempo relativo em minutos e use:
[[REMINDER|MINUTES|MESSAGE]]

2. Listar Lembretes:
Se o usuário perguntar "quais são meus lembretes?" ou similar, use:
[[REMINDER_LIST]]

3. Deletar Lembrete:
Se o usuário pedir para cancelar/remover um lembrete (geralmente pelo ID), use:
[[REMINDER_DELETE|ID]]

Exemplos:
- "Me lembre de sair em 1h" -> "Feito! [[REMINDER|60|Sair de casa]]"
- "Quais meus lembretes?" -> "Vou verificar... [[REMINDER_LIST]]"
- "Cancele o lembrete 3" -> "Cancelando... [[REMINDER_DELETE|3]]"

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
    full_response = await get_ai_response(user_msg, context_history, facts)
    
    # Process Commands (Reminders)
    reply_text = full_response
    
    # 1. CREATE REMINDER
    reminder_match = re.search(r"\[\[REMINDER\|(\d+)\|(.*?)\]\]", full_response)
    if reminder_match:
        try:
            minutes = int(reminder_match.group(1))
            reminder_msg = reminder_match.group(2)
            
            # Save to DB
            seconds_delay = minutes * 60
            reminder_id = await reminder_manager.add_reminder(user_id, reminder_msg, seconds_delay)
            
            # Schedule Job
            if context.job_queue:
                context.job_queue.run_once(
                    execute_reminder, 
                    when=seconds_delay, 
                    chat_id=user_id, 
                    data={"id": reminder_id, "msg": reminder_msg},
                    name=f"reminder_{reminder_id}"
                )
                logging.info(f"Lembrete agendado: {reminder_msg} em {minutes} min (ID: {reminder_id})")
            
            reply_text = full_response.replace(reminder_match.group(0), "").strip()
        except Exception as e:
            logging.error(f"Erro ao processar lembrete: {e}")

    # 2. LIST REMINDERS
    if "[[REMINDER_LIST]]" in full_response:
        reminders = await reminder_manager.get_active_reminders(user_id)
        if reminders:
            list_text = "📅 **Seus Lembretes Pendentes:**\n\n"
            for r_id, msg, r_at in sorted(reminders, key=lambda x: x[0]): # Sort by ID for easier deletion
                # Format time
                if isinstance(r_at, str):
                    dt = datetime.fromisoformat(r_at)
                else:
                    dt = r_at
                list_text += f"🆔 <b>{r_id}</b>: {msg} (em {dt.strftime('%d/%m %H:%M')})\n"
        else:
            list_text = "Você não tem lembretes pendentes."
        
        reply_text = full_response.replace("[[REMINDER_LIST]]", list_text).strip()

    # 3. DELETE REMINDER
    delete_match = re.search(r"\[\[REMINDER_DELETE\|(\d+)\]\]", full_response)
    if delete_match:
        try:
            r_id = int(delete_match.group(1))
            await reminder_manager.delete_reminder(r_id, user_id)
            
            # Try to cancel job if in memory (best effort)
            current_jobs = context.job_queue.get_jobs_by_name(f"reminder_{r_id}")
            for job in current_jobs:
                job.schedule_removal()
            
            reply_text = full_response.replace(delete_match.group(0), f"✅ Lembrete {r_id} cancelado.").strip()
        except Exception as e:
            logging.error(f"Erro ao deletar lembrete: {e}")
            reply_text = "Erro ao cancelar o lembrete."

    # 4. Log Response
    
    # 4. Log Response
    await memory_manager.log_message(user_id, "model", reply_text)
    
    try:
        await update.message.reply_text(reply_text, parse_mode=ParseMode.HTML)
    except Exception as e:
        logging.error(f"Erro de parsing HTML: {e}")
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
    message = reminder_data["msg"]

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

async def proactive_ping(context: ContextTypes.DEFAULT_TYPE):
    """Sends a proactive message to the user."""
    job = context.job
    chat_id = job.chat_id
    if chat_id:
        await context.bot.send_message(chat_id=chat_id, text="🔋 Sistema Proativo Iniciado. Estou monitorando.")
        logging.info("Proactive ping sent.")

async def post_init(application: Application):
    await memory_manager.init_db()
    
    # Recover Reminders
    if application.job_queue:
        # Use a proxy for the internal callback, setting execute_reminder as target
        # Actually, ReminderManager needs to know which function to call. 
        # Easier: we implement recovery logic here calling ReminderManager just to get data, 
        # or we update ReminderManager to accept the callback function.
        # Let's simple query ReminderManager and schedule here.
        
        # We need a quick way to reuse the ReminderManager.recover_reminders logic BUT pointing to OUR execute_reminder
        # Let's monkey-patch or just pass the function if we modified ReminderManager?
        # Simpler: Let's do the logic here for clarity or rely on ReminderManager if updated.
        # I defined recover_reminders to take job_queue but it hardcoded _execute_reminder_callback.
        # Let's use it but we need to ensure _execute_reminder_callback maps to execute_reminder logic.
        
        # Override the internal callback of the instance? No, that's messy.
        # Let's just call the recovery method and update `skills/reminders.py` to accept the callback, 
        # or simply rewrite the recovery loop here since we have the manager.
        pass # Placeholder, see below replacement
        
    # Re-implementing recovery here for explicit callback control
    if application.job_queue:
        # System Heartbeat
        application.job_queue.run_repeating(system_heartbeat, interval=config.HEARTBEAT_INTERVAL, first=10, name="system_heartbeat")
        
        # Recover Persisted Reminders
        try:
            logging.info("Recuperando lembretes persistentes...")
            # We need to access the logic from ReminderManager. Let's assume we can query pending.
            # I added logic to `recover_reminders` in previous step but it uses `self._execute_reminder_callback`.
            # Let's assign `execute_reminder` to that slot or just fix it.
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

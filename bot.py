from telegram import Update
from telegram.error import TelegramError
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, Application
from core import config
import asyncio
from datetime import datetime
import logging
from typing import Optional
from skills.memory import MemoryManager
from core.agent import AgentBrain
from core.telegram_formatter import TelegramFormatter, _strip_unsupported_html as _fmt_strip

# Configure Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# ── Core Setup ─────────────────────────────────────────────────────────
# memory_manager é necessário se qualquer skill de memória ou sports estiver ativa
_needs_memory = (
    config.skill_enabled("memory")
    or config.skill_enabled("sports")
    or config.skill_enabled("reminders")
)
memory_manager: Optional[MemoryManager] = MemoryManager() if _needs_memory else None

# Agent Brain Setup
brain = AgentBrain(
    config.AI_PROVIDER,
    config.GEMINI_MODEL if config.AI_PROVIDER == 'gemini' else config.GROQ_MODEL,
)

# ── Skill Registration (controlado por config.skill_enabled) ───────────

# Skill: Lembretes
from skills.reminders import ReminderManager, AddReminderSkill, ListRemindersSkill, DeleteReminderSkill, UpdateReminderSkill
from skills.calendar_reminder_bridge import run_calendar_sync
reminder_manager: Optional[ReminderManager] = None
if config.skill_enabled("reminders"):
    reminder_manager = ReminderManager()
    brain.register_skill(AddReminderSkill(reminder_manager))
    brain.register_skill(ListRemindersSkill(reminder_manager))
    brain.register_skill(DeleteReminderSkill(reminder_manager))
    brain.register_skill(UpdateReminderSkill(reminder_manager))
else:
    logging.info("Skill 'reminders' desabilitada pela configuração.")

# Skill: Clima
if config.skill_enabled("weather"):
    from skills.weather_manager import WeatherSkill
    weather_skill = WeatherSkill()
    brain.register_skill(weather_skill)
else:
    logging.info("Skill 'weather' desabilitada pela configuração.")
    weather_skill = None  # type: ignore[assignment]

# Skill: Hardware Monitoring
if config.skill_enabled("hardware"):
    from skills.hardware import HardwareMonitoringSkill
    hardware_skill = HardwareMonitoringSkill()
    brain.register_skill(hardware_skill)
else:
    logging.info("Skill 'hardware' desabilitada pela configuração.")
    hardware_skill = None  # type: ignore[assignment]

# Skill: System Control (Power User)
if config.skill_enabled("system_control"):
    from skills.system_control import SystemControlSkill
    system_control_skill = SystemControlSkill()
    brain.register_skill(system_control_skill)
else:
    logging.info("Skill 'system_control' desabilitada pela configuração.")
    system_control_skill = None  # type: ignore[assignment]

# Skill: Horário
if config.skill_enabled("time"):
    from skills.time import GetTimeSkill
    brain.register_skill(GetTimeSkill())
else:
    logging.info("Skill 'time' desabilitada pela configuração.")

# Skill: Memória de Usuário (long-term facts)
if config.skill_enabled("memory"):
    from skills.memory import SaveFactSkill
    assert memory_manager is not None  # memory skill enabled → manager initialized
    brain.register_skill(SaveFactSkill(memory_manager))
else:
    logging.info("Skill 'memory' desabilitada pela configuração.")

# Skill: Job Hunter
if config.skill_enabled("job_hunter"):
    from skills.job_hunter import JobHunterRunSearchSkill, JobHunterGetDefaultsSkill
    brain.register_skill(JobHunterRunSearchSkill())
    brain.register_skill(JobHunterGetDefaultsSkill())
else:
    logging.info("Skill 'job_hunter' desabilitada pela configuração.")

# Skill: Sports Manager
if config.skill_enabled("sports"):
    from skills.sports_manager import SportsManagerSkill
    assert memory_manager is not None  # sports skill enabled → manager initialized
    sports_skill = SportsManagerSkill(memory_manager)
    brain.register_skill(sports_skill)
else:
    logging.info("Skill 'sports' desabilitada pela configuração.")

# Skill: Usage Report
if config.skill_enabled("usage_report"):
    from skills.usage_report import UsageReportSkill
    assert memory_manager is not None  # usage_report skill enabled → manager initialized
    brain.register_skill(UsageReportSkill(memory_manager))
else:
    logging.info("Skill 'usage_report' desabilitada pela configuração.")

# Skill: Daily Briefing
if config.skill_enabled("daily_briefing"):
    from skills.daily_briefing import DailyBriefingSkill
    _briefing_weather = weather_skill if config.skill_enabled("weather") else None
    _briefing_calendar = brain.skills.get("google_calendar")
    _briefing_rss = brain.skills.get("rss_read")
    daily_briefing_skill = DailyBriefingSkill(
        weather_skill=_briefing_weather,
        calendar_skill=_briefing_calendar,
        rss_skill=_briefing_rss,
    )
    brain.register_skill(daily_briefing_skill)
else:
    logging.info("Skill 'daily_briefing' desabilitada pela configuração.")
    daily_briefing_skill = None  # type: ignore[assignment]

# Skill: Remote Update
if config.skill_enabled("remote_update"):
    from skills.remote_update import RemoteUpdateSkill
    brain.register_skill(RemoteUpdateSkill())
else:
    logging.info("Skill 'remote_update' desabilitada pela configuração.")

# Onboarding States
WAITING_NAME = 1
WAITING_SURNAME = 2
onboarding_states = {}

logging.info(f"Iniciando bot com provedor: {config.AI_PROVIDER}")

# _strip_unsupported_html is now provided by core.telegram_formatter (imported above).
# The local alias keeps backward compatibility with existing tests and call sites.
_strip_unsupported_html = _fmt_strip

# Security Filter
def is_authorized(user_id):
    return user_id == config.AUTHORIZED_USER_ID

# Authorized Check Handler
async def acesso_negado(update: Update):
    if not update.message:
        return
    await update.message.reply_text("⛔ Acesso negado. Este bot é privado.")

# Message Handler (AI)
async def responder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.from_user:
        return

    if memory_manager is None:
        logging.warning("responder: Tentativa de processar mensagem, mas memory_manager está desativado.")
        await update.message.reply_text(
            "⚠️ O sistema de memória e histórico está desativado. Por favor, ative-o nas configurações para conversar comigo."
        )
        return

    user_id = update.message.from_user.id

    if not is_authorized(user_id):
        await acesso_negado(update)
        return

    user_msg = update.message.text or ""
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
            welcome_back = "Entendido! Configuração concluída! Como posso ajudar hoje?"
            
            await update.message.reply_text(welcome_back)
            await memory_manager.log_message(user_id, "model", welcome_back)
            return
    # --- ONBOARDING FLOW END ---
    
    # 2. Retrieve Context (Structured Session Memory: Max 50 msgs in last 4 hours)
    context_history = await memory_manager.get_context(user_id, limit=50, minutes_ago=240)
    user_facts = await memory_manager.get_facts(user_id)
    assistant_surname = await memory_manager.get_fact_value(user_id, "assistant_surname") or ""

    # 3. Agent Brain Execution
    # Capture narrowed refs before closures (pyright doesn't carry narrowing into nested funcs)
    _msg = update.message
    _chat = update.effective_chat
    assert _chat is not None

    agent_context = {
        "user_id": user_id,
        "user_name": full_name,
        "user_facts": user_facts,
        "job_queue": context.job_queue,
        "assistant_surname": assistant_surname,
        "memory_manager": memory_manager,
        "raw_message": user_msg,
        "bot": context.bot,
        "chat_id": _chat.id,
    }

    async def keep_typing():
        """Sends TYPING action every 4s while the agent processes."""
        try:
            while True:
                await _chat.send_action("typing")
                await asyncio.sleep(4)
        except asyncio.CancelledError:
            pass

    async def intermediate_reply(text: str):
        """Callback to send preamble text before tool execution."""
        if text and text.strip():
            safe_text = TelegramFormatter.normalize(text.strip())
            try:
                await _msg.reply_text(safe_text, parse_mode=ParseMode.HTML)
            except TelegramError as e:
                logging.warning(f"Erro no intermediate_reply (HTML): {e}")
                try:
                    await _msg.reply_text(_strip_unsupported_html(safe_text), parse_mode=ParseMode.HTML)
                except TelegramError:
                    await _msg.reply_text(text.strip())
            except Exception as e:
                logging.error(f"Erro no intermediate_reply: {e}")

    async def direct_reply(html: str):
        """Callback para enviar HTML pré-formatado diretamente ao Telegram.
        Usado por skills que retornam direct_html, bypassando o LLM."""
        if not html:
            return
        try:
            await _msg.reply_text(html, parse_mode=ParseMode.HTML)
        except TelegramError as e:
            logging.warning(f"Erro no direct_reply (HTML): {e}")
            try:
                await _msg.reply_text(_strip_unsupported_html(html), parse_mode=ParseMode.HTML)
            except TelegramError:
                await _msg.reply_text(html)
        except Exception as e:
            logging.error(f"Erro no direct_reply: {e}")

    typing_task = asyncio.create_task(keep_typing())
    try:
        response_text = await brain.process(
            user_msg,
            agent_context,
            chat_history=context_history,
            on_intermediate_reply=intermediate_reply,
            on_direct_reply=direct_reply,
        )
    except Exception as e:
        logging.error(f"Brain Error: {e}")
        response_text = "Ocorreu um erro interno no meu cérebro. Tente novamente."
    finally:
        typing_task.cancel()

    # 4. Guard: if process() returned None, all content was already delivered via
    #    direct_html — no LLM follow-up needed.
    if response_text is None:
        return

    # 5. Log Response & Send
    response_text = TelegramFormatter.normalize(response_text)
    await memory_manager.log_message(user_id, "model", response_text)

    try:
        await _msg.reply_text(response_text, parse_mode=ParseMode.HTML)
    except TelegramError as e:
        logging.warning(f"Erro de parsing HTML: {e}")
        # Fallback: strip unsupported tags and retry with HTML
        clean_text = _strip_unsupported_html(response_text)
        try:
            await _msg.reply_text(clean_text, parse_mode=ParseMode.HTML)
        except TelegramError:
            # Last resort: send as plain text
            await _msg.reply_text(response_text)

# --- JOB QUEUE CALLBACKS ---
async def execute_reminder(context: ContextTypes.DEFAULT_TYPE):
    """Executes a scheduled reminder after verifying DB status.

    For recurring reminders: resets remind_at and reschedules instead of marking SENT.
    For is_task reminders: runs the message through the agent brain to trigger skills.
    """
    assert reminder_manager is not None  # job registered only when reminders enabled
    job = context.job
    if job is None:
        return
    chat_id = job.chat_id
    if chat_id is None:
        logging.error("execute_reminder: job has no chat_id")
        return

    reminder_data = job.data

    if not isinstance(reminder_data, dict):
        # Fallback for old plain-text jobs
        await context.bot.send_message(chat_id=chat_id, text=f"⏰ Lembrete: {reminder_data}")
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
            if memory_manager is None:
                logging.error(f"execute_reminder: Não foi possível executar a tarefa {reminder_id} porque memory_manager está desativado.")
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"⚠️ Erro ao executar tarefa agendada: {message}. O sistema de memória está desativado."
                )
                return
            user_facts = await memory_manager.get_facts(chat_id)
            assistant_surname = await memory_manager.get_fact_value(chat_id, "assistant_surname") or ""
            agent_context = {
                "user_id": chat_id,
                "user_name": "Usuário",
                "user_facts": user_facts,
                "job_queue": context.job_queue,
                "assistant_surname": assistant_surname,
                "memory_manager": memory_manager,
            }
            response_text = await brain.process(message, agent_context, chat_history=None)
            if response_text is None:
                response_text = ""
            response_text = TelegramFormatter.normalize(response_text)
            try:
                if response_text:
                    await context.bot.send_message(chat_id=chat_id, text=response_text, parse_mode=ParseMode.HTML)
            except TelegramError as e:
                logging.warning(f"Erro de parsing HTML via Reminder: {e}")
                clean_text = _strip_unsupported_html(response_text)
                try:
                    await context.bot.send_message(chat_id=chat_id, text=clean_text, parse_mode=ParseMode.HTML)
                except TelegramError:
                    await context.bot.send_message(chat_id=chat_id, text=response_text)
            except Exception as e:
                logging.error(f"Erro inesperado ao enviar mensagem de Task: {e}")
                raise e
        except Exception as e:
            task_error = True
            logging.error(f"Error executing task reminder {reminder_id}: {e}")
            try:
                await context.bot.send_message(chat_id=chat_id, text=f"⚠️ Erro ao executar tarefa agendada: {message}")
            except Exception as send_err:
                logging.error(f"Failed to notify user of task error for reminder {reminder_id}: {send_err}")
    else:
        try:
            await context.bot.send_message(chat_id=chat_id, text=f"⏰ Lembrete: {message}")
        except Exception as e:
            task_error = True
            logging.error(f"Error sending simple reminder {reminder_id}: {e}")

    # --- Reschedule or mark as sent ---
    if recurrence:
        next_time = reminder_manager._next_occurrence(recurrence, from_time=remind_at)
        await reminder_manager.reset_recurring_reminder(reminder_id, next_time)
        next_delay = (next_time - datetime.now()).total_seconds()
        assert context.job_queue is not None
        context.job_queue.run_once(
            execute_reminder,
            when=max(next_delay, 1),
            chat_id=chat_id,
            data={"id": reminder_id, "msg": message},
            name=f"reminder_{reminder_id}",
        )
        logging.info(f"Recurring reminder {reminder_id} rescheduled → {next_time}")
    if not recurrence and not task_error:
        await reminder_manager.mark_as_sent(reminder_id)

async def _send_proactive_message(context: ContextTypes.DEFAULT_TYPE, msg: str):
    """Helper to send a proactive message to the authorized user."""
    if config.AUTHORIZED_USER_ID == 0 or not msg:
        return
    safe_msg = TelegramFormatter.normalize(msg)
    try:
        await context.bot.send_message(
            chat_id=config.AUTHORIZED_USER_ID,
            text=safe_msg,
            parse_mode=ParseMode.HTML
        )
    except TelegramError:
        await context.bot.send_message(
            chat_id=config.AUTHORIZED_USER_ID,
            text=safe_msg
        )
    if memory_manager is not None:
        try:
            await memory_manager.log_message(config.AUTHORIZED_USER_ID, "model", msg)
        except Exception as e:
            logging.error(f"Erro ao salvar mensagem proativa no histórico: {e}")

async def system_heartbeat(context: ContextTypes.DEFAULT_TYPE):
    """
    Heartbeat + Reflection Loop.
    Logs status and checks if the Agent wants to speak proactively.

    When daily_briefing is enabled, the morning greeting is replaced by a
    full briefing (weather + calendar + news) composed by the LLM.
    """
    logging.info("💓 Status Heartbeat: Online.")

    if not config.REFLECTION_ENABLED:
        return

    try:
        now = datetime.now()
        current_hour = now.hour
        greeting_start = config.REFLECTION_GREETING_HOUR_START
        greeting_end = config.REFLECTION_GREETING_HOUR_END
        is_greeting_window = greeting_start <= current_hour < greeting_end
        already_greeted = brain._last_greeting_date == now.date()

        # ── Daily Briefing (replaces simple greeting) ─────────────────
        if (
            is_greeting_window
            and not already_greeted
            and config.skill_enabled("daily_briefing")
            and daily_briefing_skill is not None
        ):
            logging.info("📋 Daily Briefing: gathering data...")
            briefing_ctx = {"user_id": config.AUTHORIZED_USER_ID}

            # Resolve user name for personalized greeting
            user_name = ""
            if memory_manager is not None:
                user_name = await memory_manager.get_fact_value(
                    config.AUTHORIZED_USER_ID, "personal_name"
                ) or ""

            briefing_result = await daily_briefing_skill.execute(briefing_ctx)
            briefing_data = briefing_result.get("data", {}) if briefing_result.get("status") == "success" else {}

            msg = await brain.compose_briefing(briefing_data, user_name=user_name)
            if msg:
                logging.info(f"📋 Daily Briefing sent: {msg[:80]}...")
                brain._last_greeting_date = now.date()
                await _send_proactive_message(context, msg)
                return  # Skip normal reflect — briefing already includes greeting

        # ── Normal Reflection (hardware alerts, simple greeting, etc.) ──
        hw_metrics: dict = {}
        if hardware_skill is not None:
            hw_status = await hardware_skill.execute({})
            hw_metrics = hw_status.get("metrics", {})

        reflection_context = {
            "time": now.strftime("%Y-%m-%d %H:%M:%S"),
            "hour": now.hour,
            "hardware": hw_metrics,
        }

        msg = await brain.reflect(reflection_context)

        if msg:
            logging.info(f"🔔 Proactive Reflection Triggered: {msg}")
            await _send_proactive_message(context, msg)
        else:
            logging.info("🤫 Reflection: SILENCE")

    except Exception as e:
        logging.error(f"Heartbeat Reflection Error: {e}")

async def check_token_health(context: ContextTypes.DEFAULT_TYPE):
    """
    Health check job for Google OAuth credentials.

    Runs daily at 8 AM to validate token integrity and alert user
    if re-authentication is needed.
    """
    from core.credential_manager import load_google_credentials
    from core.audit_logger import AuditLogger

    logger = logging.getLogger("token_health")
    audit = AuditLogger()

    try:
        creds = load_google_credentials()

        if not creds:
            # Token missing
            logger.warning("Token health check: No credentials found")
            audit.log_event("token_health_check", user_id=0, success=False, details={
                "status": "missing",
                "action_required": "user_reauth"
            })

            # Notify user via Telegram
            if config.AUTHORIZED_USER_ID != 0:
                await context.bot.send_message(
                    chat_id=config.AUTHORIZED_USER_ID,
                    text="⚠️ Google Calendar não autenticado\n\nUse /setup_calendar para reconectar."
                )
            return

        if not creds.valid:
            if creds.expired and creds.refresh_token:
                # Expired but recoverable (auto-refresh will handle)
                logger.info("Token expired but refresh_token present (OK)")
                audit.log_event("token_health_check", user_id=0, success=True, details={
                    "status": "expired_recoverable"
                })
            else:
                # Invalid and no refresh token (critical)
                logger.error("Token invalid and no refresh_token (BAD)")
                audit.log_event("token_health_check", user_id=0, success=False, details={
                    "status": "invalid_unrecoverable",
                    "action_required": "user_reauth"
                })

                # Notify user via Telegram
                if config.AUTHORIZED_USER_ID != 0:
                    await context.bot.send_message(
                        chat_id=config.AUTHORIZED_USER_ID,
                        text="❌ Google Calendar: token inválido\n\nSuas credenciais expiraram. Use /setup_calendar para autenticar novamente."
                    )
        else:
            # Healthy
            logger.debug("Token health check: OK")
            audit.log_event("token_health_check", user_id=0, success=True, details={"status": "healthy"})

    except Exception as e:
        logger.error(f"Token health check failed: {e}")

async def post_init(application: Application):
    if memory_manager is not None:
        await memory_manager.init_db()
    # Start MCP Clients
    await brain.start_mcp_clients()

    # Remote Update: check for post-restart sentinel and notify user if found
    from skills.remote_update import check_update_sentinel
    await check_update_sentinel(application.bot, config.AUTHORIZED_USER_ID)
    
    if application.job_queue:
        # System Heartbeat
        application.job_queue.run_repeating(system_heartbeat, interval=config.HEARTBEAT_INTERVAL, first=10, name="system_heartbeat")

        # Recover Persisted Reminders
        if reminder_manager is not None:
            try:
                logging.info("Recuperando lembretes persistentes...")
                reminder_manager._execute_reminder_callback = execute_reminder
                await reminder_manager.recover_reminders(application.job_queue)
            except Exception as e:
                logging.error(f"Erro ao recuperar lembretes: {e}")

        # Google Calendar Sync
        if config.GCAL_CLIENT_ID and config.GCAL_CLIENT_SECRET:
            sync_interval = config.GCAL_SYNC_INTERVAL_MINUTES * 60
            async def _calendar_sync_job(context: ContextTypes.DEFAULT_TYPE) -> None:
                await run_calendar_sync(config.AUTHORIZED_USER_ID)

            application.job_queue.run_repeating(
                _calendar_sync_job,
                interval=sync_interval,
                first=60,  # First sync after 1 minute
                name="calendar_sync"
            )
            logging.info(f"Calendar sync job agendado (intervalo: {config.GCAL_SYNC_INTERVAL_MINUTES} minutos)")

            # Google Calendar Token Health Check (daily at 8 AM)
            application.job_queue.run_daily(
                check_token_health,
                time=datetime.strptime("08:00", "%H:%M").time(),
                name="token_health_check"
            )
            logging.info("Token health check job agendado (diário às 8:00)")

        # Pattern Analysis (sugestões proativas de automação)
        if config.skill_enabled("pattern_analysis") and memory_manager is not None:
            from skills.pattern_analyzer import run_pattern_check as _run_pattern_check

            async def _pattern_check_job(context: ContextTypes.DEFAULT_TYPE):
                try:
                    messages = await _run_pattern_check(
                        config.AUTHORIZED_USER_ID, memory_manager, config
                    )
                    for msg in messages:
                        await _send_proactive_message(context, msg)
                except Exception as e:
                    logging.error(f"Pattern check error: {e}")

            pattern_interval = config.PATTERN_CHECK_INTERVAL_HOURS * 3600
            application.job_queue.run_repeating(
                _pattern_check_job,
                interval=pattern_interval,
                first=120,  # 2 min após startup (evita race com DB init)
                name="pattern_check"
            )
            logging.info(
                f"Pattern analysis job agendado "
                f"(intervalo: {config.PATTERN_CHECK_INTERVAL_HOURS}h)"
            )

        logging.info("Jobs agendados: Heartbeat + Lembretes + Calendar Sync + Token Health + Pattern Analysis")
    else:
        logging.error("JobQueue não está disponível!")

# Status Command (Automation)
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.from_user:
        return
    if not is_authorized(update.message.from_user.id):
        await acesso_negado(update)
        return

    provider_status = f"IA: {config.AI_PROVIDER.upper()}"
    await update.message.reply_text(f"✅ Sistema Online e você está autenticado! (Agentic Mode)\n{provider_status}")

def run_pre_start_checks() -> bool:
    """Executa verificações de configuração e ambiente antes de iniciar a Aplicação."""
    if not config.TELEGRAM_TOKEN:
        logging.error("❌ TELEGRAM_TOKEN ausente na configuração. O bot não pode iniciar.")
        return False
        
    from core import health
    diag = health.run_full_diagnostic()
    if diag["status"] == "critical":
        logging.error("❌ STATUS CRÍTICO NO HEALTH CHECK: " + "; ".join(diag["issues"]))
        print("Erro: Falha crítica na configuração. Verifique os logs.")
        return False
    elif diag["status"] == "warning":
        logging.warning("⚠️ HEALTH CHECK (AVISOS): " + "; ".join(diag["issues"]))
    else:
        logging.info("✅ Health Check: Sistema Saudável.")
    
    return True

def main():
    if not run_pre_start_checks():
        return

    assert config.TELEGRAM_TOKEN, "TELEGRAM_TOKEN must be set (validated in run_pre_start_checks)"
    app = ApplicationBuilder().token(config.TELEGRAM_TOKEN).post_init(post_init).build()
    
    app.add_handler(CommandHandler("status", status))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), responder))
    
    print(f"Bot Curupira iniciado com trava de segurança! Provedor: {config.AI_PROVIDER}")
    app.run_polling()

if __name__ == '__main__':
    main()

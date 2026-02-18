import aiosqlite
import logging
from datetime import datetime, timedelta
import dateparser
from skills.memory import DB_FILE

class ReminderManager:
    def __init__(self, db_path=DB_FILE):
        self.db_path = db_path
        self.logger = logging.getLogger("ReminderManager")

    async def add_reminder(self, user_id, message, delay_seconds):
        """Saves a reminder to the database and returns its ID."""
        remind_at = datetime.now() + timedelta(seconds=delay_seconds)
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO reminders (user_id, message, remind_at, created_at, status)
                VALUES (?, ?, ?, ?, 'PENDING')
            """, (user_id, message, remind_at, datetime.now()))
            await db.commit()
            self.logger.info(f"Reminder saved for user {user_id} at {remind_at}")
            return cursor.lastrowid

    async def get_active_reminders(self, user_id):
        """Returns a list of active (PENDING) reminders for a user."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("""
                SELECT id, message, remind_at FROM reminders
                WHERE user_id = ? AND status = 'PENDING'
                ORDER BY remind_at ASC
            """, (user_id,)) as cursor:
                rows = await cursor.fetchall()
                return rows

    async def delete_reminder(self, reminder_id, user_id):
        """Marks a reminder as CANCELLED."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE reminders SET status = 'CANCELLED'
                WHERE id = ? AND user_id = ?
            """, (reminder_id, user_id))
            await db.commit()
            self.logger.info(f"Reminder {reminder_id} cancelled.")

    async def update_reminder(self, reminder_id, user_id, message=None, delay_seconds=None):
        """Updates a reminder's message and/or trigger time."""
        updates = []
        params = []
        new_remind_at = None
        
        if message is not None:
            updates.append("message = ?")
            params.append(message)
            
        if delay_seconds is not None:
            new_remind_at = datetime.now() + timedelta(seconds=delay_seconds)
            updates.append("remind_at = ?")
            params.append(new_remind_at)
            
        if not updates:
            return None

        params.append(reminder_id)
        params.append(user_id)
        
        query = f"UPDATE reminders SET {', '.join(updates)} WHERE id = ? AND user_id = ? AND status = 'PENDING'"
        
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(query, tuple(params))
            await db.commit()
            
            if cursor.rowcount > 0:
                self.logger.info(f"Reminder {reminder_id} updated.")
                return new_remind_at if delay_seconds is not None else True
            return False

    async def mark_as_sent(self, reminder_id):
        """Marks a reminder as SENT."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("UPDATE reminders SET status = 'SENT' WHERE id = ?", (reminder_id,))
            await db.commit()

    async def get_reminder_status(self, reminder_id):
        """Checks if a reminder is still PENDING."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT status FROM reminders WHERE id = ?", (reminder_id,)) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else None

    async def get_reminder_message(self, reminder_id):
        """Fetches the current message for a reminder."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT message FROM reminders WHERE id = ?", (reminder_id,)) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else None


    async def recover_reminders(self, job_queue):
        """Recovers pending reminders on startup and reschedules them."""
        self.logger.info("Recovering pending reminders...")
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("""
                SELECT id, user_id, message, remind_at FROM reminders
                WHERE status = 'PENDING'
            """) as cursor:
                rows = await cursor.fetchall()
                
                now = datetime.now()
                for row in rows:
                    reminder_id, user_id, message, remind_at_iso = row
                    # aiosqlite returns datetime objects for DATETIME columns usually, but let's be safe
                    if isinstance(remind_at_iso, str):
                        remind_at = datetime.fromisoformat(remind_at_iso)
                    else:
                        remind_at = remind_at_iso
                        
                    delay = (remind_at - now).total_seconds()
                    
                    if delay > 0:
                        # Schedule with ID in data
                        job_queue.run_once(
                            self._execute_reminder_callback, 
                            when=delay, 
                            chat_id=user_id, 
                            data={"id": reminder_id, "msg": message},
                            name=f"reminder_{reminder_id}"
                        )
                        self.logger.info(f"Rescheduled reminder {reminder_id} for {delay:.1f}s")
                    else:
                        # Expired while offline
                        # We send it immediately but mark it
                        job_queue.run_once(
                            self._execute_reminder_callback,
                            when=1, 
                            chat_id=user_id,
                            data={"id": reminder_id, "msg": f"{message} (Atrasado - estava offline)"},
                            name=f"reminder_{reminder_id}"
                        )
                        self.logger.warning(f"Reminder {reminder_id} was expired, sending immediately.")

    # We need a static wrapper because JobQueue callbacks are rigid
    # Alternatively, we can import this function in bot.py
    async def _execute_reminder_callback(self, context):
        """Internal callback for consistency, but likely we'll use the one in bot.py"""
        pass

# --- Skills Adapters ---
from .base import BaseSkill
from typing import Any, Dict, Optional, List

class AddReminderSkill(BaseSkill):
    def __init__(self, manager: ReminderManager):
        self.manager = manager
    
    @property
    def name(self) -> str:
        return "add_reminder"
    
    @property
    def display_name(self) -> str:
        return "📝 Criar Lembrete"
    
    @property
    def description(self) -> str:
        return "Agendar um novo lembrete. Use quando o usuário pedir para ser lembrado de algo no futuro."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "O conteúdo do lembrete. O que deve ser lembrado."
                },
                "when": {
                    "type": "string",
                    "description": "Quando lembrar? Ex: '10m', 'amanhã 9h', '14:00', '2026-02-10 10:00'. Se for apenas número, será considerado minutos."
                }
            },
            "required": ["message", "when"]
        }
    
    def _preprocess_time_string(self, text: str) -> str:
        """
        Pre-processes natural language time strings to fix common parser ambiguities.

        Examples:
        - "amanhã as 10h" -> "amanhã às 10:00" (forces absolute time)
        - "as 10" -> "às 10:00"
        - "as 10h30" -> Unchanged (handled by dateparser)
        - "toda manhã" / "de manhã" -> "amanhã às 08:00"
        - "toda tarde" / "de tarde" -> "amanhã às 14:00"
        - "toda noite" / "de noite" -> "amanhã às 20:00"
        """
        import re
        # Map period-of-day expressions to a concrete time (preserves any leading date word)
        _PERIOD_MAP = [
            (r'(?i)\b(?:toda\s+)?manh[aã]\b', '08:00'),
            (r'(?i)\b(?:toda\s+)?tarde\b', '14:00'),
            (r'(?i)\b(?:toda\s+)?noite\b', '20:00'),
        ]
        for pattern, time_str in _PERIOD_MAP:
            if re.search(pattern, text):
                text = re.sub(pattern, f'amanhã às {time_str}', text)
                break  # A reminder has a single target time; stop at the first period match

        # Convert "as 10h", "às 10", "at 10H" to "às 10:00"
        # Uses logical grouping to match '10', '10h', '10 h' but avoid '10h30'
        text = re.sub(r'(?i)\b(?:as|às|at)\s+(\d{1,2})(?:\s*[hH])?\b', r'às \1:00', text)

        # Cleanup for better dateparser compatibility in PT-BR
        # Remove "na ", "no ", "em " at start or after space
        text = re.sub(r'(?i)\b(?:na|no|em)\s+', '', text)
        
        # Remove " feira" (optional)
        text = re.sub(r'(?i)\s+feira\b', '', text)
        
        # Remove "próxima " (let dateparser handle future preference)
        text = re.sub(r'(?i)\bpróxima\s+', '', text)
        
        return text

    async def execute(self, context: Dict[str, Any], message: str, when: str) -> Dict[str, Any]:
        """Executes the add_reminder skill.

        Args:
            context: The execution context containing 'user_id' and 'job_queue'.
            message: The reminder message.
            when: Time string (relative or absolute).

        Returns:
            Dict containing the status and info of the created reminder.
        """
        user_id = context.get('user_id')
        if not user_id:
             return {"error": "User ID not found in context."}
             
        try:
            # Parse 'when'
            now = datetime.now()
            target_time = None
            delay_minutes_display = 0
            
            # 1. Try simple integer (legacy/minutes)
            if when.isdigit():
                minutes = int(when)
                target_time = now + timedelta(minutes=minutes)
                delay_minutes_display = minutes
            else:
                # 2. Use dateparser for natural language
                # Pre-process to fix ambiguities
                when_fixed = self._preprocess_time_string(when)
                if when_fixed != when:
                    self.manager.logger.info(f"Fixed time string: '{when}' -> '{when_fixed}'")
                
                # settings={'PREFER_DATES_FROM': 'future', 'DATE_ORDER': 'DMY'}
                target_time = dateparser.parse(when_fixed, settings={'PREFER_DATES_FROM': 'future', 'DATE_ORDER': 'DMY'})
            
            if not target_time:
                return {"error": f"Não entendi a data/hora: '{when}'. Tente algo como '10 minutos' ou '14:00'."}
            
            # Validation: Block past dates (allow 1 min grace period for processing)
            if target_time < now - timedelta(minutes=1):
                friendly = target_time.strftime('%d/%m %H:%M')
                return {"error": f"O horário {friendly} já passou. Por favor, escolha um horário futuro."}
                
            # Calculate delay in seconds
            delay_seconds = (target_time - now).total_seconds()
            
            if delay_seconds < 0:
                 # Check if it was a small slip (e.g. "now" parsed as slightly past)
                 if delay_seconds > -60:
                     delay_seconds = 0
                 else:
                     return {"error": f"O horário {target_time.strftime('%d/%m %H:%M')} já passou."}

            delay_minutes_display = int(delay_seconds / 60)
            
            # --- Persist to DB ---
            r_id = await self.manager.add_reminder(user_id, message, delay_seconds)
            
            # --- Schedule Job ---
            job_queue = context.get('job_queue')
            if job_queue:
                callback = self.manager._execute_reminder_callback
                if callback:
                    job_queue.run_once(
                        callback, 
                        when=delay_seconds, 
                        chat_id=user_id, 
                        data={"id": r_id, "msg": message},
                        name=f"reminder_{r_id}"
                    )
                else:
                    self.manager.logger.warning("Reminder callback not found, job not scheduled in memory.")
            else:
                self.manager.logger.warning("JobQueue not found in context, reminder saved but not scheduled in memory.")
            
            # Feedback Message
            target_str = target_time.strftime('%H:%M')
            if target_time.date() != now.date():
                target_str = target_time.strftime('%d/%m às %H:%M')
                
            info_msg = f"Lembrete criado para {target_str}: '{message}'."
            if delay_seconds < 5:
                info_msg = f"Disparando lembrete agora mesmo: '{message}'!"
            
            return {
                "status": "success", 
                "reminder_id": r_id, 
                "message": message, 
                "target_time": target_str,
                "info": info_msg
            }
        except Exception as e:
            self.manager.logger.error(f"Error adding reminder: {e}")
            return {"error": str(e)}

class ListRemindersSkill(BaseSkill):
    def __init__(self, manager: ReminderManager):
        self.manager = manager
    
    @property
    def name(self) -> str:
        return "list_reminders"
    
    @property
    def display_name(self) -> str:
        return "📋 Listar Lembretes"
    
    @property
    def description(self) -> str:
        return "Listar os lembretes pendentes agendados para o usuário atual."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {"type": "object", "properties": {}}
    
    def _format_friendly_date(self, dt: datetime) -> str:
        """Helper to format datetime into a friendly string."""
        now = datetime.now()
        diff = dt.date() - now.date()
        time_str = dt.strftime('%H:%M')
        
        if diff.days == 0:
            day_str = "hoje"
        elif diff.days == 1:
            day_str = "amanhã"
        else:
            day_str = f"dia {dt.strftime('%d/%m')}"
            
        return f"{day_str} às {time_str}"

    async def execute(self, context: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        Lists pending reminders for the user.
        
        Args:
            context: The execution context.
            **kwargs: Ignored extra arguments (prevents crashes from hallucinations).

        Returns:
            Dict containing the list of reminders and count.
        """
        user_id = context.get('user_id')
        if not user_id: return {"error": "User ID missing"}
        
        try:
            reminders = await self.manager.get_active_reminders(user_id)
            if not reminders:
                return {
                    "reminders": [], 
                    "count": 0, 
                    "info": "Nenhum lembrete pendente encontrado. A lista está vazia."
                }
                
            # Filter valid rows and format
            formatted_reminders = []
            
            for r in reminders:
                if len(r) != 3:
                     self.manager.logger.warning(f"Skipping invalid reminder row: {r}")
                     continue
                     
                r_id, msg, at_dt = r
                
                # Normalize to datetime
                if isinstance(at_dt, str):
                    try:
                        at_dt = datetime.fromisoformat(at_dt)
                    except ValueError:
                        self.manager.logger.warning(f"Invalid date format for reminder {r_id}: {at_dt}")
                        continue
                
                if not isinstance(at_dt, datetime):
                    continue

                friendly_date = self._format_friendly_date(at_dt)
                    
                formatted_reminders.append({
                "id": r_id, 
                "message": msg, 
                "at": friendly_date
                })
                
            # Create a bullet list for the LLM to use directly
            if not formatted_reminders:
                 summary = "Você não tem lembretes pendentes."
            else:
                 lines = [f"Você tem {len(formatted_reminders)} lembrete(s) pendente(s):"]
                 for r in formatted_reminders:
                     lines.append(f"* [ID {r['id']}] {r['message']} (para {r['at']})")
                 summary = "\n".join(lines)
            
            return {
                "reminders": formatted_reminders,
                "count": len(formatted_reminders),
                "summary": summary
            }
        except Exception as e:
             self.manager.logger.error(f"Error listing reminders: {e}")
             return {"error": str(e)}

class DeleteReminderSkill(BaseSkill):
    def __init__(self, manager: ReminderManager):
        self.manager = manager

    @property
    def name(self) -> str:
        return "delete_reminder"

    @property
    def display_name(self) -> str:
        return "🗑️ Deletar Lembrete"

    @property
    def description(self) -> str:
        return "Cancelar/Deletar um lembrete existente pelo ID. Use list_reminders primeiro se não souber o ID."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "reminder_id": {"type": "integer", "description": "O ID do lembrete a ser removido."}
            },
            "required": ["reminder_id"]
        }

    async def execute(self, context: Dict[str, Any], reminder_id: int) -> Dict[str, Any]:
        """Executes the delete_reminder skill.

        Args:
            context: The execution context.
            reminder_id: The ID of the reminder to delete.

        Returns:
            Dict indicating success or failure.
        """
        user_id = context.get('user_id')
        if not user_id: return {"error": "User ID missing"}
        
        try:
            # Type safety
            rid = int(reminder_id)
            
            await self.manager.delete_reminder(rid, user_id)
            
            # Cancel Job gracefully
            job_queue = context.get('job_queue')
            if job_queue:
                try:
                    job_name = f"reminder_{rid}"
                    jobs = job_queue.get_jobs_by_name(job_name)
                    if jobs:
                        for job in jobs:
                            job.schedule_removal()
                except Exception as je:
                    self.manager.logger.warning(f"Could not remove job from queue: {je}")
                    
            return {"status": "success", "deleted_id": rid, "info": f"Lembrete {rid} cancelado."}
        except ValueError:
            return {"error": "Invalid reminder_id format"}
        except Exception as e:
            return {"error": str(e)}

class UpdateReminderSkill(BaseSkill):
    def __init__(self, manager: ReminderManager):
        self.manager = manager

    @property
    def name(self) -> str:
        return "update_reminder"

    @property
    def display_name(self) -> str:
        return "✏️ Atualizar Lembrete"

    @property
    def description(self) -> str:
        return "Atualizar um lembrete existente (texto ou data/hora)."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "reminder_id": {"type": "integer", "description": "ID do lembrete."},
                "new_message": {"type": "string", "description": "Novo texto para o lembrete (opcional)."},
                "new_delay_minutes": {"type": "integer", "description": "Novo tempo de espera em minutos a partir de agora (opcional)."}
            },
            "required": ["reminder_id"]
        }

    async def execute(self, context: Dict[str, Any], reminder_id: int, new_message: Optional[str] = None, new_delay_minutes: Optional[int] = None) -> Dict[str, Any]:
         """Executes the update_reminder skill.

         Args:
             context: The execution context.
             reminder_id: ID of the reminder.
             new_message: Optional new message.
             new_delay_minutes: Optional new delay in minutes.

         Returns:
             Dict with update status.
         """
         user_id = context.get('user_id')
         if not user_id: return {"error": "User ID missing"}
         
         try:
             rid = int(reminder_id)
             delay_seconds = None
             if new_delay_minutes is not None:
                 delay_seconds = int(new_delay_minutes) * 60
             
             result = await self.manager.update_reminder(rid, user_id, new_message, delay_seconds)
             
             if not result:
                 return {"error": "Reminder not found or update failed (maybe it's not pending?)"}
                 
             # Reschedule if needed
             if delay_seconds is not None:
                 job_queue = context.get('job_queue')
                 if job_queue:
                     try:
                         # Cancel old
                         job_name = f"reminder_{rid}"
                         jobs = job_queue.get_jobs_by_name(job_name)
                         for job in jobs: job.schedule_removal()
                         
                         # Schedule new
                         callback = self.manager._execute_reminder_callback
                         if callback:
                             msg_to_use = new_message or "FETCH_FROM_DB"
                             if msg_to_use == "FETCH_FROM_DB":
                                 saved_msg = await self.manager.get_reminder_message(rid)
                                 msg_to_use = saved_msg or "Lembrete"

                             job_queue.run_once(
                                 callback, 
                                 when=delay_seconds, 
                                 chat_id=user_id, 
                                 data={"id": rid, "msg": msg_to_use}, 
                                 name=job_name
                             )
                     except Exception as je:
                         self.manager.logger.warning(f"Error rescheduling job: {je}")
                         
             return {"status": "success", "updated_id": rid, "info": "Lembrete atualizado."}
         except ValueError:
             return {"error": "Invalid input format (integers required for ID/minutes)"}
         except Exception as e:
             return {"error": str(e)}

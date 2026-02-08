import aiosqlite
import logging
from datetime import datetime, timedelta
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
                "delay_minutes": {
                    "type": "integer",
                    "description": "Tempo de espera até o lembrete disparar, em minutos."
                }
            },
            "required": ["message", "delay_minutes"]
        }
    
    async def execute(self, context: Dict[str, Any], message: str, delay_minutes: int) -> Dict[str, Any]:
        """Executes the add_reminder skill.

        Args:
            context: The execution context containing 'user_id' and 'job_queue'.
            message: The reminder message.
            delay_minutes: The delay in minutes.

        Returns:
            Dict containing the status and info of the created reminder.
        """
        user_id = context.get('user_id')
        if not user_id:
             return {"error": "User ID not found in context."}
             
        try:
            # Ensure delay_minutes is an integer to avoid calculation errors
            minutes = int(delay_minutes)
            delay_seconds = minutes * 60
            
            r_id = await self.manager.add_reminder(user_id, message, delay_seconds)
            
            # Schedule Job
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
            
            return {
                "status": "success", 
                "reminder_id": r_id, 
                "message": message, 
                "delay_minutes": minutes,
                "info": f"Lembrete criado: '{message}' em {minutes} minutos."
            }
        except ValueError as ve:
            self.manager.logger.error(f"Value error in add_reminder: {ve}")
            return {"error": f"Invalid input: {ve}"}
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
    def description(self) -> str:
        return "Listar os lembretes pendentes agendados para o usuário atual."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {"type": "object", "properties": {}}
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Executes the list_reminders skill.

        Args:
            context: The execution context.

        Returns:
            Dict containing the list of reminders and count.
        """
        user_id = context.get('user_id')
        if not user_id: return {"error": "User ID missing"}
        
        try:
            reminders = await self.manager.get_active_reminders(user_id)
            if not reminders:
                return {"reminders": [], "info": "Você não tem lembretes pendentes.", "count": 0}
                
            # Filter valid rows and format
            formatted_reminders = []
            for r in reminders:
                if len(r) >= 3:
                     r_id, msg, at_dt = r
                     
                     # Safe ISO format conversion
                     at_str = str(at_dt)
                     if hasattr(at_dt, 'isoformat'):
                         at_str = at_dt.isoformat()
                         
                     formatted_reminders.append({
                        "id": r_id, 
                        "message": msg, 
                        "at": at_str
                     })
                
            return {
                "reminders": formatted_reminders,
                "count": len(formatted_reminders)
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

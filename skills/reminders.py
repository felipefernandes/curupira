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
from typing import Any, Dict

class AddReminderSkill(BaseSkill):
    def __init__(self, manager: ReminderManager):
        self.manager = manager
    
    @property
    def name(self) -> str:
        return "add_reminder"
    
    @property
    def description(self) -> str:
        return "Agendar um novo lembrete para o usuário."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "O conteúdo do lembrete (ex: 'Tomar remédio', 'Reunião')."
                },
                "delay_minutes": {
                    "type": "integer",
                    "description": "Daqui a quantos minutos o lembrete deve ser enviado."
                }
            },
            "required": ["message", "delay_minutes"]
        }
    
    async def execute(self, context: Dict[str, Any], message: str, delay_minutes: int) -> Dict[str, Any]:
        user_id = context.get('user_id')
        if not user_id:
             return {"error": "User ID not found in context."}
             
        delay_seconds = delay_minutes * 60
        r_id = await self.manager.add_reminder(user_id, message, delay_seconds)
        
        # We need to return info so the Agent can inform the user AND maybe schedule the job?
        # The JobQueue scheduling was in bot.py. 
        # The ReminderManager only saves to DB.
        # We need to trigger the job scheduling. 
        # Ideally, ReminderManager or this Skill should handle it.
        # Since JobQueue is in bot context, we might need access to it via context?
        # Or returns a special instruction?
        # Let's assume for now the Brain handles the response, but the SCHEDULING needs to happen.
        # If ReminderManager had access to JobQueue (passed in init?), it could do it.
        # But ReminderManager is initialized in bot.py without JobQueue (initially). It has recover_reminders(job_queue).
        # We should pass JobQueue to ReminderManager or the Skill. 
        # Context can have 'job_queue'.
        
        job_queue = context.get('job_queue')
        if job_queue:
            # We need the callback function. 
            # Ideally ReminderManager has it or we import it. 
            # For now, let's use the internal callback if available or fail gracefully.
            # actually bot.py's execute_reminder is the one.
            # Let's try to get it from context or use a generic one if possible.
            # Simplest: The AgentBrain can return a "Side Effect" request? 
            # No, keep it simple. The Skill does the job.
            
            # We need to import execute_reminder from bot? No, circular import.
            # ReminderManager has `_execute_reminder_callback` which is a placeholder.
            # In bot.py, we assigned it! `reminder_manager._execute_reminder_callback = execute_reminder`.
            # So we can use that!
            
            callback = self.manager._execute_reminder_callback
            if callback:
                job_queue.run_once(
                    callback, 
                    when=delay_seconds, 
                    chat_id=user_id, 
                    data={"id": r_id, "msg": message},
                    name=f"reminder_{r_id}"
                )
        
        return {"status": "success", "reminder_id": r_id, "message": message, "delay_minutes": delay_minutes}

class ListRemindersSkill(BaseSkill):
    def __init__(self, manager: ReminderManager):
        self.manager = manager
    
    @property
    def name(self) -> str:
        return "list_reminders"
    
    @property
    def description(self) -> str:
        return "Listar os lembretes pendentes ativos."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {"type": "object", "properties": {}}
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        user_id = context.get('user_id')
        if not user_id: return {"error": "User ID missing"}
        
        reminders = await self.manager.get_active_reminders(user_id)
        if not reminders:
            return {"reminders": []}
            
        # Format for LLM consumption
        return {
            "reminders": [
                {"id": r[0], "message": r[1], "at": r[2].isoformat() if hasattr(r[2], 'isoformat') else str(r[2])}
                for r in reminders
            ]
        }

class DeleteReminderSkill(BaseSkill):
    def __init__(self, manager: ReminderManager):
        self.manager = manager

    @property
    def name(self) -> str:
        return "delete_reminder"

    @property
    def description(self) -> str:
        return "Cancelar/Deletar um lembrete existente pelo ID."

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
        user_id = context.get('user_id')
        if not user_id: return {"error": "User ID missing"}
        
        await self.manager.delete_reminder(reminder_id, user_id)
        
        # Cancel Job
        job_queue = context.get('job_queue')
        if job_queue:
            jobs = job_queue.get_jobs_by_name(f"reminder_{reminder_id}")
            for job in jobs:
                job.schedule_removal()
                
        return {"status": "success", "deleted_id": reminder_id}

class UpdateReminderSkill(BaseSkill):
    def __init__(self, manager: ReminderManager):
        self.manager = manager

    @property
    def name(self) -> str:
        return "update_reminder"

    @property
    def description(self) -> str:
        return "Atualizar um lembrete existente (texto ou data)."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "reminder_id": {"type": "integer", "description": "ID do lembrete."},
                "new_message": {"type": "string", "description": "Novo texto (opcional)."},
                "new_delay_minutes": {"type": "integer", "description": "Novos minutos a partir de agora (opcional)."}
            },
            "required": ["reminder_id"]
        }

    async def execute(self, context: Dict[str, Any], reminder_id: int, new_message: str = None, new_delay_minutes: int = None) -> Dict[str, Any]:
         user_id = context.get('user_id')
         if not user_id: return {"error": "User ID missing"}
         
         delay_seconds = new_delay_minutes * 60 if new_delay_minutes is not None else None
         
         result = await self.manager.update_reminder(reminder_id, user_id, new_message, delay_seconds)
         
         if not result:
             return {"error": "Reminder not found or update failed"}
             
         # Reschedule if needed
         if delay_seconds is not None:
             job_queue = context.get('job_queue')
             if job_queue:
                 # Cancel old
                 jobs = job_queue.get_jobs_by_name(f"reminder_{reminder_id}")
                 for job in jobs: job.schedule_removal()
                 
                 # Schedule new
                 callback = self.manager._execute_reminder_callback
                 if callback:
                     job_queue.run_once(
                         callback, 
                         when=delay_seconds, 
                         chat_id=user_id, 
                         data={"id": reminder_id, "msg": new_message or "FETCH_FROM_DB"}, 
                         name=f"reminder_{reminder_id}"
                     )
                     
         return {"status": "success", "updated_id": reminder_id}

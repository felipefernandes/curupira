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

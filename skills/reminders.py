import aiosqlite
import logging
import random
import re
from datetime import datetime, timedelta
from typing import Optional, Tuple
import dateparser
from skills.memory import DB_FILE
import html

class ReminderManager:
    def __init__(self, db_path=DB_FILE):
        self.db_path = db_path
        self.logger = logging.getLogger("ReminderManager")

    async def add_reminder(self, user_id, message, delay_seconds, recurrence=None, is_task=False):
        """Saves a reminder to the database and returns its ID."""
        remind_at = datetime.now() + timedelta(seconds=delay_seconds)
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("""
                    INSERT INTO reminders (user_id, message, remind_at, created_at, status, recurrence, is_task)
                    VALUES (?, ?, ?, ?, 'PENDING', ?, ?)
                """, (user_id, message, remind_at, datetime.now(), recurrence, 1 if is_task else 0))
                await db.commit()
                self.logger.info(f"Reminder saved for user {user_id} at {remind_at} (recurrence={recurrence}, is_task={is_task})")
                return cursor.lastrowid
        except Exception as e:
            self.logger.error(f"DB error saving reminder for user {user_id}: {e}")
            raise

    async def get_active_reminders(self, user_id):
        """Returns a list of active (PENDING) reminders for a user."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("""
                    SELECT id, message, remind_at, recurrence, is_task FROM reminders
                    WHERE user_id = ? AND status = 'PENDING'
                    ORDER BY id ASC
                """, (user_id,)) as cursor:
                    rows = await cursor.fetchall()
                    return rows
        except Exception as e:
            self.logger.error(f"DB error fetching active reminders for user {user_id}: {e}")
            return []

    async def get_reminder_recurrence(self, reminder_id) -> Tuple[Optional[str], bool, Optional[datetime]]:
        """Returns (recurrence_str, is_task, remind_at) for a reminder."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(
                    "SELECT recurrence, is_task, remind_at FROM reminders WHERE id = ?", (reminder_id,)
                ) as cursor:
                    row = await cursor.fetchone()
                    if not row:
                        return None, False, None
                    remind_at = None
                    if row[2]:
                        if isinstance(row[2], str):
                            try:
                                remind_at = datetime.fromisoformat(row[2])
                            except ValueError:
                                pass
                        elif isinstance(row[2], datetime):
                            remind_at = row[2]
                    return row[0], bool(row[1]), remind_at
        except Exception as e:
            self.logger.error(f"DB error fetching recurrence for reminder {reminder_id}: {e}")
            return None, False, None

    async def reset_recurring_reminder(self, reminder_id, next_time: datetime):
        """Updates remind_at for a recurring reminder (keeps status PENDING)."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    "UPDATE reminders SET remind_at = ? WHERE id = ?", (next_time, reminder_id)
                )
                await db.commit()
                self.logger.info(f"Recurring reminder {reminder_id} rescheduled to {next_time}")
        except Exception as e:
            self.logger.error(f"DB error rescheduling reminder {reminder_id}: {e}")

    @staticmethod
    def _next_occurrence(recurrence_str: str, from_time: Optional[datetime] = None) -> datetime:
        """Computes the next trigger datetime for a recurrence rule.

        Supported formats:
          DAILY@HH:MM                     — every day at fixed time
          DAILY@RANDOM:HH:MM-HH:MM        — every day at random time in range
          WEEKLY:DOW[,DOW...]@HH:MM        — specific weekday(s) at fixed time
          WORKDAYS@HH:MM                  — Mon–Fri at fixed time

        Returns from_time + 24h as a safe fallback for malformed input.
        """
        from_time = from_time or datetime.now()

        if not recurrence_str or "@" not in recurrence_str:
            return from_time + timedelta(hours=24)

        DOW_NAMES = {"MON": 0, "TUE": 1, "WED": 2, "THU": 3, "FRI": 4, "SAT": 5, "SUN": 6}

        freq_part, time_part = recurrence_str.split("@", 1)
        freq_parts = freq_part.split(":", 1)
        freq = freq_parts[0].upper()
        dow_list = [d.strip().upper() for d in freq_parts[1].split(",")] if len(freq_parts) > 1 else []

        try:
            is_random = time_part.upper().startswith("RANDOM:")
            if is_random:
                range_str = time_part[7:]
                start_str, end_str = range_str.split("-")
                sh, sm = map(int, start_str.split(":"))
                eh, em = map(int, end_str.split(":"))
            else:
                h, m = map(int, time_part.split(":"))
        except (ValueError, IndexError):
            return from_time + timedelta(hours=24)

        def _make_candidate(base: datetime) -> datetime:
            if is_random:
                start_min = sh * 60 + sm
                end_min = eh * 60 + em
                if start_min > end_min:
                    start_min, end_min = end_min, start_min
                rand_min = random.randint(start_min, end_min)
                return base.replace(hour=rand_min // 60, minute=rand_min % 60, second=0, microsecond=0)
            return base.replace(hour=h, minute=m, second=0, microsecond=0)

        if freq == "DAILY":
            if is_random:
                # Fire today only if we haven't reached the range start yet.
                # Once at or within the range, schedule tomorrow to avoid firing
                # twice on the same day after a post-fire reschedule.
                effective_start_min = min(sh * 60 + sm, eh * 60 + em)
                from_min = from_time.hour * 60 + from_time.minute
                base = from_time if from_min < effective_start_min else from_time + timedelta(days=1)
                return _make_candidate(base)
            else:
                candidate = _make_candidate(from_time)
                if candidate <= from_time:
                    candidate = _make_candidate(from_time + timedelta(days=1))
                return candidate

        if freq == "WORKDAYS":
            candidate = _make_candidate(from_time)
            if candidate <= from_time:
                candidate = _make_candidate(from_time + timedelta(days=1))
            while candidate.weekday() > 4:
                candidate = _make_candidate(candidate + timedelta(days=1))
            return candidate

        if freq == "WEEKLY":
            target_weekdays = [DOW_NAMES[d] for d in dow_list if d in DOW_NAMES]
            if not target_weekdays:
                # Fallback to daily
                candidate = _make_candidate(from_time)
                if candidate <= from_time:
                    candidate = _make_candidate(from_time + timedelta(days=1))
                return candidate

            best = None
            for wd in target_weekdays:
                days_ahead = (wd - from_time.weekday()) % 7
                if days_ahead == 0:
                    candidate = _make_candidate(from_time)
                    if candidate <= from_time:
                        candidate = _make_candidate(from_time + timedelta(days=7))
                else:
                    candidate = _make_candidate(from_time + timedelta(days=days_ahead))
                if best is None or candidate < best:
                    best = candidate
            return best

        # Fallback: 24h from now
        return from_time + timedelta(hours=24)

    async def delete_reminder(self, reminder_id, user_id):
        """Marks a reminder as CANCELLED."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    UPDATE reminders SET status = 'CANCELLED'
                    WHERE id = ? AND user_id = ?
                """, (reminder_id, user_id))
                await db.commit()
                self.logger.info(f"Reminder {reminder_id} cancelled.")
        except Exception as e:
            self.logger.error(f"DB error cancelling reminder {reminder_id}: {e}")
            raise

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

        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(query, tuple(params))
                await db.commit()

                if cursor.rowcount > 0:
                    self.logger.info(f"Reminder {reminder_id} updated.")
                    return new_remind_at if delay_seconds is not None else True
                return False
        except Exception as e:
            self.logger.error(f"DB error updating reminder {reminder_id}: {e}")
            raise

    async def mark_as_sent(self, reminder_id):
        """Marks a reminder as SENT."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("UPDATE reminders SET status = 'SENT' WHERE id = ?", (reminder_id,))
                await db.commit()
        except Exception as e:
            self.logger.error(f"DB error marking reminder {reminder_id} as SENT: {e}")

    async def get_reminder_status(self, reminder_id):
        """Checks if a reminder is still PENDING."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("SELECT status FROM reminders WHERE id = ?", (reminder_id,)) as cursor:
                    row = await cursor.fetchone()
                    return row[0] if row else None
        except Exception as e:
            self.logger.error(f"DB error fetching status for reminder {reminder_id}: {e}")
            return None

    async def get_reminder_message(self, reminder_id):
        """Fetches the current message for a reminder."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("SELECT message FROM reminders WHERE id = ?", (reminder_id,)) as cursor:
                    row = await cursor.fetchone()
                    return row[0] if row else None
        except Exception as e:
            self.logger.error(f"DB error fetching message for reminder {reminder_id}: {e}")
            return None


    async def recover_reminders(self, job_queue):
        """Recovers pending reminders on startup and reschedules them."""
        self.logger.info("Recovering pending reminders...")
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("""
                    SELECT id, user_id, message, remind_at, recurrence, is_task FROM reminders
                    WHERE status = 'PENDING'
                """) as cursor:
                    rows = await cursor.fetchall()

            now = datetime.now()
            for row in rows:
                try:
                    reminder_id, user_id, message, remind_at_iso, recurrence, is_task = row
                    if isinstance(remind_at_iso, str):
                        remind_at = datetime.fromisoformat(remind_at_iso)
                    else:
                        remind_at = remind_at_iso

                    delay = (remind_at - now).total_seconds()

                    if delay > 0:
                        job_queue.run_once(
                            self._execute_reminder_callback,
                            when=delay,
                            chat_id=user_id,
                            data={"id": reminder_id, "msg": message},
                            name=f"reminder_{reminder_id}",
                        )
                        self.logger.info(f"Rescheduled reminder {reminder_id} for {delay:.1f}s")
                    elif recurrence:
                        # Recurring reminder expired while offline → compute next future occurrence
                        next_time = self._next_occurrence(recurrence, now)
                        await self.reset_recurring_reminder(reminder_id, next_time)
                        next_delay = (next_time - now).total_seconds()
                        job_queue.run_once(
                            self._execute_reminder_callback,
                            when=max(next_delay, 1),
                            chat_id=user_id,
                            data={"id": reminder_id, "msg": message},
                            name=f"reminder_{reminder_id}",
                        )
                        self.logger.info(f"Recurring reminder {reminder_id} rescheduled to next occurrence: {next_time}")
                    else:
                        # One-shot expired while offline → fire immediately
                        job_queue.run_once(
                            self._execute_reminder_callback,
                            when=1,
                            chat_id=user_id,
                            data={"id": reminder_id, "msg": f"{message} (Atrasado - estava offline)"},
                            name=f"reminder_{reminder_id}",
                        )
                        self.logger.warning(f"Reminder {reminder_id} was expired, sending immediately.")
                except Exception as row_err:
                    self.logger.error(f"Error recovering reminder row {row}: {row_err}")
        except Exception as e:
            self.logger.error(f"DB error during reminder recovery: {e}")

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
    def skill_group(self) -> str:
        return "reminders"

    @property
    def skill_group_emoji(self) -> str:
        return "⏰"
    
    @property
    def description(self) -> str:
        return (
            "Agenda um lembrete ou tarefa recorrente. "
            "Exemplos válidos de when: 'amanhã 9h', 'todo dia às 8h', 'toda segunda às 10h'. "
            "Se for is_task=true, o bot assumirá que 'message' é uma tarefa/'skill' automática."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "O conteúdo do lembrete ou a tarefa a executar. Para is_task=true, escreva como um comando direto (ex: 'busca vagas agora', 'manda o boletim do tempo')."
                },
                "when": {
                    "type": "string",
                    "description": (
                        "Quando disparar. Exemplos:\n"
                        "- Único: '10 minutos', 'amanhã 9h', '14:00', '2026-02-10 10:00'\n"
                        "- Recorrente: 'todo dia às 9h', 'toda manhã', 'toda tarde às 15h', "
                        "'toda noite entre 19h e 23h', 'toda segunda às 8h', "
                        "'toda segunda e quinta às 10h', 'dias úteis às 9h'"
                    )
                },
                "is_task": {
                    "type": "boolean",
                    "description": (
                        "Se true, o bot executa 'message' como uma tarefa (aciona skills e envia resultado). "
                        "Se false (padrão), envia apenas o texto de lembrete. "
                        "Use true para: 'manda o boletim do tempo', 'busca vagas', 'resumo de notícias'."
                    )
                }
            },
            "required": ["message", "when"]
        }

    def _parse_schedule(self, when_str: str):
        """Parses a 'when' string and returns (target_time, recurrence_str | None).

        Detects recurring patterns ('todo dia', 'toda manhã', 'toda segunda', etc.)
        and returns the appropriate recurrence rule alongside the first target datetime.
        Falls back to one-shot dateparser parsing when no recurrence is detected.
        """
        text = when_str.strip().lower()

        DOW_MAP = {
            "segunda": "MON", "segunda-feira": "MON",
            "terça": "TUE", "terca": "TUE", "terça-feira": "TUE",
            "quarta": "WED", "quarta-feira": "WED",
            "quinta": "THU", "quinta-feira": "THU",
            "sexta": "FRI", "sexta-feira": "FRI",
            "sábado": "SAT", "sabado": "SAT",
            "domingo": "SUN",
        }

        recurrence = None

        # --- Random range: "entre 19h e 23h" / "entre 19:00 e 23:00" ---
        rand_match = re.search(r'entre\s+(\d{1,2})(?:h|:00)?\s+e\s+(\d{1,2})(?:h|:00)?', text)
        if rand_match:
            h1, h2 = int(rand_match.group(1)), int(rand_match.group(2))
            recurrence = f"DAILY@RANDOM:{h1:02d}:00-{h2:02d}:00"
            target_time = ReminderManager._next_occurrence(recurrence)
            return target_time, recurrence

        # --- Extract explicit HH:MM time (used for fixed recurring) ---
        time_match = re.search(r'(\d{1,2})[h:](\d{2})?(?:\s|$)', text)
        if time_match:
            h = int(time_match.group(1))
            m = int(time_match.group(2) or 0)
            time_str = f"{h:02d}:{m:02d}"
        else:
            time_str = None

        # --- Recurring patterns ---
        if re.search(r'\btodo\s+dia\b|\btodos\s+os\s+dias\b|\bdiariamente\b', text):
            recurrence = f"DAILY@{time_str or '08:00'}"
        elif re.search(r'\btoda\s+manh[aã]\b|\bde\s+manh[aã]\b', text):
            recurrence = f"DAILY@{time_str or '08:00'}"
        elif re.search(r'\btoda\s+tarde\b|\bde\s+tarde\b', text):
            recurrence = f"DAILY@{time_str or '14:00'}"
        elif re.search(r'\btoda\s+noite\b|\bde\s+noite\b', text):
            recurrence = f"DAILY@{time_str or '20:00'}"
        elif re.search(r'\bdias?\s+[uú]teis\b', text):
            recurrence = f"WORKDAYS@{time_str or '09:00'}"
        else:
            # Weekday pattern: "toda segunda", "toda terça e quinta"
            days_found: List[str] = []
            for pt_day, en_day in DOW_MAP.items():
                if pt_day in text and en_day not in days_found:
                    days_found.append(en_day)
            if days_found:
                recurrence = f"WEEKLY:{','.join(days_found)}@{time_str or '09:00'}"

        if recurrence:
            target_time = ReminderManager._next_occurrence(recurrence)
            return target_time, recurrence

        # --- One-shot fallback ---
        when_fixed = self._preprocess_time_string(when_str)
        if when_fixed != when_str:
            self.manager.logger.info(f"Fixed time string: '{when_str}' -> '{when_fixed}'")
        target_time = dateparser.parse(when_fixed, settings={'PREFER_DATES_FROM': 'future', 'DATE_ORDER': 'DMY'})
        return target_time, None

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

    async def execute(self, context: Dict[str, Any], message: str, when: str, is_task: bool = False, **kwargs) -> Dict[str, Any]:
        """Executes the add_reminder skill.

        Args:
            context: The execution context containing 'user_id' and 'job_queue'.
            message: The reminder message or task command.
            when: Time string — relative, absolute, or recurring pattern.
            is_task: If True, fires by running message through the agent brain.

        Returns:
            Dict containing the status and info of the created reminder.
        """
        user_id = context.get('user_id')
        if not user_id:
            return self.error("User ID not found in context.")

        try:
            now = datetime.now()

            # 1. Try simple integer (legacy: minutes)
            if str(when).strip().isdigit():
                minutes = int(when)
                target_time = now + timedelta(minutes=minutes)
                recurrence = None
            else:
                target_time, recurrence = self._parse_schedule(when)

            if not target_time:
                return self.error(f"Não entendi a data/hora: '{when}'. Tente algo como '10 minutos', '14:00' ou 'todo dia às 9h'.")

            # Block past dates for one-shot reminders (allow 1 min grace period)
            if not recurrence and target_time < now - timedelta(minutes=1):
                friendly = target_time.strftime('%d/%m %H:%M')
                return self.error(f"O horário {friendly} já passou. Por favor, escolha um horário futuro.")

            delay_seconds = max((target_time - now).total_seconds(), 0)

            # --- Persist to DB ---
            r_id = await self.manager.add_reminder(
                user_id, message, delay_seconds,
                recurrence=recurrence, is_task=is_task
            )

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
                        name=f"reminder_{r_id}",
                    )
                else:
                    self.manager.logger.warning("Reminder callback not found, job not scheduled in memory.")
            else:
                self.manager.logger.warning("JobQueue not found in context, reminder saved but not scheduled in memory.")

            # --- Build confirmation message ---
            target_str = target_time.strftime('%H:%M')
            if target_time.date() != now.date():
                target_str = target_time.strftime('%d/%m às %H:%M')

            if recurrence:
                label = ListRemindersSkill(self.manager)._recurrence_label(recurrence)
                info_msg = f"Lembrete recorrente criado: {label} — '{message}'. Próximo disparo: {target_str}."
            elif delay_seconds < 5:
                info_msg = f"Disparando lembrete agora mesmo: '{message}'!"
            else:
                info_msg = f"Lembrete criado para {target_str}: '{message}'."

            return self.success({
                "reminder_id": r_id,
                "message": message,
                "target_time": target_str,
                "recurrence": recurrence,
                "is_task": is_task,
            }, message=info_msg)
        except Exception as e:
            self.manager.logger.error(f"Error adding reminder: {e}")
            return self.error(str(e))

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
    def skill_group(self) -> str:
        return "reminders"

    @property
    def skill_group_emoji(self) -> str:
        return "⏰"
    
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

    _RECURRENCE_LABELS = {
        "DAILY": "Todo dia",
        "WORKDAYS": "Dias úteis",
        "WEEKLY": "Semanal",
    }

    def _recurrence_label(self, recurrence: str) -> str:
        """Returns a human-readable recurrence label."""
        freq_part, time_part = recurrence.split("@", 1)
        freq = freq_part.split(":")[0].upper()
        days_part = freq_part.split(":", 1)[1] if ":" in freq_part else ""

        if time_part.upper().startswith("RANDOM:"):
            range_str = time_part[7:]
            start, end = range_str.split("-")
            time_label = f"entre {start} e {end}"
        else:
            time_label = f"às {time_part}"

        if freq == "DAILY":
            return f"Todo dia {time_label}"
        if freq == "WORKDAYS":
            return f"Dias úteis {time_label}"
        if freq == "WEEKLY" and days_part:
            PT = {"MON": "Seg", "TUE": "Ter", "WED": "Qua", "THU": "Qui", "FRI": "Sex", "SAT": "Sáb", "SUN": "Dom"}
            day_labels = ", ".join(PT.get(d.strip().upper(), d) for d in days_part.split(","))
            return f"{day_labels} {time_label}"
        return recurrence

    async def execute(self, context: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Lists pending reminders for the user."""
        user_id = context.get('user_id')
        if not user_id:
            return self.error("User ID missing")

        try:
            reminders = await self.manager.get_active_reminders(user_id)
            if not reminders:
                return self.success({
                    "reminders": [],
                    "count": 0
                }, message="Nenhum lembrete pendente encontrado. A lista está vazia.")

            formatted_reminders = []

            for r in reminders:
                if len(r) < 3:
                    self.manager.logger.warning(f"Skipping invalid reminder row: {r}")
                    continue

                r_id, msg, at_dt = r[0], r[1], r[2]
                recurrence = r[3] if len(r) > 3 else None
                is_task = bool(r[4]) if len(r) > 4 else False

                if isinstance(at_dt, str):
                    try:
                        at_dt = datetime.fromisoformat(at_dt)
                    except ValueError:
                        self.manager.logger.warning(f"Invalid date format for reminder {r_id}: {at_dt}")
                        continue

                if not isinstance(at_dt, datetime):
                    continue

                entry = {
                    "id": r_id,
                    "message": msg,
                    "at": self._format_friendly_date(at_dt),
                }
                if recurrence:
                    entry["recurrence"] = recurrence
                if is_task:
                    entry["is_task"] = True

                formatted_reminders.append(entry)

            if not formatted_reminders:
                summary = "Você não tem lembretes pendentes."
            else:
                lines = [f"Você tem {len(formatted_reminders)} lembrete(s) pendente(s):"]
                for r in formatted_reminders:
                    rec_str = f" 🔁 {self._recurrence_label(r['recurrence'])}" if r.get("recurrence") else ""
                    task_str = " | Tarefa automática" if r.get("is_task") else ""
                    # Escape HTML para evitar quebra de formatação e injection
                    safe_msg = html.escape(r['message'])
                    lines.append(f"• <code>[ID {r['id']}]</code> <b>{safe_msg}</b>\n  <i>(próximo: {r['at']}{rec_str}{task_str})</i>")
                
                summary = "\n".join(lines)
                instruction = "\n\n[INSTRUÇÃO IMPORTANTE: Devolva a lista acima EXATAMENTE com essa formatação HTML (<code>, <b>, <i>). NÃO converta para Markdown.]"
                summary += instruction

            return self.success({
                "reminders": formatted_reminders,
                "count": len(formatted_reminders),
            }, summary)
        except Exception as e:
            self.manager.logger.error(f"Error listing reminders: {e}")
            return self.error(str(e))

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
    def skill_group(self) -> str:
        return "reminders"

    @property
    def skill_group_emoji(self) -> str:
        return "⏰"

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
        if not user_id: return self.error("User ID missing")
        
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
                    
            return self.success({"deleted_id": rid}, message=f"Lembrete {rid} cancelado.")
        except ValueError:
            return self.error("Invalid reminder_id format")
        except Exception as e:
            return self.error(str(e))

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
    def skill_group(self) -> str:
        return "reminders"

    @property
    def skill_group_emoji(self) -> str:
        return "⏰"

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
         if not user_id: return self.error("User ID missing")
         
         try:
             rid = int(reminder_id)
             delay_seconds = None
             if new_delay_minutes is not None:
                 delay_seconds = int(new_delay_minutes) * 60
             
             result = await self.manager.update_reminder(rid, user_id, new_message, delay_seconds)
             
             if not result:
                 return self.error("Reminder not found or update failed (maybe it's not pending?)")
                 
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
                         
             return self.success({"updated_id": rid}, message="Lembrete atualizado.")
         except ValueError:
             return self.error("Invalid input format (integers required for ID/minutes)")
         except Exception as e:
             return self.error(str(e))

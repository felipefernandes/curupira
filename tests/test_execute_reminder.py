"""
Tests for execute_reminder callback logic from bot.py.

Since bot.py has module-level side effects (AgentBrain instantiation, etc.),
we replicate the exact callback logic here as a standalone function and test
it in isolation — following the same pattern as test_bot_typing.py.

Ref: Issue #76 — coverage for bot.py execute_reminder().
"""

import asyncio
import unittest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch, call

from skills.reminders import ReminderManager


# ---------------------------------------------------------------------------
# Exact replica of execute_reminder() from bot.py
# (dependencies injected as parameters for testability)
# ---------------------------------------------------------------------------

async def _execute_reminder_impl(context, reminder_manager, memory_manager, brain):
    """Mirror of execute_reminder() in bot.py — used for isolated unit tests."""
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
    if status != "PENDING":
        return

    recurrence, is_task, remind_at = await reminder_manager.get_reminder_recurrence(reminder_id)

    # --- Execute the reminder action ---
    if is_task:
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
        except Exception:
            await context.bot.send_message(
                chat_id=job.chat_id,
                text=f"⚠️ Erro ao executar tarefa agendada: {message}",
            )
    else:
        await context.bot.send_message(chat_id=job.chat_id, text=f"⏰ Lembrete: {message}")

    # --- Reschedule or mark as sent ---
    if recurrence:
        next_time = reminder_manager._next_occurrence(recurrence, from_time=remind_at)
        await reminder_manager.reset_recurring_reminder(reminder_id, next_time)
        next_delay = (next_time - datetime.now()).total_seconds()
        context.job_queue.run_once(
            lambda ctx: None,
            when=max(next_delay, 1),
            chat_id=job.chat_id,
            data={"id": reminder_id, "msg": message},
            name=f"reminder_{reminder_id}",
        )
    else:
        await reminder_manager.mark_as_sent(reminder_id)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_context(chat_id=99, reminder_data=None):
    ctx = MagicMock()
    ctx.job = MagicMock()
    ctx.job.chat_id = chat_id
    ctx.job.data = reminder_data
    ctx.bot.send_message = AsyncMock()
    ctx.job_queue = MagicMock()
    ctx.job_queue.run_once = MagicMock()
    return ctx


def _make_reminder_manager(
    message="Test reminder",
    status="PENDING",
    recurrence=None,
    is_task=False,
    remind_at=None,
):
    mgr = MagicMock(spec=ReminderManager)
    mgr.get_reminder_message = AsyncMock(return_value=message)
    mgr.get_reminder_status = AsyncMock(return_value=status)
    mgr.get_reminder_recurrence = AsyncMock(
        return_value=(recurrence, is_task, remind_at or datetime.now() + timedelta(hours=1))
    )
    mgr.reset_recurring_reminder = AsyncMock()
    mgr.mark_as_sent = AsyncMock()
    # Provide a real _next_occurrence so reschedule tests work
    mgr._next_occurrence = ReminderManager._next_occurrence
    return mgr


def _make_memory_manager(facts="", surname=""):
    mgr = MagicMock()
    mgr.get_facts = AsyncMock(return_value=facts)
    mgr.get_fact_value = AsyncMock(return_value=surname)
    return mgr


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestExecuteReminderCallback(unittest.IsolatedAsyncioTestCase):

    async def test_plain_text_fallback_sends_reminder_and_returns(self):
        """Old plain-text job data (not dict) sends ⏰ message and exits early."""
        context = _make_context(reminder_data="Beba água agora")
        mgr = _make_reminder_manager()
        mem_mgr = _make_memory_manager()
        brain = MagicMock()

        await _execute_reminder_impl(context, mgr, mem_mgr, brain)

        context.bot.send_message.assert_awaited_once()
        text = context.bot.send_message.call_args[1]["text"]
        self.assertIn("⏰ Lembrete:", text)
        self.assertIn("Beba água agora", text)
        # Must not touch DB when data is plain text
        mgr.get_reminder_message.assert_not_awaited()

    async def test_non_pending_status_skips_silently(self):
        """A SENT or CANCELLED reminder is skipped without sending any message."""
        context = _make_context(reminder_data={"id": 1, "msg": "test"})
        mgr = _make_reminder_manager(status="SENT")
        mem_mgr = _make_memory_manager()
        brain = MagicMock()

        await _execute_reminder_impl(context, mgr, mem_mgr, brain)

        context.bot.send_message.assert_not_awaited()
        mgr.mark_as_sent.assert_not_awaited()
        mgr.reset_recurring_reminder.assert_not_awaited()

    async def test_is_task_false_sends_reminder_text(self):
        """is_task=False sends '⏰ Lembrete: <message>' and calls mark_as_sent."""
        context = _make_context(reminder_data={"id": 2, "msg": "tomar remédio"})
        mgr = _make_reminder_manager(message="tomar remédio", is_task=False, recurrence=None)
        mem_mgr = _make_memory_manager()
        brain = MagicMock()

        await _execute_reminder_impl(context, mgr, mem_mgr, brain)

        context.bot.send_message.assert_awaited_once()
        text = context.bot.send_message.call_args[1]["text"]
        self.assertIn("⏰ Lembrete:", text)
        self.assertIn("tomar remédio", text)
        mgr.mark_as_sent.assert_awaited_once_with(2)

    async def test_is_task_true_calls_brain_and_sends_result(self):
        """is_task=True calls brain.process() and sends the returned text."""
        context = _make_context(chat_id=42, reminder_data={"id": 3, "msg": "busca vagas"})
        mgr = _make_reminder_manager(message="busca vagas", is_task=True, recurrence=None)
        mem_mgr = _make_memory_manager(facts="- city: SP", surname="Silva")
        brain = MagicMock()
        brain.process = AsyncMock(return_value="3 vagas encontradas")

        await _execute_reminder_impl(context, mgr, mem_mgr, brain)

        brain.process.assert_awaited_once()
        process_call = brain.process.call_args
        self.assertEqual(process_call[0][0], "busca vagas")
        agent_ctx = process_call[0][1]
        self.assertEqual(agent_ctx["user_id"], 42)
        self.assertEqual(agent_ctx["assistant_surname"], "Silva")
        self.assertEqual(agent_ctx["user_facts"], "- city: SP")

        context.bot.send_message.assert_awaited_once()
        self.assertIn("3 vagas encontradas", context.bot.send_message.call_args[1]["text"])

    async def test_is_task_true_brain_error_sends_error_message(self):
        """When brain.process() raises, sends ⚠️ error message instead."""
        context = _make_context(reminder_data={"id": 4, "msg": "busca vagas"})
        mgr = _make_reminder_manager(message="busca vagas", is_task=True, recurrence=None)
        mem_mgr = _make_memory_manager()
        brain = MagicMock()
        brain.process = AsyncMock(side_effect=RuntimeError("brain crash"))

        await _execute_reminder_impl(context, mgr, mem_mgr, brain)

        context.bot.send_message.assert_awaited_once()
        text = context.bot.send_message.call_args[1]["text"]
        self.assertIn("⚠️", text)
        self.assertIn("busca vagas", text)

    async def test_one_shot_calls_mark_as_sent_not_reschedule(self):
        """One-shot reminder (no recurrence) calls mark_as_sent, not reschedule."""
        context = _make_context(reminder_data={"id": 5, "msg": "comprar leite"})
        mgr = _make_reminder_manager(message="comprar leite", is_task=False, recurrence=None)
        mem_mgr = _make_memory_manager()
        brain = MagicMock()

        await _execute_reminder_impl(context, mgr, mem_mgr, brain)

        mgr.mark_as_sent.assert_awaited_once_with(5)
        mgr.reset_recurring_reminder.assert_not_awaited()
        context.job_queue.run_once.assert_not_called()

    async def test_recurring_reschedules_and_does_not_mark_sent(self):
        """Recurring reminder calls reset_recurring_reminder + run_once, not mark_as_sent."""
        remind_at = datetime.now() + timedelta(hours=1)
        context = _make_context(reminder_data={"id": 6, "msg": "daily task"})
        mgr = _make_reminder_manager(
            message="daily task", is_task=False,
            recurrence="DAILY@09:00", remind_at=remind_at,
        )
        mem_mgr = _make_memory_manager()
        brain = MagicMock()

        await _execute_reminder_impl(context, mgr, mem_mgr, brain)

        mgr.reset_recurring_reminder.assert_awaited_once()
        mgr.mark_as_sent.assert_not_awaited()
        context.job_queue.run_once.assert_called_once()

    async def test_recurring_passes_remind_at_as_from_time(self):
        """Anti-drift: _next_occurrence is called with remind_at as from_time."""
        remind_at = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
        context = _make_context(reminder_data={"id": 7, "msg": "daily 9h"})
        mgr = _make_reminder_manager(
            message="daily 9h", is_task=False,
            recurrence="DAILY@09:00", remind_at=remind_at,
        )
        # Replace _next_occurrence with a spy
        next_time = datetime.now() + timedelta(days=1)
        mock_next = MagicMock(return_value=next_time)
        mgr._next_occurrence = mock_next

        mem_mgr = _make_memory_manager()
        brain = MagicMock()

        await _execute_reminder_impl(context, mgr, mem_mgr, brain)

        mock_next.assert_called_once_with("DAILY@09:00", from_time=remind_at)

    async def test_db_message_used_over_job_data_msg(self):
        """If DB has an updated message, it takes priority over job.data['msg']."""
        context = _make_context(reminder_data={"id": 8, "msg": "old message"})
        mgr = _make_reminder_manager(message="updated message", is_task=False, recurrence=None)
        mem_mgr = _make_memory_manager()
        brain = MagicMock()

        await _execute_reminder_impl(context, mgr, mem_mgr, brain)

        text = context.bot.send_message.call_args[1]["text"]
        self.assertIn("updated message", text)
        self.assertNotIn("old message", text)

    async def test_fallback_to_job_data_msg_when_db_returns_none(self):
        """When DB returns None for message, job.data['msg'] is used as fallback."""
        context = _make_context(reminder_data={"id": 9, "msg": "fallback msg"})
        mgr = _make_reminder_manager(message=None, is_task=False, recurrence=None)
        mgr.get_reminder_message = AsyncMock(return_value=None)
        mem_mgr = _make_memory_manager()
        brain = MagicMock()

        await _execute_reminder_impl(context, mgr, mem_mgr, brain)

        text = context.bot.send_message.call_args[1]["text"]
        self.assertIn("fallback msg", text)


if __name__ == "__main__":
    unittest.main()

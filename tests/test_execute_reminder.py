"""
Tests for execute_reminder callback logic from bot.py.

Since bot.py has module-level side effects (AgentBrain instantiation, etc.),
we replicate the exact callback logic here as a standalone function and test
it in isolation — following the same pattern as test_bot_typing.py.

Ref: Issue #76 — coverage for bot.py execute_reminder().
"""

import unittest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from skills.reminders import ReminderManager


# ---------------------------------------------------------------------------
# Import real execute_reminder() from bot.py and patch variables
# ---------------------------------------------------------------------------
from bot import execute_reminder

async def _execute_reminder_impl(context, reminder_manager, memory_manager, brain):
    with patch("bot.reminder_manager", reminder_manager), \
         patch("bot.memory_manager", memory_manager), \
         patch("bot.brain", brain):
        await execute_reminder(context)


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
        # One-shot task failure must NOT mark as sent (leaves reminder PENDING)
        mgr.mark_as_sent.assert_not_awaited()

    async def test_is_task_one_shot_error_does_not_mark_sent(self):
        """task_error=True on a one-shot task: reminder stays PENDING (no mark_as_sent)."""
        context = _make_context(reminder_data={"id": 10, "msg": "enviar relatório"})
        mgr = _make_reminder_manager(message="enviar relatório", is_task=True, recurrence=None)
        mem_mgr = _make_memory_manager()
        brain = MagicMock()
        brain.process = AsyncMock(side_effect=ValueError("unavailable"))

        await _execute_reminder_impl(context, mgr, mem_mgr, brain)

        mgr.mark_as_sent.assert_not_awaited()
        context.job_queue.run_once.assert_not_called()

    async def test_is_task_recurring_error_still_reschedules(self):
        """task_error=True on a recurring task: still reschedules for next occurrence."""
        remind_at = datetime.now() + timedelta(hours=1)
        context = _make_context(reminder_data={"id": 11, "msg": "busca vagas diária"})
        mgr = _make_reminder_manager(
            message="busca vagas diária", is_task=True,
            recurrence="DAILY@09:00", remind_at=remind_at,
        )
        mem_mgr = _make_memory_manager()
        brain = MagicMock()
        brain.process = AsyncMock(side_effect=RuntimeError("transient error"))

        await _execute_reminder_impl(context, mgr, mem_mgr, brain)

        # Error message sent
        text = context.bot.send_message.call_args[1]["text"]
        self.assertIn("⚠️", text)
        # Recurring task must still be rescheduled (transient failures don't stop the schedule)
        mgr.reset_recurring_reminder.assert_awaited_once()
        context.job_queue.run_once.assert_called_once()
        mgr.mark_as_sent.assert_not_awaited()

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
        mgr = _make_reminder_manager(message=None, is_task=False, recurrence=None)  # type: ignore[arg-type]
        mgr.get_reminder_message = AsyncMock(return_value=None)
        mem_mgr = _make_memory_manager()
        brain = MagicMock()

        await _execute_reminder_impl(context, mgr, mem_mgr, brain)

        text = context.bot.send_message.call_args[1]["text"]
        self.assertIn("fallback msg", text)

    async def test_get_facts_failure_sets_task_error_and_notifies(self):
        """If get_facts raises, task_error is set, error notification is sent, and mark_as_sent is NOT called."""
        context = _make_context(reminder_data={"id": 12, "msg": "busca vagas"})
        mgr = _make_reminder_manager(message="busca vagas", is_task=True, recurrence=None)
        mem_mgr = _make_memory_manager()
        mem_mgr.get_facts = AsyncMock(side_effect=RuntimeError("DB unavailable"))
        brain = MagicMock()

        await _execute_reminder_impl(context, mgr, mem_mgr, brain)

        context.bot.send_message.assert_awaited_once()
        text = context.bot.send_message.call_args[1]["text"]
        self.assertIn("⚠️", text)
        mgr.mark_as_sent.assert_not_awaited()

    async def test_task_error_notification_send_fails_silently(self):
        """If brain fails AND error notification send also fails, no exception propagates."""
        context = _make_context(reminder_data={"id": 13, "msg": "tarefa"})
        mgr = _make_reminder_manager(message="tarefa", is_task=True, recurrence=None)
        mem_mgr = _make_memory_manager()
        brain = MagicMock()
        brain.process = AsyncMock(side_effect=RuntimeError("crash"))
        context.bot.send_message = AsyncMock(side_effect=RuntimeError("telegram down"))

        try:
            await _execute_reminder_impl(context, mgr, mem_mgr, brain)
        except Exception:
            self.fail("Exception propagated when both brain and send_message failed")

        mgr.mark_as_sent.assert_not_awaited()

    async def test_execute_reminder_job_is_none_returns_early(self):
        """When context.job is None, returns early without processing."""
        context = MagicMock()
        context.job = None
        mgr = _make_reminder_manager()
        mem_mgr = _make_memory_manager()
        brain = MagicMock()

        await _execute_reminder_impl(context, mgr, mem_mgr, brain)
        context.bot.send_message.assert_not_called()

    async def test_execute_reminder_chat_id_is_none_returns_early(self):
        """When context.job.chat_id is None, returns early and logs error."""
        context = MagicMock()
        context.job = MagicMock()
        context.job.chat_id = None
        context.job.data = {"id": 14, "msg": "test"}
        mgr = _make_reminder_manager()
        mem_mgr = _make_memory_manager()
        brain = MagicMock()

        with patch("bot.logging.error") as mock_log_err:
            await _execute_reminder_impl(context, mgr, mem_mgr, brain)
            mock_log_err.assert_called_once_with("execute_reminder: job has no chat_id")

    async def test_execute_reminder_memory_manager_is_none_fails_gracefully(self):
        """When memory_manager is None, task execution fails gracefully with error notification."""
        context = _make_context(chat_id=123, reminder_data={"id": 15, "msg": "tarefa"})
        mgr = _make_reminder_manager(message="tarefa", is_task=True, recurrence=None)
        brain = MagicMock()

        # memory_manager is None
        await _execute_reminder_impl(context, mgr, None, brain)

        # Should send error message to Telegram
        context.bot.send_message.assert_called_once()
        text = context.bot.send_message.call_args[1]["text"]
        self.assertIn("⚠️ Erro ao executar tarefa agendada", text)
        self.assertIn("sistema de memória está desativado", text)
        # Should not mark as sent
        mgr.mark_as_sent.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()

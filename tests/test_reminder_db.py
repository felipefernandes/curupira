"""
DB-level integration tests for ReminderManager.

Tests the async DB methods (add_reminder, get_reminder_recurrence,
reset_recurring_reminder, recover_reminders) using a real temporary SQLite
database initialised via MemoryManager.init_db().

Ref: Issue #76 — coverage for reminders.py DB methods.
"""

import os
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import aiosqlite

from skills.memory import MemoryManager
from skills.reminders import ReminderManager

FAKE_USER_ID = 77


class TestReminderManagerDB(unittest.IsolatedAsyncioTestCase):
    """Integration tests that exercise ReminderManager against a real SQLite DB."""

    async def asyncSetUp(self):
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tmp.close()
        self.db_path = tmp.name
        # Use MemoryManager to create schema (users, facts, conversations, reminders + migration)
        mm = MemoryManager(db_path=Path(self.db_path))
        await mm.init_db()
        await mm.add_user(FAKE_USER_ID, "testuser", "Test User")
        self.manager = ReminderManager(db_path=Path(self.db_path))
        self.manager._execute_reminder_callback = MagicMock()

    async def asyncTearDown(self):
        os.unlink(self.db_path)

    # ------------------------------------------------------------------
    # add_reminder
    # ------------------------------------------------------------------

    async def test_add_reminder_returns_id(self):
        """add_reminder persists the row and returns a positive integer ID."""
        r_id = await self.manager.add_reminder(FAKE_USER_ID, "test msg", 3600)
        self.assertIsNotNone(r_id)
        assert r_id is not None
        self.assertIsInstance(r_id, int)
        self.assertGreater(r_id, 0)

    async def test_add_reminder_with_recurrence(self):
        """add_reminder stores recurrence and is_task=False correctly."""
        r_id = await self.manager.add_reminder(
            FAKE_USER_ID, "tomar remédio", 3600,
            recurrence="DAILY@08:00", is_task=False,
        )
        recurrence, is_task, remind_at = await self.manager.get_reminder_recurrence(r_id)
        self.assertEqual(recurrence, "DAILY@08:00")
        self.assertFalse(is_task)
        self.assertIsNotNone(remind_at)

    async def test_add_reminder_with_is_task(self):
        """add_reminder stores is_task=True correctly."""
        r_id = await self.manager.add_reminder(
            FAKE_USER_ID, "busca vagas", 60,
            recurrence="DAILY@09:00", is_task=True,
        )
        _, is_task, _ = await self.manager.get_reminder_recurrence(r_id)
        self.assertTrue(is_task)

    async def test_add_reminder_status_is_pending(self):
        """Newly added reminders have status PENDING."""
        r_id = await self.manager.add_reminder(FAKE_USER_ID, "test", 300)
        status = await self.manager.get_reminder_status(r_id)
        self.assertEqual(status, "PENDING")

    # ------------------------------------------------------------------
    # get_active_reminders
    # ------------------------------------------------------------------

    async def test_get_active_reminders_returns_pending_rows(self):
        """get_active_reminders returns rows with recurrence and is_task columns."""
        await self.manager.add_reminder(
            FAKE_USER_ID, "daily task", 3600,
            recurrence="DAILY@09:00", is_task=True,
        )
        rows = list(await self.manager.get_active_reminders(FAKE_USER_ID))
        self.assertEqual(len(rows), 1)
        r_id, msg, at_dt, recurrence, is_task = rows[0]
        self.assertEqual(msg, "daily task")
        self.assertEqual(recurrence, "DAILY@09:00")
        self.assertTrue(bool(is_task))

    async def test_get_active_reminders_excludes_cancelled(self):
        """Cancelled reminders are not returned by get_active_reminders."""
        r_id = await self.manager.add_reminder(FAKE_USER_ID, "cancelled", 300)
        await self.manager.delete_reminder(r_id, FAKE_USER_ID)
        rows = list(await self.manager.get_active_reminders(FAKE_USER_ID))
        self.assertEqual(len(rows), 0)

    # ------------------------------------------------------------------
    # get_reminder_recurrence
    # ------------------------------------------------------------------

    async def test_get_reminder_recurrence_not_found(self):
        """Returns (None, False, None) for a non-existent reminder ID."""
        recurrence, is_task, remind_at = await self.manager.get_reminder_recurrence(99999)
        self.assertIsNone(recurrence)
        self.assertFalse(is_task)
        self.assertIsNone(remind_at)

    async def test_get_reminder_recurrence_returns_datetime(self):
        """remind_at is returned as a datetime instance."""
        r_id = await self.manager.add_reminder(
            FAKE_USER_ID, "test", 7200, recurrence="DAILY@10:00",
        )
        _, _, remind_at = await self.manager.get_reminder_recurrence(r_id)
        self.assertIsInstance(remind_at, datetime)

    async def test_get_reminder_recurrence_no_recurrence(self):
        """One-shot reminder returns None for recurrence."""
        r_id = await self.manager.add_reminder(FAKE_USER_ID, "one-shot", 600)
        recurrence, _, _ = await self.manager.get_reminder_recurrence(r_id)
        self.assertIsNone(recurrence)

    # ------------------------------------------------------------------
    # reset_recurring_reminder
    # ------------------------------------------------------------------

    async def test_reset_recurring_reminder_updates_remind_at(self):
        """reset_recurring_reminder updates remind_at and keeps status PENDING."""
        r_id = await self.manager.add_reminder(FAKE_USER_ID, "recurring", 60)
        new_time = datetime.now() + timedelta(days=1)

        await self.manager.reset_recurring_reminder(r_id, new_time)

        status = await self.manager.get_reminder_status(r_id)
        self.assertEqual(status, "PENDING")

        # Verify remind_at was updated
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT remind_at FROM reminders WHERE id = ?", (r_id,)
            ) as cursor:
                row = await cursor.fetchone()
                self.assertIsNotNone(row)
                assert row is not None
                stored = datetime.fromisoformat(row[0]) if isinstance(row[0], str) else row[0]
                # Should be within 1 second of new_time
                self.assertAlmostEqual(
                    stored.timestamp(), new_time.timestamp(), delta=1
                )

    # ------------------------------------------------------------------
    # recover_reminders
    # ------------------------------------------------------------------

    async def test_recover_reminders_schedules_future_reminder(self):
        """A reminder with future remind_at gets scheduled with positive delay."""
        from unittest.mock import MagicMock
        r_id = await self.manager.add_reminder(FAKE_USER_ID, "future task", 7200)

        job_queue = MagicMock()
        job_queue.run_once = MagicMock()
        await self.manager.recover_reminders(job_queue)

        job_queue.run_once.assert_called_once()
        call_kwargs = job_queue.run_once.call_args[1]
        self.assertGreater(call_kwargs["when"], 0)
        self.assertEqual(call_kwargs["data"]["id"], r_id)

    async def test_recover_reminders_expired_recurring_reschedules(self):
        """Expired recurring reminder is rescheduled to next future occurrence."""
        from unittest.mock import MagicMock
        r_id = await self.manager.add_reminder(FAKE_USER_ID, "daily task", 1)

        # Force remind_at to the past with recurrence set
        past_time = (datetime.now() - timedelta(hours=3)).isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE reminders SET remind_at = ?, recurrence = ? WHERE id = ?",
                (past_time, "DAILY@08:00", r_id),
            )
            await db.commit()

        job_queue = MagicMock()
        job_queue.run_once = MagicMock()
        await self.manager.recover_reminders(job_queue)

        job_queue.run_once.assert_called_once()
        call_kwargs = job_queue.run_once.call_args[1]
        # Delay must be positive (next occurrence, not past)
        self.assertGreater(call_kwargs["when"], 0)

    async def test_recover_reminders_expired_one_shot_fires_immediately(self):
        """Expired one-shot reminder fires immediately with (Atrasado) marker."""
        from unittest.mock import MagicMock
        r_id = await self.manager.add_reminder(FAKE_USER_ID, "missed task", 1)

        past_time = (datetime.now() - timedelta(hours=2)).isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE reminders SET remind_at = ? WHERE id = ?",
                (past_time, r_id),
            )
            await db.commit()

        job_queue = MagicMock()
        job_queue.run_once = MagicMock()
        await self.manager.recover_reminders(job_queue)

        job_queue.run_once.assert_called_once()
        call_kwargs = job_queue.run_once.call_args[1]
        self.assertEqual(call_kwargs["when"], 1)
        self.assertIn("Atrasado", call_kwargs["data"]["msg"])

    async def test_recover_reminders_skips_sent(self):
        """SENT reminders are not recovered."""
        from unittest.mock import MagicMock
        r_id = await self.manager.add_reminder(FAKE_USER_ID, "already sent", 1)
        await self.manager.mark_as_sent(r_id)

        job_queue = MagicMock()
        job_queue.run_once = MagicMock()
        await self.manager.recover_reminders(job_queue)

        job_queue.run_once.assert_not_called()


# ---------------------------------------------------------------------------
# ReminderManager — DB error resilience
# ---------------------------------------------------------------------------

class TestReminderManagerDBErrors(unittest.IsolatedAsyncioTestCase):
    """Tests that DB methods return safe defaults and log errors on DB failure."""

    def _make_broken_manager(self) -> Any:
        """Returns a ReminderManager pointing at an invalid DB path."""
        mgr = ReminderManager(db_path=Path("/nonexistent/path/curupira.db"))
        mgr.logger = MagicMock()
        return mgr

    async def test_get_active_reminders_returns_empty_list_on_db_error(self):
        """get_active_reminders returns [] when DB is unavailable."""
        mgr = self._make_broken_manager()
        result = await mgr.get_active_reminders(99)
        self.assertEqual(result, [])
        mgr.logger.error.assert_called_once()

    async def test_get_reminder_recurrence_returns_none_tuple_on_db_error(self):
        """get_reminder_recurrence returns (None, False, None) when DB is unavailable."""
        mgr = self._make_broken_manager()
        recurrence, is_task, remind_at = await mgr.get_reminder_recurrence(1)
        self.assertIsNone(recurrence)
        self.assertFalse(is_task)
        self.assertIsNone(remind_at)
        mgr.logger.error.assert_called_once()

    async def test_get_reminder_status_returns_none_on_db_error(self):
        """get_reminder_status returns None when DB is unavailable."""
        mgr = self._make_broken_manager()
        result = await mgr.get_reminder_status(1)
        self.assertIsNone(result)
        mgr.logger.error.assert_called_once()

    async def test_get_reminder_message_returns_none_on_db_error(self):
        """get_reminder_message returns None when DB is unavailable."""
        mgr = self._make_broken_manager()
        result = await mgr.get_reminder_message(1)
        self.assertIsNone(result)
        mgr.logger.error.assert_called_once()

    async def test_mark_as_sent_logs_and_does_not_raise_on_db_error(self):
        """mark_as_sent logs the error and does not raise when DB is unavailable."""
        mgr = self._make_broken_manager()
        try:
            await mgr.mark_as_sent(1)
        except Exception:
            self.fail("mark_as_sent raised an exception on DB error")
        mgr.logger.error.assert_called_once()

    async def test_reset_recurring_reminder_logs_and_does_not_raise_on_db_error(self):
        """reset_recurring_reminder logs the error and does not raise when DB is unavailable."""
        mgr = self._make_broken_manager()
        try:
            await mgr.reset_recurring_reminder(1, datetime.now() + timedelta(days=1))
        except Exception:
            self.fail("reset_recurring_reminder raised an exception on DB error")
        mgr.logger.error.assert_called_once()

    async def test_recover_reminders_logs_and_does_not_raise_on_db_error(self):
        """recover_reminders logs the error and does not raise when DB is unavailable."""
        from unittest.mock import MagicMock
        mgr = self._make_broken_manager()
        job_queue = MagicMock()
        try:
            await mgr.recover_reminders(job_queue)
        except Exception:
            self.fail("recover_reminders raised an exception on DB error")
        mgr.logger.error.assert_called_once()
        job_queue.run_once.assert_not_called()

    async def test_add_reminder_re_raises_on_db_error(self):
        """add_reminder logs and re-raises on DB error (caller's try/except handles it)."""
        mgr = self._make_broken_manager()
        with self.assertRaises(Exception):
            await mgr.add_reminder(99, "test", 60)
        mgr.logger.error.assert_called_once()


if __name__ == "__main__":
    unittest.main()

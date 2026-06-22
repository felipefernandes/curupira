"""
Tests for recurring reminders & scheduled tasks.
Ref: Issue #76 — https://github.com/felipefernandes/curupira/issues/76
"""

import unittest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

from skills.reminders import (
    ReminderManager,
    AddReminderSkill,
    ListRemindersSkill,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _dt(hour: int, minute: int = 0, days_offset: int = 0) -> datetime:
    """Returns a datetime anchored to today at the given time ± offset days."""
    base = datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)
    return base + timedelta(days=days_offset)


# ---------------------------------------------------------------------------
# _next_occurrence
# ---------------------------------------------------------------------------

class TestNextOccurrence(unittest.TestCase):

    def test_daily_fixed_time_today_before_trigger(self):
        """Next DAILY@09:00 when it's 08:00 → today at 09:00."""
        from_time = _dt(8, 0)
        result = ReminderManager._next_occurrence("DAILY@09:00", from_time)
        self.assertEqual(result.hour, 9)
        self.assertEqual(result.minute, 0)
        self.assertEqual(result.date(), from_time.date())

    def test_daily_fixed_time_today_after_trigger(self):
        """Next DAILY@09:00 when it's 10:00 → tomorrow at 09:00."""
        from_time = _dt(10, 0)
        result = ReminderManager._next_occurrence("DAILY@09:00", from_time)
        self.assertEqual(result.hour, 9)
        self.assertEqual(result.date(), (from_time + timedelta(days=1)).date())

    def test_daily_random_range_within_bounds(self):
        """DAILY@RANDOM:19:00-23:00 → time between 19:00 and 23:00."""
        from_time = _dt(8, 0)  # well before the range, so today
        result = ReminderManager._next_occurrence("DAILY@RANDOM:19:00-23:00", from_time)
        self.assertGreaterEqual(result.hour * 60 + result.minute, 19 * 60)
        self.assertLessEqual(result.hour * 60 + result.minute, 23 * 60)

    def test_daily_random_fires_today_when_before_range(self):
        """RANDOM range: from_time before range start → schedule fires today."""
        from_time = _dt(8, 0)  # 08:00, well before range 19:00-23:00
        result = ReminderManager._next_occurrence("DAILY@RANDOM:19:00-23:00", from_time)
        self.assertEqual(result.date(), from_time.date())
        total_min = result.hour * 60 + result.minute
        self.assertGreaterEqual(total_min, 19 * 60)
        self.assertLessEqual(total_min, 23 * 60)

    def test_daily_random_fires_tomorrow_when_within_range(self):
        """RANDOM range: from_time within the range → schedule fires tomorrow (no double-fire)."""
        from_time = _dt(21, 0)  # 21:00, inside range 19:00-23:00
        result = ReminderManager._next_occurrence("DAILY@RANDOM:19:00-23:00", from_time)
        tomorrow = (from_time + timedelta(days=1)).date()
        self.assertEqual(result.date(), tomorrow)
        total_min = result.hour * 60 + result.minute
        self.assertGreaterEqual(total_min, 19 * 60)
        self.assertLessEqual(total_min, 23 * 60)

    def test_daily_random_fires_tomorrow_when_past_range(self):
        """RANDOM range: from_time past the range end → schedule fires tomorrow."""
        from_time = _dt(23, 30)  # 23:30, past range 19:00-23:00
        result = ReminderManager._next_occurrence("DAILY@RANDOM:19:00-23:00", from_time)
        tomorrow = (from_time + timedelta(days=1)).date()
        self.assertEqual(result.date(), tomorrow)

    def test_workdays_skips_weekend(self):
        """WORKDAYS@09:00 starting on a Saturday → next Monday."""
        # Find the next Saturday
        base = datetime.now()
        days_until_saturday = (5 - base.weekday()) % 7
        saturday = base + timedelta(days=days_until_saturday)
        saturday = saturday.replace(hour=10, minute=0, second=0, microsecond=0)  # after 09:00

        result = ReminderManager._next_occurrence("WORKDAYS@09:00", saturday)
        self.assertLessEqual(result.weekday(), 4)  # Mon–Fri

    def test_weekly_specific_day(self):
        """WEEKLY:MON@08:00 → next Monday at 08:00."""
        # Use a Wednesday as from_time
        base = datetime.now()
        days_until_wed = (2 - base.weekday()) % 7
        wednesday = base + timedelta(days=days_until_wed)
        wednesday = wednesday.replace(hour=10, minute=0, second=0, microsecond=0)

        result = ReminderManager._next_occurrence("WEEKLY:MON@08:00", wednesday)
        self.assertEqual(result.weekday(), 0)  # Monday
        self.assertEqual(result.hour, 8)
        self.assertGreater(result, wednesday)

    def test_weekly_multiple_days(self):
        """WEEKLY:MON,WED,FRI@09:00 returns the soonest upcoming target day."""
        from_time = _dt(10, 0)  # after 09:00 today
        result = ReminderManager._next_occurrence("WEEKLY:MON,WED,FRI@09:00", from_time)
        self.assertIn(result.weekday(), [0, 2, 4])  # Mon, Wed, Fri
        self.assertGreater(result, from_time)

    def test_weekly_same_day_before_time(self):
        """WEEKLY:MON@10:00 on a Monday at 08:00 → same day at 10:00."""
        base = datetime.now()
        days_until_mon = (0 - base.weekday()) % 7
        monday_morning = base + timedelta(days=days_until_mon)
        monday_morning = monday_morning.replace(hour=8, minute=0, second=0, microsecond=0)

        result = ReminderManager._next_occurrence("WEEKLY:MON@10:00", monday_morning)
        self.assertEqual(result.weekday(), 0)
        self.assertEqual(result.hour, 10)
        self.assertEqual(result.date(), monday_morning.date())


# ---------------------------------------------------------------------------
# _next_occurrence — input validation (Iara bug fixes)
# ---------------------------------------------------------------------------

class TestNextOccurrenceValidation(unittest.TestCase):

    def test_malformed_no_at_sign_returns_24h_fallback(self):
        """Malformed recurrence string without '@' returns from_time + 24h."""
        from_time = _dt(10, 0)
        result = ReminderManager._next_occurrence("DAILY09:00", from_time)
        expected = from_time + timedelta(hours=24)
        self.assertAlmostEqual(result.timestamp(), expected.timestamp(), delta=1)

    def test_empty_string_returns_24h_fallback(self):
        """Empty recurrence string returns from_time + 24h."""
        from_time = _dt(9, 0)
        result = ReminderManager._next_occurrence("", from_time)
        expected = from_time + timedelta(hours=24)
        self.assertAlmostEqual(result.timestamp(), expected.timestamp(), delta=1)

    def test_random_range_start_greater_than_end_is_swapped(self):
        """RANDOM range with start > end is automatically swapped — no ValueError."""
        from_time = _dt(6, 0)  # well before range
        # Range is inverted: 23:00-19:00 (should be swapped to 19:00-23:00)
        result = ReminderManager._next_occurrence("DAILY@RANDOM:23:00-19:00", from_time)
        total_min = result.hour * 60 + result.minute
        self.assertGreaterEqual(total_min, 19 * 60)
        self.assertLessEqual(total_min, 23 * 60)

    def test_random_range_equal_start_and_end_returns_exact_time(self):
        """RANDOM range where start == end returns that exact time."""
        from_time = _dt(6, 0)
        result = ReminderManager._next_occurrence("DAILY@RANDOM:10:00-10:00", from_time)
        self.assertEqual(result.hour, 10)
        self.assertEqual(result.minute, 0)

    def test_invalid_time_format_non_numeric_returns_24h_fallback(self):
        """DAILY@abc:xyz (non-numeric time) returns from_time + 24h instead of crashing."""
        from_time = _dt(10, 0)
        result = ReminderManager._next_occurrence("DAILY@abc:xyz", from_time)
        expected = from_time + timedelta(hours=24)
        self.assertAlmostEqual(result.timestamp(), expected.timestamp(), delta=1)

    def test_invalid_random_range_no_dash_returns_24h_fallback(self):
        """RANDOM range without '-' separator returns from_time + 24h instead of crashing."""
        from_time = _dt(10, 0)
        result = ReminderManager._next_occurrence("DAILY@RANDOM:19:00", from_time)
        expected = from_time + timedelta(hours=24)
        self.assertAlmostEqual(result.timestamp(), expected.timestamp(), delta=1)

    def test_invalid_random_range_non_numeric_returns_24h_fallback(self):
        """RANDOM range with non-numeric parts returns from_time + 24h instead of crashing."""
        from_time = _dt(10, 0)
        result = ReminderManager._next_occurrence("DAILY@RANDOM:aa:bb-cc:dd", from_time)
        expected = from_time + timedelta(hours=24)
        self.assertAlmostEqual(result.timestamp(), expected.timestamp(), delta=1)


# ---------------------------------------------------------------------------
# _parse_schedule
# ---------------------------------------------------------------------------

class TestParseSchedule(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        manager = MagicMock()
        manager.logger = MagicMock()
        self.skill = AddReminderSkill(manager)

    def test_parse_daily_fixed_time(self):
        target, recurrence = self.skill._parse_schedule("todo dia às 9h")
        self.assertEqual(recurrence, "DAILY@09:00")
        self.assertIsNotNone(target)

    def test_parse_toda_manha_default_time(self):
        target, recurrence = self.skill._parse_schedule("toda manhã")
        self.assertEqual(recurrence, "DAILY@08:00")

    def test_parse_toda_manha_explicit_time(self):
        target, recurrence = self.skill._parse_schedule("toda manhã às 7h")
        self.assertEqual(recurrence, "DAILY@07:00")

    def test_parse_toda_tarde(self):
        target, recurrence = self.skill._parse_schedule("toda tarde")
        self.assertEqual(recurrence, "DAILY@14:00")

    def test_parse_toda_noite_default_time(self):
        target, recurrence = self.skill._parse_schedule("toda noite")
        self.assertEqual(recurrence, "DAILY@20:00")

    def test_parse_toda_noite_random_range(self):
        target, recurrence = self.skill._parse_schedule("toda noite entre 19h e 23h")
        self.assertEqual(recurrence, "DAILY@RANDOM:19:00-23:00")
        self.assertIsNotNone(target)

    def test_parse_workdays(self):
        target, recurrence = self.skill._parse_schedule("dias úteis às 9h")
        self.assertEqual(recurrence, "WORKDAYS@09:00")

    def test_parse_weekly_single_day(self):
        target, recurrence = self.skill._parse_schedule("toda segunda às 8h")
        self.assertIsNotNone(recurrence)
        assert recurrence is not None
        self.assertTrue(recurrence.startswith("WEEKLY:MON"))
        self.assertIn("@08:00", recurrence)

    def test_parse_weekly_multiple_days(self):
        target, recurrence = self.skill._parse_schedule("toda segunda e quarta às 10h")
        self.assertIsNotNone(recurrence)
        assert recurrence is not None
        self.assertIn("MON", recurrence)
        self.assertIn("WED", recurrence)

    def test_parse_one_shot_returns_no_recurrence(self):
        target, recurrence = self.skill._parse_schedule("amanhã às 10h")
        self.assertIsNone(recurrence)

    def test_parse_plain_integer_no_recurrence(self):
        """Plain integer is handled upstream by execute(), not _parse_schedule."""
        # _parse_schedule sees it as a one-shot via dateparser fallback
        target, recurrence = self.skill._parse_schedule("30")
        self.assertIsNone(recurrence)


# ---------------------------------------------------------------------------
# AddReminderSkill.execute — recurrence path
# ---------------------------------------------------------------------------

FAKE_USER_ID = 12345


class TestAddReminderSkillRecurring(unittest.IsolatedAsyncioTestCase):

    def _make_skill(self):
        manager = MagicMock(spec=ReminderManager)
        manager.logger = MagicMock()
        manager.add_reminder = AsyncMock(return_value=42)
        manager._execute_reminder_callback = AsyncMock()
        skill = AddReminderSkill(manager)
        return skill, manager

    def _make_context(self, job_queue=None):
        return {
            "user_id": FAKE_USER_ID,
            "job_queue": job_queue or MagicMock(),
        }

    async def test_recurring_reminder_persists_recurrence(self):
        skill, manager = self._make_skill()
        ctx = self._make_context()

        result = await skill.execute(ctx, message="tomar remédio", when="todo dia às 8h")

        self.assertEqual(result["status"], "success")
        self.assertIsNotNone(result["data"]["recurrence"])
        self.assertTrue(result["data"]["recurrence"].startswith("DAILY@08"))
        # Verify recurrence was passed to add_reminder
        _, call_kwargs = manager.add_reminder.call_args
        self.assertEqual(call_kwargs["recurrence"], result["data"]["recurrence"])

    async def test_is_task_flag_persisted(self):
        skill, manager = self._make_skill()
        ctx = self._make_context()

        result = await skill.execute(ctx, message="busca vagas agora", when="todo dia às 9h", is_task=True)

        self.assertEqual(result["data"]["is_task"], True)
        _, call_kwargs = manager.add_reminder.call_args
        self.assertEqual(call_kwargs["is_task"], True)

    async def test_one_shot_no_recurrence(self):
        skill, manager = self._make_skill()
        ctx = self._make_context()

        result = await skill.execute(ctx, message="comprar leite", when="amanhã às 10h")

        self.assertIsNone(result["data"].get("recurrence"))
        _, call_kwargs = manager.add_reminder.call_args
        self.assertIsNone(call_kwargs["recurrence"])

    async def test_confirmation_message_mentions_recurrence(self):
        skill, manager = self._make_skill()
        ctx = self._make_context()

        result = await skill.execute(ctx, message="tomar remédio", when="toda manhã às 8h")

        self.assertIn("recorrente", result["message"].lower())

    async def test_multiple_time_hint_single_call(self):
        """A single call with one time slot creates exactly one reminder."""
        skill, manager = self._make_skill()
        ctx = self._make_context()

        await skill.execute(ctx, message="tomar remédio", when="todo dia às 8h")

        self.assertEqual(manager.add_reminder.call_count, 1)


# ---------------------------------------------------------------------------
# ListRemindersSkill — recurrence display
# ---------------------------------------------------------------------------

class TestListRemindersSkillRecurrence(unittest.IsolatedAsyncioTestCase):

    def _make_skill(self, rows):
        manager = MagicMock(spec=ReminderManager)
        manager.logger = MagicMock()
        manager.get_active_reminders = AsyncMock(return_value=rows)
        return ListRemindersSkill(manager)

    async def test_list_shows_recurrence_symbol(self):
        remind_at = (datetime.now() + timedelta(days=1)).isoformat()
        rows = [(1, "tomar remédio", remind_at, "DAILY@08:00", 0)]
        skill = self._make_skill(rows)

        result = await skill.execute({"user_id": FAKE_USER_ID})

        self.assertIn("🔁", result["direct_html"])
        self.assertIn("Todo dia", result["direct_html"])

    async def test_list_shows_task_indicator(self):
        remind_at = (datetime.now() + timedelta(days=1)).isoformat()
        rows = [(2, "busca vagas agora", remind_at, "DAILY@09:00", 1)]
        skill = self._make_skill(rows)

        result = await skill.execute({"user_id": FAKE_USER_ID})

        self.assertIn("Tarefa automática", result["direct_html"])

    async def test_list_one_shot_no_recurrence_symbol(self):
        remind_at = (datetime.now() + timedelta(hours=2)).isoformat()
        rows = [(3, "comprar leite", remind_at, None, 0)]
        skill = self._make_skill(rows)

        result = await skill.execute({"user_id": FAKE_USER_ID})

        self.assertNotIn("🔁", result["direct_html"])
        self.assertNotIn("Tarefa automática", result["direct_html"])

    async def test_recurrence_weekly_label(self):
        remind_at = (datetime.now() + timedelta(days=2)).isoformat()
        rows = [(4, "reunião semanal", remind_at, "WEEKLY:MON@10:00", 0)]
        skill = self._make_skill(rows)

        result = await skill.execute({"user_id": FAKE_USER_ID})

        self.assertIn("Seg", result["direct_html"])

    async def test_list_empty_reminders(self):
        """Empty reminder list returns success with message, no direct_html."""
        skill = self._make_skill([])

        result = await skill.execute({"user_id": FAKE_USER_ID})

        self.assertEqual(result["status"], "success")
        self.assertIn("pendente", result["message"])
        self.assertNotIn("direct_html", result)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import unittest
from datetime import date, datetime, timedelta

from dailygrind.reminders import ReminderScheduler


class ReminderSchedulerTests(unittest.TestCase):
    def test_disabled_never_fires(self) -> None:
        scheduler = ReminderScheduler(enabled=False, reminder_hhmm="20:30")
        now = datetime(2026, 11, 1, 22, 0)
        self.assertFalse(scheduler.is_due(now, all_done=False))

    def test_fires_only_after_time_and_when_incomplete(self) -> None:
        scheduler = ReminderScheduler(enabled=True, reminder_hhmm="20:30")
        before = datetime(2026, 11, 1, 20, 29)
        after = datetime(2026, 11, 1, 20, 30)
        self.assertFalse(scheduler.is_due(before, all_done=False))
        self.assertFalse(scheduler.is_due(after, all_done=True))
        self.assertTrue(scheduler.is_due(after, all_done=False))

    def test_snooze_blocks_until_due_again(self) -> None:
        scheduler = ReminderScheduler(enabled=True, reminder_hhmm="20:30")
        now = datetime(2026, 11, 1, 20, 30)
        resume = scheduler.snooze(now, minutes=10)
        self.assertEqual(resume, datetime(2026, 11, 1, 20, 40))
        self.assertFalse(
            scheduler.is_due(datetime(2026, 11, 1, 20, 35), all_done=False)
        )
        self.assertTrue(
            scheduler.is_due(datetime(2026, 11, 1, 20, 40), all_done=False)
        )

    def test_dismissal_stops_reminders_for_today_only(self) -> None:
        scheduler = ReminderScheduler(enabled=True, reminder_hhmm="20:30")
        now = datetime(2026, 11, 1, 20, 30)
        scheduler.dismiss_for_day(now)
        self.assertFalse(
            scheduler.is_due(datetime(2026, 11, 1, 23, 59), all_done=False)
        )
        self.assertTrue(
            scheduler.is_due(datetime(2026, 11, 2, 20, 30), all_done=False)
        )

    def test_configure_resets_state(self) -> None:
        scheduler = ReminderScheduler(enabled=True, reminder_hhmm="20:30")
        now = datetime(2026, 11, 1, 20, 30)
        scheduler.dismiss_for_day(now)
        scheduler.configure(True, "21:00")
        self.assertTrue(
            scheduler.is_due(datetime(2026, 11, 1, 21, 0), all_done=False)
        )
        self.assertFalse(
            scheduler.is_due(datetime(2026, 11, 1, 20, 59), all_done=False)
        )

    def test_invalid_time_rejected(self) -> None:
        with self.assertRaises(ValueError):
            ReminderScheduler(reminder_hhmm="20:99")


if __name__ == "__main__":
    unittest.main()

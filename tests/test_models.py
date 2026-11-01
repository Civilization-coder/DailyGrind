from __future__ import annotations

import unittest
from datetime import date, datetime, timedelta

from dailygrind.models import (
    Task,
    TaskState,
    current_streak,
    format_hhmm,
    longest_streak,
    make_snapshot,
    parse_hhmm,
    question_for_day,
    recent_completion,
    reminder_has_passed,
)


def make_task(
    task_id: int = 1,
    target: int = 10,
    step: int = 1,
    title: str = "测试任务",
) -> Task:
    return Task(
        id=task_id,
        title=title,
        description="",
        target=target,
        unit="个",
        icon="测",
        color="#2F7A57",
        step=step,
        sort_order=0,
    )


class SnapshotTests(unittest.TestCase):
    def test_empty_day_is_not_done(self) -> None:
        snapshot = make_snapshot([], {})
        self.assertEqual(snapshot.percent, 0)
        self.assertFalse(snapshot.all_done)

    def test_progress_is_capped_at_target(self) -> None:
        task = make_task(target=10)
        state = TaskState(task=task, amount=13)
        self.assertEqual(state.capped_amount, 10)
        self.assertEqual(state.percent, 100)
        self.assertTrue(state.completed)
        self.assertEqual(state.remaining, 0)

    def test_snapshot_combines_units_and_tasks(self) -> None:
        tasks = [make_task(1, 10), make_task(2, 5), make_task(3, 1)]
        snapshot = make_snapshot(tasks, {1: 5, 2: 5})
        self.assertEqual(snapshot.total_tasks, 3)
        self.assertEqual(snapshot.completed_tasks, 1)
        self.assertEqual(snapshot.remaining_tasks, 2)
        self.assertEqual(snapshot.total_units, 16)
        self.assertEqual(snapshot.done_units, 10)
        self.assertEqual(snapshot.percent, 63)
        self.assertFalse(snapshot.all_done)
        self.assertEqual([s.task.id for s in snapshot.outstanding], [1, 3])


class StreakTests(unittest.TestCase):
    def test_empty_streak(self) -> None:
        self.assertEqual(current_streak([], date(2026, 11, 1)), 0)
        self.assertEqual(longest_streak([]), 0)

    def test_today_counts_when_completed(self) -> None:
        today = date(2026, 11, 1)
        days = [today - timedelta(days=i) for i in range(3)]
        self.assertEqual(current_streak(days, today), 3)

    def test_open_today_does_not_break_yesterday_streak(self) -> None:
        today = date(2026, 11, 1)
        days = [today - timedelta(days=i) for i in range(1, 4)]
        self.assertEqual(current_streak(days, today), 3)

    def test_missed_yesterday_breaks_streak(self) -> None:
        today = date(2026, 11, 1)
        days = [today - timedelta(days=2), today - timedelta(days=3)]
        self.assertEqual(current_streak(days, today), 0)
        self.assertEqual(longest_streak(days), 2)

    def test_longest_streak_handles_separate_runs(self) -> None:
        days = [
            date(2026, 10, 1),
            date(2026, 10, 2),
            date(2026, 10, 3),
            date(2026, 10, 8),
            date(2026, 10, 9),
        ]
        self.assertEqual(longest_streak(days), 3)
        self.assertEqual(current_streak(set(days), date(2026, 10, 9)), 2)

    def test_recent_completion_stops_at_tracking_start(self) -> None:
        today = date(2026, 11, 3)
        done = {today - timedelta(days=2), today}
        count, total = recent_completion(done, today, date(2026, 11, 1))
        self.assertEqual((count, total), (2, 3))

    def test_recent_completion_uses_seven_day_window(self) -> None:
        today = date(2026, 11, 10)
        done = {today - timedelta(days=i) for i in range(0, 10)}
        count, total = recent_completion(done, today, date(2026, 1, 1))
        self.assertEqual((count, total), (7, 7))


class ReminderTimeTests(unittest.TestCase):
    def test_parse_and_format(self) -> None:
        self.assertEqual(parse_hhmm("8:05").strftime("%H:%M"), "08:05")
        self.assertEqual(format_hhmm("08:05"), "08:05")
        with self.assertRaises(ValueError):
            parse_hhmm("25:00")

    def test_due_at_and_after_time(self) -> None:
        day = date(2026, 11, 1)
        self.assertFalse(reminder_has_passed(datetime(day.year, day.month, day.day, 20, 29), "20:30"))
        self.assertTrue(reminder_has_passed(datetime(day.year, day.month, day.day, 20, 30), "20:30"))
        self.assertTrue(reminder_has_passed(datetime(day.year, day.month, day.day, 23, 59), "20:30"))

    def test_quote_is_stable_per_day(self) -> None:
        first = question_for_day(date(2026, 11, 1))
        second = question_for_day(date(2026, 11, 1))
        self.assertEqual(first, second)
        self.assertTrue(first)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from dailygrind.models import current_streak
from dailygrind.store import Store


class MutableClock:
    def __init__(self, now: datetime) -> None:
        self.now = now

    def __call__(self) -> datetime:
        return self.now

    def advance_days(self, days: int) -> None:
        self.now += timedelta(days=days)


class StoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tempdir.name) / "dailygrind.db"
        self.clock = MutableClock(datetime(2026, 11, 1, 9, 0))
        self.store = Store(self.db_path, clock=self.clock)

    def tearDown(self) -> None:
        self.store.close()
        self.tempdir.cleanup()

    def complete_all(self) -> None:
        for task in self.store.list_tasks():
            self.store.complete_task(task.id)

    def test_defaults_are_seeded_once(self) -> None:
        tasks = self.store.list_tasks()
        self.assertEqual(
            [task.title for task in tasks],
            ["蓝桥杯真题", "六级词汇", "六级真题"],
        )
        self.assertEqual(tasks[1].target, 30)
        self.assertEqual(tasks[1].step, 5)
        self.assertEqual(self.store.get_setting("reminder_time"), "20:30")
        self.assertEqual(
            self.store.get_tracking_start().isoformat(), "2026-11-01"
        )

        self.store.close()
        self.store = Store(self.db_path, clock=self.clock)
        self.assertEqual(len(self.store.list_tasks()), 3)

    def test_partial_progress_and_completion(self) -> None:
        tasks = {task.title: task for task in self.store.list_tasks()}
        self.store.set_progress(tasks["六级词汇"].id, 15)
        snapshot = self.store.get_day_snapshot()
        self.assertEqual(snapshot.completed_tasks, 0)
        self.assertEqual(snapshot.percent, 47)
        self.assertTrue(self.store.has_progress())
        self.assertFalse(self.store.is_day_complete())

        self.complete_all()
        snapshot = self.store.get_day_snapshot()
        self.assertTrue(snapshot.all_done)
        self.assertTrue(self.store.is_day_complete())
        self.assertIn(self.clock.now.date(), self.store.completed_days())

    def test_progress_is_clamped_and_zero_removes_row(self) -> None:
        task = self.store.list_tasks()[1]
        self.assertEqual(self.store.set_progress(task.id, 999), 30)
        self.assertEqual(self.store.adjust_progress(task.id, 5), 30)
        self.assertEqual(self.store.adjust_progress(task.id, -100), 0)
        self.assertFalse(self.store.has_progress())

    def test_adding_task_reopens_a_completed_day(self) -> None:
        self.complete_all()
        self.assertTrue(self.store.is_day_complete())
        self.store.create_task("额外任务", target=1, unit="次")
        self.assertFalse(self.store.is_day_complete())

    def test_deleting_incomplete_task_can_complete_day(self) -> None:
        extra = self.store.create_task("额外任务", target=1, unit="次")
        self.complete_all()
        self.assertTrue(self.store.is_day_complete())
        self.store.set_progress(extra.id, 0)
        self.assertFalse(self.store.is_day_complete())
        self.store.delete_task(extra.id)
        self.assertTrue(self.store.is_day_complete())

    def test_raising_target_reopens_today(self) -> None:
        vocab = self.store.list_tasks()[1]
        self.complete_all()
        self.assertTrue(self.store.is_day_complete())
        self.store.update_task(
            vocab.id,
            title=vocab.title,
            description=vocab.description,
            target=40,
            unit=vocab.unit,
            icon=vocab.icon,
            step=vocab.step,
        )
        self.assertFalse(self.store.is_day_complete())
        self.assertEqual(self.store.get_amounts()[vocab.id], 30)

    def test_historical_completion_and_streak(self) -> None:
        self.complete_all()
        self.clock.advance_days(1)
        self.complete_all()
        completed = self.store.completed_days()
        self.assertEqual(len(completed), 2)
        self.assertEqual(current_streak(completed, self.clock.now.date()), 2)
        self.assertEqual(self.store.total_completed_days(), 2)

    def test_history_ranges_and_progress_days(self) -> None:
        task = self.store.list_tasks()[0]
        self.store.set_progress(task.id, 1, day=self.clock.now.date() - timedelta(days=2))
        self.complete_all()
        self.assertIn(
            self.clock.now.date() - timedelta(days=2),
            self.store.days_with_progress(),
        )
        self.assertEqual(
            self.store.completed_days(
                self.clock.now.date(), self.clock.now.date()
            ),
            {self.clock.now.date()},
        )

    def test_settings_round_trip(self) -> None:
        self.store.set_setting("reminder_enabled", "0")
        self.store.set_setting("reminder_time", "21:15")
        self.store.close()
        self.store = Store(self.db_path, clock=self.clock)
        self.assertEqual(self.store.get_setting("reminder_enabled"), "0")
        self.assertEqual(self.store.get_setting("reminder_time"), "21:15")

    def test_task_validation(self) -> None:
        with self.assertRaises(ValueError):
            self.store.create_task("   ")
        with self.assertRaises(ValueError):
            self.store.create_task("错误", target=0)
        with self.assertRaises(ValueError):
            self.store.update_task(
                999,
                title="不存在",
                description="",
                target=1,
                unit="次",
                icon="",
                step=1,
            )


if __name__ == "__main__":
    unittest.main()

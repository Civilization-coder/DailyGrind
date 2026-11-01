from __future__ import annotations

import tempfile
import tkinter as tk
import traceback
import unittest
from pathlib import Path
from unittest.mock import patch

from dailygrind.store import Store
from dailygrind.ui.main_window import DailyGrindApp
from dailygrind.ui.theme import BG
from dailygrind.ui.widgets import ScrollableFrame


class UiSmokeTests(unittest.TestCase):
    def setUp(self) -> None:
        try:
            self.root = tk.Tk()
        except tk.TclError as exc:
            self.skipTest(f"Tk unavailable: {exc}")
        self.root.withdraw()
        self.tempdir = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.tempdir.name) / "ui.db")
        self.store.set_setting("reminder_enabled", "0")
        self.errors: list[str] = []
        self.app = DailyGrindApp(self.root, self.store)
        self.app.start_minimized = True
        self.root.report_callback_exception = lambda *exc: self.errors.append(
            "".join(traceback.format_exception(*exc))
        )
        self.root.update_idletasks()
        self.root.update()

    def tearDown(self) -> None:
        try:
            self.app.shutdown()
        except Exception:
            pass
        try:
            self.root.destroy()
        except Exception:
            pass
        try:
            self.store.close()
        except Exception:
            pass
        self.tempdir.cleanup()

    def pump(self) -> None:
        self.root.update_idletasks()
        self.root.update()
        self.assertEqual(self.errors, [])

    def test_all_pages_render(self) -> None:
        for page in ("today", "vocab", "calendar", "settings", "today"):
            self.app.navigate(page)
            self.pump()
        self.assertEqual(self.app._current_page_key, "today")

    def test_progress_actions_update_day_record(self) -> None:
        tasks = self.store.list_tasks()
        self.app.change_progress(tasks[0].id, 1)
        self.pump()
        self.assertEqual(self.store.get_amounts()[tasks[0].id], 1)
        for task in self.store.list_tasks():
            self.app.complete_task(task.id)
        self.pump()
        self.assertTrue(self.store.is_day_complete())
        self.app.navigate("calendar")
        self.pump()

    def test_vocab_practice_flow(self) -> None:
        self.app.navigate("vocab")
        self.pump()
        page = self.app.pages["vocab"]
        page.start_study()
        self.pump()
        self.assertEqual(page.mode, "study")
        self.assertIsNotNone(page.current_word)
        correct_index = next(
            index
            for index, choice in enumerate(page.choices)
            if choice.correct
        )
        page._choose(correct_index)
        self.pump()
        self.assertEqual(len(self.store.get_all_vocab_progress()), 1)
        self.assertEqual(
            self.store.get_vocab_plan_stats(self.app.today)["completed"], 1
        )
        first_word = page.current_word.word
        page._next_word()
        self.pump()
        self.assertEqual(page.mode, "study")
        self.assertNotEqual(page.current_word.word, first_word)

    def test_add_task_dialog_submits(self) -> None:
        self.app.navigate("settings")
        self.pump()
        before = len(self.store.list_tasks())
        self.app.open_add_task()
        self.root.update_idletasks()
        dialog = self.app._task_dialog
        self.assertIsNotNone(dialog)
        assert dialog is not None
        dialog.withdraw()
        dialog._title_var.set("错题复盘")
        dialog._description_var.set("复盘当天的错题")
        dialog._target_var.set("10")
        dialog._unit_var.set("题")
        dialog._step_var.set("2")
        dialog._submit()
        self.pump()
        self.assertEqual(len(self.store.list_tasks()), before + 1)
        self.assertIsNone(self.app._task_dialog)
        self.pump()

    def test_edit_vocab_target_dialog(self) -> None:
        task = self.store.get_vocab_task()
        assert task is not None
        self.app.open_edit_task(task)
        self.root.update_idletasks()
        dialog = self.app._task_dialog
        self.assertIsNotNone(dialog)
        assert dialog is not None
        dialog.withdraw()
        dialog._target_var.set("12")
        dialog._submit()
        self.pump()
        updated = self.store.get_vocab_task()
        assert updated is not None
        self.assertEqual(updated.target, 12)
        self.assertIsNone(self.app._task_dialog)

    def test_builtin_vocab_task_cannot_be_deleted(self) -> None:
        task = self.store.get_vocab_task()
        assert task is not None
        with patch(
            "dailygrind.ui.main_window.messagebox.showinfo"
        ) as warning:
            self.app.delete_task(task)
        self.assertTrue(warning.called)
        self.assertIsNotNone(self.store.get_vocab_task())

    def test_delete_task_uses_confirmation(self) -> None:
        task = self.store.list_tasks()[0]
        title = task.title
        with patch(
            "dailygrind.ui.main_window.messagebox.askyesno",
            return_value=True,
        ):
            self.app.delete_task(task)
        self.pump()
        self.assertNotIn(title, [item.title for item in self.store.list_tasks()])

    def test_reminder_settings_round_trip(self) -> None:
        self.app.save_reminder_settings(True, "21:05")
        self.pump()
        self.assertEqual(self.app.reminder_hhmm, "21:05")
        self.assertTrue(self.app.scheduler.enabled)
        self.assertEqual(self.store.get_setting("reminder_time"), "21:05")
        self.assertEqual(self.store.get_setting("reminder_enabled"), "1")


class ScrollbarTests(unittest.TestCase):
    def setUp(self) -> None:
        try:
            self.root = tk.Tk()
        except tk.TclError as exc:
            self.skipTest(f"Tk unavailable: {exc}")
        self.root.geometry("420x320+10000+10000")
        try:
            self.root.attributes("-alpha", 0.0)
        except tk.TclError:
            pass
        self.errors: list[str] = []
        self.root.report_callback_exception = lambda *exc: self.errors.append(
            "".join(traceback.format_exception(*exc))
        )

    def tearDown(self) -> None:
        try:
            self.root.destroy()
        except Exception:
            pass

    def test_scrollbar_appears_for_tall_content(self) -> None:
        frame = ScrollableFrame(self.root, bg=BG)
        frame.pack(fill="both", expand=True)
        for index in range(60):
            tk.Label(
                frame.body,
                text=f"row {index}",
                bg=BG,
                anchor="w",
            ).pack(fill="x")
        for _ in range(3):
            self.root.update_idletasks()
            self.root.update()
        self.assertTrue(frame._scrollbar_visible)
        self.assertTrue(frame.scrollbar.winfo_ismapped())
        self.assertEqual(self.errors, [])
        frame.scrollbar._draw()


class StartupCommandTests(unittest.TestCase):
    def test_command_targets_project_entrypoint(self) -> None:
        from dailygrind.startup import startup_command

        command = startup_command()
        self.assertIn("app.py", command)
        self.assertIn("--minimized", command)


if __name__ == "__main__":
    unittest.main()

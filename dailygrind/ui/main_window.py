"""Application shell: navigation, controller actions and reminder timing."""

from __future__ import annotations

import sys
import tkinter as tk
from datetime import date, datetime, timedelta
from tkinter import messagebox

from .. import __version__
from ..models import current_streak, format_hhmm
from ..paths import APP_TITLE, DATA_DIR, ICON_PATH, open_path
from ..reminders import ReminderScheduler
from ..startup import is_startup_enabled, set_startup
from ..store import Store
from . import theme as th
from .calendar_page import CalendarPage
from .dialogs import ReminderDialog, TaskDialog
from .settings_page import SettingsPage
from .theme import S, draw_round_rect, font
from .today_page import TodayPage
from .widgets import NavButton, ProgressBar, TextButton


class DailyGrindApp:
    def __init__(
        self,
        root: tk.Tk,
        store: Store,
        *,
        start_minimized: bool = False,
    ) -> None:
        self.root = root
        self.store = store
        self.today: date = store.current_date()
        self.start_minimized = start_minimized

        th.configure_theme(root)
        root.configure(bg=th.BG)
        root.title(APP_TITLE)
        self._set_icon()
        self._set_window_geometry()
        root.protocol("WM_DELETE_WINDOW", self.on_close)
        root.report_callback_exception = self._report_callback_exception

        self._shutting_down = False
        self._tick_job: str | None = None
        self._tick_interval_ms = 1000
        self._modal_depth = 0
        self._task_dialog: TaskDialog | None = None
        self._reminder_dialog: ReminderDialog | None = None
        self._started_at = datetime.now()
        self._current_page_key = "today"

        self.reminder_enabled, self.reminder_hhmm = self._load_reminder_settings()
        self.scheduler = ReminderScheduler(
            enabled=self.reminder_enabled,
            reminder_hhmm=self.reminder_hhmm,
        )

        self.store.sync_day(self.today)
        self._build_shell()
        self._build_pages()
        self._refresh_page("today")
        self._update_sidebar()
        self._set_active_nav("today")
        self._bind_shortcuts()

        self.root.after(120, self._on_ready)
        self._schedule_tick()

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------
    def _set_icon(self) -> None:
        if ICON_PATH.exists():
            try:
                self.root.iconbitmap(default=str(ICON_PATH))
            except tk.TclError:
                pass

    def _set_window_geometry(self) -> None:
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        width = min(S(1180), max(S(900), screen_w - S(40)))
        height = min(S(850), max(S(610), screen_h - S(100)))
        x = max(0, (screen_w - width) // 2)
        y = max(0, (screen_h - height) // 2 - S(12))
        min_width = min(S(1000), max(S(780), screen_w - S(24)))
        min_height = min(S(640), max(S(540), screen_h - S(80)))
        self.root.minsize(min_width, min_height)
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def _build_shell(self) -> None:
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=1)

        self.sidebar = tk.Frame(
            self.root,
            bg=th.SIDEBAR,
            width=S(226),
            bd=0,
            highlightthickness=0,
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)
        self.sidebar.pack_propagate(False)

        self.page_host = tk.Frame(self.root, bg=th.BG)
        self.page_host.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)
        self.page_host.grid_rowconfigure(0, weight=1)
        self.page_host.grid_columnconfigure(0, weight=1)

        self._build_sidebar()

    def _build_sidebar(self) -> None:
        brand = tk.Frame(self.sidebar, bg=th.SIDEBAR)
        brand.pack(fill="x", padx=S(20), pady=(S(25), S(28)))

        logo = tk.Canvas(
            brand,
            width=S(44),
            height=S(44),
            bg=th.SIDEBAR,
            bd=0,
            highlightthickness=0,
        )
        logo.pack(side="left")
        draw_round_rect(
            logo,
            S(1),
            S(1),
            S(43),
            S(43),
            S(13),
            fill=th.SIDEBAR_TEXT,
        )
        logo.create_text(
            S(22),
            S(22),
            text="日",
            fill=th.SIDEBAR,
            font=font(18, "bold"),
        )
        logo.create_oval(
            S(33),
            S(5),
            S(39),
            S(11),
            fill=th.ORANGE,
            outline="",
        )

        wordmark = tk.Frame(brand, bg=th.SIDEBAR)
        wordmark.pack(side="left", padx=(S(11), 0))
        tk.Label(
            wordmark,
            text="日拱一卒",
            bg=th.SIDEBAR,
            fg=th.SIDEBAR_TEXT,
            font=font(15, "bold"),
            anchor="w",
        ).pack(fill="x")
        tk.Label(
            wordmark,
            text="D A I L Y   G R I N D",
            bg=th.SIDEBAR,
            fg=th.ORANGE,
            font=font(6, "bold"),
            anchor="w",
        ).pack(fill="x", pady=(S(2), 0))

        tagline = tk.Frame(self.sidebar, bg=th.SIDEBAR)
        tagline.pack(fill="x", padx=S(21), pady=(0, S(20)))
        tk.Label(
            tagline,
            text="把每天，过成积累。",
            bg=th.SIDEBAR,
            fg=th.SIDEBAR_MUTED,
            font=font(8),
            anchor="w",
        ).pack(fill="x")

        tk.Frame(self.sidebar, bg=th.SIDEBAR_LINE, height=S(1)).pack(
            fill="x", padx=S(20), pady=(0, S(16))
        )

        nav = tk.Frame(self.sidebar, bg=th.SIDEBAR)
        nav.pack(fill="x", padx=S(12))
        self._nav_buttons: dict[str, NavButton] = {}
        nav_items = (
            ("today", "今日计划"),
            ("calendar", "打卡日历"),
            ("settings", "任务设置"),
        )
        for key, label in nav_items:
            button = NavButton(
                nav,
                label,
                lambda page_key=key: self.navigate(page_key),
            )
            button.pack(fill="x", pady=S(2))
            self._nav_buttons[key] = button

        bottom = tk.Frame(self.sidebar, bg=th.SIDEBAR)
        bottom.pack(side="bottom", fill="x", padx=S(16), pady=(S(12), S(16)))
        status_card = tk.Frame(bottom, bg=th.SIDEBAR_2)
        status_card.pack(fill="x")
        status_inner = tk.Frame(status_card, bg=th.SIDEBAR_2)
        status_inner.pack(fill="x", padx=S(14), pady=S(13))

        tk.Label(
            status_inner,
            text="今日进度",
            bg=th.SIDEBAR_2,
            fg=th.SIDEBAR_MUTED,
            font=font(8),
            anchor="w",
        ).pack(fill="x")
        self._side_progress_label = tk.Label(
            status_inner,
            text="0 / 0 项",
            bg=th.SIDEBAR_2,
            fg=th.SIDEBAR_TEXT,
            font=font(16, "bold"),
            anchor="w",
        )
        self._side_progress_label.pack(fill="x", pady=(S(1), S(7)))
        self._side_progress = ProgressBar(
            status_inner,
            bg=th.SIDEBAR_2,
            track_color=th.SIDEBAR_LINE,
        )
        self._side_progress.pack(fill="x")
        self._side_streak_label = tk.Label(
            status_inner,
            text="连续 0 天",
            bg=th.SIDEBAR_2,
            fg=th.SIDEBAR_MUTED,
            font=font(8),
            anchor="w",
        )
        self._side_streak_label.pack(fill="x", pady=(S(8), 0))

        divider = tk.Frame(bottom, bg=th.SIDEBAR_LINE, height=S(1))
        divider.pack(fill="x", pady=(S(13), S(11)))
        self._side_date_label = tk.Label(
            bottom,
            text="",
            bg=th.SIDEBAR,
            fg=th.SIDEBAR_MUTED,
            font=font(8),
            anchor="w",
        )
        self._side_date_label.pack(fill="x", padx=S(3))
        row = tk.Frame(bottom, bg=th.SIDEBAR)
        row.pack(fill="x", padx=S(3), pady=(S(8), 0))
        self._side_version = tk.Label(
            row,
            text=f"v{__version__}",
            bg=th.SIDEBAR,
            fg=th.SIDEBAR_LINE,
            font=font(7),
            anchor="w",
        )
        self._side_version.pack(side="left")
        TextButton(
            row,
            "退出程序",
            self.on_close,
            fg=th.SIDEBAR_MUTED,
            hover_fg=th.ORANGE,
            bg=th.SIDEBAR,
            font_size=8,
        ).pack(side="right")

    def _build_pages(self) -> None:
        self.pages: dict[str, tk.Frame] = {
            "today": TodayPage(self.page_host, self),
            "calendar": CalendarPage(self.page_host, self),
            "settings": SettingsPage(self.page_host, self),
        }
        for page in self.pages.values():
            page.grid(row=0, column=0, sticky="nsew")
        self.pages["today"].tkraise()

    def _on_ready(self) -> None:
        self.root.update_idletasks()
        if self.start_minimized:
            self.root.iconify()
        else:
            self.root.lift()

    # ------------------------------------------------------------------
    # Navigation and refresh
    # ------------------------------------------------------------------
    def navigate(self, key: str) -> None:
        if key not in self.pages:
            return
        if key == self._current_page_key:
            self._refresh_page(key)
            return
        self._current_page_key = key
        page = self.pages[key]
        page.refresh()
        page.tkraise()
        self._set_active_nav(key)
        self._update_sidebar()

    def _refresh_page(self, key: str) -> None:
        page = self.pages.get(key)
        if page is not None:
            page.refresh()

    def _refresh_current_page(self) -> None:
        self._refresh_page(self._current_page_key)

    def _refresh_all_pages(self) -> None:
        for key in self.pages:
            self._refresh_page(key)

    def _set_active_nav(self, key: str) -> None:
        for nav_key, button in self._nav_buttons.items():
            button.set_active(nav_key == key)

    def _update_sidebar(self) -> None:
        snapshot = self.store.get_day_snapshot(self.today)
        completed_days = self.store.completed_days()
        streak = current_streak(completed_days, self.today)
        if snapshot.total_tasks == 0:
            self._side_progress_label.configure(
                text="还没有任务", font=font(12, "bold")
            )
            self._side_progress.set(0, th.ORANGE)
        else:
            self._side_progress_label.configure(
                text=f"{snapshot.completed_tasks} / {snapshot.total_tasks} 项",
                font=font(16, "bold"),
            )
            self._side_progress.set(snapshot.percent, th.ORANGE)
        streak_text = f"连续 {streak} 天"
        if snapshot.all_done:
            streak_text = "今天已收工 · 连续 {} 天".format(streak)
            self._side_progress_label.configure(fg=th.ORANGE)
        else:
            self._side_progress_label.configure(fg=th.SIDEBAR_TEXT)
        self._side_streak_label.configure(text=streak_text)
        self._side_date_label.configure(
            text=f"{self.today.year}.{self.today.month:02d}.{self.today.day:02d} · "
            f"周{'一二三四五六日'[self.today.weekday()]}"
        )

    # ------------------------------------------------------------------
    # Task / progress actions
    # ------------------------------------------------------------------
    def change_progress(self, task_id: int, delta: int) -> None:
        try:
            self.store.adjust_progress(task_id, delta, self.today)
        except ValueError as exc:
            messagebox.showerror("无法更新", str(exc), parent=self.root)
            return
        self._after_data_change()

    def set_progress_amount(self, task_id: int, amount: int) -> None:
        try:
            self.store.set_progress(task_id, amount, self.today)
        except ValueError as exc:
            messagebox.showerror("无法更新", str(exc), parent=self.root)
            return
        self._after_data_change()

    def complete_task(self, task_id: int) -> None:
        try:
            self.store.complete_task(task_id, self.today)
        except ValueError as exc:
            messagebox.showerror("无法更新", str(exc), parent=self.root)
            return
        self._after_data_change()

    def _after_data_change(self) -> None:
        self._refresh_current_page()
        self._update_sidebar()
        snapshot = self.store.get_day_snapshot(self.today)
        if snapshot.all_done:
            self._close_reminder_window()

    def open_add_task(self) -> None:
        self._open_task_dialog(None)

    def open_edit_task(self, task) -> None:
        self._open_task_dialog(task)

    def _open_task_dialog(self, task) -> None:
        if self._task_dialog is not None:
            try:
                self._task_dialog.lift()
                self._task_dialog.focus_force()
            except tk.TclError:
                self._task_dialog = None
            else:
                return

        def submit(payload: dict[str, object]) -> None:
            if task is None:
                self.store.create_task(**payload)  # type: ignore[arg-type]
            else:
                self.store.update_task(task.id, **payload)  # type: ignore[arg-type]
            self._refresh_current_page()
            self._update_sidebar()
            if self.store.get_day_snapshot(self.today).all_done:
                self._close_reminder_window()

        self.begin_modal()
        try:
            dialog = TaskDialog(self.root, on_submit=submit, task=task)
        except Exception:
            self.end_modal()
            raise
        self._task_dialog = dialog

        def on_destroy(event: tk.Event) -> None:
            if event.widget is dialog:
                self.end_modal()
                if self._task_dialog is dialog:
                    self._task_dialog = None

        dialog.bind("<Destroy>", on_destroy, add="+")

    def delete_task(self, task) -> None:
        self.begin_modal()
        try:
            confirmed = messagebox.askyesno(
                "删除任务",
                f"确定删除「{task.title}」吗？\n\n"
                "这项任务的今日和历史数量记录会一起删除；"
                "已经记录的全勤日期会保留。",
                parent=self.root,
            )
        finally:
            self.end_modal()
        if not confirmed:
            return
        try:
            self.store.delete_task(task.id)
        except Exception as exc:
            messagebox.showerror("删除失败", str(exc), parent=self.root)
            return
        self._refresh_current_page()
        self._update_sidebar()
        if self.store.get_day_snapshot(self.today).all_done:
            self._close_reminder_window()

    # ------------------------------------------------------------------
    # Reminder configuration and startup
    # ------------------------------------------------------------------
    def _load_reminder_settings(self) -> tuple[bool, str]:
        enabled = self.store.get_setting("reminder_enabled", "1") != "0"
        raw = self.store.get_setting("reminder_time", "20:30") or "20:30"
        try:
            hhmm = format_hhmm(raw)
        except ValueError:
            hhmm = "20:30"
            self.store.set_setting("reminder_time", hhmm)
        return enabled, hhmm

    def save_reminder_settings(self, enabled: bool, hhmm: str) -> None:
        normalized = format_hhmm(hhmm)
        self.store.set_setting("reminder_enabled", "1" if enabled else "0")
        self.store.set_setting("reminder_time", normalized)
        self.reminder_enabled = bool(enabled)
        self.reminder_hhmm = normalized
        self.scheduler.configure(self.reminder_enabled, self.reminder_hhmm)
        if not self.reminder_enabled:
            self._close_reminder_window()
        self.pages["today"].refresh()
        self._update_sidebar()

    def is_startup_enabled(self) -> bool:
        return is_startup_enabled()

    def set_startup_enabled(self, enabled: bool) -> None:
        set_startup(enabled)

    def open_data_folder(self) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        open_path(DATA_DIR)

    # ------------------------------------------------------------------
    # Reminder loop
    # ------------------------------------------------------------------
    def _schedule_tick(self) -> None:
        if self._shutting_down:
            return
        self._tick_job = self.root.after(self._tick_interval_ms, self._tick)

    def _tick(self) -> None:
        if self._shutting_down:
            return
        now = datetime.now()
        current_date = self.store.current_date()
        if current_date != self.today:
            self.today = current_date
            self.scheduler.reset()
            self._close_reminder_window()
            self.store.sync_day(self.today)
            self._refresh_all_pages()
            self._update_sidebar()
        self._maybe_show_reminder(now)
        self._schedule_tick()

    def _maybe_show_reminder(self, now: datetime) -> None:
        if self._modal_depth > 0 or self._task_dialog is not None:
            return
        if self._reminder_dialog is not None:
            try:
                if self._reminder_dialog.winfo_exists():
                    return
            except tk.TclError:
                self._reminder_dialog = None
        if now - self._started_at < timedelta(seconds=2):
            return
        snapshot = self.store.get_day_snapshot(self.today)
        if snapshot.total_tasks == 0 or snapshot.all_done:
            return
        if not self.scheduler.is_due(now, snapshot.all_done):
            return
        self._show_reminder(snapshot)

    def _show_reminder(self, snapshot) -> None:
        completed_days = self.store.completed_days()
        streak = current_streak(completed_days, self.today)
        try:
            dialog = ReminderDialog(
                self.root,
                snapshot,
                streak,
                self.reminder_hhmm,
                on_snooze=self._on_reminder_snoozed,
                on_go=self._on_reminder_go,
            )
        except Exception:
            self._report_callback_exception(*sys.exc_info())
            return
        self._reminder_dialog = dialog

        def clear_reference(event: tk.Event) -> None:
            if event.widget is dialog and self._reminder_dialog is dialog:
                self._reminder_dialog = None

        dialog.bind("<Destroy>", clear_reference, add="+")

    def _on_reminder_snoozed(self) -> None:
        self._reminder_dialog = None
        self.scheduler.snooze(datetime.now())

    def _on_reminder_go(self) -> None:
        self._reminder_dialog = None
        self.scheduler.dismiss_for_day(datetime.now())
        try:
            if self.root.state() == "iconic":
                self.root.deiconify()
            self.root.lift()
            self.root.focus_force()
        except tk.TclError:
            pass

    def _close_reminder_window(self) -> None:
        dialog = self._reminder_dialog
        self._reminder_dialog = None
        if dialog is not None:
            try:
                dialog.destroy()
            except tk.TclError:
                pass

    # ------------------------------------------------------------------
    # Modal tracking, shortcuts and shutdown
    # ------------------------------------------------------------------
    def begin_modal(self) -> None:
        self._modal_depth += 1

    def end_modal(self) -> None:
        self._modal_depth = max(0, self._modal_depth - 1)

    def _bind_shortcuts(self) -> None:
        self.root.bind("<Control-q>", lambda _event: self.on_close())
        self.root.bind("<Control-Key-1>", lambda _event: self.navigate("today"))
        self.root.bind("<Control-Key-2>", lambda _event: self.navigate("calendar"))
        self.root.bind("<Control-Key-3>", lambda _event: self.navigate("settings"))

    def on_close(self) -> None:
        if self._shutting_down:
            return
        snapshot = self.store.get_day_snapshot(self.today)
        incomplete = snapshot.total_tasks > 0 and not snapshot.all_done

        if incomplete and self.reminder_enabled:
            self.begin_modal()
            try:
                answer = messagebox.askyesnocancel(
                    "今天还没收工",
                    "要退出 DailyGrind 吗？\n\n"
                    "退出后今天的提醒会停止。\n\n"
                    "选择“是”：最小化到任务栏并继续提醒\n"
                    "选择“否”：直接退出\n"
                    "选择“取消”：返回继续做事",
                    parent=self.root,
                )
            finally:
                self.end_modal()
            if answer is None:
                return
            if answer:
                self.root.iconify()
                return
            self.shutdown()
            return

        self.begin_modal()
        try:
            confirm = messagebox.askyesno(
                "退出 DailyGrind",
                "确定要退出吗？退出后将停止每日提醒。",
                parent=self.root,
            )
        finally:
            self.end_modal()
        if confirm:
            self.shutdown()

    def shutdown(self) -> None:
        if self._shutting_down:
            return
        self._shutting_down = True
        if self._tick_job is not None:
            try:
                self.root.after_cancel(self._tick_job)
            except tk.TclError:
                pass
            self._tick_job = None
        self._close_reminder_window()
        try:
            self.root.destroy()
        finally:
            self.store.close()

    def _report_callback_exception(self, exc_type, exc_value, exc_traceback) -> None:
        import traceback

        detail = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        try:
            from ..paths import LOG_PATH

            LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
            with LOG_PATH.open("a", encoding="utf-8") as handle:
                handle.write(f"\n[{datetime.now():%Y-%m-%d %H:%M:%S}]\n{detail}")
        except Exception:
            pass
        try:
            messagebox.showerror(
                "DailyGrind 遇到问题",
                "程序遇到一个错误，详细信息已写入 data/dailygrind.log。\n\n"
                f"{exc_value}",
                parent=self.root,
            )
        except tk.TclError:
            pass

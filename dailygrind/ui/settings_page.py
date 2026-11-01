"""Settings page: task management, reminders, startup and data location."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from typing import TYPE_CHECKING

from .. import __version__
from ..models import Task, format_short_date_cn, weekday_cn
from ..paths import DATA_DIR
from . import theme as th
from .theme import S, draw_round_rect, font
from .widgets import (
    Pill,
    RoundedButton,
    ScrollableFrame,
    TextButton,
    ToggleSwitch,
    make_card,
)

if TYPE_CHECKING:
    from .main_window import DailyGrindApp


class SettingsPage(tk.Frame):
    def __init__(self, master: tk.Misc, app: "DailyGrindApp") -> None:
        super().__init__(master, bg=th.BG)
        self.app = app
        self.scroll = ScrollableFrame(self, bg=th.BG)
        self.scroll.pack(fill="both", expand=True)
        self.content = tk.Frame(self.scroll.body, bg=th.BG)
        self.content.pack(fill="both", expand=True, padx=S(34), pady=S(24))

        self._reminder_status: tk.Label | None = None
        self._startup_status: tk.Label | None = None
        self._time_widgets: list[tk.Spinbox] = []

    def refresh(self) -> None:
        fraction = self.scroll.scroll_fraction()
        for child in self.content.winfo_children():
            child.destroy()
        self._time_widgets = []

        self._build_header()
        self._build_tasks_section()
        self._build_reminder_section()
        self._build_app_section()
        self._build_about()
        self.scroll.restore_scroll(fraction)

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------
    def _build_header(self) -> None:
        header = tk.Frame(self.content, bg=th.BG)
        header.pack(fill="x", pady=(0, S(20)))
        left = tk.Frame(header, bg=th.BG)
        left.pack(side="left")
        tk.Label(
            left,
            text="设定你的节奏",
            bg=th.BG,
            fg=th.INK,
            font=font(22, "bold"),
            anchor="w",
        ).pack(fill="x")
        tk.Label(
            left,
            text="任务要具体，提醒要准时，剩下的交给重复。",
            bg=th.BG,
            fg=th.MUTED,
            font=font(9),
            anchor="w",
        ).pack(fill="x", pady=(S(5), 0))
        today = self.app.today
        Pill(
            header,
            f"{format_short_date_cn(today)} · {weekday_cn(today)}",
            bg=th.CARD,
            fg=th.SUBTEXT,
            font_size=9,
            padx=13,
            pady=6,
            parent_bg=th.BG,
        ).pack(side="right", anchor="n", pady=(S(4), 0))

    def _section_heading(
        self,
        title: str,
        subtitle: str,
        right_factory: Callable[[tk.Misc], tk.Widget] | None = None,
    ) -> None:
        row = tk.Frame(self.content, bg=th.BG)
        row.pack(fill="x", pady=(S(8), S(9)))
        left = tk.Frame(row, bg=th.BG)
        left.pack(side="left")
        tk.Label(
            left,
            text=title,
            bg=th.BG,
            fg=th.INK,
            font=font(13, "bold"),
            anchor="w",
        ).pack(fill="x")
        tk.Label(
            left,
            text=subtitle,
            bg=th.BG,
            fg=th.MUTED,
            font=font(8),
            anchor="w",
        ).pack(fill="x", pady=(S(2), 0))
        if right_factory is not None:
            right = right_factory(row)
            right.pack(side="right", pady=(S(5), 0))

    def _divider(self, master: tk.Misc) -> None:
        tk.Frame(master, bg=th.BORDER, height=S(1)).pack(fill="x")

    # ------------------------------------------------------------------
    # Tasks
    # ------------------------------------------------------------------
    def _build_tasks_section(self) -> None:
        self._section_heading(
            "每日任务",
            "目标可以小，但每天都要碰到它。",
            lambda parent: RoundedButton(
                parent,
                "＋ 添加任务",
                self.app.open_add_task,
                fill=th.GREEN,
                bg=th.BG,
                padx=13,
                pady=6,
                font_size=9,
            ),
        )

        card = make_card(self.content)
        card.pack(fill="x")
        inner = tk.Frame(card, bg=th.CARD)
        inner.pack(fill="x", padx=S(18), pady=S(5))

        tasks = self.app.store.list_tasks()
        if not tasks:
            empty = tk.Frame(inner, bg=th.CARD)
            empty.pack(fill="x", pady=S(18))
            tk.Label(
                empty,
                text="还没有任务。先加一项，不要一次排太满。",
                bg=th.CARD,
                fg=th.MUTED,
                font=font(9),
                anchor="w",
            ).pack(side="left")
            RoundedButton(
                empty,
                "添加任务",
                self.app.open_add_task,
                fill=th.GREEN_SOFT,
                hover_fill=th.tint(th.GREEN, 0.75),
                text_color=th.GREEN_DARK,
                bg=th.CARD,
                padx=12,
                pady=5,
                font_size=9,
            ).pack(side="right")
            return

        for index, task in enumerate(tasks):
            if index:
                self._divider(inner)
            self._build_task_row(inner, task)

    def _build_task_row(self, master: tk.Misc, task: Task) -> None:
        row = tk.Frame(master, bg=th.CARD)
        row.pack(fill="x", pady=S(11))

        badge = tk.Canvas(
            row,
            width=S(36),
            height=S(36),
            bg=th.CARD,
            bd=0,
            highlightthickness=0,
        )
        badge.pack(side="left")
        draw_round_rect(
            badge,
            S(1),
            S(1),
            S(35),
            S(35),
            S(10),
            fill=th.tint(task.color, 0.84),
        )
        badge.create_text(
            S(18),
            S(18),
            text=task.icon or task.title[:1],
            fill=task.color,
            font=font(12, "bold"),
        )

        copy = tk.Frame(row, bg=th.CARD)
        copy.pack(side="left", fill="x", expand=True, padx=(S(12), S(8)))
        tk.Label(
            copy,
            text=task.title,
            bg=th.CARD,
            fg=th.INK,
            font=font(10, "bold"),
            anchor="w",
        ).pack(fill="x")
        detail = f"每天 {task.target} {task.unit} · 每次 ±{task.step}"
        if task.description:
            detail = f"{detail} · {task.description}"
        tk.Label(
            copy,
            text=detail,
            bg=th.CARD,
            fg=th.MUTED,
            font=font(8),
            anchor="w",
        ).pack(fill="x", pady=(S(2), 0))

        TextButton(
            row,
            "删除",
            lambda current=task: self.app.delete_task(current),
            fg=th.FAINT,
            hover_fg=th.RED,
            bg=th.CARD,
            font_size=8,
        ).pack(side="right", padx=(S(10), 0))
        TextButton(
            row,
            "编辑",
            lambda current=task: self.app.open_edit_task(current),
            fg=th.MUTED,
            hover_fg=th.GREEN,
            bg=th.CARD,
            font_size=8,
        ).pack(side="right")

    # ------------------------------------------------------------------
    # Reminder
    # ------------------------------------------------------------------
    def _build_reminder_section(self) -> None:
        self._section_heading(
            "每日提醒",
            "只有程序在运行时才会提醒；可以配合下面的开机自启。",
        )
        card = make_card(self.content)
        card.pack(fill="x")
        inner = tk.Frame(card, bg=th.CARD)
        inner.pack(fill="x", padx=S(18), pady=S(15))

        top = tk.Frame(inner, bg=th.CARD)
        top.pack(fill="x")
        copy = tk.Frame(top, bg=th.CARD)
        copy.pack(side="left", fill="x", expand=True)
        tk.Label(
            copy,
            text="到点提醒我",
            bg=th.CARD,
            fg=th.INK,
            font=font(11, "bold"),
            anchor="w",
        ).pack(fill="x")
        tk.Label(
            copy,
            text="如果当天还有任务没完成，会弹出一个置顶提醒窗口。",
            bg=th.CARD,
            fg=th.MUTED,
            font=font(8),
            anchor="w",
        ).pack(fill="x", pady=(S(2), 0))
        self._reminder_toggle = ToggleSwitch(
            top,
            value=self.app.reminder_enabled,
            command=self._on_reminder_toggle,
            bg=th.CARD,
        )
        self._reminder_toggle.pack(side="right", pady=S(4))
        self._reminder_state_label = tk.Label(
            top,
            text="",
            bg=th.CARD,
            fg=th.MUTED,
            font=font(8),
        )
        self._reminder_state_label.pack(
            side="right", padx=(0, S(8)), pady=S(9)
        )

        self._divider(inner)

        time_row = tk.Frame(inner, bg=th.CARD)
        time_row.pack(fill="x", pady=(S(15), 0))
        tk.Label(
            time_row,
            text="提醒时间",
            bg=th.CARD,
            fg=th.SUBTEXT,
            font=font(9, "bold"),
            anchor="w",
        ).pack(side="left", pady=(0, S(2)))
        time_inputs = tk.Frame(time_row, bg=th.CARD)
        time_inputs.pack(side="left", padx=(S(14), 0))

        try:
            hour_text, minute_text = self.app.reminder_hhmm.split(":")
        except ValueError:
            hour_text, minute_text = "20", "30"
        self._hour_var = tk.StringVar(value=f"{int(hour_text):02d}")
        self._minute_var = tk.StringVar(value=f"{int(minute_text):02d}")
        self._hour_spin = self._time_spinbox(time_inputs, self._hour_var, 23)
        self._hour_spin.pack(side="left")
        tk.Label(
            time_inputs,
            text=":",
            bg=th.CARD,
            fg=th.SUBTEXT,
            font=font(13, "bold"),
        ).pack(side="left", padx=S(4))
        self._minute_spin = self._time_spinbox(time_inputs, self._minute_var, 59)
        self._minute_spin.pack(side="left")
        tk.Label(
            time_inputs,
            text="每天",
            bg=th.CARD,
            fg=th.MUTED,
            font=font(8),
        ).pack(side="left", padx=(S(7), 0))
        self._time_widgets = [self._hour_spin, self._minute_spin]

        self._save_button = RoundedButton(
            time_row,
            "保存提醒设置",
            self._save_reminder,
            fill=th.GREEN,
            bg=th.CARD,
            padx=14,
            pady=6,
            font_size=9,
        )
        self._save_button.pack(side="right")

        self._reminder_status = tk.Label(
            inner,
            text="",
            bg=th.CARD,
            fg=th.MUTED,
            font=font(8),
            anchor="w",
        )
        self._reminder_status.pack(fill="x", pady=(S(8), 0))
        self._on_reminder_toggle(
            self.app.reminder_enabled, update_status=False
        )

    def _time_spinbox(
        self,
        master: tk.Misc,
        variable: tk.StringVar,
        maximum: int,
    ) -> tk.Spinbox:
        return tk.Spinbox(
            master,
            from_=0,
            to=maximum,
            wrap=True,
            textvariable=variable,
            format="%02.0f",
            width=3,
            justify="center",
            font=font(12, "bold"),
            bg=th.CARD_TINT,
            fg=th.INK,
            buttonbackground=th.CARD_TINT,
            insertbackground=th.TEXT,
            disabledbackground=th.CARD_TINT,
            disabledforeground=th.FAINT,
            relief="flat",
            bd=0,
            highlightthickness=S(1),
            highlightbackground=th.BORDER,
            highlightcolor=th.GREEN,
        )

    def _on_reminder_toggle(
        self,
        value: bool,
        *,
        update_status: bool = True,
    ) -> None:
        state = "normal" if value else "disabled"
        for widget in self._time_widgets:
            widget.configure(state=state)
        if hasattr(self, "_reminder_state_label"):
            self._reminder_state_label.configure(
                text="已开启" if value else "已关闭",
                fg=th.GREEN_DARK if value else th.MUTED,
            )
        if update_status and self._reminder_status is not None:
            self._reminder_status.configure(
                text="提醒已开启，记得点击保存。" if value else "提醒已关闭，记得点击保存。",
                fg=th.MUTED,
            )

    def _save_reminder(self) -> None:
        if self._reminder_status is None:
            return
        try:
            hour = int(self._hour_var.get())
            minute = int(self._minute_var.get())
        except ValueError:
            self._reminder_status.configure(text="时间必须是 0 到 59 之间的整数。", fg=th.RED)
            return
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            self._reminder_status.configure(text="时间格式不正确。", fg=th.RED)
            return
        hhmm = f"{hour:02d}:{minute:02d}"
        try:
            self.app.save_reminder_settings(
                self._reminder_toggle.get(), hhmm
            )
        except Exception as exc:
            self._reminder_status.configure(text=f"保存失败：{exc}", fg=th.RED)
            return
        self._hour_var.set(f"{hour:02d}")
        self._minute_var.set(f"{minute:02d}")
        if self._reminder_toggle.get():
            message = f"已保存 · 每天 {hhmm} 提醒你"
        else:
            message = "已保存 · 每日提醒已关闭"
        self._reminder_status.configure(text=message, fg=th.GREEN_DARK)

    # ------------------------------------------------------------------
    # Startup and data
    # ------------------------------------------------------------------
    def _build_app_section(self) -> None:
        self._section_heading(
            "启动与数据",
            "所有记录只保存在这台电脑上。",
        )
        card = make_card(self.content)
        card.pack(fill="x")
        inner = tk.Frame(card, bg=th.CARD)
        inner.pack(fill="x", padx=S(18), pady=S(15))

        startup_row = tk.Frame(inner, bg=th.CARD)
        startup_row.pack(fill="x")
        startup_copy = tk.Frame(startup_row, bg=th.CARD)
        startup_copy.pack(side="left", fill="x", expand=True)
        tk.Label(
            startup_copy,
            text="开机自启",
            bg=th.CARD,
            fg=th.INK,
            font=font(11, "bold"),
            anchor="w",
        ).pack(fill="x")
        tk.Label(
            startup_copy,
            text="登录 Windows 后自动启动，并最小化到任务栏继续提醒。",
            bg=th.CARD,
            fg=th.MUTED,
            font=font(8),
            anchor="w",
        ).pack(fill="x", pady=(S(2), 0))
        try:
            startup_enabled = self.app.is_startup_enabled()
        except Exception:
            startup_enabled = False
        self._startup_toggle = ToggleSwitch(
            startup_row,
            value=startup_enabled,
            command=self._on_startup_toggle,
            bg=th.CARD,
        )
        self._startup_toggle.pack(side="right", pady=S(4))
        self._startup_state_label = tk.Label(
            startup_row,
            text="已开启" if startup_enabled else "未开启",
            bg=th.CARD,
            fg=th.GREEN_DARK if startup_enabled else th.MUTED,
            font=font(8),
        )
        self._startup_state_label.pack(
            side="right", padx=(0, S(8)), pady=S(9)
        )
        self._startup_status = tk.Label(
            inner,
            text=(
                "当前已开启。登录 Windows 后会自动启动。"
                if startup_enabled
                else "当前未开启。"
            ),
            bg=th.CARD,
            fg=th.MUTED,
            font=font(8),
            anchor="w",
        )
        self._startup_status.pack(fill="x", pady=(S(7), 0))

        self._divider(inner)

        data_row = tk.Frame(inner, bg=th.CARD)
        data_row.pack(fill="x", pady=(S(14), 0))
        data_copy = tk.Frame(data_row, bg=th.CARD)
        data_copy.pack(side="left", fill="x", expand=True)
        tk.Label(
            data_copy,
            text="数据位置",
            bg=th.CARD,
            fg=th.SUBTEXT,
            font=font(9, "bold"),
            anchor="w",
        ).pack(fill="x")
        tk.Label(
            data_copy,
            text=str(DATA_DIR),
            bg=th.CARD,
            fg=th.FAINT,
            font=font(8),
            anchor="w",
        ).pack(fill="x", pady=(S(3), 0))
        tk.Label(
            data_copy,
            text="备份时复制 dailygrind.db 即可。",
            bg=th.CARD,
            fg=th.MUTED,
            font=font(8),
            anchor="w",
        ).pack(fill="x", pady=(S(2), 0))
        RoundedButton(
            data_row,
            "打开文件夹",
            self._open_data_folder,
            fill=th.CARD_TINT,
            hover_fill=th.BG_SOFT,
            pressed_fill=th.TRACK,
            text_color=th.SUBTEXT,
            bg=th.CARD,
            outline=th.BORDER,
            padx=12,
            pady=5,
            font_size=9,
        ).pack(side="right", pady=S(4))

    def _on_startup_toggle(self, value: bool) -> None:
        try:
            self.app.set_startup_enabled(value)
        except Exception as exc:
            self._startup_toggle.set(not value)
            if hasattr(self, "_startup_state_label"):
                self._startup_state_label.configure(
                    text="已开启" if not value else "未开启",
                    fg=th.GREEN_DARK if not value else th.MUTED,
                )
            if self._startup_status is not None:
                self._startup_status.configure(
                    text=f"设置失败：{exc}",
                    fg=th.RED,
                )
            return
        if hasattr(self, "_startup_state_label"):
            self._startup_state_label.configure(
                text="已开启" if value else "未开启",
                fg=th.GREEN_DARK if value else th.MUTED,
            )
        if self._startup_status is not None:
            if value:
                text = "已开启。下次登录 Windows 时会自动启动。"
                color = th.GREEN_DARK
            else:
                text = "已关闭开机自启。"
                color = th.MUTED
            self._startup_status.configure(text=text, fg=color)

    def _open_data_folder(self) -> None:
        try:
            self.app.open_data_folder()
        except Exception as exc:
            if self._startup_status is not None:
                self._startup_status.configure(
                    text=f"无法打开文件夹：{exc}", fg=th.RED
                )

    def _build_about(self) -> None:
        footer = tk.Frame(self.content, bg=th.BG)
        footer.pack(fill="x", pady=(S(18), S(4)))
        tk.Label(
            footer,
            text=f"DailyGrind v{__version__}",
            bg=th.BG,
            fg=th.FAINT,
            font=font(8),
            anchor="w",
        ).pack(side="left")
        tk.Label(
            footer,
            text="不积跬步，无以至千里。",
            bg=th.BG,
            fg=th.FAINT,
            font=font(8),
            anchor="e",
        ).pack(side="right")

"""The Today page: daily progress, streak and task cards."""

from __future__ import annotations

import tkinter as tk
from datetime import timedelta
from tkinter import simpledialog
from typing import TYPE_CHECKING

from ..models import (
    DaySnapshot,
    TaskState,
    current_streak,
    format_date_cn,
    longest_streak,
    question_for_day,
    recent_completion,
)
from . import theme as th
from .theme import S, draw_round_rect, font
from .widgets import (
    Pill,
    ProgressBar,
    RingProgress,
    RoundedButton,
    ScrollableFrame,
    TextButton,
    make_card,
)

if TYPE_CHECKING:
    from .main_window import DailyGrindApp


def _shorten(text: str, limit: int) -> str:
    clean = " ".join(text.split())
    if len(clean) <= limit:
        return clean
    return clean[: max(0, limit - 1)] + "…"


class TodayPage(tk.Frame):
    def __init__(self, master: tk.Misc, app: "DailyGrindApp") -> None:
        super().__init__(master, bg=th.BG)
        self.app = app
        self.scroll = ScrollableFrame(self, bg=th.BG)
        self.scroll.pack(fill="both", expand=True)
        self.content = tk.Frame(self.scroll.body, bg=th.BG)
        self.content.pack(fill="both", expand=True, padx=S(34), pady=S(24))

    def refresh(self) -> None:
        fraction = self.scroll.scroll_fraction()
        for child in self.content.winfo_children():
            child.destroy()

        store = self.app.store
        today = self.app.today
        snapshot = store.get_day_snapshot(today)
        completed_days = store.completed_days()
        streak = current_streak(completed_days, today)
        best = longest_streak(completed_days)
        recent_done, recent_total = recent_completion(
            completed_days,
            today,
            store.get_tracking_start(),
            window=7,
        )

        self._build_header(today)
        self._build_hero(
            snapshot,
            streak,
            best,
            recent_done,
            recent_total,
            completed_days,
            store.days_with_progress(),
        )
        self._build_task_section(snapshot, best)
        self.scroll.restore_scroll(fraction)

    # ------------------------------------------------------------------
    # Header and hero cards
    # ------------------------------------------------------------------
    def _build_header(self, today) -> None:
        header = tk.Frame(self.content, bg=th.BG)
        header.pack(fill="x", pady=(0, S(20)))

        left = tk.Frame(header, bg=th.BG)
        left.pack(side="left")
        tk.Label(
            left,
            text="今天，继续日拱一卒。",
            bg=th.BG,
            fg=th.INK,
            font=font(22, "bold"),
            anchor="w",
        ).pack(fill="x")
        tk.Label(
            left,
            text="把大目标拆成今天能完成的小事。",
            bg=th.BG,
            fg=th.MUTED,
            font=font(9),
            anchor="w",
        ).pack(fill="x", pady=(S(5), 0))

        right = tk.Frame(header, bg=th.BG)
        right.pack(side="right")
        Pill(
            right,
            format_date_cn(today),
            bg=th.CARD,
            fg=th.SUBTEXT,
            font_size=9,
            padx=13,
            pady=6,
            parent_bg=th.BG,
        ).pack(anchor="e")
        if self.app.reminder_enabled:
            reminder_text = f"每日提醒 · {self.app.reminder_hhmm}"
        else:
            reminder_text = "提醒已关闭"
        tk.Label(
            right,
            text=reminder_text,
            bg=th.BG,
            fg=th.FAINT,
            font=font(8),
            anchor="e",
        ).pack(anchor="e", pady=(S(6), 0))

    def _build_hero(
        self,
        snapshot: DaySnapshot,
        streak: int,
        best: int,
        recent_done: int,
        recent_total: int,
        completed_days: set,
        progress_days: set,
    ) -> None:
        hero = tk.Frame(self.content, bg=th.BG)
        hero.pack(fill="x")
        hero.grid_columnconfigure(0, weight=5, uniform="hero")
        hero.grid_columnconfigure(1, weight=3, uniform="hero")
        hero.grid_rowconfigure(0, weight=1)

        summary = make_card(hero)
        summary.grid(row=0, column=0, sticky="nsew", padx=(0, S(9)))
        inner = tk.Frame(summary, bg=th.CARD)
        inner.pack(fill="both", expand=True, padx=S(22), pady=S(18))

        ring = RingProgress(inner, size=124, bg=th.CARD)
        ring.pack(side="left")
        ring.set(snapshot.percent, th.GREEN if snapshot.all_done else th.GREEN)

        info = tk.Frame(inner, bg=th.CARD)
        info.pack(side="left", fill="both", expand=True, padx=(S(20), 0))

        eyebrow = tk.Frame(info, bg=th.CARD)
        eyebrow.pack(fill="x")
        tk.Frame(eyebrow, bg=th.ORANGE, width=S(18), height=S(3)).pack(
            side="left", pady=(S(4), 0)
        )
        tk.Label(
            eyebrow,
            text="  TODAY / 今日进度",
            bg=th.CARD,
            fg=th.ORANGE_DARK,
            font=font(8, "bold"),
            anchor="w",
        ).pack(side="left")

        if not snapshot.states:
            headline = "还没有任务"
            tail = "去设置里添加第一项每日任务吧。"
        elif snapshot.all_done:
            headline = "全部完成"
            tail = f"连续打卡第 {streak} 天，收工。"
        else:
            headline = f"{snapshot.completed_tasks} / {snapshot.total_tasks} 项完成"
            tail = f"还差 {snapshot.remaining_tasks} 项，完成比完美重要。"

        tk.Label(
            info,
            text=headline,
            bg=th.CARD,
            fg=th.INK,
            font=font(19, "bold"),
            anchor="w",
        ).pack(fill="x", pady=(S(11), S(3)))
        tk.Label(
            info,
            text=tail,
            bg=th.CARD,
            fg=th.SUBTEXT,
            font=font(9),
            anchor="w",
        ).pack(fill="x")

        progress = ProgressBar(info, bg=th.CARD)
        progress.pack(fill="x", pady=(S(12), S(9)))
        progress.set(snapshot.percent, th.GREEN if snapshot.all_done else th.ORANGE)

        tk.Label(
            info,
            text=question_for_day(self.app.today),
            bg=th.CARD,
            fg=th.FAINT,
            font=font(8),
            anchor="w",
            justify="left",
            wraplength=S(370),
        ).pack(fill="x")

        streak_card = tk.Frame(
            hero,
            bg=th.SIDEBAR,
            bd=0,
            highlightthickness=0,
        )
        streak_card.grid(row=0, column=1, sticky="nsew", padx=(S(9), 0))
        streak_inner = tk.Frame(streak_card, bg=th.SIDEBAR)
        streak_inner.pack(fill="both", expand=True, padx=S(22), pady=S(17))

        streak_header = tk.Frame(streak_inner, bg=th.SIDEBAR)
        streak_header.pack(fill="x")
        tk.Label(
            streak_header,
            text="连续打卡",
            bg=th.SIDEBAR,
            fg=th.SIDEBAR_MUTED,
            font=font(9),
            anchor="w",
        ).pack(side="left")
        tk.Label(
            streak_header,
            text=f"最长 {best} 天",
            bg=th.SIDEBAR,
            fg=th.SIDEBAR_MUTED,
            font=font(8),
            anchor="e",
        ).pack(side="right")

        number_row = tk.Frame(streak_inner, bg=th.SIDEBAR)
        number_row.pack(fill="x", pady=(S(2), 0))
        tk.Label(
            number_row,
            text=str(streak),
            bg=th.SIDEBAR,
            fg=th.SIDEBAR_TEXT,
            font=font(36, "bold"),
            anchor="w",
        ).pack(side="left")
        tk.Label(
            number_row,
            text="天",
            bg=th.SIDEBAR,
            fg=th.SIDEBAR_MUTED,
            font=font(11),
            anchor="sw",
        ).pack(side="left", padx=(S(5), 0), pady=(0, S(8)))

        status_text = (
            "今天也守住了，很好。"
            if self.app.today in completed_days
            else ("今天完成后，就从 1 开始。" if streak == 0 else "今天完成，就能继续往上加。")
        )
        tk.Label(
            streak_inner,
            text=status_text,
            bg=th.SIDEBAR,
            fg=th.SIDEBAR_MUTED,
            font=font(8),
            anchor="w",
        ).pack(fill="x", pady=(S(2), S(10)))

        week_header = tk.Frame(streak_inner, bg=th.SIDEBAR)
        week_header.pack(fill="x")
        tk.Label(
            week_header,
            text="近 7 天",
            bg=th.SIDEBAR,
            fg=th.SIDEBAR_MUTED,
            font=font(8),
            anchor="w",
        ).pack(side="left")
        tk.Label(
            week_header,
            text=f"{recent_done} / {recent_total}",
            bg=th.SIDEBAR,
            fg=th.SIDEBAR_TEXT,
            font=font(8, "bold"),
            anchor="e",
        ).pack(side="right")

        dots = tk.Frame(streak_inner, bg=th.SIDEBAR)
        dots.pack(fill="x", pady=(S(5), 0))
        for index in range(7):
            column = tk.Frame(dots, bg=th.SIDEBAR)
            column.grid(row=0, column=index, sticky="ew")
            dots.grid_columnconfigure(index, weight=1)
            day = self.app.today - timedelta(days=6 - index)
            is_done = day in completed_days
            has_progress = day in progress_days
            color = (
                th.ORANGE
                if is_done
                else (th.AMBER if has_progress else th.SIDEBAR_LINE)
            )
            tk.Label(
                column,
                text="●",
                bg=th.SIDEBAR,
                fg=color,
                font=font(10),
            ).pack()
            tk.Label(
                column,
                text="一二三四五六日"[day.weekday()],
                bg=th.SIDEBAR,
                fg=th.SIDEBAR_MUTED if day != self.app.today else th.SIDEBAR_TEXT,
                font=font(7),
            ).pack(pady=(S(1), 0))

    # ------------------------------------------------------------------
    # Task list
    # ------------------------------------------------------------------
    def _build_task_section(self, snapshot: DaySnapshot, best: int) -> None:
        section = tk.Frame(self.content, bg=th.BG)
        section.pack(fill="x", pady=(S(22), S(9)))
        tk.Label(
            section,
            text="今日清单",
            bg=th.BG,
            fg=th.INK,
            font=font(14, "bold"),
            anchor="w",
        ).pack(side="left")
        Pill(
            section,
            f"{snapshot.completed_tasks} / {snapshot.total_tasks} 已完成",
            bg=th.CARD,
            fg=th.MUTED,
            font_size=8,
            padx=9,
            pady=3,
            parent_bg=th.BG,
        ).pack(side="left", padx=(S(9), 0), pady=(S(3), 0))
        TextButton(
            section,
            "管理任务",
            lambda: self.app.navigate("settings"),
            fg=th.MUTED,
            hover_fg=th.GREEN,
            bg=th.BG,
            font_size=9,
        ).pack(side="right", pady=(S(3), 0))

        if not snapshot.states:
            self._build_empty_state()
            return

        for index, state in enumerate(snapshot.states):
            card = self._build_task_card(state)
            card.pack(fill="x", pady=(0, S(9)))
            if index == len(snapshot.states) - 1 and snapshot.all_done:
                footer = tk.Frame(self.content, bg=th.BG)
                footer.pack(fill="x", pady=(S(8), 0))
                tk.Label(
                    footer,
                    text="今天的承诺已经全部兑现。明天见。",
                    bg=th.BG,
                    fg=th.GREEN_DARK,
                    font=font(9),
                    anchor="w",
                ).pack(side="left")
                if best > 0:
                    tk.Label(
                        footer,
                        text=f"最长连续 {best} 天",
                        bg=th.BG,
                        fg=th.FAINT,
                        font=font(8),
                        anchor="e",
                    ).pack(side="right")

    def _build_empty_state(self) -> None:
        card = make_card(self.content)
        card.pack(fill="x")
        inner = tk.Frame(card, bg=th.CARD)
        inner.pack(fill="x", padx=S(24), pady=S(26))
        badge = tk.Canvas(
            inner,
            width=S(48),
            height=S(48),
            bg=th.CARD,
            bd=0,
            highlightthickness=0,
        )
        badge.pack(side="left")
        draw_round_rect(
            badge,
            S(1),
            S(1),
            S(47),
            S(47),
            S(14),
            fill=th.GREEN_SOFT,
        )
        badge.create_text(
            S(24),
            S(24),
            text="日",
            fill=th.GREEN_DARK,
            font=font(17, "bold"),
        )
        text = tk.Frame(inner, bg=th.CARD)
        text.pack(side="left", fill="x", expand=True, padx=(S(14), 0))
        tk.Label(
            text,
            text="今天还没有安排",
            bg=th.CARD,
            fg=th.INK,
            font=font(12, "bold"),
            anchor="w",
        ).pack(fill="x")
        tk.Label(
            text,
            text="先加一件今天能完成的小事，别一次排太满。",
            bg=th.CARD,
            fg=th.MUTED,
            font=font(9),
            anchor="w",
        ).pack(fill="x", pady=(S(3), 0))
        RoundedButton(
            inner,
            "添加任务",
            self.app.open_add_task,
            fill=th.GREEN,
            bg=th.CARD,
            padx=14,
            pady=7,
            font_size=9,
        ).pack(side="right")

    def _build_task_card(self, state: TaskState) -> tk.Frame:
        task = state.task
        is_vocab = task.kind == "vocab"
        border_color = th.tint(task.color, 0.62) if state.completed else th.BORDER
        card = tk.Frame(
            self.content,
            bg=th.CARD,
            bd=0,
            highlightthickness=S(1),
            highlightbackground=border_color,
            highlightcolor=border_color,
        )
        inner = tk.Frame(card, bg=th.CARD)
        inner.pack(fill="x", padx=S(17), pady=S(14))

        top = tk.Frame(inner, bg=th.CARD)
        top.pack(fill="x")

        badge = tk.Canvas(
            top,
            width=S(44),
            height=S(44),
            bg=th.CARD,
            bd=0,
            highlightthickness=0,
        )
        badge.pack(side="left")
        draw_round_rect(
            badge,
            S(1),
            S(1),
            S(43),
            S(43),
            S(13),
            fill=th.tint(task.color, 0.84),
        )
        badge.create_text(
            S(22),
            S(22),
            text=task.icon or task.title[:1],
            fill=task.color,
            font=font(15, "bold"),
        )

        copy = tk.Frame(top, bg=th.CARD)
        copy.pack(side="left", fill="x", expand=True, padx=(S(13), S(10)))
        tk.Label(
            copy,
            text=_shorten(task.title, 22),
            bg=th.CARD,
            fg=th.INK,
            font=font(12, "bold"),
            anchor="w",
        ).pack(fill="x")
        description = _shorten(task.description, 42) if task.description else "每天做一点，别让今天空着。"
        tk.Label(
            copy,
            text=description,
            bg=th.CARD,
            fg=th.MUTED,
            font=font(8),
            anchor="w",
        ).pack(fill="x", pady=(S(3), 0))

        if state.completed:
            Pill(
                top,
                "已完成",
                bg=th.GREEN_SOFT,
                fg=th.GREEN_DARK,
                font_size=8,
                padx=10,
                pady=4,
                parent_bg=th.CARD,
            ).pack(side="right", pady=S(10))
        elif is_vocab:
            RoundedButton(
                top,
                "去背单词",
                self.app.open_vocab_study,
                fill=th.GREEN,
                hover_fill=th.shade(th.GREEN, 0.08),
                pressed_fill=th.shade(th.GREEN, 0.16),
                text_color=th.WHITE,
                bg=th.CARD,
                padx=13,
                pady=5,
                font_size=9,
            ).pack(side="right", pady=S(6))
        else:
            RoundedButton(
                top,
                "打卡",
                lambda task_id=task.id: self.app.complete_task(task_id),
                fill=th.GREEN_SOFT,
                hover_fill=th.tint(th.GREEN, 0.74),
                pressed_fill=th.tint(th.GREEN, 0.64),
                text_color=th.GREEN_DARK,
                bg=th.CARD,
                padx=12,
                pady=5,
                font_size=9,
            ).pack(side="right", pady=S(6))

        bottom = tk.Frame(inner, bg=th.CARD)
        bottom.pack(fill="x", pady=(S(9), 0), padx=(S(57), 0))
        bottom.grid_columnconfigure(2, weight=1)

        tk.Label(
            bottom,
            text=state.amount_text,
            bg=th.CARD,
            fg=th.GREEN_DARK if state.completed else th.SUBTEXT,
            font=font(9, "bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="w")

        if is_vocab:
            TextButton(
                bottom,
                "词库自动记录",
                lambda: self.app.navigate("vocab"),
                fg=th.FAINT,
                hover_fg=th.GREEN,
                bg=th.CARD,
                font_size=8,
            ).grid(row=0, column=1, sticky="w", padx=(S(7), S(12)))
            progress = ProgressBar(bottom, bg=th.CARD)
            progress.grid(row=0, column=2, sticky="ew", padx=(0, S(12)))
            progress.set(
                state.percent,
                task.color if not state.completed else th.GREEN,
            )
            return card

        TextButton(
            bottom,
            "修改",
            lambda current=state: self._edit_amount(current),
            fg=th.FAINT,
            hover_fg=th.GREEN,
            bg=th.CARD,
            font_size=8,
        ).grid(row=0, column=1, sticky="w", padx=(S(7), S(12)))

        progress = ProgressBar(bottom, bg=th.CARD)
        progress.grid(row=0, column=2, sticky="ew", padx=(0, S(12)))
        progress.set(state.percent, task.color if not state.completed else th.GREEN)

        minus = RoundedButton(
            bottom,
            "−",
            lambda task_id=task.id: self.app.change_progress(task_id, -task.step),
            fill=th.CARD_TINT,
            hover_fill=th.BG_SOFT,
            pressed_fill=th.TRACK,
            text_color=th.SUBTEXT,
            bg=th.CARD,
            outline=th.BORDER,
            padx=10,
            pady=4,
            font_size=12,
        )
        minus.grid(row=0, column=3, sticky="e")
        minus.set_enabled(state.amount > 0)

        plus = RoundedButton(
            bottom,
            f"+{task.step}",
            lambda task_id=task.id: self.app.change_progress(task_id, task.step),
            fill=th.GREEN_SOFT,
            hover_fill=th.tint(th.GREEN, 0.73),
            pressed_fill=th.tint(th.GREEN, 0.63),
            text_color=th.GREEN_DARK,
            bg=th.CARD,
            padx=10,
            pady=4,
            font_size=9,
        )
        plus.grid(row=0, column=4, sticky="e", padx=(S(7), 0))
        plus.set_enabled(not state.completed)

        return card

    def _edit_amount(self, state: TaskState) -> None:
        self.app.begin_modal()
        try:
            value = simpledialog.askinteger(
                "修改今日进度",
                f"「{state.task.title}」今天完成了多少{state.task.unit}？",
                parent=self,
                initialvalue=state.capped_amount,
                minvalue=0,
                maxvalue=state.task.target,
            )
        finally:
            self.app.end_modal()
        if value is not None:
            self.app.set_progress_amount(state.task.id, int(value))

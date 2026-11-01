"""Calendar and historical statistics page."""

from __future__ import annotations

import calendar
import tkinter as tk
from datetime import date, timedelta
from typing import TYPE_CHECKING

from ..models import (
    current_streak,
    format_month_cn,
    format_short_date_cn,
    longest_streak,
    recent_completion,
    weekday_cn,
)
from . import theme as th
from .theme import S, draw_round_rect, font
from .widgets import Pill, RoundedButton, ScrollableFrame, TextButton, make_card

if TYPE_CHECKING:
    from .main_window import DailyGrindApp


class CalendarGrid(tk.Canvas):
    WEEKDAY_LABELS = ("一", "二", "三", "四", "五", "六", "日")

    def __init__(
        self,
        master: tk.Misc,
        year: int,
        month: int,
        completed: set[date],
        partial: set[date],
        today: date,
        selected: date | None,
        on_select,
    ) -> None:
        super().__init__(
            master,
            height=S(362),
            bg=th.CARD,
            bd=0,
            highlightthickness=0,
            cursor="hand2",
        )
        self.year = year
        self.month = month
        self.completed = set(completed)
        self.partial = set(partial)
        self.today = today
        self.selected = selected
        self._on_select = on_select
        self._hovered: date | None = None
        self._leading = date(year, month, 1).weekday()
        self._days = calendar.monthrange(year, month)[1]
        self.bind("<Configure>", lambda _event: self._draw())
        self.bind("<Button-1>", self._handle_click)
        self.bind("<Motion>", self._handle_motion)
        self.bind("<Leave>", self._handle_leave)

    def _layout(self) -> tuple[int, int, float, float]:
        width = max(1, self.winfo_width())
        height = max(1, self.winfo_height())
        header_h = S(31)
        cell_w = width / 7
        cell_h = max(S(38), (height - header_h) / 6)
        return width, height, cell_w, cell_h

    def _day_from_position(self, x: float, y: float) -> date | None:
        _width, _height, cell_w, cell_h = self._layout()
        header_h = S(31)
        if y < header_h or x < 0 or y > header_h + cell_h * 6:
            return None
        column = int(x // cell_w)
        row = int((y - header_h) // cell_h)
        index = row * 7 + column - self._leading
        if column < 0 or column > 6 or index < 0 or index >= self._days:
            return None
        return date(self.year, self.month, index + 1)

    def _draw(self) -> None:
        self.delete("all")
        width, height, cell_w, cell_h = self._layout()
        if width <= 1 or height <= 1:
            return
        header_h = S(31)

        for column, label in enumerate(self.WEEKDAY_LABELS):
            x = column * cell_w + cell_w / 2
            self.create_text(
                x,
                header_h / 2,
                text=label,
                fill=th.MUTED,
                font=font(8, "bold"),
            )

        for index in range(self._days):
            day_num = index + 1
            current = date(self.year, self.month, day_num)
            absolute = self._leading + index
            row = absolute // 7
            column = absolute % 7
            center_x = column * cell_w + cell_w / 2
            center_y = header_h + row * cell_h + cell_h / 2
            is_done = current in self.completed
            has_progress = current in self.partial
            is_today = current == self.today
            is_selected = current == self.selected
            is_hovered = current == self._hovered
            is_future = current > self.today

            if is_selected or is_hovered:
                inset_x = S(6)
                inset_y = S(5)
                draw_round_rect(
                    self,
                    column * cell_w + inset_x,
                    header_h + row * cell_h + inset_y,
                    (column + 1) * cell_w - inset_x,
                    header_h + (row + 1) * cell_h - inset_y,
                    S(10),
                    fill=th.GREEN_PALE if is_selected else th.BG_SOFT,
                )

            radius = S(15)
            if is_done:
                self.create_oval(
                    center_x - radius,
                    center_y - radius,
                    center_x + radius,
                    center_y + radius,
                    fill=th.GREEN,
                    outline=th.ORANGE if is_today else "",
                    width=S(2) if is_today else 0,
                )
            elif is_today:
                self.create_oval(
                    center_x - radius,
                    center_y - radius,
                    center_x + radius,
                    center_y + radius,
                    fill="",
                    outline=th.ORANGE,
                    width=S(2),
                )

            if is_done:
                text_color = th.WHITE
            elif is_future:
                text_color = th.FAINT
            elif is_today:
                text_color = th.ORANGE_DARK
            else:
                text_color = th.INK
            self.create_text(
                center_x,
                center_y - (S(2) if has_progress and not is_done else 0),
                text=str(day_num),
                fill=text_color,
                font=font(9, "bold" if is_done or is_today else "normal"),
            )

            if has_progress and not is_done:
                self.create_oval(
                    center_x - S(2),
                    center_y + S(12),
                    center_x + S(2),
                    center_y + S(16),
                    fill=th.AMBER,
                    outline="",
                )

        if self.month == self.today.year and self.month == self.today.month:
            self.create_line(
                S(2),
                height - S(2),
                width - S(2),
                height - S(2),
                fill=th.BG_SOFT,
            )

    def _handle_click(self, event: tk.Event) -> None:
        day = self._day_from_position(event.x, event.y)
        if day is None:
            return
        self.selected = day
        self._draw()
        self._on_select(day)

    def _handle_motion(self, event: tk.Event) -> None:
        day = self._day_from_position(event.x, event.y)
        if day != self._hovered:
            self._hovered = day
            self.configure(cursor="hand2" if day else "arrow")
            self._draw()

    def _handle_leave(self, _event: tk.Event) -> None:
        if self._hovered is not None:
            self._hovered = None
            self._draw()


class CalendarPage(tk.Frame):
    def __init__(self, master: tk.Misc, app: "DailyGrindApp") -> None:
        super().__init__(master, bg=th.BG)
        self.app = app
        today = app.today
        self.view_year = today.year
        self.view_month = today.month
        self.selected: date | None = today

        self.scroll = ScrollableFrame(self, bg=th.BG)
        self.scroll.pack(fill="both", expand=True)
        self.content = tk.Frame(self.scroll.body, bg=th.BG)
        self.content.pack(fill="both", expand=True, padx=S(34), pady=S(24))
        self._footer_label: tk.Label | None = None

    def refresh(self) -> None:
        fraction = self.scroll.scroll_fraction()
        for child in self.content.winfo_children():
            child.destroy()

        store = self.app.store
        today = self.app.today
        all_completed = store.completed_days()
        streak = current_streak(all_completed, today)
        best = longest_streak(all_completed)
        recent_done, recent_total = recent_completion(
            all_completed, today, store.get_tracking_start(), window=7
        )
        tracking_start = store.get_tracking_start()

        if (
            self.selected is None
            and self.view_year == today.year
            and self.view_month == today.month
        ):
            self.selected = today

        self._build_header(today)
        self._build_stats(
            streak,
            best,
            len(all_completed),
            recent_done,
            recent_total,
            tracking_start,
        )
        self._build_calendar_card(all_completed, store.days_with_progress())

        self.scroll.restore_scroll(fraction)

    def _build_header(self, today: date) -> None:
        header = tk.Frame(self.content, bg=th.BG)
        header.pack(fill="x", pady=(0, S(20)))
        left = tk.Frame(header, bg=th.BG)
        left.pack(side="left")
        tk.Label(
            left,
            text="打卡日历",
            bg=th.BG,
            fg=th.INK,
            font=font(22, "bold"),
            anchor="w",
        ).pack(fill="x")
        tk.Label(
            left,
            text="每一格记录，都是那天没有放弃的证据。",
            bg=th.BG,
            fg=th.MUTED,
            font=font(9),
            anchor="w",
        ).pack(fill="x", pady=(S(5), 0))
        Pill(
            header,
            f"今天 · {format_short_date_cn(today)}",
            bg=th.CARD,
            fg=th.SUBTEXT,
            font_size=9,
            padx=13,
            pady=6,
            parent_bg=th.BG,
        ).pack(side="right", anchor="n", pady=(S(4), 0))

    def _build_stats(
        self,
        streak: int,
        best: int,
        total: int,
        recent_done: int,
        recent_total: int,
        tracking_start: date,
    ) -> None:
        stats = tk.Frame(self.content, bg=th.BG)
        stats.pack(fill="x", pady=(0, S(17)))
        for column in range(4):
            stats.grid_columnconfigure(column, weight=1, uniform="stats")

        percent = (
            int(recent_done / recent_total * 100 + 0.5) if recent_total else 0
        )
        values = (
            ("当前连续", f"{streak}", "天", th.GREEN, "今天未完成也不清零"),
            ("最长连续", f"{best}", "天", th.ORANGE, "历史最好的自己"),
            ("累计全勤", f"{total}", "天", th.BLUE, f"从 {tracking_start.year}.{tracking_start.month:02d} 开始"),
            ("近 7 天", f"{recent_done} / {recent_total}", "", th.AMBER, f"完成率 {percent}%"),
        )
        for column, (label, value, unit, color, note) in enumerate(values):
            card = make_card(stats)
            card.grid(
                row=0,
                column=column,
                sticky="nsew",
                padx=(0 if column == 0 else S(5), 0 if column == 3 else S(5)),
            )
            inner = tk.Frame(card, bg=th.CARD)
            inner.pack(fill="both", expand=True, padx=S(15), pady=S(13))
            tk.Label(
                inner,
                text=label,
                bg=th.CARD,
                fg=th.MUTED,
                font=font(8),
                anchor="w",
            ).pack(fill="x")
            value_row = tk.Frame(inner, bg=th.CARD)
            value_row.pack(fill="x", pady=(S(3), S(1)))
            tk.Label(
                value_row,
                text=value,
                bg=th.CARD,
                fg=th.INK,
                font=font(19, "bold"),
                anchor="w",
            ).pack(side="left")
            if unit:
                tk.Label(
                    value_row,
                    text=unit,
                    bg=th.CARD,
                    fg=th.MUTED,
                    font=font(8),
                    anchor="sw",
                ).pack(side="left", padx=(S(3), 0), pady=(0, S(3)))
            tk.Frame(inner, bg=color, height=S(2), width=S(22)).pack(
                fill="none", anchor="w", pady=(S(1), S(3))
            )
            tk.Label(
                inner,
                text=note,
                bg=th.CARD,
                fg=th.FAINT,
                font=font(7),
                anchor="w",
            ).pack(fill="x")

    def _build_calendar_card(
        self,
        all_completed: set[date],
        all_progress: set[date],
    ) -> None:
        first_day = date(self.view_year, self.view_month, 1)
        last_num = calendar.monthrange(self.view_year, self.view_month)[1]
        last_day = date(self.view_year, self.view_month, last_num)
        month_completed = {
            day for day in all_completed if first_day <= day <= last_day
        }
        month_progress = {
            day for day in all_progress if first_day <= day <= last_day
        }

        card = make_card(self.content)
        card.pack(fill="x")
        inner = tk.Frame(card, bg=th.CARD)
        inner.pack(fill="both", expand=True, padx=S(20), pady=S(17))

        header = tk.Frame(inner, bg=th.CARD)
        header.pack(fill="x", pady=(0, S(5)))
        title_box = tk.Frame(header, bg=th.CARD)
        title_box.pack(side="left")
        tk.Label(
            title_box,
            text=format_month_cn(self.view_year, self.view_month),
            bg=th.CARD,
            fg=th.INK,
            font=font(15, "bold"),
            anchor="w",
        ).pack(fill="x")
        tk.Label(
            title_box,
            text=f"本月全勤 {len(month_completed)} 天 · 有记录 {len(month_progress)} 天",
            bg=th.CARD,
            fg=th.MUTED,
            font=font(8),
            anchor="w",
        ).pack(fill="x", pady=(S(2), 0))

        nav = tk.Frame(header, bg=th.CARD)
        nav.pack(side="right")
        TextButton(
            nav,
            "回到今天",
            self._go_today,
            fg=th.MUTED,
            hover_fg=th.GREEN,
            bg=th.CARD,
            font_size=8,
        ).pack(side="left", padx=(0, S(10)))
        RoundedButton(
            nav,
            "‹",
            lambda: self._shift_month(-1),
            fill=th.CARD_TINT,
            hover_fill=th.BG_SOFT,
            pressed_fill=th.TRACK,
            text_color=th.SUBTEXT,
            bg=th.CARD,
            outline=th.BORDER,
            padx=9,
            pady=3,
            font_size=13,
        ).pack(side="left", padx=(0, S(4)))
        RoundedButton(
            nav,
            "›",
            lambda: self._shift_month(1),
            fill=th.CARD_TINT,
            hover_fill=th.BG_SOFT,
            pressed_fill=th.TRACK,
            text_color=th.SUBTEXT,
            bg=th.CARD,
            outline=th.BORDER,
            padx=9,
            pady=3,
            font_size=13,
        ).pack(side="left")

        grid = CalendarGrid(
            inner,
            self.view_year,
            self.view_month,
            month_completed,
            month_progress,
            self.app.today,
            self.selected,
            lambda day: self._select_day(day, all_completed, all_progress),
        )
        grid.pack(fill="x", pady=(S(2), S(7)))

        footer = tk.Frame(inner, bg=th.CARD)
        footer.pack(fill="x", pady=(S(4), 0))
        legend = tk.Frame(footer, bg=th.CARD)
        legend.pack(side="left")
        self._legend(legend, th.GREEN, "全部完成")
        self._legend(legend, th.AMBER, "有记录", padx=S(13))
        self._legend(legend, "outline", "今天", padx=S(13))

        self._footer_label = tk.Label(
            footer,
            text="",
            bg=th.CARD,
            fg=th.MUTED,
            font=font(8),
            anchor="e",
        )
        self._footer_label.pack(side="right")
        self._update_footer(all_completed, all_progress)

    def _legend(
        self,
        master: tk.Misc,
        color: str,
        text: str,
        *,
        padx: int = 0,
    ) -> None:
        item = tk.Frame(master, bg=th.CARD)
        item.pack(side="left", padx=(padx, 0))
        dot = tk.Canvas(
            item,
            width=S(11),
            height=S(14),
            bg=th.CARD,
            bd=0,
            highlightthickness=0,
        )
        dot.pack(side="left")
        if color == "outline":
            dot.create_oval(
                S(2),
                S(4),
                S(9),
                S(11),
                fill="",
                outline=th.ORANGE,
                width=S(1.5),
            )
        else:
            dot.create_oval(
                S(3),
                S(6),
                S(8),
                S(11),
                fill=color,
                outline="",
            )
        tk.Label(
            item,
            text=text,
            bg=th.CARD,
            fg=th.MUTED,
            font=font(8),
        ).pack(side="left", padx=(S(3), 0))

    def _update_footer(
        self,
        completed: set[date],
        progress: set[date],
    ) -> None:
        if self._footer_label is None:
            return
        selected = self.selected
        if selected is None:
            self._footer_label.configure(text="点一天看看记录")
            return
        label = f"{format_short_date_cn(selected)} · {weekday_cn(selected)}"
        if selected > self.app.today:
            detail = "还没到"
        elif selected in completed:
            detail = "全部完成"
        elif selected in progress:
            detail = "有记录，未全部完成"
        else:
            detail = "没有记录"
        self._footer_label.configure(text=f"{label} · {detail}")

    def _select_day(
        self,
        day: date,
        completed: set[date],
        progress: set[date],
    ) -> None:
        self.selected = day
        self._update_footer(completed, progress)

    def _shift_month(self, delta: int) -> None:
        month = self.view_month + delta
        year = self.view_year
        if month < 1:
            month = 12
            year -= 1
        elif month > 12:
            month = 1
            year += 1
        self.view_year = year
        self.view_month = month
        if not (
            year == self.app.today.year and month == self.app.today.month
        ):
            self.selected = None
        else:
            self.selected = self.app.today
        self.refresh()

    def _go_today(self) -> None:
        self.view_year = self.app.today.year
        self.view_month = self.app.today.month
        self.selected = self.app.today
        self.refresh()

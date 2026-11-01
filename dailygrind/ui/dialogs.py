"""Modal dialogs: task editing and the daily reminder popup."""

from __future__ import annotations

import sys
import tkinter as tk
from collections.abc import Callable

from ..models import DaySnapshot, Task
from ..paths import ICON_PATH
from . import theme as th
from .theme import S, font
from .widgets import Pill, ProgressBar, RoundedButton

TaskSubmit = Callable[[dict[str, object]], None]


def _make_entry(
    master: tk.Misc,
    variable: tk.StringVar,
    *,
    width: int | None = None,
) -> tk.Entry:
    entry = tk.Entry(
        master,
        textvariable=variable,
        width=width or 0,
        font=font(10),
        bg=th.CARD_TINT,
        fg=th.TEXT,
        insertbackground=th.TEXT,
        relief="flat",
        bd=0,
        highlightthickness=S(1),
        highlightbackground=th.BORDER,
        highlightcolor=th.GREEN,
        disabledbackground=th.TRACK,
    )
    return entry


def _make_spinbox(
    master: tk.Misc,
    variable: tk.StringVar,
    *,
    minimum: int,
    maximum: int,
    width: int = 8,
) -> tk.Spinbox:
    return tk.Spinbox(
        master,
        from_=minimum,
        to=maximum,
        textvariable=variable,
        width=width,
        font=font(10),
        bg=th.CARD_TINT,
        fg=th.TEXT,
        insertbackground=th.TEXT,
        relief="flat",
        bd=0,
        highlightthickness=S(1),
        highlightbackground=th.BORDER,
        highlightcolor=th.GREEN,
        buttonbackground=th.CARD_TINT,
        readonlybackground=th.CARD_TINT,
        justify="left",
    )


class TaskDialog(tk.Toplevel):
    def __init__(
        self,
        parent: tk.Misc,
        on_submit: TaskSubmit,
        task: Task | None = None,
    ) -> None:
        super().__init__(parent)
        self._on_submit = on_submit
        self._task = task
        self._host = parent.winfo_toplevel()
        self.configure(bg=th.CARD)
        self.resizable(False, False)
        self.title("编辑每日任务" if task else "添加每日任务")
        if ICON_PATH.exists():
            try:
                self.iconbitmap(default=str(ICON_PATH))
            except tk.TclError:
                pass

        self._title_var = tk.StringVar(value=task.title if task else "")
        self._description_var = tk.StringVar(
            value=task.description if task else ""
        )
        self._target_var = tk.StringVar(value=str(task.target) if task else "1")
        self._unit_var = tk.StringVar(value=task.unit if task else "次")
        self._step_var = tk.StringVar(value=str(task.step) if task else "1")
        self._icon_var = tk.StringVar(value=task.icon if task else "")

        self._build()
        self._center()
        self.bind("<Escape>", lambda _event: self.destroy())
        self.bind("<Return>", self._handle_return)
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.transient(self._host)
        try:
            self.grab_set()
        except tk.TclError:
            pass
        self.after(80, self._focus_name)

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------
    def _build(self) -> None:
        outer = tk.Frame(self, bg=th.CARD)
        outer.pack(fill="both", expand=True, padx=S(28), pady=S(22))

        heading = "编辑任务" if self._task else "添加一项每日任务"
        tk.Label(
            outer,
            text=heading,
            bg=th.CARD,
            fg=th.INK,
            font=font(18, "bold"),
            anchor="w",
        ).pack(fill="x")
        tk.Label(
            outer,
            text="目标要小到今天就能完成，长期才跑得远。",
            bg=th.CARD,
            fg=th.MUTED,
            font=font(9),
            anchor="w",
        ).pack(fill="x", pady=(S(4), S(17)))

        self._name_entry = self._add_text_field(
            outer, "任务名称", self._title_var, "例如：蓝桥杯真题", max_chars=30
        )
        self._add_text_field(
            outer,
            "补充说明",
            self._description_var,
            "例如：独立完成，写下思路和易错点",
            max_chars=80,
        )

        number_row = tk.Frame(outer, bg=th.CARD)
        number_row.pack(fill="x", pady=(0, S(14)))
        for column in range(3):
            number_row.columnconfigure(column, weight=1, uniform="number")

        target_cell = tk.Frame(number_row, bg=th.CARD)
        target_cell.grid(row=0, column=0, sticky="ew", padx=(0, S(8)))
        self._field_label(target_cell, "每日目标").pack(fill="x")
        self._target_spin = _make_spinbox(
            target_cell, self._target_var, minimum=1, maximum=9999
        )
        self._target_spin.pack(fill="x", ipady=S(6), pady=(S(6), 0))

        unit_cell = tk.Frame(number_row, bg=th.CARD)
        unit_cell.grid(row=0, column=1, sticky="ew", padx=S(4))
        self._field_label(unit_cell, "单位").pack(fill="x")
        self._unit_entry = _make_entry(unit_cell, self._unit_var)
        self._unit_entry.pack(fill="x", ipady=S(6), pady=(S(6), 0))

        step_cell = tk.Frame(number_row, bg=th.CARD)
        step_cell.grid(row=0, column=2, sticky="ew", padx=(S(8), 0))
        self._field_label(step_cell, "每次点击增减").pack(fill="x")
        self._step_spin = _make_spinbox(
            step_cell, self._step_var, minimum=1, maximum=9999
        )
        self._step_spin.pack(fill="x", ipady=S(6), pady=(S(6), 0))

        icon_row = tk.Frame(outer, bg=th.CARD)
        icon_row.pack(fill="x", pady=(0, S(6)))
        self._field_label(icon_row, "图标文字").pack(fill="x")
        icon_line = tk.Frame(icon_row, bg=th.CARD)
        icon_line.pack(fill="x", pady=(S(6), 0))
        self._icon_entry = _make_entry(
            icon_line, self._icon_var, width=5
        )
        self._icon_entry.pack(side="left", ipady=S(6))
        tk.Label(
            icon_line,
            text="留空会使用任务名称的第一个字",
            bg=th.CARD,
            fg=th.FAINT,
            font=font(8),
            anchor="w",
        ).pack(side="left", padx=(S(10), 0))

        self._error_label = tk.Label(
            outer,
            text="",
            bg=th.CARD,
            fg=th.RED,
            font=font(9),
            anchor="w",
        )
        self._error_label.pack(fill="x", pady=(S(10), S(4)))

        button_row = tk.Frame(outer, bg=th.CARD)
        button_row.pack(fill="x", pady=(S(3), 0))
        self._save_button = RoundedButton(
            button_row,
            "保存",
            self._submit,
            fill=th.GREEN,
            bg=th.CARD,
            padx=22,
            pady=8,
        )
        self._save_button.pack(side="right")
        cancel = RoundedButton(
            button_row,
            "取消",
            self.destroy,
            fill=th.CARD_TINT,
            hover_fill=th.BG_SOFT,
            pressed_fill=th.TRACK,
            text_color=th.SUBTEXT,
            bg=th.CARD,
            outline=th.BORDER,
            padx=18,
            pady=8,
        )
        cancel.pack(side="right", padx=(0, S(8)))

    def _field_label(self, master: tk.Misc, text: str) -> tk.Label:
        return tk.Label(
            master,
            text=text,
            bg=th.CARD,
            fg=th.MUTED,
            font=font(9),
            anchor="w",
        )

    def _add_text_field(
        self,
        master: tk.Misc,
        label: str,
        variable: tk.StringVar,
        placeholder: str,
        *,
        max_chars: int,
    ) -> tk.Entry:
        holder = tk.Frame(master, bg=th.CARD)
        holder.pack(fill="x", pady=(0, S(14)))
        self._field_label(holder, label).pack(fill="x")
        entry = _make_entry(holder, variable)
        entry.pack(fill="x", ipady=S(6), pady=(S(6), 0))
        entry._placeholder = placeholder  # type: ignore[attr-defined]
        entry._max_chars = max_chars  # type: ignore[attr-defined]
        return entry

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def _focus_name(self) -> None:
        self._name_entry.focus_set()
        self._name_entry.selection_range(0, "end")

    def _handle_return(self, _event: tk.Event) -> None:
        self._submit()

    def _show_error(self, message: str) -> None:
        self._error_label.configure(text=message)

    def _submit(self) -> None:
        title = self._title_var.get().strip()
        description = self._description_var.get().strip()
        unit = self._unit_var.get().strip()
        icon = self._icon_var.get().strip()

        if not title:
            self._show_error("请先填写任务名称。")
            self._name_entry.focus_set()
            return
        if len(title) > 30:
            self._show_error("任务名称最多 30 个字符。")
            return
        if len(description) > 80:
            self._show_error("补充说明最多 80 个字符。")
            return
        if len(unit) > 4:
            self._show_error("单位最多 4 个字符。")
            return
        if len(icon) > 2:
            self._show_error("图标文字最多 2 个字符。")
            return
        try:
            target = int(self._target_var.get())
            step = int(self._step_var.get())
        except ValueError:
            self._show_error("目标和步长必须是整数。")
            return
        if target < 1 or target > 9999:
            self._show_error("每日目标应在 1 到 9999 之间。")
            return
        if step < 1 or step > target:
            self._show_error("单次增减应在 1 到每日目标之间。")
            return

        payload = {
            "title": title,
            "description": description,
            "target": target,
            "unit": unit or "次",
            "icon": icon,
            "step": step,
        }
        try:
            self._on_submit(payload)
        except ValueError as exc:
            self._show_error(str(exc))
            return
        except Exception as exc:  # pragma: no cover - defensive UI boundary
            self._show_error(f"保存失败：{exc}")
            return
        self.destroy()

    def _center(self) -> None:
        self.update_idletasks()
        width = S(500)
        content_height = self.winfo_reqheight()
        height = min(S(650), max(S(430), content_height + S(12)))
        self._host.update_idletasks()
        x = self._host.winfo_rootx() + (self._host.winfo_width() - width) // 2
        y = self._host.winfo_rooty() + (self._host.winfo_height() - height) // 2
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        x = max(S(12), min(x, screen_w - width - S(12)))
        y = max(S(12), min(y, screen_h - height - S(40)))
        self.geometry(f"{width}x{height}+{x}+{y}")


class ReminderDialog(tk.Toplevel):
    def __init__(
        self,
        parent: tk.Misc,
        snapshot: DaySnapshot,
        streak: int,
        reminder_hhmm: str,
        on_snooze: Callable[[], None],
        on_go: Callable[[], None],
        *,
        snooze_minutes: int = 10,
    ) -> None:
        super().__init__(parent)
        self._snapshot = snapshot
        self._streak = streak
        self._on_snooze = on_snooze
        self._on_go = on_go
        self._snooze_minutes = snooze_minutes
        self._handled = False

        self.configure(bg=th.CARD)
        self.title("DailyGrind · 每日提醒")
        self.resizable(False, False)
        self.attributes("-topmost", True)
        if ICON_PATH.exists():
            try:
                self.iconbitmap(default=str(ICON_PATH))
            except tk.TclError:
                pass
        self._build(reminder_hhmm)
        self._center()
        self.protocol("WM_DELETE_WINDOW", self._snooze)
        try:
            self.grab_set()
        except tk.TclError:
            pass
        self.after(100, self._attention)
        self._play_sound()

    def _build(self, reminder_hhmm: str) -> None:
        tk.Frame(self, bg=th.ORANGE, height=S(5)).pack(fill="x")

        body = tk.Frame(self, bg=th.CARD)
        body.pack(fill="both", expand=True, padx=S(28), pady=S(22))

        top = tk.Frame(body, bg=th.CARD)
        top.pack(fill="x")
        badge = tk.Canvas(
            top,
            width=S(42),
            height=S(42),
            bg=th.CARD,
            bd=0,
            highlightthickness=0,
        )
        badge.pack(side="left")
        badge.create_oval(
            S(1),
            S(1),
            S(41),
            S(41),
            fill=th.ORANGE_SOFT,
            outline="",
        )
        badge.create_text(
            S(21),
            S(20),
            text="!",
            fill=th.ORANGE_DARK,
            font=font(18, "bold"),
        )
        meta = tk.Frame(top, bg=th.CARD)
        meta.pack(side="left", padx=(S(12), 0), fill="x", expand=True)
        tk.Label(
            meta,
            text="每日提醒",
            bg=th.CARD,
            fg=th.ORANGE_DARK,
            font=font(9, "bold"),
            anchor="w",
        ).pack(fill="x")
        tk.Label(
            meta,
            text=f"{reminder_hhmm} · 今天的计划还开着",
            bg=th.CARD,
            fg=th.MUTED,
            font=font(8),
            anchor="w",
        ).pack(fill="x", pady=(S(2), 0))
        if self._streak > 0:
            Pill(
                top,
                f"连续 {self._streak} 天",
                bg=th.GREEN_SOFT,
                fg=th.GREEN_DARK,
                font_size=8,
                parent_bg=th.CARD,
            ).pack(side="right", pady=S(7))

        if self._snapshot.all_done:
            title_text = "今天已经全部完成"
            subtitle = "这份自律已经记下来了，去休息吧。"
        else:
            title_text = f"今天还差 {self._snapshot.remaining_tasks} 项"
            subtitle = (
                f"已经完成 {self._snapshot.completed_tasks} / "
                f"{self._snapshot.total_tasks} 项，再收个尾。"
            )
        tk.Label(
            body,
            text=title_text,
            bg=th.CARD,
            fg=th.INK,
            font=font(20, "bold"),
            anchor="w",
        ).pack(fill="x", pady=(S(19), S(4)))
        tk.Label(
            body,
            text=subtitle,
            bg=th.CARD,
            fg=th.SUBTEXT,
            font=font(9),
            anchor="w",
        ).pack(fill="x")

        progress = ProgressBar(body, bg=th.CARD)
        progress.pack(fill="x", pady=(S(15), S(14)))
        progress.set(self._snapshot.percent)

        outstanding = self._snapshot.outstanding
        if outstanding:
            tk.Label(
                body,
                text="还没完成",
                bg=th.CARD,
                fg=th.MUTED,
                font=font(8, "bold"),
                anchor="w",
            ).pack(fill="x", pady=(0, S(5)))
            for state in outstanding[:4]:
                row = tk.Frame(body, bg=th.CARD)
                row.pack(fill="x", pady=S(3))
                dot = tk.Canvas(
                    row,
                    width=S(12),
                    height=S(18),
                    bg=th.CARD,
                    bd=0,
                    highlightthickness=0,
                )
                dot.pack(side="left")
                dot.create_oval(
                    S(4),
                    S(7),
                    S(9),
                    S(12),
                    fill=state.task.color,
                    outline="",
                )
                tk.Label(
                    row,
                    text=state.task.title,
                    bg=th.CARD,
                    fg=th.TEXT,
                    font=font(10),
                    anchor="w",
                ).pack(side="left", fill="x", expand=True)
                tk.Label(
                    row,
                    text=state.amount_text,
                    bg=th.CARD,
                    fg=th.MUTED,
                    font=font(8),
                ).pack(side="right")
            if len(outstanding) > 4:
                tk.Label(
                    body,
                    text=f"还有 {len(outstanding) - 4} 项未显示",
                    bg=th.CARD,
                    fg=th.FAINT,
                    font=font(8),
                    anchor="w",
                ).pack(fill="x", pady=(S(2), 0))

        tk.Label(
            body,
            text="今天不需要完美，只需要收尾。",
            bg=th.CARD,
            fg=th.FAINT,
            font=font(8),
            anchor="w",
        ).pack(fill="x", pady=(S(14), S(13)))

        buttons = tk.Frame(body, bg=th.CARD)
        buttons.pack(fill="x")
        if self._snapshot.all_done:
            RoundedButton(
                buttons,
                "收下这份完成",
                self._go,
                fill=th.GREEN,
                bg=th.CARD,
                padx=20,
                pady=8,
            ).pack(side="right")
            RoundedButton(
                buttons,
                "稍后再看",
                self._snooze,
                fill=th.CARD_TINT,
                hover_fill=th.BG_SOFT,
                text_color=th.SUBTEXT,
                bg=th.CARD,
                outline=th.BORDER,
                padx=14,
                pady=8,
            ).pack(side="right", padx=(0, S(8)))
        else:
            RoundedButton(
                buttons,
                "现在去完成",
                self._go,
                fill=th.GREEN,
                bg=th.CARD,
                padx=18,
                pady=8,
            ).pack(side="right")
            RoundedButton(
                buttons,
                f"{self._snooze_minutes} 分钟后再提醒",
                self._snooze,
                fill=th.CARD_TINT,
                hover_fill=th.BG_SOFT,
                text_color=th.SUBTEXT,
                bg=th.CARD,
                outline=th.BORDER,
                padx=14,
                pady=8,
            ).pack(side="right", padx=(0, S(8)))

    def _center(self) -> None:
        self.update_idletasks()
        width = S(490)
        content_height = self.winfo_reqheight()
        height = min(S(620), max(S(360), content_height + S(10)))
        x = (self.winfo_screenwidth() - width) // 2
        y = (self.winfo_screenheight() - height) // 2 - S(20)
        self.geometry(f"{width}x{height}+{max(0, x)}+{max(0, y)}")

    def _attention(self) -> None:
        if not self.winfo_exists():
            return
        self.lift()
        self.focus_force()

    def _snooze(self) -> None:
        if self._handled:
            return
        self._handled = True
        self.destroy()
        self._on_snooze()

    def _go(self) -> None:
        if self._handled:
            return
        self._handled = True
        self.destroy()
        self._on_go()

    def _play_sound(self) -> None:
        if sys.platform != "win32":
            return
        try:
            import winsound

            winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
        except Exception:
            try:
                self.bell()
            except tk.TclError:
                pass

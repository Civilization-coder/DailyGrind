"""Reusable Tkinter widgets for DailyGrind."""

from __future__ import annotations

import tkinter as tk
import tkinter.font as tkfont
from collections.abc import Callable

from . import theme as th
from .theme import S, draw_round_rect, font


def _widget_bg(master: tk.Misc) -> str:
    try:
        return str(master.cget("bg"))
    except tk.TclError:
        return th.BG


def make_card(master: tk.Misc, *, bg: str = th.CARD) -> tk.Frame:
    return tk.Frame(
        master,
        bg=bg,
        bd=0,
        highlightthickness=S(1),
        highlightbackground=th.BORDER,
        highlightcolor=th.BORDER,
    )


class RoundedButton(tk.Canvas):
    """A small rounded button that looks consistent across Windows themes."""

    def __init__(
        self,
        master: tk.Misc,
        text: str,
        command: Callable[[], None] | None = None,
        *,
        fill: str = th.GREEN,
        hover_fill: str | None = None,
        pressed_fill: str | None = None,
        text_color: str = th.WHITE,
        font_size: int = 10,
        font_weight: str = "bold",
        padx: int = 16,
        pady: int = 8,
        width: int | None = None,
        height: int | None = None,
        bg: str | None = None,
        radius: int | None = None,
        outline: str = "",
        outline_width: int = 1,
        cursor: str = "hand2",
    ) -> None:
        self._font_spec = font(font_size, font_weight)
        self._measure_font = tkfont.Font(
            family=self._font_spec[0],
            size=self._font_spec[1],
            weight=self._font_spec[2],
        )
        self._text = text
        self._auto_width = width is None
        self._fixed_height = height
        calculated_height = (
            self._measure_font.metrics("linespace") + 2 * S(pady)
            if height is None
            else int(height)
        )
        calculated_width = (
            self._measure_font.measure(text) + 2 * S(padx)
            if width is None
            else int(width)
        )
        self._bg = bg or _widget_bg(master)
        super().__init__(
            master,
            width=max(S(24), calculated_width),
            height=max(S(20), calculated_height),
            bg=self._bg,
            bd=0,
            highlightthickness=0,
            cursor=cursor,
            takefocus=0,
        )

        self._command = command
        self._fill = fill
        self._hover_fill = hover_fill or th.shade(fill, 0.08)
        self._pressed_fill = pressed_fill or th.shade(fill, 0.16)
        self._text_color = text_color
        self._radius = radius
        self._outline = outline
        self._outline_width = outline_width
        self._padx = padx
        self._enabled = True
        self._hovered = False
        self._pressed = False

        self.bind("<Configure>", lambda _event: self._redraw())
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.after_idle(self._redraw)

    def _current_fill(self) -> str:
        if not self._enabled:
            return th.TRACK
        if self._pressed:
            return self._pressed_fill
        if self._hovered:
            return self._hover_fill
        return self._fill

    def _redraw(self) -> None:
        if not self.winfo_exists():
            return
        self.delete("all")
        width = max(1, self.winfo_width())
        height = max(1, self.winfo_height())
        if width <= 1 or height <= 1:
            width = int(self.cget("width"))
            height = int(self.cget("height"))
        fill = self._current_fill()
        text_color = self._text_color if self._enabled else th.FAINT
        radius = height / 2 if self._radius is None else S(self._radius)
        outline = self._outline if self._enabled else th.BORDER
        draw_round_rect(
            self,
            S(1),
            S(1),
            width - S(1),
            height - S(1),
            radius,
            fill=fill,
            outline=outline,
            width=S(self._outline_width) if outline else 0,
        )
        self.create_text(
            width / 2,
            height / 2 + S(0.5),
            text=self._text,
            fill=text_color,
            font=self._font_spec,
        )

    def _set_hover(self, value: bool) -> None:
        if self._hovered != value:
            self._hovered = value
            self._redraw()

    def _on_enter(self, _event: tk.Event) -> None:
        if self._enabled:
            self._set_hover(True)

    def _on_leave(self, _event: tk.Event) -> None:
        self._pressed = False
        self._set_hover(False)

    def _on_press(self, _event: tk.Event) -> None:
        if self._enabled:
            self._pressed = True
            self._redraw()

    def _on_release(self, event: tk.Event) -> None:
        was_pressed = self._pressed
        self._pressed = False
        inside = (
            0 <= event.x <= self.winfo_width()
            and 0 <= event.y <= self.winfo_height()
        )
        self._redraw()
        if self._enabled and was_pressed and inside and self._command:
            self.after_idle(self._invoke)

    def _invoke(self) -> None:
        if self._enabled and self._command:
            self._command()

    def set_text(self, text: str) -> None:
        self._text = text
        if self._auto_width:
            width = self._measure_font.measure(text) + 2 * S(self._padx)
            self.configure(width=width)
        self._redraw()

    def set_enabled(self, enabled: bool) -> None:
        if self._enabled == enabled:
            return
        self._enabled = bool(enabled)
        self.configure(cursor="hand2" if enabled else "arrow")
        self._redraw()

    def set_colors(
        self,
        *,
        fill: str | None = None,
        text_color: str | None = None,
    ) -> None:
        if fill:
            self._fill = fill
            self._hover_fill = th.shade(fill, 0.08)
            self._pressed_fill = th.shade(fill, 0.16)
        if text_color:
            self._text_color = text_color
        self._redraw()


class Pill(tk.Canvas):
    def __init__(
        self,
        master: tk.Misc,
        text: str,
        *,
        bg: str = th.GREEN_SOFT,
        fg: str = th.GREEN_DARK,
        font_size: int = 9,
        weight: str = "normal",
        padx: int = 10,
        pady: int = 4,
        parent_bg: str | None = None,
    ) -> None:
        self._font_spec = font(font_size, weight)
        self._measure_font = tkfont.Font(
            family=self._font_spec[0],
            size=self._font_spec[1],
            weight=self._font_spec[2],
        )
        self._text = text
        self._pill_bg = bg
        self._fg = fg
        self._padx = padx
        self._pady = pady
        width = self._measure_font.measure(text) + 2 * S(padx)
        height = self._measure_font.metrics("linespace") + 2 * S(pady)
        super().__init__(
            master,
            width=width,
            height=height,
            bg=parent_bg or _widget_bg(master),
            highlightthickness=0,
            bd=0,
        )
        self._redraw()

    def _redraw(self) -> None:
        self.delete("all")
        width = int(self.cget("width"))
        height = int(self.cget("height"))
        draw_round_rect(
            self,
            S(1),
            S(1),
            width - S(1),
            height - S(1),
            height / 2,
            fill=self._pill_bg,
        )
        self.create_text(
            width / 2,
            height / 2,
            text=self._text,
            fill=self._fg,
            font=self._font_spec,
        )

    def set_text(self, text: str) -> None:
        self._text = text
        width = self._measure_font.measure(text) + 2 * S(self._padx)
        self.configure(width=width)
        self._redraw()

    def set_colors(self, bg: str, fg: str) -> None:
        self._pill_bg = bg
        self._fg = fg
        self._redraw()


class NavButton(tk.Canvas):
    def __init__(
        self,
        master: tk.Misc,
        text: str,
        command: Callable[[], None],
    ) -> None:
        super().__init__(
            master,
            height=S(44),
            bg=th.SIDEBAR,
            bd=0,
            highlightthickness=0,
            cursor="hand2",
        )
        self._text = text
        self._command = command
        self._active = False
        self._hovered = False
        self.bind("<Configure>", lambda _event: self._redraw())
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", lambda _event: self._command())

    def _redraw(self) -> None:
        self.delete("all")
        width = self.winfo_width()
        height = self.winfo_height()
        if width <= 1:
            return
        if self._active or self._hovered:
            draw_round_rect(
                self,
                S(2),
                S(3),
                width - S(2),
                height - S(3),
                S(11),
                fill=th.SIDEBAR_ACTIVE if self._active else th.SIDEBAR_2,
            )
        dot_color = th.ORANGE if self._active else th.SIDEBAR_LINE
        self.create_oval(
            S(15),
            height / 2 - S(3),
            S(21),
            height / 2 + S(3),
            fill=dot_color,
            outline="",
        )
        self.create_text(
            S(32),
            height / 2,
            text=self._text,
            anchor="w",
            fill=th.SIDEBAR_TEXT if self._active else th.SIDEBAR_MUTED,
            font=font(10, "bold" if self._active else "normal"),
        )

    def _on_enter(self, _event: tk.Event) -> None:
        self._hovered = True
        self._redraw()

    def _on_leave(self, _event: tk.Event) -> None:
        self._hovered = False
        self._redraw()

    def set_active(self, active: bool) -> None:
        if self._active != active:
            self._active = active
            self._redraw()


class TextButton(tk.Label):
    def __init__(
        self,
        master: tk.Misc,
        text: str,
        command: Callable[[], None],
        *,
        fg: str = th.SUBTEXT,
        hover_fg: str = th.GREEN,
        bg: str | None = None,
        font_size: int = 9,
        weight: str = "normal",
    ) -> None:
        self._normal_fg = fg
        self._hover_fg = hover_fg
        super().__init__(
            master,
            text=text,
            fg=fg,
            bg=bg or _widget_bg(master),
            font=font(font_size, weight),
            cursor="hand2",
            bd=0,
            padx=0,
            pady=0,
        )
        self.bind("<Enter>", lambda _event: self.configure(fg=self._hover_fg))
        self.bind("<Leave>", lambda _event: self.configure(fg=self._normal_fg))
        self.bind("<Button-1>", lambda _event: command())


class SlimScrollbar(tk.Canvas):
    """A quiet, draggable scrollbar without native arrow buttons."""

    def __init__(
        self,
        master: tk.Misc,
        command: Callable[..., None],
        *,
        bg: str = th.BG,
    ) -> None:
        super().__init__(
            master,
            width=S(12),
            bg=bg,
            bd=0,
            highlightthickness=0,
            cursor="arrow",
        )
        self._command = command
        self._first = 0.0
        self._last = 1.0
        self._thumb = (0.0, 0.0)
        self._drag_offset: float | None = None
        self._hovered = False
        self.bind("<Configure>", lambda _event: self._draw())
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<B1-Motion>", self._on_drag)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)

    def set(self, first: str | float, last: str | float) -> None:
        self._first = float(first)
        self._last = float(last)
        self._draw()

    def _draw(self) -> None:
        self.delete("all")
        width = self.winfo_width()
        height = self.winfo_height()
        if width <= 1 or height <= 1:
            width = int(self.cget("width"))
            height = int(self.cget("height"))
        if height <= 1:
            return
        y1 = self._first * height
        y2 = self._last * height
        minimum = S(34)
        if y2 - y1 < minimum:
            middle = (y1 + y2) / 2
            y1 = middle - minimum / 2
            y2 = middle + minimum / 2
        y1 = max(S(2), min(y1, height - minimum - S(2)))
        y2 = max(y1 + minimum, min(y2, height - S(2)))
        self._thumb = (y1, y2)
        color = th.MUTED if self._hovered else th.BORDER_STRONG
        draw_round_rect(
            self,
            width / 2 - S(2),
            y1,
            width / 2 + S(2),
            y2,
            S(2),
            fill=color,
        )

    def _jump_to(self, y: float) -> None:
        height = max(1, self.winfo_height())
        y1, y2 = self._thumb
        offset = self._drag_offset
        if offset is None:
            offset = (y2 - y1) / 2
        fraction = (y - offset) / height
        self._command("moveto", max(0.0, min(1.0, fraction)))

    def _on_press(self, event: tk.Event) -> None:
        y1, y2 = self._thumb
        if y1 <= event.y <= y2:
            self._drag_offset = event.y - y1
        else:
            self._drag_offset = (y2 - y1) / 2
            self._jump_to(event.y)
        self.configure(cursor="hand2")

    def _on_drag(self, event: tk.Event) -> None:
        if self._drag_offset is not None:
            self._jump_to(event.y)

    def _on_release(self, _event: tk.Event) -> None:
        self._drag_offset = None
        self.configure(cursor="hand2" if self._hovered else "arrow")

    def _on_enter(self, _event: tk.Event) -> None:
        self._hovered = True
        self.configure(cursor="hand2")
        self._draw()

    def _on_leave(self, _event: tk.Event) -> None:
        self._hovered = False
        if self._drag_offset is None:
            self.configure(cursor="arrow")
        self._draw()


class ScrollableFrame(tk.Frame):
    """A vertically scrollable page body with a scrollbar only when needed."""

    def __init__(self, master: tk.Misc, *, bg: str = th.BG) -> None:
        super().__init__(master, bg=bg, bd=0, highlightthickness=0)
        self._bg = bg
        self.canvas = tk.Canvas(
            self,
            bg=bg,
            bd=0,
            highlightthickness=0,
            yscrollincrement=S(26),
        )
        self.scrollbar = SlimScrollbar(self, self.canvas.yview, bg=bg)
        self.canvas.configure(yscrollcommand=self._on_scroll)
        self.canvas.pack(side="left", fill="both", expand=True)
        self._scrollbar_visible = False

        self.body = tk.Frame(self.canvas, bg=bg)
        self._window_id = self.canvas.create_window(
            (0, 0), window=self.body, anchor="nw"
        )
        self.body.bind("<Configure>", self._on_body_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.winfo_toplevel().bind_all(
            "<MouseWheel>", self._on_global_mousewheel, add="+"
        )

    def _on_body_configure(self, _event: tk.Event) -> None:
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self.after_idle(self._update_scrollbar)

    def _on_canvas_configure(self, event: tk.Event) -> None:
        self.canvas.itemconfigure(self._window_id, width=event.width)
        self.after_idle(self._update_scrollbar)

    def _on_scroll(self, first: str, last: str) -> None:
        self.scrollbar.set(first, last)
        self.after_idle(self._update_scrollbar)

    def _update_scrollbar(self) -> None:
        if not self.winfo_exists():
            return
        content_height = self.body.winfo_reqheight()
        viewport_height = self.canvas.winfo_height()
        needed = content_height > viewport_height + 2
        if needed and not self._scrollbar_visible:
            self.scrollbar.place(
                relx=1.0,
                y=0,
                anchor="ne",
                x=-S(10),
                relheight=1.0,
            )
            self.scrollbar.tk.call("raise", self.scrollbar._w)
            self._scrollbar_visible = True
        elif not needed and self._scrollbar_visible:
            self.scrollbar.place_forget()
            self._scrollbar_visible = False

    def _on_global_mousewheel(self, event: tk.Event) -> str | None:
        if not self.winfo_ismapped():
            return None
        try:
            pointer_x, pointer_y = self.winfo_pointerxy()
            widget = self.winfo_containing(pointer_x, pointer_y)
        except (tk.TclError, KeyError):
            return None
        current = widget
        while current is not None:
            if current is self:
                if not self._scrollbar_visible:
                    return None
                step = -1 if event.delta > 0 else 1
                self.canvas.yview_scroll(step, "units")
                return "break"
            current = getattr(current, "master", None)
        return None

    def scroll_fraction(self) -> float:
        try:
            return float(self.canvas.yview()[0])
        except (tk.TclError, IndexError):
            return 0.0

    def restore_scroll(self, fraction: float) -> None:
        self.after_idle(
            lambda: self.canvas.yview_moveto(max(0.0, min(1.0, fraction)))
        )

    def scroll_to_top(self) -> None:
        self.after_idle(lambda: self.canvas.yview_moveto(0))


class ProgressBar(tk.Canvas):
    def __init__(
        self,
        master: tk.Misc,
        *,
        bg: str | None = None,
        track_color: str = th.TRACK,
    ) -> None:
        super().__init__(
            master,
            width=1,
            height=S(8),
            bg=bg or _widget_bg(master),
            bd=0,
            highlightthickness=0,
        )
        self._value = 0
        self._color = th.GREEN
        self._track_color = track_color
        self.bind("<Configure>", lambda _event: self._redraw())

    def set(self, value: int, color: str | None = None) -> None:
        self._value = max(0, min(100, int(value)))
        if color:
            self._color = color
        self._redraw()

    def _redraw(self) -> None:
        self.delete("all")
        width = self.winfo_width()
        height = self.winfo_height()
        if width <= 1:
            width = int(self.cget("width"))
        if height <= 1:
            return
        draw_round_rect(
            self,
            S(1),
            0,
            width - S(1),
            height,
            height / 2,
            fill=self._track_color,
        )
        if self._value <= 0:
            return
        usable = max(1, width - S(2))
        fill_width = usable * self._value / 100
        fill_width = max(fill_width, height)
        draw_round_rect(
            self,
            S(1),
            0,
            S(1) + fill_width,
            height,
            height / 2,
            fill=self._color,
        )


class RingProgress(tk.Canvas):
    def __init__(
        self,
        master: tk.Misc,
        size: int = 126,
        *,
        bg: str | None = None,
    ) -> None:
        self._size = S(size)
        super().__init__(
            master,
            width=self._size,
            height=self._size,
            bg=bg or _widget_bg(master),
            bd=0,
            highlightthickness=0,
        )
        self._value = 0
        self._color = th.GREEN
        self._redraw()

    def set(self, value: int, color: str = th.GREEN) -> None:
        self._value = max(0, min(100, int(value)))
        self._color = color
        self._redraw()

    def _redraw(self) -> None:
        self.delete("all")
        size = self._size
        pad = S(9)
        ring_width = S(10)
        self.create_oval(
            pad,
            pad,
            size - pad,
            size - pad,
            outline=th.TRACK,
            width=ring_width,
        )
        if self._value > 0:
            extent = -359.9 * self._value / 100
            self.create_arc(
                pad,
                pad,
                size - pad,
                size - pad,
                start=90,
                extent=extent,
                style="arc",
                outline=self._color,
                width=ring_width,
            )
        self.create_text(
            size / 2,
            size / 2 - S(7),
            text=f"{self._value}%",
            fill=th.INK,
            font=font(22, "bold"),
        )
        self.create_text(
            size / 2,
            size / 2 + S(19),
            text="今日完成",
            fill=th.MUTED,
            font=font(8),
        )


class ToggleSwitch(tk.Canvas):
    def __init__(
        self,
        master: tk.Misc,
        value: bool = True,
        command: Callable[[bool], None] | None = None,
        *,
        bg: str | None = None,
    ) -> None:
        self._width = S(48)
        self._height = S(27)
        super().__init__(
            master,
            width=self._width,
            height=self._height,
            bg=bg or _widget_bg(master),
            bd=0,
            highlightthickness=0,
            cursor="hand2",
        )
        self._value = bool(value)
        self._command = command
        self._enabled = True
        self.bind("<Button-1>", self._toggle)
        self._redraw()

    def _redraw(self) -> None:
        self.delete("all")
        width = self._width
        height = self._height
        track = th.GREEN if self._value else th.BORDER_STRONG
        if not self._enabled:
            track = th.BORDER
        draw_round_rect(
            self,
            S(1),
            S(1),
            width - S(1),
            height - S(1),
            height / 2,
            fill=track,
        )
        knob = height - S(6)
        y1 = S(3)
        x1 = width - knob - S(3) if self._value else S(3)
        self.create_oval(
            x1,
            y1,
            x1 + knob,
            y1 + knob,
            fill=th.WHITE,
            outline="",
        )

    def _toggle(self, _event: tk.Event) -> None:
        if not self._enabled:
            return
        self._value = not self._value
        self._redraw()
        if self._command:
            self._command(self._value)

    def get(self) -> bool:
        return self._value

    def set(self, value: bool, notify: bool = False) -> None:
        self._value = bool(value)
        self._redraw()
        if notify and self._command:
            self._command(self._value)

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = bool(enabled)
        self.configure(cursor="hand2" if enabled else "arrow")
        self._redraw()

"""The CET-6 vocabulary trainer page."""

from __future__ import annotations

import tkinter as tk
from typing import TYPE_CHECKING

from ..tts import speak_word
from ..vocab import AnswerResult, MeaningChoice, PlanEntry, VocabDay, VocabStats, Word
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


class ChoiceCard(tk.Frame):
    def __init__(
        self,
        master: tk.Misc,
        letter: str,
        text: str,
        command,
    ) -> None:
        super().__init__(
            master,
            bg=th.CARD,
            bd=0,
            highlightthickness=S(1),
            highlightbackground=th.BORDER,
            highlightcolor=th.BORDER,
            cursor="hand2",
        )
        self._letter = letter
        self._text = text
        self._command = command
        self._enabled = True
        self._hovered = False
        self._answered = False
        self._is_correct = False
        self._is_selected = False

        self._badge = tk.Canvas(
            self,
            width=S(30),
            height=S(30),
            bg=th.CARD,
            bd=0,
            highlightthickness=0,
        )
        self._badge.pack(side="left", padx=(S(12), S(10)), pady=S(8))
        self._label = tk.Label(
            self,
            text=text,
            bg=th.CARD,
            fg=th.INK,
            font=font(10),
            justify="left",
            anchor="w",
            wraplength=S(520),
        )
        self._label.pack(side="left", fill="x", expand=True, padx=(0, S(14)), pady=S(8))

        for widget in (self, self._badge, self._label):
            widget.bind("<Button-1>", self._click, add="+")
            widget.bind("<Enter>", self._enter, add="+")
            widget.bind("<Leave>", self._leave, add="+")
        self.bind("<Configure>", self._on_configure, add="+")
        self._apply_colors()

    def _on_configure(self, event: tk.Event) -> None:
        wrap = max(S(160), int(event.width) - S(76))
        if int(self._label.cget("wraplength")) != wrap:
            self._label.configure(wraplength=wrap)

    def _click(self, _event: tk.Event) -> None:
        if self._enabled:
            self._command()

    def _enter(self, _event: tk.Event) -> None:
        if self._enabled and not self._answered:
            self._hovered = True
            self._apply_colors()

    def _leave(self, _event: tk.Event) -> None:
        if not self._enabled or self._answered:
            return
        try:
            x, y = self.winfo_pointerxy()
            current = self.winfo_containing(x, y)
        except tk.TclError:
            current = None
        while current is not None:
            if current is self:
                return
            current = getattr(current, "master", None)
        self._hovered = False
        self._apply_colors()

    def _draw_badge(
        self,
        fill: str,
        foreground: str,
        text: str,
    ) -> None:
        self._badge.delete("all")
        draw_round_rect(
            self._badge,
            S(1),
            S(1),
            S(29),
            S(29),
            S(9),
            fill=fill,
        )
        self._badge.create_text(
            S(15),
            S(15),
            text=text,
            fill=foreground,
            font=font(10, "bold"),
        )

    def _apply_colors(self) -> None:
        if self._answered and self._is_correct:
            bg = th.GREEN_PALE
            border = th.GREEN
            foreground = th.GREEN_DARK
            badge_bg = th.GREEN
            badge_fg = th.WHITE
        elif self._answered and self._is_selected:
            bg = th.RED_SOFT
            border = th.RED
            foreground = th.RED
            badge_bg = th.RED
            badge_fg = th.WHITE
        elif self._answered:
            bg = th.CARD_TINT
            border = th.BORDER
            foreground = th.FAINT
            badge_bg = th.TRACK
            badge_fg = th.FAINT
        else:
            bg = th.BG_SOFT if self._hovered else th.CARD
            border = th.GREEN if self._hovered else th.BORDER
            foreground = th.INK
            badge_bg = th.GREEN_SOFT
            badge_fg = th.GREEN_DARK

        self.configure(bg=bg, highlightbackground=border, highlightcolor=border)
        self._label.configure(bg=bg, fg=foreground)
        self._badge.configure(bg=bg)
        if self._answered and self._is_correct:
            letter = "✓"
        elif self._answered and self._is_selected:
            letter = "×"
        else:
            letter = self._letter
        self._draw_badge(badge_bg, badge_fg, letter)

    def set_answer_state(self, *, correct: bool, selected: bool) -> None:
        self._answered = True
        self._enabled = False
        self._is_correct = bool(correct)
        self._is_selected = bool(selected)
        self._hovered = False
        self.configure(cursor="arrow")
        self._badge.configure(cursor="arrow")
        self._label.configure(cursor="arrow")
        self._apply_colors()


class VocabPage(tk.Frame):
    def __init__(self, master: tk.Misc, app: "DailyGrindApp") -> None:
        super().__init__(master, bg=th.BG)
        self.app = app
        self.scroll = ScrollableFrame(self, bg=th.BG)
        self.scroll.pack(fill="both", expand=True)
        self.content = tk.Frame(self.scroll.body, bg=th.BG)
        self.content.pack(fill="both", expand=True, padx=S(34), pady=S(24))

        self.mode = "overview"
        self.current_word: Word | None = None
        self.choices: list[MeaningChoice] = []
        self.choice_cards: list[ChoiceCard] = []
        self.feedback: dict | None = None
        self._bind_keys()

    # ------------------------------------------------------------------
    # Lifecycle and state
    # ------------------------------------------------------------------
    def refresh(self) -> None:
        self.mode = "overview"
        self.current_word = None
        self.choices = []
        self.feedback = None
        self._render(scroll_top=True)

    def start_study(self) -> None:
        plan = self.app.vocab.ensure_plan(self.app.today)
        entry = plan.next_incomplete()
        if entry is None:
            self.mode = "overview"
            self._render(scroll_top=True)
            return
        self._begin_word(entry)

    def _begin_word(self, entry: PlanEntry) -> None:
        self.mode = "study"
        self.current_word = entry.word
        self.choices = self.app.vocab.options_for(entry.word, self.app.today)
        self.feedback = None
        self._render(scroll_top=True)
        self.after_idle(self.focus_set)

    def _render(
        self,
        *,
        scroll_top: bool = False,
        scroll_bottom: bool = False,
    ) -> None:
        for child in self.content.winfo_children():
            child.destroy()
        plan = self.app.vocab.ensure_plan(self.app.today)
        stats = self.app.vocab.stats(self.app.today)
        if self.mode == "study" and self.current_word is not None:
            entry = next(
                (
                    item
                    for item in plan.entries
                    if item.word.word == self.current_word.word
                ),
                None,
            )
            if entry is None or (entry.completed and self.feedback is None):
                self.mode = "overview"
                self.current_word = None
            else:
                self._build_study(plan, stats, entry)
        if self.mode == "summary":
            self._build_summary(plan, stats)
        elif self.mode == "overview":
            self._build_overview(plan, stats)
        if scroll_top:
            self.scroll.scroll_to_top()
        elif scroll_bottom:
            self.after(80, self._scroll_to_bottom)

    def _scroll_to_bottom(self) -> None:
        try:
            self.scroll.canvas.update_idletasks()
            self.scroll.canvas.configure(
                scrollregion=self.scroll.canvas.bbox("all")
            )
            self.scroll.canvas.yview_moveto(1.0)
        except tk.TclError:
            pass

    def _bind_keys(self) -> None:
        for index in range(4):
            self.bind(
                f"<KeyPress-{index + 1}>",
                lambda _event, choice=index: self._choose(choice),
            )
        self.bind("<Return>", self._handle_enter)
        self.bind("<KP_Enter>", self._handle_enter)

    def _handle_enter(self, _event: tk.Event) -> None:
        if self.mode == "study" and self.feedback is not None:
            self._next_word()

    # ------------------------------------------------------------------
    # Header and overview
    # ------------------------------------------------------------------
    def _build_header(
        self,
        title: str,
        subtitle: str,
        *,
        right_factory=None,
    ) -> None:
        header = tk.Frame(self.content, bg=th.BG)
        header.pack(fill="x", pady=(0, S(18)))
        left = tk.Frame(header, bg=th.BG)
        left.pack(side="left")
        tk.Label(
            left,
            text=title,
            bg=th.BG,
            fg=th.INK,
            font=font(22, "bold"),
            anchor="w",
        ).pack(fill="x")
        tk.Label(
            left,
            text=subtitle,
            bg=th.BG,
            fg=th.MUTED,
            font=font(9),
            anchor="w",
        ).pack(fill="x", pady=(S(5), 0))
        if right_factory is not None:
            right = right_factory(header)
            right.pack(side="right", anchor="n", pady=(S(4), 0))

    def _build_overview(self, plan: VocabDay, stats: VocabStats) -> None:
        self._build_header(
            "六级单词",
            "按 2020–2025 年 35 套六级真题词频排词，每天学一点。",
            right_factory=lambda parent: Pill(
                parent,
                f"词库 {stats.bank_total:,} 词",
                bg=th.CARD,
                fg=th.SUBTEXT,
                font_size=9,
                padx=13,
                pady=6,
                parent_bg=th.BG,
            ),
        )

        hero = tk.Frame(self.content, bg=th.BG)
        hero.pack(fill="x")
        hero.grid_columnconfigure(0, weight=5, uniform="vocabhero")
        hero.grid_columnconfigure(1, weight=3, uniform="vocabhero")
        hero.grid_rowconfigure(0, weight=1)

        summary = make_card(hero)
        summary.grid(row=0, column=0, sticky="nsew", padx=(0, S(9)))
        inner = tk.Frame(summary, bg=th.CARD)
        inner.pack(fill="both", expand=True, padx=S(22), pady=S(18))

        percent = round(plan.completed / plan.total * 100) if plan.total else 0
        ring = RingProgress(inner, size=124, bg=th.CARD)
        ring.pack(side="left")
        ring.set(percent, th.GREEN if plan.all_done else th.ORANGE)

        info = tk.Frame(inner, bg=th.CARD)
        info.pack(side="left", fill="both", expand=True, padx=(S(20), 0))
        eyebrow = tk.Frame(info, bg=th.CARD)
        eyebrow.pack(fill="x")
        tk.Frame(eyebrow, bg=th.ORANGE, width=S(18), height=S(3)).pack(
            side="left", pady=(S(4), 0)
        )
        tk.Label(
            eyebrow,
            text="  TODAY'S VOCAB / 今日单词",
            bg=th.CARD,
            fg=th.ORANGE_DARK,
            font=font(8, "bold"),
            anchor="w",
        ).pack(side="left")

        if plan.total == 0:
            headline = "词库已经学完"
            subline = "所有单词都已完成，继续保持复习节奏。"
        elif plan.all_done:
            headline = "今天的单词完成了"
            attempts = sum(entry.attempts for entry in plan.entries)
            acc_text = f"{plan.accuracy}%" if attempts else "—"
            subline = (
                f"答对率 {acc_text} · 明天继续安排复习。"
                if attempts
                else "今天的任务已经落袋。"
            )
        else:
            headline = f"{plan.completed} / {plan.total} 个单词"
            subline = f"{plan.new_count} 个新词 · {plan.review_count} 个复习"
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
            text=subline,
            bg=th.CARD,
            fg=th.SUBTEXT,
            font=font(9),
            anchor="w",
        ).pack(fill="x")
        progress = ProgressBar(info, bg=th.CARD)
        progress.pack(fill="x", pady=(S(12), S(12)))
        progress.set(percent, th.GREEN if plan.all_done else th.ORANGE)

        action_row = tk.Frame(info, bg=th.CARD)
        action_row.pack(fill="x")
        if plan.total == 0:
            Pill(
                action_row,
                "今日无待学单词",
                bg=th.GREEN_SOFT,
                fg=th.GREEN_DARK,
                font_size=9,
                padx=12,
                pady=5,
                parent_bg=th.CARD,
            ).pack(side="left")
        elif plan.all_done:
            Pill(
                action_row,
                "已完成",
                bg=th.GREEN_SOFT,
                fg=th.GREEN_DARK,
                font_size=9,
                padx=12,
                pady=5,
                parent_bg=th.CARD,
            ).pack(side="left")
            TextButton(
                action_row,
                "查看今日总结",
                self._show_summary,
                fg=th.GREEN_DARK,
                hover_fg=th.GREEN,
                bg=th.CARD,
                font_size=9,
            ).pack(side="left", padx=(S(12), 0))
        else:
            label = "开始背单词" if plan.completed == 0 else f"继续背单词 ({plan.completed}/{plan.total})"
            RoundedButton(
                action_row,
                label,
                self.start_study,
                fill=th.GREEN,
                bg=th.CARD,
                padx=15,
                pady=6,
                font_size=9,
            ).pack(side="left")
            tk.Label(
                action_row,
                text="答错次日复习，答对间隔拉长",
                bg=th.CARD,
                fg=th.FAINT,
                font=font(8),
            ).pack(side="left", padx=(S(12), 0))

        deck = tk.Frame(hero, bg=th.SIDEBAR, bd=0, highlightthickness=0)
        deck.grid(row=0, column=1, sticky="nsew", padx=(S(9), 0))
        deck_inner = tk.Frame(deck, bg=th.SIDEBAR)
        deck_inner.pack(fill="both", expand=True, padx=S(22), pady=S(17))

        tk.Label(
            deck_inner,
            text="词库进度",
            bg=th.SIDEBAR,
            fg=th.SIDEBAR_MUTED,
            font=font(9),
            anchor="w",
        ).pack(fill="x")
        learned_row = tk.Frame(deck_inner, bg=th.SIDEBAR)
        learned_row.pack(fill="x", pady=(S(5), 0))
        tk.Label(
            learned_row,
            text=f"{stats.learned:,}",
            bg=th.SIDEBAR,
            fg=th.SIDEBAR_TEXT,
            font=font(28, "bold"),
            anchor="w",
        ).pack(side="left")
        tk.Label(
            learned_row,
            text=f" / {stats.bank_total:,} 词",
            bg=th.SIDEBAR,
            fg=th.SIDEBAR_MUTED,
            font=font(9),
            anchor="sw",
        ).pack(side="left", padx=(S(4), 0), pady=(0, S(7)))
        learned_percent = (
            round(stats.learned / stats.bank_total * 100)
            if stats.bank_total
            else 0
        )
        learned_bar = ProgressBar(
            deck_inner,
            bg=th.SIDEBAR,
            track_color=th.SIDEBAR_LINE,
        )
        learned_bar.pack(fill="x", pady=(S(12), S(13)))
        learned_bar.set(learned_percent, th.ORANGE)

        counts = tk.Frame(deck_inner, bg=th.SIDEBAR)
        counts.pack(fill="x")
        self._deck_stat(counts, "标记认识", f"{stats.mastered:,}", th.GREEN)
        self._deck_stat(counts, "待复习", f"{stats.due:,}", th.ORANGE, right=True)
        tk.Label(
            deck_inner,
            text=f"核心 {stats.core_total} · 真题 {stats.exam_total}",
            bg=th.SIDEBAR,
            fg=th.SIDEBAR_MUTED,
            font=font(8),
            anchor="w",
        ).pack(fill="x", pady=(S(14), 0))

        stats_row = tk.Frame(self.content, bg=th.BG)
        stats_row.pack(fill="x", pady=(S(17), S(14)))
        for column in range(4):
            stats_row.grid_columnconfigure(column, weight=1, uniform="vocabstats")
        accuracy_text = (
            f"{round(stats.today_correct / stats.today_attempts * 100)}%"
            if stats.today_attempts
            else "—"
        )
        cards = (
            ("今日新词", str(plan.new_count), th.GREEN, "从高频核心词开始"),
            ("今日复习", str(plan.review_count), th.BLUE, "优先清掉到期词"),
            ("今日答对率", accuracy_text, th.ORANGE, "做完才会更新"),
            ("待复习", str(stats.due), th.AMBER, "答错词会排到明天"),
        )
        for column, (label, value, color, note) in enumerate(cards):
            card = make_card(stats_row)
            card.grid(
                row=0,
                column=column,
                sticky="nsew",
                padx=(0 if column == 0 else S(5), 0 if column == 3 else S(5)),
            )
            inner_card = tk.Frame(card, bg=th.CARD)
            inner_card.pack(fill="both", expand=True, padx=S(15), pady=S(13))
            tk.Label(
                inner_card,
                text=label,
                bg=th.CARD,
                fg=th.MUTED,
                font=font(8),
                anchor="w",
            ).pack(fill="x")
            tk.Label(
                inner_card,
                text=value,
                bg=th.CARD,
                fg=th.INK,
                font=font(18, "bold"),
                anchor="w",
            ).pack(fill="x", pady=(S(2), S(1)))
            tk.Frame(inner_card, bg=color, height=S(2), width=S(22)).pack(
                anchor="w", pady=(S(1), S(3))
            )
            tk.Label(
                inner_card,
                text=note,
                bg=th.CARD,
                fg=th.FAINT,
                font=font(7),
                anchor="w",
            ).pack(fill="x")

        guide = make_card(self.content)
        guide.pack(fill="x")
        guide_inner = tk.Frame(guide, bg=th.CARD)
        guide_inner.pack(fill="x", padx=S(18), pady=S(14))
        tk.Label(
            guide_inner,
            text="学习节奏",
            bg=th.CARD,
            fg=th.INK,
            font=font(10, "bold"),
            anchor="w",
        ).pack(fill="x")
        tk.Label(
            guide_inner,
            text=(
                f"每天 {plan.target} 个单词：先安排到期复习，再用新词补足。"
                "答错的词明天再见面，答对后复习间隔逐渐拉长；选“我认识”的词不再作为新词出现。"
            ),
            bg=th.CARD,
            fg=th.MUTED,
            font=font(8),
            justify="left",
            anchor="w",
            wraplength=S(760),
        ).pack(fill="x", pady=(S(4), S(7)))
        tk.Label(
            guide_inner,
            text=(
                "词库来源：wangjiuyi543-ui/cet6-vocabulary（MIT，2020–2025 真题词频）"
                " + KyleBing/english-vocabulary（BSD-3-Clause，释义/音标/例句）。"
            ),
            bg=th.CARD,
            fg=th.FAINT,
            font=font(7),
            justify="left",
            anchor="w",
            wraplength=S(760),
        ).pack(fill="x")

    def _deck_stat(
        self,
        parent: tk.Misc,
        label: str,
        value: str,
        color: str,
        *,
        right: bool = False,
    ) -> None:
        box = tk.Frame(parent, bg=th.SIDEBAR)
        box.pack(side="right" if right else "left")
        tk.Label(
            box,
            text=label,
            bg=th.SIDEBAR,
            fg=th.SIDEBAR_MUTED,
            font=font(8),
            anchor="w" if not right else "e",
        ).pack(fill="x")
        tk.Label(
            box,
            text=value,
            bg=th.SIDEBAR,
            fg=color,
            font=font(14, "bold"),
            anchor="w" if not right else "e",
        ).pack(fill="x")

    def _show_summary(self) -> None:
        self.mode = "summary"
        self.current_word = None
        self.feedback = None
        self._render(scroll_top=True)

    # ------------------------------------------------------------------
    # Study screen
    # ------------------------------------------------------------------
    def _build_study(
        self,
        plan: VocabDay,
        stats: VocabStats,
        entry: PlanEntry,
    ) -> None:
        self._build_header(
            "背单词",
            "选一个最接近的中文释义。",
            right_factory=lambda parent: TextButton(
                parent,
                "退出学习",
                self._back_to_overview,
                fg=th.MUTED,
                hover_fg=th.ORANGE,
                bg=th.BG,
                font_size=9,
            ),
        )

        progress_row = tk.Frame(self.content, bg=th.BG)
        progress_row.pack(fill="x", pady=(0, S(13)))
        tk.Label(
            progress_row,
            text=f"已完成 {plan.completed} / {plan.total}",
            bg=th.BG,
            fg=th.SUBTEXT,
            font=font(8, "bold"),
            anchor="w",
        ).pack(side="left")
        tk.Label(
            progress_row,
            text=f"新词 {plan.new_count} · 复习 {plan.review_count}",
            bg=th.BG,
            fg=th.FAINT,
            font=font(8),
            anchor="e",
        ).pack(side="right")
        overall = ProgressBar(self.content, bg=th.BG)
        overall.pack(fill="x", pady=(S(6), 0))
        pct = round(plan.completed / plan.total * 100) if plan.total else 0
        overall.set(pct, th.GREEN)

        study = tk.Frame(self.content, bg=th.BG)
        study.pack(fill="x", padx=(S(58), S(58)), pady=(S(16), 0))

        word_card = make_card(study)
        word_card.pack(fill="x")
        inner = tk.Frame(word_card, bg=th.CARD)
        inner.pack(fill="x", padx=S(24), pady=S(20))

        meta = tk.Frame(inner, bg=th.CARD)
        meta.pack(fill="x")
        kind_bg = th.GREEN_SOFT if entry.kind == "new" else th.BLUE_SOFT
        kind_fg = th.GREEN_DARK if entry.kind == "new" else th.BLUE
        Pill(
            meta,
            "新词" if entry.kind == "new" else "复习",
            bg=kind_bg,
            fg=kind_fg,
            font_size=8,
            padx=9,
            pady=3,
            parent_bg=th.CARD,
        ).pack(side="left")
        if entry.word.band == "core":
            Pill(
                meta,
                "高频核心",
                bg=th.ORANGE_SOFT,
                fg=th.ORANGE_DARK,
                font_size=8,
                padx=9,
                pady=3,
                parent_bg=th.CARD,
            ).pack(side="left", padx=(S(6), 0))
        tk.Label(
            meta,
            text=entry.word.frequency_text,
            bg=th.CARD,
            fg=th.FAINT,
            font=font(8),
            anchor="e",
        ).pack(side="right")

        tk.Label(
            inner,
            text=entry.word.word,
            bg=th.CARD,
            fg=th.INK,
            font=font(32, "bold"),
            anchor="w",
        ).pack(fill="x", pady=(S(18), 0))

        pronunciation = tk.Frame(inner, bg=th.CARD)
        pronunciation.pack(fill="x", pady=(S(1), 0))
        if entry.word.phonetic_display:
            tk.Label(
                pronunciation,
                text=entry.word.phonetic_display,
                bg=th.CARD,
                fg=th.SUBTEXT,
                font=font(11),
                anchor="w",
            ).pack(side="left")
        TextButton(
            pronunciation,
            "发音",
            self._speak_current,
            fg=th.GREEN_DARK,
            hover_fg=th.GREEN,
            bg=th.CARD,
            font_size=9,
            weight="bold",
        ).pack(side="left", padx=(S(12), 0))
        if entry.word.tag:
            tk.Label(
                pronunciation,
                text=f"· {entry.word.tag}",
                bg=th.CARD,
                fg=th.FAINT,
                font=font(8),
            ).pack(side="right")

        self._divider(inner)

        prompt = tk.Frame(inner, bg=th.CARD)
        prompt.pack(fill="x", pady=(S(13), S(8)))
        tk.Label(
            prompt,
            text="选择正确的中文释义",
            bg=th.CARD,
            fg=th.INK,
            font=font(10, "bold"),
            anchor="w",
        ).pack(side="left")
        if self.feedback is None:
            tk.Label(
                prompt,
                text="按 1–4 也可选择",
                bg=th.CARD,
                fg=th.FAINT,
                font=font(8),
            ).pack(side="right")

        self.choice_cards = []
        letters = "ABCD"
        for index, choice in enumerate(self.choices):
            card = ChoiceCard(
                inner,
                letters[index] if index < len(letters) else str(index + 1),
                choice.text,
                lambda idx=index: self._choose(idx),
            )
            card.pack(fill="x", pady=(0, S(7)))
            if self.feedback is not None:
                selected = self.feedback.get("selected") == index
                card.set_answer_state(
                    correct=choice.correct,
                    selected=selected,
                )
            self.choice_cards.append(card)

        if self.feedback is None:
            footer = tk.Frame(inner, bg=th.CARD)
            footer.pack(fill="x", pady=(S(6), 0))
            TextButton(
                footer,
                "不会，看答案",
                self._show_answer,
                fg=th.MUTED,
                hover_fg=th.RED,
                bg=th.CARD,
                font_size=9,
            ).pack(side="left")
            TextButton(
                footer,
                "我认识，直接跳过",
                self._mark_known,
                fg=th.FAINT,
                hover_fg=th.GREEN,
                bg=th.CARD,
                font_size=9,
            ).pack(side="right")
        else:
            self._build_feedback(inner, plan, entry)

    def _divider(self, master: tk.Misc) -> None:
        tk.Frame(master, bg=th.BORDER, height=S(1)).pack(
            fill="x", pady=(S(13), S(0))
        )

    def _build_feedback(
        self,
        parent: tk.Misc,
        plan: VocabDay,
        entry: PlanEntry,
    ) -> None:
        assert self.feedback is not None
        result: AnswerResult = self.feedback["result"]
        known = bool(self.feedback.get("known"))
        correct = bool(self.feedback.get("correct"))
        if known:
            status = "已标记为认识"
            detail = "这个词不再作为新词出现，之后只会在到期复习里出现。"
            color = th.GREEN_DARK
            bg = th.GREEN_SOFT
        elif correct:
            status = "答对了"
            detail = f"下次复习：{self._interval_label(result.interval_days)}"
            color = th.GREEN_DARK
            bg = th.GREEN_SOFT
        else:
            status = "这次没答对"
            detail = "已经安排明天再考一次，先把它认熟。"
            color = th.RED
            bg = th.RED_SOFT
        panel = tk.Frame(
            parent,
            bg=bg,
            bd=0,
            highlightthickness=S(1),
            highlightbackground=th.tint(color, 0.65),
        )
        panel.pack(fill="x", pady=(S(12), 0))
        panel_inner = tk.Frame(panel, bg=bg)
        panel_inner.pack(fill="x", padx=S(15), pady=S(12))

        banner = tk.Frame(panel_inner, bg=bg)
        banner.pack(fill="x")
        tk.Label(
            banner,
            text=status,
            bg=bg,
            fg=color,
            font=font(11, "bold"),
            anchor="w",
        ).pack(side="left")
        tk.Label(
            banner,
            text=entry.word.word,
            bg=bg,
            fg=color,
            font=font(10, "bold"),
            anchor="e",
        ).pack(side="right")
        tk.Label(
            panel_inner,
            text=detail,
            bg=bg,
            fg=th.SUBTEXT,
            font=font(8),
            anchor="w",
            justify="left",
        ).pack(fill="x", pady=(S(2), S(9)))

        for pos, meaning in entry.word.definitions:
            row = tk.Frame(panel_inner, bg=bg)
            row.pack(fill="x", pady=(0, S(3)))
            if pos:
                tk.Label(
                    row,
                    text=pos,
                    bg=bg,
                    fg=th.MUTED,
                    font=font(8, "bold"),
                    anchor="w",
                    width=7,
                ).pack(side="left", anchor="n")
            tk.Label(
                row,
                text=meaning,
                bg=bg,
                fg=th.INK,
                font=font(9),
                anchor="w",
                justify="left",
                wraplength=S(620),
            ).pack(side="left", fill="x", expand=True)
        if entry.word.usage:
            tk.Label(
                panel_inner,
                text=f"搭配：{entry.word.usage}",
                bg=bg,
                fg=th.SUBTEXT,
                font=font(8),
                anchor="w",
                justify="left",
                wraplength=S(620),
            ).pack(fill="x", pady=(S(3), 0))
        if entry.word.has_example:
            tk.Frame(panel_inner, bg=th.tint(color, 0.45), height=S(1)).pack(
                fill="x", pady=(S(10), S(8))
            )
            tk.Label(
                panel_inner,
                text="例句",
                bg=bg,
                fg=th.MUTED,
                font=font(7, "bold"),
                anchor="w",
            ).pack(fill="x")
            tk.Label(
                panel_inner,
                text=entry.word.example_en,
                bg=bg,
                fg=th.INK,
                font=font(9),
                anchor="w",
                justify="left",
                wraplength=S(620),
            ).pack(fill="x", pady=(S(3), 0))
            tk.Label(
                panel_inner,
                text=entry.word.example_zh,
                bg=bg,
                fg=th.SUBTEXT,
                font=font(8),
                anchor="w",
                justify="left",
                wraplength=S(620),
            ).pack(fill="x", pady=(S(3), 0))

        actions = tk.Frame(panel_inner, bg=bg)
        actions.pack(fill="x", pady=(S(13), 0))
        next_label = "完成今日单词" if plan.remaining <= 0 else "下一个"
        RoundedButton(
            actions,
            next_label,
            self._next_word,
            fill=th.GREEN,
            bg=bg,
            padx=17,
            pady=7,
            font_size=9,
        ).pack(side="right")
        tk.Label(
            actions,
            text="回车继续",
            bg=bg,
            fg=th.FAINT,
            font=font(8),
        ).pack(side="right", padx=(0, S(10)))
        self.after_idle(self.focus_set)

    @staticmethod
    def _interval_label(days: int) -> str:
        if days <= 1:
            return "明天"
        if days < 7:
            return f"{days} 天后"
        if days < 30:
            return f"{round(days / 7)} 周后"
        return f"{round(days / 30)} 个月后"

    def _speak_current(self) -> None:
        if self.current_word is not None:
            speak_word(self.current_word.word)

    def _choose(self, index: int) -> None:
        if self.mode != "study" or self.feedback is not None:
            return
        if index < 0 or index >= len(self.choices):
            return
        choice = self.choices[index]
        if self.current_word is None:
            return
        result = self.app.vocab.answer(
            self.app.today,
            self.current_word.word,
            correct=choice.correct,
        )
        if result is None:
            return
        self.feedback = {
            "selected": index,
            "correct": choice.correct,
            "known": False,
            "result": result,
        }
        self.app.handle_vocab_activity()
        self.focus_set()
        self._render(scroll_bottom=True)

    def _show_answer(self) -> None:
        if self.mode != "study" or self.feedback is not None:
            return
        if self.current_word is None:
            return
        result = self.app.vocab.answer(
            self.app.today,
            self.current_word.word,
            correct=False,
        )
        if result is None:
            return
        self.feedback = {
            "selected": None,
            "correct": False,
            "known": False,
            "result": result,
        }
        self.app.handle_vocab_activity()
        self.focus_set()
        self._render(scroll_bottom=True)

    def _mark_known(self) -> None:
        if self.mode != "study" or self.feedback is not None:
            return
        if self.current_word is None:
            return
        result = self.app.vocab.answer(
            self.app.today,
            self.current_word.word,
            correct=False,
            known=True,
        )
        if result is None:
            return
        self.feedback = {
            "selected": None,
            "correct": False,
            "known": True,
            "result": result,
        }
        self.app.handle_vocab_activity()
        self.focus_set()
        self._render(scroll_bottom=True)

    def _next_word(self) -> None:
        if self.feedback is None:
            return
        self.feedback = None
        self.choices = []
        plan = self.app.vocab.ensure_plan(self.app.today)
        entry = plan.next_incomplete()
        if entry is None:
            self.mode = "summary"
            self.current_word = None
            self._render(scroll_top=True)
            return
        self._begin_word(entry)

    def _back_to_overview(self) -> None:
        self.mode = "overview"
        self.current_word = None
        self.choices = []
        self.feedback = None
        self._render(scroll_top=True)

    # ------------------------------------------------------------------
    # Completion screen
    # ------------------------------------------------------------------
    def _build_summary(self, plan: VocabDay, stats: VocabStats) -> None:
        self._build_header(
            "今日单词 · 完成",
            "学习记录已经自动写进今天的任务。",
            right_factory=lambda parent: Pill(
                parent,
                "六级单词",
                bg=th.CARD,
                fg=th.SUBTEXT,
                font_size=9,
                padx=13,
                pady=6,
                parent_bg=th.BG,
            ),
        )
        study = tk.Frame(self.content, bg=th.BG)
        study.pack(fill="x", padx=(S(58), S(58)), pady=(S(20), 0))
        card = make_card(study)
        card.pack(fill="x")
        inner = tk.Frame(card, bg=th.CARD)
        inner.pack(fill="x", padx=S(30), pady=S(28))

        badge = tk.Canvas(
            inner,
            width=S(64),
            height=S(64),
            bg=th.CARD,
            bd=0,
            highlightthickness=0,
        )
        badge.pack()
        badge.create_oval(
            S(2),
            S(2),
            S(62),
            S(62),
            fill=th.GREEN_SOFT,
            outline="",
        )
        badge.create_text(
            S(32),
            S(30),
            text="✓",
            fill=th.GREEN,
            font=font(26, "bold"),
        )
        tk.Label(
            inner,
            text="今天的单词收工了",
            bg=th.CARD,
            fg=th.INK,
            font=font(21, "bold"),
        ).pack(pady=(S(10), S(4)))
        attempts = sum(entry.attempts for entry in plan.entries)
        accuracy_text = f"{plan.accuracy}%" if attempts else "—"
        tk.Label(
            inner,
            text=f"{plan.total} 个单词 · 答对率 {accuracy_text} · 新词 {plan.new_count} · 复习 {plan.review_count}",
            bg=th.CARD,
            fg=th.SUBTEXT,
            font=font(9),
        ).pack()

        stats_row = tk.Frame(inner, bg=th.CARD)
        stats_row.pack(fill="x", pady=(S(22), S(20)))
        self._summary_stat(stats_row, "已学单词", f"{stats.learned:,}")
        self._summary_stat(stats_row, "标记认识", f"{stats.mastered:,}")
        self._summary_stat(stats_row, "到期复习", f"{stats.due:,}")

        buttons = tk.Frame(inner, bg=th.CARD)
        buttons.pack()
        RoundedButton(
            buttons,
            "回到今日计划",
            lambda: self.app.navigate("today"),
            fill=th.GREEN,
            bg=th.CARD,
            padx=18,
            pady=8,
            font_size=9,
        ).pack(side="left")
        RoundedButton(
            buttons,
            "留在单词页",
            self._back_to_overview,
            fill=th.CARD_TINT,
            hover_fill=th.BG_SOFT,
            pressed_fill=th.TRACK,
            text_color=th.SUBTEXT,
            bg=th.CARD,
            outline=th.BORDER,
            padx=15,
            pady=8,
            font_size=9,
        ).pack(side="left", padx=(S(8), 0))
        missed = sum(
            1
            for entry in plan.entries
            if entry.attempts and not entry.correct
        )
        if missed:
            footer_text = f"今天有 {missed} 个错词，已经排进明天的复习。"
        elif stats.mastered:
            footer_text = "标记为认识的词已收进掌握列表，之后只安排到期复习。"
        else:
            footer_text = "答对的词会按间隔继续复习，明天见。"
        tk.Label(
            inner,
            text=footer_text,
            bg=th.CARD,
            fg=th.FAINT,
            font=font(8),
        ).pack(pady=(S(16), 0))

    def _summary_stat(self, parent: tk.Misc, label: str, value: str) -> None:
        card = tk.Frame(
            parent,
            bg=th.BG_SOFT,
            bd=0,
            highlightthickness=S(1),
            highlightbackground=th.BORDER,
        )
        card.pack(side="left", fill="x", expand=True, padx=(0, S(8)))
        tk.Label(
            card,
            text=value,
            bg=th.BG_SOFT,
            fg=th.INK,
            font=font(18, "bold"),
        ).pack(pady=(S(10), 0))
        tk.Label(
            card,
            text=label,
            bg=th.BG_SOFT,
            fg=th.MUTED,
            font=font(8),
        ).pack(pady=(0, S(10)))

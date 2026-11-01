"""Vocabulary deck, spaced-repetition scheduling and daily word planning."""

from __future__ import annotations

import json
import random
import re
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

from .store import Store

DEFAULT_WORD_DATA = Path(__file__).with_name("worddata") / "cet6_words.json"
DEFAULT_DAILY_WORDS = 30


@dataclass(frozen=True, slots=True)
class Word:
    word: str
    phonetic: str
    definitions: tuple[tuple[str, str], ...]
    short: str
    example_en: str
    example_zh: str
    rank: int
    frequency: int
    papers: int
    years: int
    band: str
    tag: str
    usage: str

    @property
    def phonetic_display(self) -> str:
        if not self.phonetic:
            return ""
        value = self.phonetic.strip("/[] ")
        value = value.replace("'", "ˈ").replace(":", "ː")
        return f"/{value}/"

    @property
    def frequency_text(self) -> str:
        if self.rank > 0:
            return f"真题词频 #{self.rank} · 出现 {self.frequency} 次 · {self.papers} 套试卷"
        return "六级核心词"

    @property
    def has_example(self) -> bool:
        return bool(self.example_en and self.example_zh)


@dataclass(frozen=True, slots=True)
class MeaningChoice:
    text: str
    correct: bool


@dataclass(frozen=True, slots=True)
class PlanEntry:
    word: Word
    kind: str
    position: int
    completed: bool
    correct: bool
    known: bool
    attempts: int


@dataclass(frozen=True, slots=True)
class VocabDay:
    day: date
    target: int
    entries: tuple[PlanEntry, ...]

    @property
    def total(self) -> int:
        return len(self.entries)

    @property
    def completed(self) -> int:
        return sum(1 for entry in self.entries if entry.completed)

    @property
    def remaining(self) -> int:
        return self.total - self.completed

    @property
    def new_count(self) -> int:
        return sum(1 for entry in self.entries if entry.kind == "new")

    @property
    def review_count(self) -> int:
        return sum(1 for entry in self.entries if entry.kind == "review")

    @property
    def all_done(self) -> bool:
        return bool(self.entries) and self.completed == self.total

    @property
    def accuracy(self) -> int:
        attempts = sum(entry.attempts for entry in self.entries)
        if attempts <= 0:
            return 0
        correct = sum(1 for entry in self.entries if entry.correct)
        return round(correct / attempts * 100)

    def next_incomplete(self) -> PlanEntry | None:
        for entry in self.entries:
            if not entry.completed:
                return entry
        return None


@dataclass(frozen=True, slots=True)
class AnswerResult:
    word: Word
    correct: bool
    known: bool
    next_review: date
    interval_days: int


@dataclass(frozen=True, slots=True)
class VocabStats:
    learned: int
    mastered: int
    due: int
    today_correct: int
    today_attempts: int
    plan_total: int
    plan_completed: int
    bank_total: int
    core_total: int
    exam_total: int


def schedule_next(
    existing: dict | None,
    *,
    correct: bool,
    known: bool,
    day: date,
) -> tuple[int, float, date]:
    """Return (interval days, ease, next review date) for one answer."""
    if known:
        ease = max(2.6, float(existing["ease"]) if existing else 2.5)
        return 60, ease, day + timedelta(days=60)
    if not correct:
        ease = max(1.3, (float(existing["ease"]) if existing else 2.5) - 0.2)
        return 1, ease, day + timedelta(days=1)
    if existing is None:
        return 1, 2.5, day + timedelta(days=1)
    ease = min(3.0, float(existing["ease"]) + 0.05)
    interval = max(1, min(365, round(int(existing["interval_days"]) * ease)))
    return interval, ease, day + timedelta(days=interval)


class WordBank:
    def __init__(self, path: str | Path = DEFAULT_WORD_DATA) -> None:
        self.path = Path(path)
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"无法加载六级词库：{exc}") from exc
        self.meta = dict(payload.get("meta", {}))
        words = []
        for item in payload.get("words", []):
            definitions = tuple(
                (str(definition.get("pos", "")), str(definition.get("cn", "")))
                for definition in item.get("defs", [])
                if definition.get("cn")
            )
            if not definitions:
                continue
            words.append(
                Word(
                    word=str(item.get("word", "")).lower(),
                    phonetic=str(item.get("phonetic", "")),
                    definitions=definitions,
                    short=str(item.get("short", "")) or definitions[0][1],
                    example_en=str(item.get("example_en", "")),
                    example_zh=str(item.get("example_zh", "")),
                    rank=int(item.get("rank", 0) or 0),
                    frequency=int(item.get("frequency", 0) or 0),
                    papers=int(item.get("papers", 0) or 0),
                    years=int(item.get("years", 0) or 0),
                    band=str(item.get("band", "exam")),
                    tag=str(item.get("tag", "")),
                    usage=str(item.get("usage", "")),
                )
            )
        self.words = tuple(words)
        self._by_word = {word.word: word for word in self.words if word.word}

    @property
    def total(self) -> int:
        return len(self.words)

    @property
    def core_total(self) -> int:
        return sum(1 for word in self.words if word.band == "core")

    @property
    def exam_total(self) -> int:
        return self.total - self.core_total

    def get(self, word: str) -> Word | None:
        return self._by_word.get(str(word).strip().lower())

    def build_options(
        self,
        target: Word,
        seed: str,
        count: int = 4,
    ) -> list[MeaningChoice]:
        correct_text = _normalise_meaning(target.short)
        correct_tokens = _meaning_tokens(target.short)
        pairs: list[tuple[int, str, str]] = []
        for word in self.words:
            if word.word == target.word:
                continue
            text = word.short.strip()
            clean = _normalise_meaning(text)
            if not clean or clean == correct_text:
                continue
            if (
                len(clean) >= 3
                and (clean in correct_text or correct_text in clean)
            ):
                continue
            if _meaning_tokens(text) & correct_tokens:
                continue
            pairs.append((abs(len(text) - len(target.short)), word.word, text))
        pairs.sort(key=lambda item: (item[0], item[1]))
        rng = random.Random(f"{seed}:{target.word}")
        pool = pairs[: min(160, len(pairs))]
        rng.shuffle(pool)
        distractors: list[str] = []
        used = {correct_text}
        used_tokens = set(correct_tokens)
        for _, _, text in pool:
            clean = _normalise_meaning(text)
            tokens = _meaning_tokens(text)
            if clean in used or (tokens & used_tokens):
                continue
            used.add(clean)
            used_tokens.update(tokens)
            distractors.append(text)
            if len(distractors) >= count - 1:
                break
        if len(distractors) < count - 1:
            for _, _, text in pairs:
                clean = _normalise_meaning(text)
                if clean in used:
                    continue
                used.add(clean)
                distractors.append(text)
                if len(distractors) >= count - 1:
                    break
        choices = [MeaningChoice(target.short.strip(), True)]
        choices.extend(MeaningChoice(text, False) for text in distractors)
        rng.shuffle(choices)
        return choices


def _normalise_meaning(text: str) -> str:
    return re.sub(r"[\s；;，,。.!！?？()（）\-—…]", "", text)


def _meaning_tokens(text: str) -> set[str]:
    return {
        token
        for token in re.split(r"[\s；;，,。.!！?？()（）\-—…/]+", text)
        if len(token) >= 2
    }


class VocabService:
    def __init__(
        self,
        store: Store,
        bank: WordBank | None = None,
    ) -> None:
        self.store = store
        self.bank = bank or WordBank()

    @property
    def bank_total(self) -> int:
        return self.bank.total

    def daily_target(self) -> int:
        task = self.store.get_vocab_task()
        if task is None:
            return DEFAULT_DAILY_WORDS
        return max(1, int(task.target))

    def ensure_plan(self, day: date | None = None) -> VocabDay:
        target_day = day or self.store.current_date()
        existing_day = self.store.get_vocab_day(target_day)
        if existing_day is not None:
            return self._build_day(target_day, existing_day["target"])
        target = self.daily_target()
        progress = {
            row["word"]: row for row in self.store.get_all_vocab_progress()
        }
        due: list[tuple[date, int, str]] = []
        for word, row in progress.items():
            if row["known"]:
                continue
            try:
                next_review = date.fromisoformat(row["next_review"])
            except ValueError:
                continue
            if next_review <= target_day and self.bank.get(word):
                due.append((next_review, -row["wrong_count"], word))
        due.sort()
        items: list[tuple[str, str]] = []
        for _, _, word in due[:target]:
            items.append((word, "review"))
        planned = {word for word, _ in items}
        if len(items) < target:
            for word in self.bank.words:
                if word.word in progress or word.word in planned:
                    continue
                items.append((word.word, "new"))
                planned.add(word.word)
                if len(items) >= target:
                    break
        self.store.create_vocab_plan(target_day, target, items)
        day_plan = self._build_day(target_day, target)
        self.sync_task(target_day, day_plan)
        return day_plan

    def _build_day(self, day: date, target: int) -> VocabDay:
        entries = []
        for row in self.store.get_vocab_plan(day):
            word = self.bank.get(row["word"])
            if word is None:
                continue
            entries.append(
                PlanEntry(
                    word=word,
                    kind=row["kind"],
                    position=row["position"],
                    completed=row["completed"],
                    correct=row["correct"],
                    known=row["known"],
                    attempts=row["attempts"],
                )
            )
        return VocabDay(day=day, target=target, entries=tuple(entries))

    def answer(
        self,
        day: date,
        word: str,
        *,
        correct: bool,
        known: bool = False,
    ) -> AnswerResult | None:
        target_word = self.bank.get(word)
        if target_word is None:
            return None
        plan = self.store.get_vocab_plan(day)
        plan_row = next(
            (row for row in plan if row["word"] == target_word.word), None
        )
        if plan_row is None or plan_row["completed"]:
            return None
        existing = self.store.get_vocab_progress(target_word.word)
        interval, ease, next_review = schedule_next(
            existing,
            correct=bool(correct),
            known=bool(known),
            day=day,
        )
        updated = self.store.record_vocab_answer(
            day,
            target_word.word,
            correct=bool(correct),
            known=bool(known),
            next_review=next_review,
            interval_days=interval,
            ease=ease,
        )
        if not updated:
            return None
        self.sync_task(day)
        return AnswerResult(
            word=target_word,
            correct=bool(correct),
            known=bool(known),
            next_review=next_review,
            interval_days=interval,
        )

    def sync_task(
        self,
        day: date | None = None,
        plan: VocabDay | None = None,
    ) -> int:
        target_day = day or self.store.current_date()
        task = self.store.get_vocab_task()
        if task is None:
            return 0
        if plan is None:
            stored_day = self.store.get_vocab_day(target_day)
            if stored_day is None:
                return 0
            plan = self._build_day(target_day, stored_day["target"])
        if not plan.entries:
            amount = task.target
        elif plan.all_done:
            amount = task.target
        else:
            amount = min(plan.completed, task.target)
        self.store.set_progress(task.id, amount, target_day)
        return amount

    def stats(self, day: date | None = None) -> VocabStats:
        target_day = day or self.store.current_date()
        plan = self.ensure_plan(target_day)
        progress = self.store.get_all_vocab_progress()
        due = 0
        for row in progress:
            if row["known"]:
                continue
            try:
                if date.fromisoformat(row["next_review"]) <= target_day:
                    due += 1
            except ValueError:
                continue
        plan_stats = self.store.get_vocab_plan_stats(target_day)
        return VocabStats(
            learned=len(progress),
            mastered=sum(1 for row in progress if row["known"]),
            due=due,
            today_correct=plan_stats["correct"],
            today_attempts=plan_stats["attempts"],
            plan_total=plan.total,
            plan_completed=plan.completed,
            bank_total=self.bank.total,
            core_total=self.bank.core_total,
            exam_total=self.bank.exam_total,
        )

    def options_for(self, word: Word, day: date) -> list[MeaningChoice]:
        return self.bank.build_options(word, f"{day.isoformat()}:{word.word}")

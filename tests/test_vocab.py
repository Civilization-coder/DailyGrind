from __future__ import annotations

import json
import tempfile
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path

from dailygrind.store import Store
from dailygrind.vocab import (
    DEFAULT_WORD_DATA,
    VocabService,
    WordBank,
    schedule_next,
)


class MutableClock:
    def __init__(self, now: datetime) -> None:
        self.now = now

    def __call__(self) -> datetime:
        return self.now

    def advance_days(self, days: int) -> None:
        self.now += timedelta(days=days)


def make_word(index: int, word: str, meaning: str) -> dict:
    return {
        "word": word,
        "phonetic": f"/{word}/",
        "defs": [{"pos": "n.", "cn": meaning}],
        "short": meaning,
        "example_en": f"This is an example with {word}.",
        "example_zh": f"这是一个包含 {word} 的例句。",
        "rank": index,
        "frequency": 100 - index,
        "papers": 5,
        "years": 3,
        "band": "core" if index <= 2 else "exam",
        "tag": "",
        "usage": "",
    }


class VocabularyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        base = Path(self.tempdir.name)
        self.clock = MutableClock(datetime(2026, 11, 1, 9, 0))
        self.store = Store(base / "vocab.db", clock=self.clock)
        data = {
            "meta": {"total_count": 5},
            "words": [
                make_word(1, "alpha", "第一个希腊字母"),
                make_word(2, "bravo", "表示喝彩的喊声"),
                make_word(3, "charlie", "通讯中代表字母 C"),
                make_word(4, "delta", "三角洲；第四个字母"),
                make_word(5, "echo", "回声；重复"),
            ],
        }
        self.data_path = base / "bank.json"
        self.data_path.write_text(
            json.dumps(data, ensure_ascii=False), encoding="utf-8"
        )
        self.bank = WordBank(self.data_path)
        task = self.store.get_vocab_task()
        assert task is not None
        self.store.update_task(
            task.id,
            title=task.title,
            description=task.description,
            target=3,
            unit=task.unit,
            icon=task.icon,
            step=task.step,
        )
        self.service = VocabService(self.store, self.bank)

    def tearDown(self) -> None:
        self.store.close()
        self.tempdir.cleanup()

    def test_plan_uses_target_and_bank_order(self) -> None:
        plan = self.service.ensure_plan(self.clock.now.date())
        self.assertEqual(plan.target, 3)
        self.assertEqual(plan.total, 3)
        self.assertEqual(plan.new_count, 3)
        self.assertEqual(plan.review_count, 0)
        self.assertEqual(
            [entry.word.word for entry in plan.entries],
            ["alpha", "bravo", "charlie"],
        )
        task = self.store.get_vocab_task()
        assert task is not None
        self.assertEqual(self.store.get_amounts().get(task.id, 0), 0)

    def test_answers_sync_vocab_task_and_known_is_mastered(self) -> None:
        plan = self.service.ensure_plan(self.clock.now.date())
        first, second, third = plan.entries
        result = self.service.answer(
            self.clock.now.date(), first.word.word, correct=True
        )
        self.assertIsNotNone(result)
        self.service.answer(
            self.clock.now.date(), second.word.word, correct=False
        )
        known = self.service.answer(
            self.clock.now.date(), third.word.word, correct=False, known=True
        )
        self.assertIsNotNone(known)
        self.assertTrue(known.known)
        task = self.store.get_vocab_task()
        assert task is not None
        self.assertEqual(self.store.get_amounts().get(task.id), 3)
        progress = {row["word"]: row for row in self.store.get_all_vocab_progress()}
        self.assertFalse(progress["alpha"]["known"])
        self.assertFalse(progress["bravo"]["known"])
        self.assertTrue(progress["charlie"]["known"])
        self.assertEqual(progress["alpha"]["next_review"], "2026-11-02")
        self.assertEqual(progress["bravo"]["next_review"], "2026-11-02")
        stats = self.service.stats(self.clock.now.date())
        self.assertEqual(stats.learned, 3)
        self.assertEqual(stats.mastered, 1)
        self.assertEqual(stats.today_correct, 1)
        self.assertEqual(stats.today_attempts, 2)

    def test_review_words_are_prioritised_next_day(self) -> None:
        plan = self.service.ensure_plan(self.clock.now.date())
        for entry in plan.entries:
            self.service.answer(
                self.clock.now.date(), entry.word.word, correct=True
            )
        self.assertTrue(
            self.store.get_vocab_plan_stats(self.clock.now.date())["completed"]
            == 3
        )
        self.clock.advance_days(1)
        next_day = self.clock.now.date()
        next_plan = self.service.ensure_plan(next_day)
        self.assertEqual(next_plan.review_count, 3)
        self.assertEqual(next_plan.new_count, 0)
        self.assertEqual(
            [entry.word.word for entry in next_plan.entries],
            ["alpha", "bravo", "charlie"],
        )
        self.assertTrue(all(entry.kind == "review" for entry in next_plan.entries))

    def test_one_answer_cannot_be_recorded_twice(self) -> None:
        plan = self.service.ensure_plan(self.clock.now.date())
        word = plan.entries[0].word.word
        first = self.service.answer(self.clock.now.date(), word, correct=True)
        second = self.service.answer(self.clock.now.date(), word, correct=False)
        self.assertIsNotNone(first)
        self.assertIsNone(second)
        progress = self.store.get_vocab_progress(word)
        assert progress is not None
        self.assertEqual(progress["seen_count"], 1)

    def test_options_are_stable_and_have_one_answer(self) -> None:
        plan = self.service.ensure_plan(self.clock.now.date())
        target = plan.entries[0].word
        first = self.service.options_for(target, self.clock.now.date())
        second = self.service.options_for(target, self.clock.now.date())
        self.assertEqual(
            [(choice.text, choice.correct) for choice in first],
            [(choice.text, choice.correct) for choice in second],
        )
        self.assertEqual(len(first), 4)
        self.assertEqual(sum(1 for choice in first if choice.correct), 1)
        self.assertIn(target.short, [choice.text for choice in first])


class SchedulerTests(unittest.TestCase):
    def test_new_word_schedules_tomorrow(self) -> None:
        interval, ease, review = schedule_next(
            None, correct=True, known=False, day=date(2026, 11, 1)
        )
        self.assertEqual((interval, ease, review), (1, 2.5, date(2026, 11, 2)))

    def test_wrong_answer_schedules_tomorrow(self) -> None:
        existing = {"ease": 2.5, "interval_days": 10}
        interval, ease, review = schedule_next(
            existing, correct=False, known=False, day=date(2026, 11, 1)
        )
        self.assertEqual(interval, 1)
        self.assertAlmostEqual(ease, 2.3)
        self.assertEqual(review, date(2026, 11, 2))

    def test_known_word_schedules_far_out(self) -> None:
        interval, _, review = schedule_next(
            None, correct=False, known=True, day=date(2026, 11, 1)
        )
        self.assertEqual(interval, 60)
        self.assertEqual(review, date(2026, 12, 31))

    def test_correct_review_grows_interval(self) -> None:
        existing = {"ease": 2.5, "interval_days": 3}
        interval, ease, review = schedule_next(
            existing, correct=True, known=False, day=date(2026, 11, 1)
        )
        self.assertEqual(interval, 8)
        self.assertAlmostEqual(ease, 2.55)
        self.assertEqual(review, date(2026, 11, 9))


class BundledWordBankTests(unittest.TestCase):
    def test_real_deck_loads_and_is_large_enough(self) -> None:
        bank = WordBank(DEFAULT_WORD_DATA)
        self.assertGreaterEqual(bank.total, 1500)
        self.assertGreaterEqual(bank.core_total, 150)
        self.assertGreater(bank.exam_total, 1000)
        first = bank.words[0]
        self.assertTrue(first.definitions)
        self.assertTrue(first.short)
        choices = bank.build_options(first, "2026-11-01")
        self.assertEqual(len(choices), 4)
        self.assertEqual(sum(1 for choice in choices if choice.correct), 1)
        self.assertTrue(all(choice.text for choice in choices))


if __name__ == "__main__":
    unittest.main()

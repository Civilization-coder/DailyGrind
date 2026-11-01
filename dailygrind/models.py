"""Pure domain logic for DailyGrind.

This module deliberately has no Tkinter or SQLite dependencies so the rules
behind progress, streaks and reminders can be tested in isolation.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Iterable, Mapping, Sequence

WEEKDAYS_CN = ("周一", "周二", "周三", "周四", "周五", "周六", "周日")

QUOTES = (
    "完成比完美更重要，先坐下来做那一道题。",
    "别高估一天，也别低估一百天。",
    "今天的一小步，会连成明天的一条路。",
    "把注意力放在下一件小事上。",
    "稳稳地走，也算走得快。",
    "真正拉开差距的，是每天都做一点。",
    "刷题不是收藏题，订正过的才算真正拥有。",
    "单词今天多见一面，考场上就少陌生一点。",
    "状态不好也没关系，降低一点强度，但别断。",
    "你今天愿意坐下来，已经赢过昨天的自己。",
)


@dataclass(frozen=True, slots=True)
class Task:
    id: int
    title: str
    description: str
    target: int
    unit: str
    icon: str
    color: str
    step: int
    sort_order: int
    created_at: str = ""

    def __post_init__(self) -> None:
        if self.target < 1:
            raise ValueError("每日目标必须大于 0")
        if self.step < 1:
            raise ValueError("单次步长必须大于 0")


@dataclass(frozen=True, slots=True)
class TaskState:
    task: Task
    amount: int

    @property
    def capped_amount(self) -> int:
        return max(0, min(self.amount, self.task.target))

    @property
    def completed(self) -> bool:
        return self.amount >= self.task.target

    @property
    def percent(self) -> int:
        return _percent(self.capped_amount, self.task.target)

    @property
    def remaining(self) -> int:
        return max(0, self.task.target - self.amount)

    @property
    def amount_text(self) -> str:
        return f"{self.capped_amount} / {self.task.target} {self.task.unit}"


@dataclass(frozen=True, slots=True)
class DaySnapshot:
    states: tuple[TaskState, ...]

    @property
    def total_tasks(self) -> int:
        return len(self.states)

    @property
    def completed_tasks(self) -> int:
        return sum(1 for state in self.states if state.completed)

    @property
    def remaining_tasks(self) -> int:
        return self.total_tasks - self.completed_tasks

    @property
    def total_units(self) -> int:
        return sum(state.task.target for state in self.states)

    @property
    def done_units(self) -> int:
        return sum(state.capped_amount for state in self.states)

    @property
    def percent(self) -> int:
        return _percent(self.done_units, self.total_units)

    @property
    def all_done(self) -> bool:
        return self.total_tasks > 0 and self.completed_tasks == self.total_tasks

    @property
    def outstanding(self) -> tuple[TaskState, ...]:
        return tuple(state for state in self.states if not state.completed)


def make_snapshot(tasks: Sequence[Task], amounts: Mapping[int, int]) -> DaySnapshot:
    states = tuple(
        TaskState(task=task, amount=max(0, int(amounts.get(task.id, 0))))
        for task in tasks
    )
    return DaySnapshot(states=states)


def _percent(part: int, total: int) -> int:
    if total <= 0:
        return 0
    return max(0, min(100, int(part * 100 / total + 0.5)))


def current_streak(completed_days: Iterable[date], today: date) -> int:
    """Count a streak including today, or up to yesterday if today is open."""
    completed = set(completed_days)
    cursor = today if today in completed else today - timedelta(days=1)
    streak = 0
    while cursor in completed:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


def longest_streak(completed_days: Iterable[date]) -> int:
    ordered = sorted(set(completed_days))
    best = 0
    running = 0
    previous: date | None = None
    for day in ordered:
        if previous is not None and day == previous + timedelta(days=1):
            running += 1
        else:
            running = 1
        best = max(best, running)
        previous = day
    return best


def recent_completion(
    completed_days: Iterable[date],
    today: date,
    tracking_start: date | None = None,
    window: int = 7,
) -> tuple[int, int]:
    """Return completed days and tracked days in a recent window.

    The denominator stops growing before the first tracked day, so a new user
    sees "1 / 1" instead of a misleading "1 / 7".
    """
    completed = set(completed_days)
    earliest = today - timedelta(days=max(1, window) - 1)
    if tracking_start is not None:
        earliest = max(earliest, tracking_start)
    if earliest > today:
        return 0, 0

    total = (today - earliest).days + 1
    done = sum(
        1
        for offset in range(total)
        if earliest + timedelta(days=offset) in completed
    )
    return done, total


def weekday_cn(day: date) -> str:
    return WEEKDAYS_CN[day.weekday()]


def format_date_cn(day: date, with_weekday: bool = True) -> str:
    text = f"{day.year} 年 {day.month} 月 {day.day} 日"
    return f"{text} · {weekday_cn(day)}" if with_weekday else text


def format_short_date_cn(day: date) -> str:
    return f"{day.month} 月 {day.day} 日"


def format_month_cn(year: int, month: int) -> str:
    return f"{year} 年 {month} 月"


def question_for_day(day: date) -> str:
    return QUOTES[day.toordinal() % len(QUOTES)]


def parse_hhmm(value: str) -> time:
    try:
        parsed = datetime.strptime(value.strip(), "%H:%M")
    except (TypeError, ValueError) as exc:
        raise ValueError("提醒时间应为 HH:MM 格式") from exc
    return parsed.time()


def format_hhmm(value: str) -> str:
    parsed = parse_hhmm(value)
    return f"{parsed.hour:02d}:{parsed.minute:02d}"


def reminder_has_passed(now: datetime, reminder_hhmm: str) -> bool:
    target = parse_hhmm(reminder_hhmm)
    return (now.hour, now.minute) >= (target.hour, target.minute)


def safe_progress(amount: int, target: int) -> int:
    if target <= 0:
        return 0
    return max(0, min(int(amount), int(target)))

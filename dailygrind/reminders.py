"""Reminder scheduling policy, kept separate from the Tk dialogs."""

from __future__ import annotations

from datetime import date, datetime, timedelta

from .models import format_hhmm, parse_hhmm, reminder_has_passed


class ReminderScheduler:
    """Decide whether a reminder popup should appear right now.

    The window layer owns the popup itself. This class only tracks timing
    state: the daily trigger, snoozes, and deliberate dismissal for the day.
    """

    def __init__(
        self,
        enabled: bool = True,
        reminder_hhmm: str = "20:30",
        snooze_minutes: int = 10,
    ) -> None:
        self.enabled = bool(enabled)
        self.reminder_hhmm = format_hhmm(reminder_hhmm)
        self.snooze_minutes = max(1, int(snooze_minutes))
        self.snooze_until: datetime | None = None
        self.dismissed_for: date | None = None

    def configure(self, enabled: bool, reminder_hhmm: str) -> None:
        self.enabled = bool(enabled)
        self.reminder_hhmm = format_hhmm(reminder_hhmm)
        self.snooze_until = None
        self.dismissed_for = None

    def is_due(self, now: datetime, all_done: bool) -> bool:
        if not self.enabled or all_done:
            return False
        if not reminder_has_passed(now, self.reminder_hhmm):
            return False
        if self.dismissed_for == now.date():
            return False
        if self.snooze_until is not None and now < self.snooze_until:
            return False
        return True

    def snooze(self, now: datetime, minutes: int | None = None) -> datetime:
        duration = self.snooze_minutes if minutes is None else max(1, int(minutes))
        self.snooze_until = now + timedelta(minutes=duration)
        self.dismissed_for = None
        return self.snooze_until

    def dismiss_for_day(self, now: datetime) -> None:
        self.dismissed_for = now.date()
        self.snooze_until = None

    def reset(self) -> None:
        self.snooze_until = None
        self.dismissed_for = None

    @property
    def reminder_time(self):
        return parse_hhmm(self.reminder_hhmm)

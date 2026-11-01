"""SQLite persistence for DailyGrind.

The rest of the app talks to this module instead of writing SQL. A completed
day is stored as a snapshot when all currently active tasks reach their target,
which keeps historical streaks stable if tasks are edited later.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from datetime import date, datetime
from pathlib import Path
from typing import Any

from .models import DaySnapshot, Task, make_snapshot, safe_progress

PALETTE = (
    "#2F7A57",
    "#C97845",
    "#527191",
    "#9A687F",
    "#777A4B",
    "#4B7A73",
)

DEFAULT_TASKS = (
    {
        "title": "蓝桥杯真题",
        "description": "独立完成一道真题，写下思路和易错点。",
        "target": 1,
        "unit": "道",
        "icon": "蓝",
        "color": "#2F7A57",
        "step": 1,
    },
    {
        "title": "六级词汇",
        "description": "新词和复习结合，重在反复见面。",
        "target": 30,
        "unit": "个",
        "icon": "词",
        "color": "#C97845",
        "step": 5,
        "kind": "vocab",
    },
    {
        "title": "六级真题",
        "description": "限时完成一套真题，订正比刷题更重要。",
        "target": 1,
        "unit": "套",
        "icon": "题",
        "color": "#527191",
        "step": 1,
    },
)

DEFAULT_SETTINGS = {
    "reminder_enabled": "1",
    "reminder_time": "20:30",
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    kind        TEXT NOT NULL DEFAULT 'manual',
    target      INTEGER NOT NULL CHECK(target > 0),
    unit        TEXT NOT NULL DEFAULT '次',
    icon        TEXT NOT NULL DEFAULT '日',
    color       TEXT NOT NULL DEFAULT '#2F7A57',
    step        INTEGER NOT NULL DEFAULT 1 CHECK(step > 0),
    sort_order  INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS progress (
    task_id    INTEGER NOT NULL,
    day        TEXT NOT NULL,
    amount     INTEGER NOT NULL CHECK(amount >= 0),
    updated_at TEXT NOT NULL,
    PRIMARY KEY (task_id, day),
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_progress_day ON progress(day);

CREATE TABLE IF NOT EXISTS day_records (
    day          TEXT PRIMARY KEY,
    completed_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS vocab_progress (
    word          TEXT PRIMARY KEY,
    first_seen    TEXT NOT NULL,
    last_seen     TEXT NOT NULL,
    next_review   TEXT NOT NULL,
    interval_days INTEGER NOT NULL DEFAULT 1,
    ease          REAL NOT NULL DEFAULT 2.5,
    correct_count INTEGER NOT NULL DEFAULT 0,
    wrong_count   INTEGER NOT NULL DEFAULT 0,
    seen_count    INTEGER NOT NULL DEFAULT 0,
    known         INTEGER NOT NULL DEFAULT 0,
    last_result   TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS vocab_days (
    day        TEXT PRIMARY KEY,
    target     INTEGER NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS vocab_plan (
    day       TEXT NOT NULL,
    word      TEXT NOT NULL,
    kind      TEXT NOT NULL CHECK(kind IN ('new', 'review')),
    position  INTEGER NOT NULL,
    completed INTEGER NOT NULL DEFAULT 0,
    correct   INTEGER NOT NULL DEFAULT 0,
    known     INTEGER NOT NULL DEFAULT 0,
    attempts  INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (day, word)
);

CREATE INDEX IF NOT EXISTS idx_vocab_plan_day ON vocab_plan(day, position);
CREATE INDEX IF NOT EXISTS idx_vocab_review ON vocab_progress(known, next_review);
"""


class Store:
    def __init__(
        self,
        db_path: str | Path,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._clock = clock or datetime.now
        self._closed = False
        self.conn = sqlite3.connect(str(self.db_path), timeout=8.0)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.execute("PRAGMA journal_mode = WAL")
        self.conn.execute("PRAGMA synchronous = NORMAL")
        self._initialize()

    # ------------------------------------------------------------------
    # Lifecycle and bootstrap
    # ------------------------------------------------------------------
    def _initialize(self) -> None:
        self.conn.executescript(SCHEMA)
        with self.conn:
            self._migrate()
            if self.get_setting("initialized") is None:
                self._seed_defaults()
                self.set_setting("tracking_start", self._today().isoformat())
                self.set_setting("initialized", "1")
            for key, value in DEFAULT_SETTINGS.items():
                if self.get_setting(key) is None:
                    self.set_setting(key, value)
            self._ensure_vocab_task()
            self.conn.execute("PRAGMA user_version = 2")

    def _migrate(self) -> None:
        columns = {
            str(row["name"])
            for row in self.conn.execute("PRAGMA table_info(tasks)").fetchall()
        }
        if "kind" not in columns:
            self.conn.execute(
                "ALTER TABLE tasks ADD COLUMN kind TEXT NOT NULL DEFAULT 'manual'"
            )

    def _ensure_vocab_task(self) -> None:
        existing = self.conn.execute(
            "SELECT id FROM tasks WHERE kind = 'vocab' LIMIT 1"
        ).fetchone()
        if existing is not None:
            return
        candidate = self.conn.execute(
            """
            SELECT id FROM tasks
             WHERE title = '六级词汇'
             ORDER BY id ASC LIMIT 1
            """
        ).fetchone()
        if candidate is not None:
            self.conn.execute(
                "UPDATE tasks SET kind = 'vocab' WHERE id = ?",
                (int(candidate["id"]),),
            )

    def _seed_defaults(self) -> None:
        now = self._now().isoformat(timespec="seconds")
        rows = []
        for index, task in enumerate(DEFAULT_TASKS):
            rows.append(
                (
                    task["title"],
                    task["description"],
                    task.get("kind", "manual"),
                    task["target"],
                    task["unit"],
                    task["icon"],
                    task["color"],
                    task["step"],
                    index,
                    now,
                )
            )
        self.conn.executemany(
            """
            INSERT INTO tasks
                (title, description, kind, target, unit, icon, color, step,
                 sort_order, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )

    def close(self) -> None:
        if not self._closed:
            self.conn.close()
            self._closed = True

    def __enter__(self) -> "Store":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Time helpers
    # ------------------------------------------------------------------
    def _now(self) -> datetime:
        return self._clock()

    def _today(self) -> date:
        return self._now().date()

    def current_date(self) -> date:
        """Today according to the store's clock (real clock in production)."""
        return self._today()

    # ------------------------------------------------------------------
    # Tasks
    # ------------------------------------------------------------------
    @staticmethod
    def _row_to_task(row: sqlite3.Row) -> Task:
        return Task(
            id=int(row["id"]),
            title=str(row["title"]),
            description=str(row["description"]),
            target=int(row["target"]),
            unit=str(row["unit"]),
            icon=str(row["icon"]),
            color=str(row["color"]),
            step=int(row["step"]),
            sort_order=int(row["sort_order"]),
            created_at=str(row["created_at"]),
            kind=str(row["kind"]),
        )

    def list_tasks(self) -> list[Task]:
        rows = self.conn.execute(
            "SELECT * FROM tasks ORDER BY sort_order ASC, id ASC"
        ).fetchall()
        return [self._row_to_task(row) for row in rows]

    def get_task(self, task_id: int) -> Task | None:
        row = self.conn.execute(
            "SELECT * FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()
        return self._row_to_task(row) if row else None

    def get_vocab_task(self) -> Task | None:
        row = self.conn.execute(
            "SELECT * FROM tasks WHERE kind = 'vocab' ORDER BY id ASC LIMIT 1"
        ).fetchone()
        return self._row_to_task(row) if row else None

    def create_task(
        self,
        title: str,
        description: str = "",
        target: int = 1,
        unit: str = "次",
        icon: str = "",
        step: int = 1,
        color: str | None = None,
        kind: str = "manual",
    ) -> Task:
        clean_title = str(title).strip()
        if not clean_title:
            raise ValueError("任务名称不能为空")
        clean_target = int(target)
        clean_step = int(step)
        if clean_target < 1:
            raise ValueError("每日目标必须大于 0")
        if clean_step < 1:
            raise ValueError("单次步长必须大于 0")
        clean_unit = str(unit).strip() or "次"
        clean_icon = str(icon).strip()[:2] or clean_title[:1]
        clean_description = str(description).strip()
        clean_kind = kind if kind in {"manual", "vocab"} else "manual"
        created_at = self._now().isoformat(timespec="seconds")

        with self.conn:
            order = self.conn.execute(
                "SELECT COALESCE(MAX(sort_order), -1) + 1 FROM tasks"
            ).fetchone()[0]
            chosen_color = color or PALETTE[int(order) % len(PALETTE)]
            cursor = self.conn.execute(
                """
                INSERT INTO tasks
                    (title, description, kind, target, unit, icon, color, step,
                     sort_order, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    clean_title,
                    clean_description,
                    clean_kind,
                    clean_target,
                    clean_unit,
                    clean_icon,
                    chosen_color,
                    clean_step,
                    int(order),
                    created_at,
                ),
            )
            task_id = int(cursor.lastrowid)

        self.sync_day(self._today())
        task = self.get_task(task_id)
        if task is None:  # pragma: no cover - only possible on database damage
            raise RuntimeError("任务创建失败")
        return task

    def update_task(
        self,
        task_id: int,
        *,
        title: str,
        description: str,
        target: int,
        unit: str,
        icon: str,
        step: int,
    ) -> Task:
        existing = self.get_task(task_id)
        if existing is None:
            raise ValueError("任务不存在或已被删除")
        clean_title = str(title).strip()
        if not clean_title:
            raise ValueError("任务名称不能为空")
        clean_target = int(target)
        clean_step = int(step)
        if clean_target < 1:
            raise ValueError("每日目标必须大于 0")
        if clean_step < 1:
            raise ValueError("单次步长必须大于 0")
        clean_unit = str(unit).strip() or "次"
        clean_icon = str(icon).strip()[:2] or clean_title[:1]

        today = self._today().isoformat()
        with self.conn:
            self.conn.execute(
                """
                UPDATE tasks
                   SET title = ?, description = ?, target = ?, unit = ?,
                       icon = ?, step = ?
                 WHERE id = ?
                """,
                (
                    clean_title,
                    str(description).strip(),
                    clean_target,
                    clean_unit,
                    clean_icon,
                    clean_step,
                    task_id,
                ),
            )
            self.conn.execute(
                """
                UPDATE progress
                   SET amount = ?
                 WHERE task_id = ? AND day = ? AND amount > ?
                """,
                (clean_target, task_id, today, clean_target),
            )

        self.sync_day(self._today())
        updated = self.get_task(task_id)
        if updated is None:  # pragma: no cover
            raise RuntimeError("任务更新失败")
        return updated

    def delete_task(self, task_id: int) -> None:
        with self.conn:
            self.conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        self.sync_day(self._today())

    def task_count(self) -> int:
        return int(self.conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0])

    # ------------------------------------------------------------------
    # Daily progress
    # ------------------------------------------------------------------
    def get_amounts(self, day: date | str | None = None) -> dict[int, int]:
        target_day = self._day_key(day)
        rows = self.conn.execute(
            "SELECT task_id, amount FROM progress WHERE day = ? AND amount > 0",
            (target_day,),
        ).fetchall()
        return {int(row["task_id"]): int(row["amount"]) for row in rows}

    def get_day_snapshot(self, day: date | str | None = None) -> DaySnapshot:
        return make_snapshot(self.list_tasks(), self.get_amounts(day))

    def set_progress(
        self,
        task_id: int,
        amount: int,
        day: date | str | None = None,
    ) -> int:
        task = self.get_task(task_id)
        if task is None:
            raise ValueError("任务不存在或已被删除")
        target_day = self._day_key(day)
        clean_amount = safe_progress(amount, task.target)
        now = self._now().isoformat(timespec="seconds")

        with self.conn:
            if clean_amount == 0:
                self.conn.execute(
                    "DELETE FROM progress WHERE task_id = ? AND day = ?",
                    (task_id, target_day),
                )
            else:
                self.conn.execute(
                    """
                    INSERT INTO progress (task_id, day, amount, updated_at)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(task_id, day) DO UPDATE SET
                        amount = excluded.amount,
                        updated_at = excluded.updated_at
                    """,
                    (task_id, target_day, clean_amount, now),
                )
        self.sync_day(target_day)
        return clean_amount

    def adjust_progress(
        self,
        task_id: int,
        delta: int,
        day: date | str | None = None,
    ) -> int:
        task = self.get_task(task_id)
        if task is None:
            raise ValueError("任务不存在或已被删除")
        target_day = self._day_key(day)
        current = int(self.get_amounts(target_day).get(task_id, 0))
        return self.set_progress(task_id, current + int(delta), target_day)

    def complete_task(
        self,
        task_id: int,
        day: date | str | None = None,
    ) -> int:
        task = self.get_task(task_id)
        if task is None:
            raise ValueError("任务不存在或已被删除")
        return self.set_progress(task_id, task.target, day)

    def sync_day(self, day: date | str | None = None) -> bool:
        """Reconcile the completed-day snapshot for one date.

        Returns True when the day is complete. Historical dates are left alone
        unless callers explicitly sync them, so adding a new task today cannot
        rewrite last week's records.
        """
        target_day = self._day_key(day)
        snapshot = self.get_day_snapshot(target_day)
        with self.conn:
            if snapshot.all_done:
                completed_at = self._now().isoformat(timespec="seconds")
                self.conn.execute(
                    """
                    INSERT INTO day_records (day, completed_at)
                    VALUES (?, ?)
                    ON CONFLICT(day) DO UPDATE SET
                        completed_at = day_records.completed_at
                    """,
                    (target_day, completed_at),
                )
            else:
                self.conn.execute(
                    "DELETE FROM day_records WHERE day = ?", (target_day,)
                )
        return snapshot.all_done

    # ------------------------------------------------------------------
    # History and statistics
    # ------------------------------------------------------------------
    def completed_days(
        self,
        start: date | None = None,
        end: date | None = None,
    ) -> set[date]:
        clauses: list[str] = []
        values: list[str] = []
        if start is not None:
            clauses.append("day >= ?")
            values.append(start.isoformat())
        if end is not None:
            clauses.append("day <= ?")
            values.append(end.isoformat())
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self.conn.execute(
            f"SELECT day FROM day_records {where} ORDER BY day", values
        ).fetchall()
        return {date.fromisoformat(row["day"]) for row in rows}

    def days_with_progress(
        self,
        start: date | None = None,
        end: date | None = None,
    ) -> set[date]:
        clauses = ["amount > 0"]
        values: list[str] = []
        if start is not None:
            clauses.append("day >= ?")
            values.append(start.isoformat())
        if end is not None:
            clauses.append("day <= ?")
            values.append(end.isoformat())
        where = " AND ".join(clauses)
        rows = self.conn.execute(
            f"SELECT DISTINCT day FROM progress WHERE {where} ORDER BY day",
            values,
        ).fetchall()
        return {date.fromisoformat(row["day"]) for row in rows}

    def get_tracking_start(self) -> date:
        value = self.get_setting("tracking_start")
        if value:
            try:
                return date.fromisoformat(value)
            except ValueError:
                pass
        return self._today()

    def total_completed_days(self) -> int:
        return int(
            self.conn.execute("SELECT COUNT(*) FROM day_records").fetchone()[0]
        )

    def has_progress(self, day: date | str | None = None) -> bool:
        target_day = self._day_key(day)
        row = self.conn.execute(
            "SELECT 1 FROM progress WHERE day = ? AND amount > 0 LIMIT 1",
            (target_day,),
        ).fetchone()
        return row is not None

    def is_day_complete(self, day: date | str | None = None) -> bool:
        target_day = self._day_key(day)
        row = self.conn.execute(
            "SELECT 1 FROM day_records WHERE day = ?", (target_day,)
        ).fetchone()
        return row is not None

    # ------------------------------------------------------------------
    # Settings
    # ------------------------------------------------------------------
    def get_setting(self, key: str, default: str | None = None) -> str | None:
        row = self.conn.execute(
            "SELECT value FROM settings WHERE key = ?", (key,)
        ).fetchone()
        return str(row["value"]) if row is not None else default

    def set_setting(self, key: str, value: Any) -> None:
        with self.conn:
            self.conn.execute(
                """
                INSERT INTO settings (key, value) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (key, str(value)),
            )

    def all_settings(self) -> dict[str, str]:
        rows = self.conn.execute("SELECT key, value FROM settings").fetchall()
        return {str(row["key"]): str(row["value"]) for row in rows}

    # ------------------------------------------------------------------
    # Vocabulary deck
    # ------------------------------------------------------------------
    def get_vocab_day(self, day: date | str | None = None) -> dict[str, Any] | None:
        target_day = self._day_key(day)
        row = self.conn.execute(
            "SELECT day, target, created_at FROM vocab_days WHERE day = ?",
            (target_day,),
        ).fetchone()
        if row is None:
            return None
        return {
            "day": str(row["day"]),
            "target": int(row["target"]),
            "created_at": str(row["created_at"]),
        }

    def get_vocab_plan(self, day: date | str | None = None) -> list[dict[str, Any]]:
        target_day = self._day_key(day)
        rows = self.conn.execute(
            """
            SELECT word, kind, position, completed, correct, known, attempts
              FROM vocab_plan
             WHERE day = ?
             ORDER BY position ASC
            """,
            (target_day,),
        ).fetchall()
        return [
            {
                "word": str(row["word"]),
                "kind": str(row["kind"]),
                "position": int(row["position"]),
                "completed": bool(row["completed"]),
                "correct": bool(row["correct"]),
                "known": bool(row["known"]),
                "attempts": int(row["attempts"]),
            }
            for row in rows
        ]

    def create_vocab_plan(
        self,
        day: date | str,
        target: int,
        items: list[tuple[str, str]],
    ) -> list[dict[str, Any]]:
        target_day = self._day_key(day)
        if self.get_vocab_day(target_day) is not None:
            return self.get_vocab_plan(target_day)
        created_at = self._now().isoformat(timespec="seconds")
        with self.conn:
            self.conn.execute(
                "INSERT INTO vocab_days (day, target, created_at) VALUES (?, ?, ?)",
                (target_day, int(target), created_at),
            )
            rows = []
            for position, (word, kind) in enumerate(items, start=1):
                clean_word = str(word).strip().lower()
                clean_kind = "review" if kind == "review" else "new"
                rows.append((target_day, clean_word, clean_kind, position))
            if rows:
                self.conn.executemany(
                    """
                    INSERT INTO vocab_plan (day, word, kind, position)
                    VALUES (?, ?, ?, ?)
                    """,
                    rows,
                )
        return self.get_vocab_plan(target_day)

    def get_all_vocab_progress(self) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            """
            SELECT word, first_seen, last_seen, next_review, interval_days,
                   ease, correct_count, wrong_count, seen_count, known, last_result
              FROM vocab_progress
             ORDER BY word ASC
            """
        ).fetchall()
        return [
            {
                "word": str(row["word"]),
                "first_seen": str(row["first_seen"]),
                "last_seen": str(row["last_seen"]),
                "next_review": str(row["next_review"]),
                "interval_days": int(row["interval_days"]),
                "ease": float(row["ease"]),
                "correct_count": int(row["correct_count"]),
                "wrong_count": int(row["wrong_count"]),
                "seen_count": int(row["seen_count"]),
                "known": bool(row["known"]),
                "last_result": str(row["last_result"]),
            }
            for row in rows
        ]

    def get_vocab_progress(self, word: str) -> dict[str, Any] | None:
        clean_word = str(word).strip().lower()
        row = self.conn.execute(
            """
            SELECT word, first_seen, last_seen, next_review, interval_days,
                   ease, correct_count, wrong_count, seen_count, known, last_result
              FROM vocab_progress WHERE word = ?
            """,
            (clean_word,),
        ).fetchone()
        if row is None:
            return None
        return {
            "word": str(row["word"]),
            "first_seen": str(row["first_seen"]),
            "last_seen": str(row["last_seen"]),
            "next_review": str(row["next_review"]),
            "interval_days": int(row["interval_days"]),
            "ease": float(row["ease"]),
            "correct_count": int(row["correct_count"]),
            "wrong_count": int(row["wrong_count"]),
            "seen_count": int(row["seen_count"]),
            "known": bool(row["known"]),
            "last_result": str(row["last_result"]),
        }

    def record_vocab_answer(
        self,
        day: date | str,
        word: str,
        *,
        correct: bool,
        known: bool,
        next_review: date | str,
        interval_days: int,
        ease: float,
    ) -> bool:
        target_day = self._day_key(day)
        clean_word = str(word).strip().lower()
        review_day = self._day_key(next_review)
        known_int = 1 if known else 0
        correct_int = 0 if known else (1 if correct else 0)
        wrong_int = 0 if known or correct else 1
        attempts = 0 if known else 1
        result = "known" if known else ("correct" if correct else "wrong")

        with self.conn:
            plan_row = self.conn.execute(
                """
                SELECT completed FROM vocab_plan
                 WHERE day = ? AND word = ?
                """,
                (target_day, clean_word),
            ).fetchone()
            if plan_row is None or bool(plan_row["completed"]):
                return False

            self.conn.execute(
                """
                INSERT INTO vocab_progress
                    (word, first_seen, last_seen, next_review, interval_days,
                     ease, correct_count, wrong_count, seen_count, known, last_result)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
                ON CONFLICT(word) DO UPDATE SET
                    last_seen = excluded.last_seen,
                    next_review = excluded.next_review,
                    interval_days = excluded.interval_days,
                    ease = excluded.ease,
                    correct_count = vocab_progress.correct_count
                                    + excluded.correct_count,
                    wrong_count = vocab_progress.wrong_count
                                  + excluded.wrong_count,
                    seen_count = vocab_progress.seen_count + 1,
                    known = excluded.known,
                    last_result = excluded.last_result
                """,
                (
                    clean_word,
                    target_day,
                    target_day,
                    review_day,
                    max(1, int(interval_days)),
                    float(ease),
                    correct_int,
                    wrong_int,
                    known_int,
                    result,
                ),
            )
            self.conn.execute(
                """
                UPDATE vocab_plan
                   SET completed = 1, correct = ?, known = ?, attempts = ?
                 WHERE day = ? AND word = ? AND completed = 0
                """,
                (
                    correct_int,
                    known_int,
                    attempts,
                    target_day,
                    clean_word,
                ),
            )
        return True

    def get_vocab_plan_stats(self, day: date | str | None = None) -> dict[str, int]:
        target_day = self._day_key(day)
        row = self.conn.execute(
            """
            SELECT COUNT(*) AS total,
                   COALESCE(SUM(completed), 0) AS completed,
                   COALESCE(SUM(correct), 0) AS correct,
                   COALESCE(SUM(known), 0) AS known,
                   COALESCE(SUM(attempts), 0) AS attempts
              FROM vocab_plan
             WHERE day = ?
            """,
            (target_day,),
        ).fetchone()
        return {
            "total": int(row["total"]),
            "completed": int(row["completed"]),
            "correct": int(row["correct"]),
            "known": int(row["known"]),
            "attempts": int(row["attempts"]),
        }

    def _day_key(self, day: date | str | None) -> str:
        if day is None:
            return self._today().isoformat()
        if isinstance(day, datetime):
            return day.date().isoformat()
        if isinstance(day, date):
            return day.isoformat()
        return str(day)

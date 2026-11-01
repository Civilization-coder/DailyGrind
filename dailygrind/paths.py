"""Application paths and small platform helpers."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

APP_NAME = "DailyGrind"
APP_TITLE = "DailyGrind · 日拱一卒"
APP_VERSION = "1.1.0"

APP_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = APP_DIR / "data"
DB_PATH = DATA_DIR / "dailygrind.db"
ICON_PATH = APP_DIR / "assets" / "dailygrind.ico"
LOG_PATH = DATA_DIR / "dailygrind.log"


def open_path(path: Path) -> None:
    """Open a file or folder in the operating system's default handler."""
    if sys.platform == "win32":
        os.startfile(str(path))  # type: ignore[attr-defined]
        return
    opener = "open" if sys.platform == "darwin" else "xdg-open"
    subprocess.Popen([opener, str(path)])  # pragma: no cover


def pythonw_executable() -> Path:
    """Return the windowless Python executable next to the current one."""
    executable = Path(sys.executable)
    if executable.name.lower() == "pythonw.exe":
        return executable
    candidate = executable.with_name("pythonw.exe")
    return candidate if candidate.exists() else executable


def entrypoint_path() -> Path:
    return APP_DIR / "app.py"

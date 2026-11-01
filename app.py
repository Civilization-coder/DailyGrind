"""DailyGrind entry point."""

from __future__ import annotations

import argparse
import ctypes
import sys
import traceback
from datetime import datetime

import tkinter as tk

from dailygrind.paths import DB_PATH, LOG_PATH
from dailygrind.store import Store
from dailygrind.ui.main_window import DailyGrindApp

_MUTEX_HANDLE = None


def _enable_windows_integration() -> None:
    if sys.platform != "win32":
        return
    try:
        # PER_MONITOR_AWARE_V2 keeps custom Tk layouts crisp on scaled screens.
        ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    except Exception:
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "DailyGrind.Desktop.1"
        )
    except Exception:
        pass


def _acquire_single_instance():
    """Return a Windows mutex handle, or None when DailyGrind is already open."""
    global _MUTEX_HANDLE
    if sys.platform != "win32":
        return True
    kernel32 = ctypes.windll.kernel32
    kernel32.CreateMutexW.argtypes = [
        ctypes.c_void_p,
        ctypes.c_bool,
        ctypes.c_wchar_p,
    ]
    kernel32.CreateMutexW.restype = ctypes.c_void_p
    kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
    handler = kernel32.CreateMutexW(
        None, False, "Local\\DailyGrind.Desktop.SingleInstance"
    )
    if not handler:
        return True
    if kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
        kernel32.CloseHandle(handler)
        return None
    _MUTEX_HANDLE = handler
    return handler


def _native_message(title: str, message: str, *, error: bool = False) -> None:
    if sys.platform == "win32":
        flags = 0x10 if error else 0x40
        try:
            ctypes.windll.user32.MessageBoxW(0, message, title, flags)
            return
        except Exception:
            pass
    if error:
        sys.stderr.write(f"{title}: {message}\n")


def _log_exception(detail: str) -> None:
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8") as handle:
            handle.write(f"\n[{datetime.now():%Y-%m-%d %H:%M:%S}]\n{detail}")
    except Exception:
        pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="DailyGrind 每日打卡")
    parser.add_argument(
        "--minimized",
        action="store_true",
        help="启动后最小化到任务栏",
    )
    args = parser.parse_args(argv)

    _enable_windows_integration()
    single_instance = _acquire_single_instance()
    if single_instance is None:
        if not args.minimized:
            _native_message("DailyGrind", "DailyGrind 已经在运行。")
        return 0

    root: tk.Tk | None = None
    store: Store | None = None
    try:
        root = tk.Tk()
        store = Store(DB_PATH)
        DailyGrindApp(root, store, start_minimized=args.minimized)
        root.mainloop()
        return 0
    except Exception:
        detail = traceback.format_exc()
        _log_exception(detail)
        _native_message(
            "DailyGrind 启动失败",
            f"程序启动失败，详细信息已写入：\n{LOG_PATH}\n\n{detail[-900:]}",
            error=True,
        )
        return 1
    finally:
        if store is not None:
            try:
                store.close()
            except Exception:
                pass
        if root is not None:
            try:
                root.destroy()
            except Exception:
                pass


if __name__ == "__main__":
    raise SystemExit(main())

"""Optional per-user Windows startup integration."""

from __future__ import annotations

import sys

from .paths import entrypoint_path, pythonw_executable

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "DailyGrind"


def startup_command() -> str:
    executable = pythonw_executable()
    entrypoint = entrypoint_path()
    return f'"{executable}" "{entrypoint}" --minimized'


def is_startup_enabled() -> bool:
    if sys.platform != "win32":
        return False
    try:
        import winreg
    except ImportError:  # pragma: no cover
        return False

    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_READ
        ) as key:
            value, _ = winreg.QueryValueEx(key, VALUE_NAME)
    except (FileNotFoundError, OSError):
        return False
    return str(value) == startup_command()


def set_startup(enabled: bool) -> None:
    if sys.platform != "win32":
        raise RuntimeError("当前系统不支持 Windows 开机自启")
    import winreg

    if enabled:
        with winreg.CreateKeyEx(
            winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE
        ) as key:
            winreg.SetValueEx(
                key, VALUE_NAME, 0, winreg.REG_SZ, startup_command()
            )
        return

    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE
        ) as key:
            winreg.DeleteValue(key, VALUE_NAME)
    except FileNotFoundError:
        return

"""Small Windows speech helper for pronouncing vocabulary words."""

from __future__ import annotations

import re
import subprocess
import sys


def speak_word(word: str) -> bool:
    """Queue a word for pronunciation without blocking the Tk main loop."""
    if sys.platform != "win32":
        return False
    if not re.fullmatch(r"[A-Za-z][A-Za-z' -]{0,48}", word):
        return False
    escaped = word.replace("'", "''")
    script = (
        "Add-Type -AssemblyName System.Speech; "
        "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
        "try { "
        "$v = $s.GetInstalledVoices() | Where-Object { "
        "$_.Enabled -and $_.VoiceInfo.Culture.Name -like 'en-*' "
        "} | Select-Object -First 1; "
        "if ($v) { $s.SelectVoice($v.VoiceInfo.Name) } "
        "} catch {}; "
        f"$s.Speak('{escaped}'); $s.Dispose()"
    )
    creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        subprocess.Popen(
            [
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-WindowStyle",
                "Hidden",
                "-Command",
                script,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creation_flags,
        )
        return True
    except OSError:
        return False

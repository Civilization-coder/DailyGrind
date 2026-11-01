@echo off
setlocal
cd /d "%~dp0"

set "PYW="
if exist "%~dp0.venv\Scripts\pythonw.exe" set "PYW=%~dp0.venv\Scripts\pythonw.exe"

if not defined PYW (
    for /f "delims=" %%P in ('where pythonw 2^>nul') do (
        if not defined PYW set "PYW=%%P"
    )
)

if not defined PYW (
    for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python3*") do (
        if exist "%%~fD\pythonw.exe" set "PYW=%%~fD\pythonw.exe"
    )
)

if not defined PYW (
    for /d %%D in ("%ProgramFiles%\Python3*") do (
        if exist "%%~fD\pythonw.exe" set "PYW=%%~fD\pythonw.exe"
    )
)

if not defined PYW (
    echo Python 3.11 or newer was not found.
    echo Install it from https://www.python.org/downloads/
    pause
    exit /b 1
)

start "" "%PYW%" "%~dp0app.py" %*
endlocal

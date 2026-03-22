@echo off
REM run.bat — Windows wrapper that delegates to run.py (cross-platform runner)
REM Works on CMD, PowerShell, and Windows Terminal

where python >nul 2>&1 && (
    python "%~dp0run.py" %*
    goto :eof
)

where python3 >nul 2>&1 && (
    python3 "%~dp0run.py" %*
    goto :eof
)

where py >nul 2>&1 && (
    py -3 "%~dp0run.py" %*
    goto :eof
)

echo ERROR: python not found. Install Python 3.8+ and try again.
exit /b 1

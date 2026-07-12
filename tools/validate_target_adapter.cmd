@echo off
setlocal

where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
  py -3 "%~dp0validate_target_adapter.py" %*
  exit /b %ERRORLEVEL%
)

where python >nul 2>nul
if %ERRORLEVEL% EQU 0 (
  python "%~dp0validate_target_adapter.py" %*
  exit /b %ERRORLEVEL%
)

echo Python 3 was not found. Install Python 3 or run the helper with an explicit Python path. 1>&2
exit /b 1

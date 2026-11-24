@echo off
chcp 65001 >nul
setlocal

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0clear-account-record.ps1" %*
set "RC=%ERRORLEVEL%"

echo.
pause
exit /b %RC%

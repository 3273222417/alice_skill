@echo off
rem ================================================================
rem  boot_schtasks.cmd -- launch target with HIGHEST integrity level
rem
rem  Why schtasks: in some environments Start-Process -Verb RunAs is
rem  blocked, while a scheduled task with /rl HIGHEST silently gets
rem  the high integrity level.
rem
rem  v1.0.2:
rem    * WORK no longer hardcoded to C:\wz_evoc.
rem      Default = parent dir of this script; override with %1.
rem    * log dir is created automatically.
rem    * pure ASCII comments (avoids GBK/936 codepage mojibake).
rem
rem  Usage:
rem    boot_schtasks.cmd                      (auto-detect)
rem    boot_schtasks.cmd "D:\evoc\evofree"   (explicit work dir)
rem ================================================================
setlocal
if "%~1"=="" (
  set "WORK=%~dp0.."
) else (
  set "WORK=%~1"
)
for %%I in ("%WORK%") do set "WORK=%%~fI"

set TASK=WZ_Run
set TARGET=%WORK%\scripts\run.cmd
set LOGDIR=%WORK%\logs

if not exist "%LOGDIR%" mkdir "%LOGDIR%" >nul 2>&1

if not exist "%TARGET%" (
  echo [boot] run.cmd not found: %TARGET%
  echo [boot] create it, or pass a work dir as the first argument.
  exit /b 2
)

echo [boot] WORK=%WORK%
echo [boot] TASK=%TASK%

schtasks /delete /tn %TASK% /f >nul 2>&1
schtasks /create /tn %TASK% /tr "cmd.exe /c %TARGET%" /sc once /st 23:59 /rl HIGHEST /f > "%LOGDIR%\boot.txt" 2>&1
echo created rc=%ERRORLEVEL% >> "%LOGDIR%\boot.txt"
schtasks /run /tn %TASK% >> "%LOGDIR%\boot.txt" 2>&1
echo run rc=%ERRORLEVEL% >> "%LOGDIR%\boot.txt"

type "%LOGDIR%\boot.txt"
exit /b 0

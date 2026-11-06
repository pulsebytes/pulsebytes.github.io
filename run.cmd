@echo off
setlocal
chcp 65001 >nul
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
set PYTHONNOUSERSITE=1
cd /d "%~dp0"
title Pulsebyte

where python >nul 2>&1 || (echo Python 3.10+ is required: https://python.org & pause & exit /b 1)
set VPY=.venv\Scripts\python.exe
if not exist %VPY% (
  echo Creating virtual environment...
  python -m venv .venv
  if errorlevel 1 (echo Could not create the virtual environment & pause & exit /b 1)
)
fc requirements.txt .venv\req.done >nul 2>&1
if errorlevel 1 (
  echo Installing packages into the virtual environment...
  %VPY% -m pip install --upgrade pip
  %VPY% -m pip install -r requirements.txt
  if errorlevel 1 (echo Package install failed & pause & exit /b 1)
  copy /y requirements.txt .venv\req.done >nul
)
if not exist .env (
  copy .env.example .env >nul
  echo Fill in .env, save it, then close Notepad to continue.
  notepad .env
)

rem ── Command dispatch ──────────────────────────────────────────────────────
if /i "%~1"=="deploy"    goto :deploy
if /i "%~1"=="orgdeploy" goto :orgdeploy
if /i "%~1"=="private"   goto :private
goto :run

:deploy
  %VPY% setup_github.py --force
  if errorlevel 1 (pause & exit /b 1)
  pause & exit /b 0

:orgdeploy
  echo.
  echo ════════════════════════════════════════════════════
  echo  Org deploy — site will live at pulsebytes.github.io
  echo ════════════════════════════════════════════════════
  echo.
  echo Before continuing, make sure you have created a GitHub
  echo organisation named "pulsebytes" at:
  echo   https://github.com/organizations/plan
  echo.
  pause
  %VPY% setup_github.py --orgdeploy
  if errorlevel 1 (pause & exit /b 1)
  pause & exit /b 0

:private
  echo Making the current repo private...
  %VPY% -c "
from dotenv import dotenv_values
from pathlib import Path
import subprocess, sys
e = dotenv_values(Path('.env'))
repo = e.get('GITHUB_REPO','')
if not repo: sys.exit('GITHUB_REPO not set in .env — run deploy first.')
r = subprocess.run(['gh','api','-XPATCH',f'repos/{repo}','-f','private=true'], capture_output=True)
print(r.stdout.decode('utf-8','replace'))
print(r.stderr.decode('utf-8','replace'))
if r.returncode == 0: print(f'Done. {repo} is now private.')
else: sys.exit('Failed.')
"
  if errorlevel 1 (pause & exit /b 1)
  pause & exit /b 0

:run
  %VPY% setup_github.py
  if errorlevel 1 (pause & exit /b 1)
  start "" cmd /c "timeout /t 4 >nul & start http://127.0.0.1:8765"
  %VPY% -m uvicorn app.main:app --host 127.0.0.1 --port 8765
  pause

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
if /i "%~1"=="deploy" (%VPY% setup_github.py --force) else (%VPY% setup_github.py)
if errorlevel 1 (pause & exit /b 1)
if /i "%~1"=="deploy" (pause & exit /b 0)
start "" cmd /c "timeout /t 4 >nul & start http://127.0.0.1:8765"
%VPY% -m uvicorn app.main:app --host 127.0.0.1 --port 8765
pause

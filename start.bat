@echo off
rem Uruchamia Generator operatow. Wymaga zainstalowanego Pythona 3.11+.
cd /d "%~dp0"
if not exist .venv (
  py -3 -m venv .venv
  .venv\Scripts\python -m pip install --upgrade pip
  .venv\Scripts\pip install -r requirements.txt
)
.venv\Scripts\python uruchom.py
pause

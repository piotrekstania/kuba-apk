@echo off
rem Uruchamia Generator operatow. Wymaga zainstalowanego Pythona 3.11+.
cd /d "%~dp0"

if not exist .venv (
  echo Pierwsze uruchomienie - przygotowuje srodowisko, to potrwa chwile...
  py -3 -m venv .venv
  if errorlevel 1 python -m venv .venv
  if not exist .venv\Scripts\python.exe (
    echo.
    echo Nie znaleziono Pythona. Zainstaluj go ze strony python.org
    echo i zaznacz opcje "Add Python to PATH", potem uruchom start.bat ponownie.
    pause
    exit /b 1
  )
)

rem Aktualizacja idzie PRZED instalacja bibliotek: gdy nowa wersja dokladana
rem nowa zaleznosc, doinstaluje sie od razu przy tym samym uruchomieniu.
rem Aktualizator stoi na samej bibliotece standardowej, wiec dziala tez wtedy,
rem gdy .venv jest jeszcze pusty. Brak internetu = program startuje po staremu.
.venv\Scripts\python -m app.aktualizacja

rem Biblioteki instalujemy takze wtedy, gdy requirements.txt zmienil sie
rem po ostatniej instalacji - inaczej program dziala ze starymi wersjami.
fc /b requirements.txt .venv\zainstalowane.txt >nul 2>&1
if errorlevel 1 (
  echo Instaluje biblioteki...
  .venv\Scripts\python -m pip install --upgrade pip
  .venv\Scripts\python -m pip install -r requirements.txt
  if errorlevel 1 (
    echo.
    echo Nie udalo sie zainstalowac bibliotek - sprawdz polaczenie z internetem.
    pause
    exit /b 1
  )
  copy /y requirements.txt .venv\zainstalowane.txt >nul
)

.venv\Scripts\python uruchom.py
pause

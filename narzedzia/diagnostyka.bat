@echo off
rem Uruchamia program w trybie diagnostycznym: kazdy krok konwersji ladu je w pliku
rem dane\konsola.log. Do uzycia, gdy program sie wysypuje i trzeba wiedziec, na czym.
rem
rem Roznice wobec start.bat:
rem   * bez aktualizacji i bez instalacji bibliotek - chodzi o to, co jest teraz,
rem   * python z -u, czyli bez buforowania: przy twardej awarii ostatnia linia
rem     zdazy trafic do pliku,
rem   * uvicorn gadatliwy, wiec widac tez zapytania z przegladarki.
rem
rem Okno bedzie puste - to normalne, wszystko idzie do pliku.

cd /d "%~dp0.."

if not exist .venv\Scripts\python.exe (
  echo Nie ma srodowiska .venv - uruchom najpierw start.bat
  pause
  exit /b 1
)

if not exist dane mkdir dane
set GENERATOR_DIAGNOSTYKA=1
rem Bez tego polskie znaki w logu wychodza jako krzaki (konsola ma cp1250, my UTF-8)
set PYTHONIOENCODING=utf-8
chcp 65001 >nul

echo.
echo Tryb diagnostyczny. Otworz http://127.0.0.1:8000/ i powtorz to, co sie wysypuje.
echo Wszystko zapisuje sie w dane\konsola.log
echo Zakoncz Ctrl+C albo zamknij okno, potem wyslij ten plik.
echo.

.venv\Scripts\python -u -m uvicorn app.main:app --host 127.0.0.1 --port 8000 ^
    --log-level debug > dane\konsola.log 2>&1

echo.
echo Serwer zakonczyl prace. Log: dane\konsola.log
pause

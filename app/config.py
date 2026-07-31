"""Ścieżki i ustawienia globalne aplikacji.

Ścieżki są liczone inaczej przy uruchomieniu z kodu, a inaczej ze spakowanego .exe:
szablony i wyniki mają leżeć obok programu (żeby dało się je edytować), a pliki
interfejsu siedzą w środku paczki PyInstallera.
"""
import sys
from pathlib import Path

KOD = Path(__file__).resolve().parent          # katalog app/

if getattr(sys, "frozen", False):              # uruchomienie ze spakowanego .exe
    BAZA = Path(sys.executable).resolve().parent
    WEB = Path(sys._MEIPASS) / "app" / "web"   # noqa: SLF001 (tak PyInstaller udostępnia zasoby)
else:
    BAZA = KOD.parent
    WEB = KOD / "web"

SZABLONY = BAZA / "szablony"       # pliki .docx z tagami {{ }} — brat edytuje je w Wordzie
WYNIKI = BAZA / "wyniki"           # wygenerowane dokumenty
DANE = BAZA / "dane"               # baza SQLite, pliki robocze

BAZA_DANYCH = DANE / "operaty.sqlite3"

HOST = "127.0.0.1"
PORT = 8000

for katalog in (SZABLONY, WYNIKI, DANE):
    katalog.mkdir(parents=True, exist_ok=True)

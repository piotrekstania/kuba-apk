"""Aktualizacja programu z GitHuba — bez gita i bez pytania programisty.

Brat uruchamia `start.bat`; ten przed startem serwera woła `python -m app.aktualizacja`.
Moduł porównuje plik `WERSJA` u siebie z tym na GitHubie i jeśli jest nowszy, pobiera
paczkę .zip gałęzi `main` i podmienia **tylko kod**.

Świętość, której nie wolno tknąć: `dane/` (baza z historią i numeracją) i `wyniki/`
(gotowe dokumenty). **`szablony/` przyjeżdżają razem z programem i są nadpisywane** —
formatki Worda utrzymuje autor w repozytorium, a nie użytkownik u siebie. Przed
podmianą stara zawartość ląduje w `dane/kopie/`, więc jest z czego wrócić.

Cały moduł stoi na bibliotece standardowej — musi działać także wtedy, gdy nowa wersja
dokłada zależności, których w `.venv` jeszcze nie ma.
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile
from datetime import datetime
from pathlib import Path

from .config import BAZA, BAZA_DANYCH, DANE

REPO = "piotrekstania/kuba-apk"
GALAZ = "main"
# Numer wersji czytamy z API, bo raw.githubusercontent serwuje plik z CDN-owego cache
# i przez kilka minut po wydaniu twierdzi, że nowej wersji nie ma (sprawdzone: paczka .zip
# miała już nowy kod, a raw nadal podawał stary numer). Raw zostaje jako zapas na wypadek
# wyczerpania limitu zapytań API — 60/godz. na adres IP, a program pyta raz na uruchomienie.
URL_WERSJA_API = f"https://api.github.com/repos/{REPO}/contents/WERSJA?ref={GALAZ}"
URL_WERSJA_RAW = f"https://raw.githubusercontent.com/{REPO}/{GALAZ}/WERSJA"
URL_PACZKA = f"https://github.com/{REPO}/archive/refs/heads/{GALAZ}.zip"
LIMIT_CZASU = 10                       # s — offline nie może blokować startu programu

PLIK_WERSJI = BAZA / "WERSJA"
KOPIE = DANE / "kopie"
ZNACZNIK_NOWOSCI = DANE / "co_nowego.txt"   # czyta go strona główna, żeby pokazać komunikat

# Co podmieniamy przy aktualizacji: kod i szablony. `szablony` są na tej liście
# celowo — jeden katalog, zawsze taki jak w repozytorium. Ta sama lista służy do
# zrobienia kopii zapasowej przed aktualizacją, więc poprzednie szablony zawsze
# lądują w `dane/kopie/`.
AKTUALIZOWANE = [
    "app", "narzedzia", "szablony",
    "requirements.txt", "start.bat", "start.sh", "uruchom.py",
    "WERSJA", "README.md", "CLAUDE.md",
]


def _czytaj_wersje(tekst: str) -> tuple[str, str]:
    """Pierwsza linia pliku WERSJA to numer, reszta to opis zmian dla użytkownika.

    BOM ucinamy sami: Notatnik i PowerShell zapisują pliki z BOM-em, a niewidzialny
    znak na początku numeru sprawiłby, że wersje nigdy nie są równe i program
    pobierałby tę samą aktualizację przy każdym uruchomieniu.
    """
    linie = [linia.strip() for linia in tekst.lstrip("﻿").strip().splitlines()]
    return (linie[0].lstrip("﻿") if linie else "?", " ".join(linie[1:]).strip())


def wersja_lokalna() -> tuple[str, str]:
    try:
        return _czytaj_wersje(PLIK_WERSJI.read_text(encoding="utf-8-sig"))
    except OSError:
        return ("?", "")


def wersja_zdalna() -> tuple[str, str] | None:
    """None = nie udało się sprawdzić (brak internetu, GitHub nie odpowiada).

    Pytamy po kolei: API (odpowiada od razu po wypchnięciu), potem raw (z cache).
    """
    for adres, naglowki in ((URL_WERSJA_API, {"Accept": "application/vnd.github.raw"}),
                            (URL_WERSJA_RAW, {})):
        try:
            zadanie = urllib.request.Request(adres, headers=naglowki)
            with urllib.request.urlopen(zadanie, timeout=LIMIT_CZASU) as odpowiedz:
                tekst = odpowiedz.read().decode("utf-8-sig")
        except (urllib.error.URLError, TimeoutError, OSError, UnicodeDecodeError):
            continue
        if tekst.lstrip().startswith("{"):
            continue          # API oddało JSON zamiast treści pliku — nie zgadujemy, idziemy dalej
        return _czytaj_wersje(tekst)
    return None


def _kopia_zapasowa(wersja: str) -> Path:
    """Baza + obecny kod lądują w dane/kopie/ — jest z czego wrócić, gdy coś padnie."""
    katalog = KOPIE / f"{datetime.now():%Y%m%d-%H%M%S}-przed-{wersja}"
    katalog.mkdir(parents=True, exist_ok=True)
    if BAZA_DANYCH.exists():
        shutil.copy2(BAZA_DANYCH, katalog / BAZA_DANYCH.name)
    for nazwa in AKTUALIZOWANE:
        zrodlo = BAZA / nazwa
        if zrodlo.is_dir():
            shutil.copytree(zrodlo, katalog / nazwa, dirs_exist_ok=True,
                            ignore=shutil.ignore_patterns("__pycache__"))
        elif zrodlo.exists():
            shutil.copy2(zrodlo, katalog / nazwa)
    return katalog


def _pobierz_paczke(katalog: Path) -> Path:
    """Ściąga zip z GitHuba i rozpakowuje; zwraca katalog z rozpakowanym projektem."""
    paczka = katalog / "nowa_wersja.zip"
    with urllib.request.urlopen(URL_PACZKA, timeout=60) as odpowiedz:
        paczka.write_bytes(odpowiedz.read())
    with zipfile.ZipFile(paczka) as zip_plik:
        zip_plik.extractall(katalog)
    # GitHub pakuje wszystko w podkatalog "<repo>-<galaz>"
    podkatalogi = [s for s in katalog.iterdir() if s.is_dir()]
    if len(podkatalogi) != 1 or not (podkatalogi[0] / "uruchom.py").exists():
        raise RuntimeError("Pobrana paczka nie wygląda na wersję programu.")
    return podkatalogi[0]


def zastosuj(nowy_kod: Path) -> None:
    for nazwa in AKTUALIZOWANE:
        zrodlo = nowy_kod / nazwa
        if not zrodlo.exists():
            continue
        cel = BAZA / nazwa
        if zrodlo.is_dir():
            # Nadpisujemy plik po pliku, nie kasujemy katalogu: `app/` jest w tej chwili
            # zaimportowany przez działający właśnie proces aktualizatora.
            shutil.copytree(zrodlo, cel, dirs_exist_ok=True,
                            ignore=shutil.ignore_patterns("__pycache__"))
        else:
            shutil.copy2(zrodlo, cel)


def co_nowego() -> str | None:
    """Jednorazowy komunikat po aktualizacji — po odczytaniu znika."""
    try:
        tresc = ZNACZNIK_NOWOSCI.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    ZNACZNIK_NOWOSCI.unlink(missing_ok=True)
    return tresc or None


def kopia_robocza_gita() -> bool:
    """Czy siedzimy w katalogu, w którym ktoś programuje, a nie u użytkownika."""
    return (BAZA / ".git").exists()


def sprawdz_i_zaktualizuj() -> bool:
    """True = coś podmieniono (program powinien wystartować już z nowego kodu)."""
    # Kopia robocza gita jest nietykalna: aktualizacja nadpisuje `app/` plikami
    # z GitHuba i skasowałaby niezacommitowane zmiany programisty. Instalacja
    # u użytkownika to rozpakowany .zip, więc katalogu `.git` tam nie ma.
    if kopia_robocza_gita() and os.environ.get("GENERATOR_WYMUS_AKTUALIZACJE") != "1":
        print("Katalog roboczy gita — pomijam aktualizację (tutaj obowiązuje `git pull`).")
        return False

    lokalna, _ = wersja_lokalna()
    zdalna = wersja_zdalna()
    if zdalna is None:
        # Nie zgadujemy przyczyny: tak samo wygląda brak internetu, padnięty GitHub
        # i literówka w adresie repozytorium.
        print("Nie udało się sprawdzić aktualizacji (brak internetu albo GitHub "
              f"nie odpowiada) — program działa dalej w wersji {lokalna}.")
        return False

    numer, opis = zdalna
    if numer == lokalna:
        print(f"Wersja {lokalna} jest aktualna.")
        return False

    print(f"Jest nowsza wersja programu: {numer} (masz {lokalna}). Pobieram...")
    KOPIE.mkdir(parents=True, exist_ok=True)
    kopia = _kopia_zapasowa(lokalna)
    try:
        with tempfile.TemporaryDirectory(dir=DANE) as tymczasowy:
            nowy_kod = _pobierz_paczke(Path(tymczasowy))
            zastosuj(nowy_kod)
    except Exception as blad:
        print("Aktualizacja się nie udała:", blad)
        print("Program działa dalej w starej wersji, nic nie zostało zepsute.")
        return False

    # Numer bierzemy z tego, co naprawdę przyszło w paczce, a nie z zapowiedzi:
    # raw.githubusercontent potrafi być kilka minut do tyłu i ogłosić starszą wersję,
    # niż zawiera pobrany .zip. Użytkownik ma zobaczyć numer, który faktycznie ma.
    zainstalowany, opis_zainstalowany = wersja_lokalna()
    ZNACZNIK_NOWOSCI.write_text(f"{zainstalowany}\n{opis_zainstalowany}", encoding="utf-8")
    print(f"Zaktualizowano do wersji {zainstalowany}. {opis_zainstalowany}")
    print(f"Kopia poprzedniej wersji i bazy: {kopia}")
    return True


if __name__ == "__main__":
    try:
        sprawdz_i_zaktualizuj()
    except Exception as blad:                     # aktualizacja nigdy nie blokuje startu
        print("Pominięto sprawdzanie aktualizacji:", blad)
    sys.exit(0)

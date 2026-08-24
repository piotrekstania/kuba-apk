"""Buduje ZMIANY.md z historii pliku WERSJA w gicie.

Każde wydanie zostawiło w `WERSJA` numer i opis napisany dla brata — to jest gotowa
historia zmian, tylko rozsypana po commitach. Skrypt ją zbiera, żeby nikt nie
przepisywał tego ręcznie i nie pomylił się w numerze.

    python narzedzia/zbuduj_zmiany.py            # pokazuje, co by zapisał
    python narzedzia/zbuduj_zmiany.py --zapisz   # zapisuje ZMIANY.md

Uruchamiaj po podbiciu `WERSJA`, przed wypchnięciem wydania. U brata ten skrypt
nigdy nie chodzi — on dostaje gotowy plik.
"""
import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path

KORZEN = Path(__file__).resolve().parent.parent
PLIK = KORZEN / "ZMIANY.md"

NAGLOWEK = """# Historia zmian

Co doszło w kolejnych wersjach programu. Ten sam opis pokazuje się raz, na stronie
głównej, zaraz po tym jak program sam się zaktualizuje.
"""


def _git(*argumenty: str) -> str:
    return subprocess.run(["git", *argumenty], cwd=KORZEN, capture_output=True,
                          text=True, encoding="utf-8", check=True).stdout


def _rozbij(tresc: str) -> tuple[str, str]:
    """Pierwsza linijka to numer, reszta — opis dla użytkownika.

    Opis zostaje **wielolinijkowy**: od wydania 103 są w nim listy punktów
    („Zmiany:”, „Nowości:”), a sklejenie wszystkiego w jeden akapit zrobiłoby z nich
    z powrotem ścianę tekstu.
    """
    czesci = [l.rstrip() for l in tresc.replace("﻿", "").strip().splitlines()]
    if not czesci:
        return "", ""
    return czesci[0].strip(), "\n".join(czesci[1:]).strip()


def wydania_zacommitowane() -> list[tuple[str, str, str]]:
    """Wydania widoczne w historii gita — bez tego, co leży w katalogu roboczym.

    Po tym liczy się numer kolejnego wydania (`narzedzia/wydaj.py`): ile wydań już
    poszło do brata, tyle jest w gicie.
    """
    return _z_gita(set())


def wydania() -> list[tuple[str, str, str]]:
    """(numer, data, opis) dla każdego wydania, od najnowszego.

    Bierzemy zawartość pliku `WERSJA` w każdym commicie, który go dotknął — a nie sam
    diff, bo wydanie bywa poprawką samego opisu przy tym samym numerze.

    Doliczamy też **niezacommitowane** podbicie z katalogu roboczego: przy wydaniu
    kolejność jest „podbij WERSJA → zbuduj historię → commit”, więc w chwili budowania
    najnowszego numeru nie ma jeszcze w gicie. Bez tego historia byłaby zawsze o jedno
    wydanie w tyle, a strażnik `test_wydana_wersja_ma_wpis_w_historii` czerwieniałby
    przy każdym wydaniu (i tak to wyszło — złapał to przy pierwszym użyciu).
    """
    zebrane: list[tuple[str, str, str]] = []
    widziane: set[str] = set()

    numer_roboczy, opis_roboczy = _rozbij(
        (KORZEN / "WERSJA").read_text(encoding="utf-8-sig"))
    if numer_roboczy:
        widziane.add(numer_roboczy)
        zebrane.append((numer_roboczy, datetime.now().strftime("%Y-%m-%d"), opis_roboczy))
    return zebrane + _z_gita(widziane)


def _z_gita(widziane: set[str]) -> list[tuple[str, str, str]]:
    zebrane: list[tuple[str, str, str]] = []
    linie = _git("log", "--format=%H %ad", "--date=short", "--", "WERSJA").splitlines()
    for wiersz in linie:
        skrot, data = wiersz.split(" ", 1)
        try:
            tresc = _git("show", f"{skrot}:WERSJA")
        except subprocess.CalledProcessError:
            continue
        numer, opis = _rozbij(tresc)
        if not numer or numer in widziane:
            continue
        widziane.add(numer)
        zebrane.append((numer, data.strip(), opis))
    return zebrane


def zbuduj() -> str:
    czesci = [NAGLOWEK]
    for numer, data, opis in wydania():
        czesci.append(f"\n## {numer} — {data}\n\n{opis or '(bez opisu)'}\n")
    return "".join(czesci)


def zapisz() -> Path:
    """Przebudowuje ZMIANY.md. Woła to też `narzedzia/wydaj.py` zaraz po stemplu."""
    PLIK.write_text(zbuduj(), encoding="utf-8")
    return PLIK


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Buduje ZMIANY.md z historii gita.")
    parser.add_argument("--zapisz", action="store_true", help="zapisz do ZMIANY.md")
    argumenty = parser.parse_args()

    tresc = zbuduj()
    if argumenty.zapisz:
        zapisz()
        print(f"zapisano {PLIK} — wydań: {len(wydania())}")
    else:
        sys.stdout.reconfigure(encoding="utf-8")
        print(tresc)

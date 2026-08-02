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


def wydania() -> list[tuple[str, str, str]]:
    """(numer, data, opis) dla każdego wydania, od najnowszego.

    Bierzemy zawartość pliku `WERSJA` w każdym commicie, który go dotknął — a nie sam
    diff, bo wydanie bywa poprawką samego opisu przy tym samym numerze.
    """
    zebrane: list[tuple[str, str, str]] = []
    widziane: set[str] = set()
    linie = _git("log", "--format=%H %ad", "--date=short", "--", "WERSJA").splitlines()
    for wiersz in linie:
        skrot, data = wiersz.split(" ", 1)
        try:
            tresc = _git("show", f"{skrot}:WERSJA")
        except subprocess.CalledProcessError:
            continue
        czesci = [l.strip() for l in tresc.replace("﻿", "").strip().splitlines()]
        if not czesci:
            continue
        numer, opis = czesci[0], " ".join(czesci[1:]).strip()
        if numer in widziane:
            continue
        widziane.add(numer)
        zebrane.append((numer, data.strip(), opis))
    return zebrane


def zbuduj() -> str:
    czesci = [NAGLOWEK]
    for numer, data, opis in wydania():
        czesci.append(f"\n## {numer} — {data}\n\n{opis or '(bez opisu)'}\n")
    return "".join(czesci)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Buduje ZMIANY.md z historii gita.")
    parser.add_argument("--zapisz", action="store_true", help="zapisz do ZMIANY.md")
    argumenty = parser.parse_args()

    tresc = zbuduj()
    if argumenty.zapisz:
        PLIK.write_text(tresc, encoding="utf-8")
        print(f"zapisano {PLIK} — wydań: {len(wydania())}")
    else:
        sys.stdout.reconfigure(encoding="utf-8")
        print(tresc)

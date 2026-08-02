"""Historia zmian czytana z pliku `ZMIANY.md`.

U brata nie ma gita — dostaje rozpakowany `.zip` — więc historia musi jechać z kodem
jako zwykły plik. Buduje go `narzedzia/zbuduj_zmiany.py` z opisów, które i tak
powstają przy każdym wydaniu w pliku `WERSJA`, więc nikt nie pisze tego dwa razy.

Format jest celowo prosty, żeby dało się go poprawić w Notatniku:

    ## 2026.08.02.7 — 2026-08-02

    Opis dla użytkownika, jedno albo kilka zdań.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import BAZA

PLIK = BAZA / "ZMIANY.md"
MYSLNIK = "—"


def _rozbij_naglowek(linia: str) -> tuple[str, str]:
    """'## 2026.08.02.7 — 2026-08-02' -> ('2026.08.02.7', '2026-08-02')."""
    tresc = linia[2:].strip()
    if MYSLNIK in tresc:
        wersja, data = tresc.split(MYSLNIK, 1)
        return wersja.strip(), data.strip()
    return tresc, ""


def wpisy(limit: int | None = None) -> list[dict[str, Any]]:
    """Wydania od najnowszego. Brak pliku to nie awaria — po prostu pusta lista."""
    try:
        tekst = PLIK.read_text(encoding="utf-8-sig")
    except OSError:
        return []

    zebrane: list[dict[str, Any]] = []
    for linia in tekst.splitlines():
        if linia.startswith("## "):
            wersja, data = _rozbij_naglowek(linia)
            zebrane.append({"wersja": wersja, "data": data, "opis": []})
        elif zebrane and linia.strip() and not linia.startswith("#"):
            zebrane[-1]["opis"].append(linia.strip())

    for wpis in zebrane:
        wpis["opis"] = " ".join(wpis["opis"])
    return zebrane[:limit] if limit else zebrane

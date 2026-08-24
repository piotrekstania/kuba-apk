"""Historia zmian czytana z pliku `ZMIANY.md`.

U brata nie ma gita — dostaje rozpakowany `.zip` — więc historia musi jechać z kodem
jako zwykły plik. Buduje go `narzedzia/zbuduj_zmiany.py` z opisów, które i tak
powstają przy każdym wydaniu w pliku `WERSJA`, więc nikt nie pisze tego dwa razy.

Format jest celowo prosty, żeby dało się go poprawić w Notatniku:

    ## 2026.08.02.7 — 2026-08-02

    Zmiany:
    - co działa inaczej niż dotąd
    - i druga taka rzecz

    Nowości:
    - co doszło

    **Cała treść idzie w punktach**, bez zdań wstępu (decyzja z 24.08.2026): wydanie to
    zwykle kilkanaście commitów, a akapit robił się ścianą tekstu, w której nie dało się
    znaleźć konkretnej zmiany. Nagłówek listy to linijka zakończona dwukropkiem, punkt
    zaczyna się od myślnika. **Opisy sprzed tej zmiany czytają się nadal** — akapit bez
    myślników jest po prostu wstępem i tak też się pokazuje.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import BAZA

PLIK = BAZA / "ZMIANY.md"
MYSLNIK = "—"
PUNKTORY = ("- ", "* ", "• ")
# Nagłówek listy to krótka linijka z dwukropkiem („Zmiany:", „Nowości:”). Ograniczenie
# długości jest po to, żeby zdanie ze wstępu zakończone dwukropkiem nie zrobiło się
# nagłówkiem pustej listy.
DLUGOSC_NAGLOWKA = 40


def rozbierz_opis(tekst: str) -> dict[str, Any]:
    """Opis wydania na wstęp i listy punktów.

    Zwraca `{"wstep": str, "grupy": [{"tytul": str, "punkty": [str, ...]}]}`.
    Linijka bez myślnika, stojąca pod punktem, jest **dalszym ciągiem tego punktu** —
    w Notatniku długi punkt sam się zawija i nie ma to znaczyć nowej pozycji.
    """
    wstep: list[str] = []
    grupy: list[dict[str, Any]] = []
    for linia in tekst.splitlines():
        tresc = linia.strip()
        if not tresc or tresc.startswith("#"):
            continue
        if tresc.startswith(PUNKTORY):
            if not grupy:
                grupy.append({"tytul": "", "punkty": []})
            grupy[-1]["punkty"].append(tresc[2:].strip())
        elif tresc.endswith(":") and len(tresc) <= DLUGOSC_NAGLOWKA:
            grupy.append({"tytul": tresc[:-1].strip(), "punkty": []})
        elif grupy and grupy[-1]["punkty"]:
            grupy[-1]["punkty"][-1] += " " + tresc
        else:
            wstep.append(tresc)
    return {"wstep": " ".join(wstep),
            "grupy": [g for g in grupy if g["punkty"]]}


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

    # Numer porządkowy liczymy tutaj, a nie zapisujemy w pliku: wynika wprost z tego,
    # ile wydań już było, więc wpisany osobno mógłby się z listą rozjechać. Lista jest
    # od najnowszego, czyli pierwszy wpis dostaje najwyższy numer.
    for numer, wpis in enumerate(zebrane, start=1):
        wpis.update(rozbierz_opis("\n".join(wpis["opis"])))
        wpis["opis"] = " ".join(wpis["opis"])      # cała treść jednym ciągiem, do szukania
        wpis["numer"] = len(zebrane) - numer + 1
    return zebrane[:limit] if limit else zebrane

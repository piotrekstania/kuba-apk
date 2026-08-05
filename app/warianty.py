"""Własne formatki użytkownika — wiele wariantów do każdego rodzaju dokumentu.

Słownik pojęć, bo to jedyne miejsce w programie, gdzie te dwie rzeczy trzeba rozróżniać:

* **kategoria** — rodzaj dokumentu, czyli szablon z `szablony/` (spis treści, sprawozdanie
  techniczne, wykaz zmian…). Kategorie utrzymuje autor programu i to one decydują,
  **jakie pola ma formularz**;
* **wariant** — plik `.docx` wgrany przez użytkownika do jednej z kategorii. Podmienia
  wyłącznie dokument, który powstanie; formularz zostaje ten sam.

**Warianty leżą w `dane/`, a nie w `szablony/`, i to jest tu najważniejsze.**
Katalog `szablony/` jest lustrzany: przy każdej aktualizacji plik, którego nie ma
w repozytorium, jest u użytkownika kasowany (`LUSTRZANE` w `aktualizacja.py`). Własna
formatka wgrana do `szablony/` zniknęłaby przy najbliższym wydaniu — a `dane/` jest
nietykalne i trafia do kopii zapasowej.

Wariant może używać tych samych znaczników co kategoria albo mniej. Gdy wnosi nowe,
mówimy o tym przy wgrywaniu, ale **nie blokujemy** — tak samo jak przy sprawdzaniu
numeru działki w ULDK. Formatka różniąca się jednym polem to najczęstszy przypadek,
a nie błąd.
"""
from __future__ import annotations

import shutil
from dataclasses import replace
from pathlib import Path
from typing import Any, BinaryIO

from . import operaty, szablony
from .config import DANE

KATALOG = DANE / "szablony"
STANDARDOWY = ""                 # pusty identyfikator = formatka z `szablony/`
ROZDZIELNIK = "/"


class BladWariantu(RuntimeError):
    """Plik, którego nie da się przyjąć — z komunikatem gotowym do pokazania."""


# --- odczyt ------------------------------------------------------------------

def _katalog_kategorii(kategoria: str) -> Path:
    # Nazwa kategorii pochodzi z listy szablonów, ale przychodzi przez formularz,
    # więc obcinamy ją do samej nazwy pliku — żeby „../..” nie wyprowadziło z `dane/`.
    return KATALOG / Path(kategoria).name


def lista(kategoria: str) -> list[dict[str, str]]:
    """Warianty danej kategorii, alfabetycznie. Standardowy nie jest tu wymieniony."""
    katalog = _katalog_kategorii(kategoria)
    if not katalog.is_dir():
        return []
    return [{"id": f"{Path(kategoria).name}{ROZDZIELNIK}{p.stem}", "nazwa": p.stem}
            for p in sorted(katalog.glob("*.docx")) if not p.name.startswith("~$")]


def wszystkie() -> dict[str, list[dict[str, str]]]:
    """Wszystkie warianty, po kategoriach — do listy w Ustawieniach."""
    return {k["id"]: lista(k["id"]) for k in szablony.lista_skrocona()}


def sa_jakies() -> bool:
    """Czy użytkownik wgrał cokolwiek. Bez tego nie pokazujemy tabelki w formularzu."""
    return any(warianty for warianty in wszystkie().values())


def plik(identyfikator: str) -> Path | None:
    """Ścieżka do pliku wariantu. None = nie ma takiego (albo to standardowy)."""
    if not identyfikator or ROZDZIELNIK not in identyfikator:
        return None
    kategoria, _, nazwa = identyfikator.partition(ROZDZIELNIK)
    kandydat = _katalog_kategorii(kategoria) / f"{Path(nazwa).name}.docx"
    return kandydat if kandydat.is_file() else None


def z_wariantem(szablon: szablony.Szablon, identyfikator: str) -> szablony.Szablon:
    """Ten sam szablon, ale wypełniany z pliku wariantu.

    Pola zostają z kategorii — to one zbudowały formularz i to one decydują, co program
    zebrał od użytkownika. Wariant podmienia wyłącznie dokument do wypełnienia.
    Nieistniejący wariant (skasowany po wygenerowaniu starego operatu) cicho wraca
    do standardowego, bo lepszy dokument z domyślnej formatki niż komunikat o błędzie.
    """
    sciezka = plik(identyfikator)
    return replace(szablon, plik=sciezka) if sciezka else szablon


# --- zapis -------------------------------------------------------------------

def _wolna_nazwa(katalog: Path, rdzen: str) -> Path:
    """`spis` → `spis.docx`, a gdy zajęte: `spis-2.docx`. Nie nadpisujemy po cichu."""
    kandydat = katalog / f"{rdzen}.docx"
    numer = 2
    while kandydat.exists():
        kandydat = katalog / f"{rdzen}-{numer}.docx"
        numer += 1
    return kandydat


def nieznane_znaczniki(kategoria: str, sciezka: Path) -> list[str]:
    """Znaczniki wariantu, których formularz tej kategorii nie zbiera.

    Takie miejsca zostaną w gotowym dokumencie puste — bez żadnego błędu, więc
    użytkownik musi się o nich dowiedzieć teraz, a nie z operatu oddanego do ośrodka.
    """
    wzorcowy = szablony.szablon_po_id(kategoria)
    if wzorcowy is None:
        return []
    znane = set(szablony.POLA_WYLICZANE)
    for pole in wzorcowy.pola:
        znane.add(pole.klucz)
        if pole.typ == "teryt":
            znane.update(pole.klucz + s for s in szablony.SUFIKSY_TERYT)
        elif pole.typ == "date":
            znane.update(pole.klucz + s for s in szablony.SUFIKSY_DATY)
        elif pole.typ == "wybor_wielokrotny":
            znane.update(pole.klucz + s for s in szablony.SUFIKSY_WYBORU)
    return sorted(set(szablony._zmienne_szablonu(sciezka)) - znane)


def dodaj(kategoria: str, nazwa_pliku: str, zawartosc: BinaryIO) -> tuple[dict[str, Any], list[str]]:
    """Przyjmuje wgrany plik. Zwraca (opis wariantu, ostrzeżenia).

    Plik ląduje na dysku dopiero po sprawdzeniu, że w ogóle da się go otworzyć jako
    szablon — inaczej w katalogu zostawałyby uszkodzone .docx, które psują listę.
    """
    if szablony.szablon_po_id(kategoria) is None:
        raise BladWariantu("Nie ma takiego rodzaju dokumentu.")
    if not nazwa_pliku.lower().endswith(".docx"):
        raise BladWariantu(
            "To musi być plik Worda (.docx). Jeśli masz .doc, otwórz go w Wordzie "
            "i zapisz przez „Zapisz jako” w formacie .docx.")

    katalog = _katalog_kategorii(kategoria)
    katalog.mkdir(parents=True, exist_ok=True)
    # Nazwę zostawiamy taką, jaką nadał jej użytkownik — to po niej rozpozna swoją
    # formatkę na liście. Zdejmujemy tylko znaki, których Windows nie przyjmie,
    # i spacje, żeby identyfikator wariantu dało się wygodnie wstawić do formularza.
    rdzen = operaty.nazwa_bezpieczna(Path(nazwa_pliku).stem, zapas="formatka")[0]
    cel = _wolna_nazwa(katalog, rdzen.replace(" ", "_"))

    roboczy = cel.with_name(cel.name + ".czesciowy")
    try:
        with open(roboczy, "wb") as zapis:
            shutil.copyfileobj(zawartosc, zapis)
        try:
            ostrzezenia_znacznikow = nieznane_znaczniki(kategoria, roboczy)
        except Exception as blad:
            raise BladWariantu(
                "Nie udało się otworzyć tego pliku jako szablonu Worda. Sprawdź, czy nie "
                f"jest uszkodzony i czy znaczniki {{{{ }}}} są domknięte. Szczegóły: {blad}"
            ) from blad
        roboczy.replace(cel)
    finally:
        roboczy.unlink(missing_ok=True)

    ostrzezenia = []
    if ostrzezenia_znacznikow:
        ostrzezenia.append(
            "Ta formatka używa znaczników, których formularz nie zbiera: "
            + ", ".join(f"{{{{ {z} }}}}" for z in ostrzezenia_znacznikow)
            + ". W gotowym dokumencie zostaną w tych miejscach puste pola — "
            "usuń je z formatki albo poproś o dołożenie tych pól do formularza.")
    return ({"id": f"{Path(kategoria).name}{ROZDZIELNIK}{cel.stem}", "nazwa": cel.stem},
            ostrzezenia)


def usun(identyfikator: str) -> bool:
    """True = plik zniknął. Operaty zrobione tym wariantem zostają nietknięte."""
    sciezka = plik(identyfikator)
    if sciezka is None:
        return False
    sciezka.unlink(missing_ok=True)
    return True


# --- zapamiętany wybór -------------------------------------------------------

KLUCZ = "wariant__"


def domyslne(ustawienia: dict[str, str]) -> dict[str, str]:
    """Ostatnio użyte warianty, z ustawień: {kategoria: identyfikator}."""
    return {klucz[len(KLUCZ):]: wartosc
            for klucz, wartosc in ustawienia.items() if klucz.startswith(KLUCZ)}


def zapamietaj(wybor: dict[str, str]) -> None:
    """Zapisuje wybór jako domyślny dla **następnego** operatu.

    Wybór dla bieżącego operatu siedzi osobno, w jego `operat.json` — inaczej poprawka
    literówki w starym operacie brałaby dzisiejszy domyślny wariant i po cichu
    podmieniałaby formatkę w gotowym dokumencie.
    """
    from . import db
    if wybor:
        db.zapisz_ustawienia({f"{KLUCZ}{kategoria}": identyfikator
                              for kategoria, identyfikator in wybor.items()})

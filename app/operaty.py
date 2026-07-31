"""Katalog operatu: jeden folder na jedną robotę.

Każde wygenerowanie dokumentu zakłada w `wyniki/` katalog nazwany **numerem operatu**
i wkłada do niego `spis_tresci.docx`. Brat dorzuca tam potem swoje pliki — mapy, szkice,
skany, wykaz współrzędnych z C-Geo — a na końcu wszystko skleja się w jeden PDF.

**Nazwa scalonego PDF-a musi być dokładnie taka jak numer roboty (KERG)** — tego wymagają
przepisy, więc nie przepuszczamy jej przez `bezpieczna_nazwa`, która gubi polskie znaki.
Podmieniamy wyłącznie znaki, których Windows w nazwie pliku nie przyjmie, i mówimy
o tym głośno, gdy do tego dojdzie.

W katalogu leżą dwa pliki opisujące robotę:

* `operat.json` — źródło prawdy dla programu (numer roboty, numer operatu, data, dane
  z formularza). Dzięki niemu katalog jest samowystarczalny: przeżyje skopiowanie na inny
  dysk i utratę bazy przy reinstalacji,
* pusty plik o nazwie numeru roboty — wyłącznie po to, żeby brat widział numer w Eksploratorze
  bez otwierania czegokolwiek. Nie ma rozszerzenia, więc nigdy nie wejdzie do sklejania.
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from . import pdf
from .config import DANE, WYNIKI

PLIK_OPISU = "operat.json"
SPIS_TRESCI = "spis_tresci.docx"

ROZSZERZENIA_PDF = {".pdf"}
ROZSZERZENIA_WORD = {".docx", ".doc", ".rtf", ".odt"}
ROZSZERZENIA_DO_SCALENIA = ROZSZERZENIA_PDF | ROZSZERZENIA_WORD

# Windows nie przyjmie tych znaków w nazwie pliku ani katalogu.
ZNAKI_ZAKAZANE = r'<>:"/\|?*'

# Pliki Worda z katalogu operatu zamieniamy na PDF poza katalogiem — inaczej powstały
# PDF zostałby przy następnym sklejaniu policzony drugi raz, obok swojego .docx.
PODGLADY = DANE / "podglad"


def nazwa_bezpieczna(tekst: str, zapas: str = "operat") -> tuple[str, bool]:
    """Zwraca (nazwa, czy_podmieniono). Zostawia polskie znaki — zmienia tylko zakazane."""
    oczyszczona = "".join("-" if z in ZNAKI_ZAKAZANE or ord(z) < 32 else z for z in tekst)
    oczyszczona = oczyszczona.strip().rstrip(". ")      # Windows nie lubi kropki na końcu
    return (oczyszczona or zapas), oczyszczona != tekst.strip()


# --- zakładanie i opis -------------------------------------------------------

def nazwa_katalogu(nr_operatu: str) -> str:
    """'001/2026' -> '001.2026'.

    Numer operatu zostaje z ukośnikiem — tak wygląda w dokumencie i tak go czyta ośrodek.
    Katalog dostaje w tym miejscu kropkę, bo Windows ukośnika w nazwie folderu nie przyjmie,
    a myślnik czytało się gorzej niż kropka.
    """
    return nazwa_bezpieczna(nr_operatu.replace("/", "."))[0]


def katalog_operatu(nr_operatu: str) -> Path:
    return WYNIKI / nazwa_katalogu(nr_operatu)


def zaloz(nr_operatu: str, nr_roboty: str, szablon: str,
          dane: dict[str, Any]) -> tuple[Path, list[str]]:
    """Tworzy katalog operatu z opisem. Zwraca (katalog, ostrzeżenia dla użytkownika)."""
    # Ukośnik w nazwie katalogu zamieniamy na kropkę po cichu — to norma, a nie usterka
    # warta straszenia użytkownika.
    ostrzezenia: list[str] = []
    nazwa = nazwa_katalogu(nr_operatu)
    katalog = WYNIKI / nazwa
    katalog.mkdir(parents=True, exist_ok=True)

    (katalog / PLIK_OPISU).write_text(json.dumps({
        "nr_operatu": nr_operatu,
        "nr_roboty": nr_roboty,
        "szablon": szablon,
        "utworzono": datetime.now().isoformat(timespec="seconds"),
        "dane": dane,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    if nr_roboty:
        znacznik, podmieniono = nazwa_bezpieczna(nr_roboty, zapas="")
        if podmieniono:
            ostrzezenia.append(
                f"Numer roboty „{nr_roboty}” zawiera znaki zabronione w nazwach plików. "
                f"Scalony PDF będzie się nazywał „{znacznik}.pdf”, a nie dokładnie tak jak "
                "numer roboty — sprawdź, czy ośrodek to przyjmie.")
        if znacznik:
            (katalog / znacznik).touch()          # pusty plik, żeby numer było widać w folderze
    return katalog, ostrzezenia


def opis(katalog: Path) -> dict[str, Any]:
    try:
        return json.loads((katalog / PLIK_OPISU).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def lista() -> list[dict[str, Any]]:
    """Katalogi operatów, od najnowszego. Rozpoznajemy je po pliku operat.json."""
    wynik = []
    for sciezka in WYNIKI.iterdir() if WYNIKI.is_dir() else []:
        if not sciezka.is_dir() or not (sciezka / PLIK_OPISU).exists():
            continue
        dane = opis(sciezka)
        wynik.append({
            "katalog": sciezka.name,
            "nr_operatu": dane.get("nr_operatu", sciezka.name),
            "nr_roboty": dane.get("nr_roboty", ""),
            "utworzono": dane.get("utworzono", ""),
            "plikow": len(pliki(sciezka)),
        })
    return sorted(wynik, key=lambda o: o["utworzono"], reverse=True)


def katalog_po_nazwie(nazwa: str) -> Path | None:
    """Zamienia nazwę z adresu na katalog — z blokadą wyjścia poza `wyniki/`."""
    kandydat = (WYNIKI / nazwa).resolve()
    if WYNIKI.resolve() not in kandydat.parents or not (kandydat / PLIK_OPISU).exists():
        return None
    return kandydat


# --- pliki w katalogu --------------------------------------------------------

def nazwa_wyniku(katalog: Path) -> str:
    """Nazwa scalonego PDF-a: dokładnie numer roboty (przepisy), z .pdf na końcu."""
    numer = opis(katalog).get("nr_roboty") or katalog.name
    return nazwa_bezpieczna(numer, zapas=katalog.name)[0] + ".pdf"


def pliki(katalog: Path) -> list[Path]:
    """Co idzie do sklejenia: PDF-y i dokumenty Worda, spis treści zawsze pierwszy.

    Pomijamy opis operatu, pusty znacznik z numerem roboty (nie ma rozszerzenia)
    i poprzedni wynik sklejania, żeby nie wpadł sam w siebie.
    """
    if not katalog.is_dir():
        return []
    wynik_scalania = nazwa_wyniku(katalog).lower()
    znalezione = [
        p for p in katalog.iterdir()
        if p.is_file()
        and p.suffix.lower() in ROZSZERZENIA_DO_SCALENIA
        and p.name != PLIK_OPISU
        and p.name.lower() != wynik_scalania
        and not p.name.startswith("~$")
    ]
    return sorted(znalezione, key=lambda p: (p.name != SPIS_TRESCI, p.name.lower()))


def jako_pdf(plik: Path) -> Path:
    """PDF danego pliku — sam siebie dla .pdf, a dla Worda konwersja z pamięcią podręczną.

    Wynik konwersji leży poza katalogiem operatu, żeby brat nie musiał patrzeć
    na duplikaty i żeby sklejanie nie policzyło tego samego dokumentu dwa razy.
    """
    if plik.suffix.lower() in ROZSZERZENIA_PDF:
        return plik

    cel = PODGLADY / plik.parent.name / (plik.stem + ".pdf")
    if cel.exists() and cel.stat().st_mtime >= plik.stat().st_mtime:
        return cel
    cel.parent.mkdir(parents=True, exist_ok=True)
    return pdf.docx_na_pdf(plik, cel)


def usun_podglady(katalog: Path) -> None:
    import shutil
    shutil.rmtree(PODGLADY / katalog.name, ignore_errors=True)


def otworz_w_systemie(sciezka: Path) -> None:
    """Otwiera katalog w Eksploratorze (albo odpowiedniku na Linuksie/macOS).

    Program chodzi na komputerze użytkownika, więc „serwer” i „biurko” to ta sama
    maszyna — okno otworzy się tam, gdzie siedzi brat. Nie czekamy na zamknięcie
    okna, więc `Popen` bez `wait()`.
    """
    import subprocess
    import sys

    if sys.platform == "win32":
        os.startfile(sciezka)                                    # noqa: S606 (tylko Windows)
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(sciezka)])
    else:
        subprocess.Popen(["xdg-open", str(sciezka)])

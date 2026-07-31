"""Wypełnianie szablonu .docx danymi z formularza."""
from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime
from pathlib import Path
from typing import Any

from docxtpl import DocxTemplate

from . import db
from .config import WYNIKI
from .szablony import Szablon

MIESIACE = ["stycznia", "lutego", "marca", "kwietnia", "maja", "czerwca", "lipca",
            "sierpnia", "września", "października", "listopada", "grudnia"]


def _bez_ogonkow(tekst: str) -> str:
    return "".join(z for z in unicodedata.normalize("NFKD", tekst) if not unicodedata.combining(z))


def bezpieczna_nazwa(tekst: str) -> str:
    """Nazwa pliku bezpieczna również na Windowsie."""
    tekst = _bez_ogonkow(tekst).replace("/", "-").replace("\\", "-")
    tekst = re.sub(r"[^A-Za-z0-9 ._-]", "", tekst).strip(" .")
    tekst = re.sub(r"\s+", "_", tekst)
    return tekst[:120] or "dokument"


def data_slownie(wartosc: str | date) -> str:
    """'2026-07-31' -> '31 lipca 2026 r.' Puste/nieznane zwraca bez zmian."""
    if isinstance(wartosc, str):
        try:
            wartosc = datetime.strptime(wartosc.strip(), "%Y-%m-%d").date()
        except ValueError:
            return wartosc
    return f"{wartosc.day} {MIESIACE[wartosc.month - 1]} {wartosc.year} r."


def data_pl(wartosc: str) -> str:
    """'2026-07-31' -> '31.07.2026'."""
    try:
        return datetime.strptime(wartosc.strip(), "%Y-%m-%d").strftime("%d.%m.%Y")
    except (ValueError, AttributeError):
        return wartosc


def przygotuj_kontekst(szablon: Szablon, dane: dict[str, Any],
                       ustawienia: dict[str, str]) -> dict[str, Any]:
    """Łączy dane z formularza, dane stałe i wartości wyliczane automatycznie."""
    dzis = date.today()
    kontekst: dict[str, Any] = dict(ustawienia)     # dane stałe (geodeta, uprawnienia, firma)
    kontekst.update(dane)

    for pole in szablon.pola:
        if pole.typ == "auto_numer" and not kontekst.get(pole.klucz):
            nazwa_licznika = szablon.licznik or szablon.id
            numer = db.nastepny_numer(nazwa_licznika, dzis.year)
            wzor = pole.domyslnie or "{numer}/{rok}"
            kontekst[pole.klucz] = wzor.format(numer=numer, numer3=f"{numer:03d}", rok=dzis.year)
        elif pole.typ == "date" and kontekst.get(pole.klucz):
            # do dokumentu idzie format polski, ale surową datę zostawiamy pod _iso
            kontekst[f"{pole.klucz}_iso"] = kontekst[pole.klucz]
            kontekst[f"{pole.klucz}_slownie"] = data_slownie(kontekst[pole.klucz])
            kontekst[pole.klucz] = data_pl(kontekst[pole.klucz])

    kontekst.setdefault("data_dzisiaj", dzis.strftime("%d.%m.%Y"))
    kontekst.setdefault("data_dzisiaj_slownie", data_slownie(dzis))
    kontekst.setdefault("rok", str(dzis.year))
    return kontekst


def nazwa_pliku(szablon: Szablon, kontekst: dict[str, Any]) -> str:
    class Luzny(dict):
        def __missing__(self, klucz):    # brak pola we wzorcu nie może wywalić generowania
            return ""
    baza = szablon.wzor_nazwy.format_map(Luzny(kontekst, id_szablonu=szablon.id))
    return bezpieczna_nazwa(baza)


def generuj(szablon: Szablon, dane: dict[str, Any], ustawienia: dict[str, str]) -> tuple[Path, dict]:
    """Zwraca ścieżkę do gotowego .docx oraz kontekst użyty do wypełnienia."""
    kontekst = przygotuj_kontekst(szablon, dane, ustawienia)
    dokument = DocxTemplate(szablon.plik)
    dokument.render(kontekst, autoescape=True)

    znacznik = datetime.now().strftime("%Y%m%d-%H%M%S")
    plik = WYNIKI / f"{nazwa_pliku(szablon, kontekst)}__{znacznik}.docx"
    dokument.save(plik)
    return plik, kontekst

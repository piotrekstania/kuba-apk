"""Wypełnianie szablonu .docx danymi z formularza."""
from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime
from pathlib import Path
from typing import Any

from docxtpl import DocxTemplate

from . import db, operaty, teryt
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


def pola_teryt(klucz: str, wybor: dict[str, str]) -> dict[str, str]:
    """Z wybranych identyfikatorów robi komplet tagów do wstawienia w Wordzie.

    Dla pola `polozenie` powstają m.in. `polozenie_gmina`, `polozenie_gmina_teryt`,
    `polozenie_obreb`, `polozenie_obreb_teryt` — nazwa i identyfikator osobno, bo
    w operacie potrzebne są oba.
    """
    wynik: dict[str, str] = {}
    opis: list[str] = []

    for poziom in ("wojewodztwo", "powiat", "gmina"):
        jednostka = teryt.jednostka(wybor.get(poziom, ""))
        wynik[f"{klucz}_{poziom}"] = jednostka["nazwa"] if jednostka else ""
        wynik[f"{klucz}_{poziom}_teryt"] = jednostka["id"] if jednostka else ""

    obreb = teryt.obreb(wybor.get("obreb", ""))
    wynik[f"{klucz}_obreb"] = obreb["nazwa"] if obreb else ""
    wynik[f"{klucz}_obreb_teryt"] = obreb["id"] if obreb else ""
    # sam czterocyfrowy numer obrębu — w operatach cytuje się często tylko jego
    wynik[f"{klucz}_obreb_numer"] = obreb["id"].rpartition(".")[2] if obreb else ""

    if wynik[f"{klucz}_obreb"]:
        opis.append(f"obręb {wynik[f'{klucz}_obreb']} ({wynik[f'{klucz}_obreb_teryt']})")
    if wynik[f"{klucz}_gmina"]:
        opis.append(f"gmina {wynik[f'{klucz}_gmina']}")
    if wynik[f"{klucz}_powiat"]:
        opis.append(f"powiat {wynik[f'{klucz}_powiat']}")
    if wynik[f"{klucz}_wojewodztwo"]:
        opis.append(f"województwo {wynik[f'{klucz}_wojewodztwo']}")
    wynik[klucz] = ", ".join(opis)
    return wynik


def przygotuj_kontekst(szablon: Szablon, dane: dict[str, Any], ustawienia: dict[str, str],
                       rezerwacje: list[tuple[str, int, int]] | None = None) -> dict[str, Any]:
    """Łączy dane z formularza, dane stałe i wartości wyliczane automatycznie.

    Do `rezerwacje` (jeśli podana) dopisują się pobrane numery jako (licznik, rok, numer).
    Dzięki temu `generuj` potrafi je oddać, gdy wypełnianie szablonu się nie uda.
    """
    dzis = date.today()
    kontekst: dict[str, Any] = dict(ustawienia)     # dane stałe (geodeta, uprawnienia, firma)
    kontekst.update(dane)

    for pole in szablon.pola:
        if pole.typ == "auto_numer" and not kontekst.get(pole.klucz):
            nazwa_licznika = szablon.licznik or szablon.id
            numer = db.nastepny_numer(nazwa_licznika, dzis.year)
            if rezerwacje is not None:
                rezerwacje.append((nazwa_licznika, dzis.year, numer))
            wzor = pole.domyslnie or "{numer}/{rok}"
            kontekst[pole.klucz] = wzor.format(numer=numer, numer3=f"{numer:03d}", rok=dzis.year)
        elif pole.typ == "teryt":
            wybor = kontekst.get(pole.klucz)
            kontekst.update(pola_teryt(pole.klucz, wybor if isinstance(wybor, dict) else {}))
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


def dopisz_dokument(szablon: Szablon, kontekst: dict[str, Any], katalog: Path) -> Path:
    """Wypełnia dodatkowy szablon **tym samym kontekstem** i kładzie go w katalogu operatu.

    Kontekst jest gotowy, więc numer operatu, daty i położenie są identyczne jak
    w dokumencie głównym — a `auto_numer` nie sięgnie po kolejny numer z licznika,
    bo widzi, że wartość już jest.
    """
    dokument = DocxTemplate(szablon.plik)
    dokument.render(kontekst, autoescape=True)
    plik = katalog / operaty.nazwa_dokumentu(szablon.id)
    dokument.save(plik)
    return plik


def _numer_operatu(szablon: Szablon, kontekst: dict[str, Any]) -> str:
    for pole in szablon.pola:
        if pole.typ == "auto_numer" and kontekst.get(pole.klucz):
            return str(kontekst[pole.klucz])
    return ""


def generuj(szablon: Szablon, dane: dict[str, Any], ustawienia: dict[str, str],
            poprzedni: dict[str, Any] | None = None) -> tuple[Path, dict, list[str]]:
    """Zakłada katalog operatu i wkłada do niego dokument główny.

    `poprzedni` = opis operatu, który poprawiamy (z `operat.json`). Wtedy numer operatu
    bierze się stamtąd, a nie z licznika, i wszystko ląduje w tym samym katalogu —
    poprawianie dokumentu nie może zjadać kolejnych numerów.

    Zwraca (plik .docx, kontekst, ostrzeżenia do pokazania użytkownikowi).
    """
    rezerwacje: list[tuple[str, int, int]] = []
    if poprzedni and poprzedni.get("nr_operatu"):
        # Numer wpisujemy z góry — `auto_numer` po niego nie sięgnie, bo widzi wartość.
        dane = dict(dane)
        for pole in szablon.pola:
            if pole.typ == "auto_numer":
                dane.setdefault(pole.klucz, poprzedni["nr_operatu"])
    kontekst = przygotuj_kontekst(szablon, dane, ustawienia, rezerwacje)
    try:
        dokument = DocxTemplate(szablon.plik)
        dokument.render(kontekst, autoescape=True)

        # Katalog nazywa się numerem operatu; gdy szablon go nie ma, bierzemy nazwę
        # z wzorca nazwy pliku, żeby robota i tak dostała swój folder.
        numer = _numer_operatu(szablon, kontekst)
        znacznik = datetime.now().strftime("%Y%m%d-%H%M%S")
        katalog, ostrzezenia = operaty.zaloz(
            numer or f"{nazwa_pliku(szablon, kontekst)}__{znacznik}",
            str(kontekst.get("nr_roboty", "")), szablon.id, dane,
            poprzedni_numer_roboty=str((poprzedni or {}).get("nr_roboty", "")))

        plik = katalog / operaty.nazwa_dokumentu(szablon.id)
        dokument.save(plik)
    except Exception:
        # Numer musi być znany przed wypełnianiem, bo wchodzi do treści dokumentu.
        # Gdy generowanie padnie, oddajemy go — inaczej każda literówka w szablonie
        # zostawiałaby dziurę w numeracji operatów.
        for nazwa_licznika, rok, numer_licznika in rezerwacje:
            db.zwolnij_numer(nazwa_licznika, rok, numer_licznika)
        raise
    return plik, kontekst, ostrzezenia

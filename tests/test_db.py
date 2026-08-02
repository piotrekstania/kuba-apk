"""Baza: migracje schematu i ustawienia.

Baza u brata to jedyny egzemplarz historii i numeracji, a nowa wersja programu
dostaje ją w stanie, w jakim jest — musi umieć ją dociągnąć, a nie wywalić się
na brakującej kolumnie.
"""
from __future__ import annotations

import sqlite3

import pytest

from app import db


def _kolumny(nazwa_tabeli: str) -> set[str]:
    with db.polaczenie() as con:
        return {w["name"] for w in con.execute(f"PRAGMA table_info({nazwa_tabeli})")}


def test_polaczenie_zamyka_plik_bazy(srodowisko):
    """`with sqlite3.connect(...)` zatwierdza transakcję, ale **pliku nie zamyka**.

    Na Linuksie otwarty uchwyt niczego nie psuje, więc regresja przeszłaby tu i w CI
    bez śladu — a na Windowsie, czyli u brata, zablokowana baza to `PermissionError`
    przy każdej próbie ruszenia pliku (przywrócenie kopii, podmiana, sprzątanie).
    """
    with db.polaczenie() as con:
        con.execute("SELECT 1")

    with pytest.raises(sqlite3.ProgrammingError):
        con.execute("SELECT 1")


def test_swieza_baza_jest_w_najnowszym_schemacie(srodowisko):
    with db.polaczenie() as con:                 # `polacz()` zostawiłby otwarty plik
        assert int(con.execute("PRAGMA user_version").fetchone()[0]) == db.WERSJA_SCHEMATU
    assert {"katalog", "nr_operatu"} <= _kolumny("dokumenty")


def test_stara_baza_dociaga_sie_bez_utraty_danych(srodowisko):
    """Baza w schemacie 1 (bez `katalog` i `nr_operatu`) ma przeżyć aktualizację."""
    srodowisko.baza_danych.unlink()
    con = sqlite3.connect(srodowisko.baza_danych)
    with con:                    # zatwierdza, ale pliku nie zamyka — `close()` niżej
        con.executescript("""
            CREATE TABLE dokumenty (
                id INTEGER PRIMARY KEY AUTOINCREMENT, szablon TEXT NOT NULL,
                tytul TEXT NOT NULL, plik_docx TEXT NOT NULL, plik_pdf TEXT,
                dane_json TEXT NOT NULL, utworzono TEXT NOT NULL);
            CREATE TABLE liczniki (nazwa TEXT NOT NULL, rok INTEGER NOT NULL,
                stan INTEGER NOT NULL DEFAULT 0, PRIMARY KEY (nazwa, rok));
            INSERT INTO dokumenty (szablon, tytul, plik_docx, dane_json, utworzono)
                VALUES ('stary_wzor', 'Operat z 2025', 'operat.docx', '{}', '2025-05-01T10:00:00');
            INSERT INTO liczniki (nazwa, rok, stan) VALUES ('operat', 2025, 17);
            PRAGMA user_version = 1;
        """)
    con.close()

    db.init()

    assert {"katalog", "nr_operatu"} <= _kolumny("dokumenty")
    with db.polaczenie() as con:                 # `polacz()` zostawiłby otwarty plik
        assert int(con.execute("PRAGMA user_version").fetchone()[0]) == db.WERSJA_SCHEMATU
    wiersze = db.dokumenty()
    assert len(wiersze) == 1
    assert wiersze[0]["tytul"] == "Operat z 2025"
    assert db.podglad_numeru("operat", 2025) == 18          # licznik nietknięty


def _kopie(srodowisko) -> list:
    return sorted((srodowisko.dane / "kopie").glob("*.sqlite3"))


def _zaloz_baze_w_schemacie_1(srodowisko) -> None:
    """Baza w stanie sprzed migracji — z danymi, po których poznamy kopię."""
    srodowisko.baza_danych.unlink()
    con = sqlite3.connect(srodowisko.baza_danych)
    with con:                    # zatwierdza, ale pliku nie zamyka — `close()` niżej
        con.executescript("CREATE TABLE liczniki (nazwa TEXT, rok INTEGER, stan INTEGER);"
                          "INSERT INTO liczniki VALUES ('operat', 2025, 17);"
                          "PRAGMA user_version = 1;")
    con.close()


def test_swieza_baza_nie_zostawia_kopii(srodowisko):
    """Baza założona przed sekundą nie ma czego ratować — kopia byłaby kopią pustki.

    To nie jest kosmetyka. Dopóki `init()` robił kopię także świeżej bazy, każdy test
    zaczynał z jednym plikiem w `dane/kopie/`, a nazwa kopii ma rozdzielczość jednej
    sekundy — więc kopia z migracji zwykle nadpisywała tamtą i wychodziło „jedna”.
    Gdy tylko obie trafiły w różne sekundy, `test_migracja_zostawia_kopie_bazy` padał
    na dwie kopie. Wychodziło mniej więcej raz na kilkanaście przebiegów.
    """
    assert _kopie(srodowisko) == [], "kopia bazy przy zakładaniu jej od zera"


def test_migracja_zostawia_kopie_bazy(srodowisko):
    _zaloz_baze_w_schemacie_1(srodowisko)

    db.init()

    kopie = _kopie(srodowisko)
    assert len(kopie) == 1, "przed migracją nie powstała kopia bazy"
    # ...i to kopia sprzed migracji, a nie zdublowany plik po niej
    assert "schemat1" in kopie[0].name
    kopia = sqlite3.connect(kopie[0])
    try:
        assert int(kopia.execute("PRAGMA user_version").fetchone()[0]) == 1
        assert kopia.execute(
            "SELECT stan FROM liczniki WHERE nazwa = 'operat'").fetchone()[0] == 17
    finally:
        kopia.close()


def test_powtorne_init_nic_nie_psuje(srodowisko):
    """Start programu na aktualnej bazie ma być bezczynny — bez migracji i bez kopii."""
    kopie = lambda: len(list((srodowisko.dane / "kopie").glob("*.sqlite3")))  # noqa: E731
    db.zapisz_dokument("wzor", "Operat", "operat.docx", {"a": 1}, "001.2026", "001/2026")
    przed = kopie()
    db.init()
    db.init()
    assert len(db.dokumenty()) == 1
    assert kopie() == przed, "kopia bazy robi się przy każdym starcie, a nie przy migracji"


def test_zapis_i_odczyt_dokumentu(srodowisko):
    identyfikator = db.zapisz_dokument("wzor", "Operat", "001.2026/spis_tresci.docx",
                                       {"nr_roboty": "GK.1"}, "001.2026", "001/2026")
    wiersz = db.dokument(identyfikator)
    assert wiersz["katalog"] == "001.2026"
    assert wiersz["nr_operatu"] == "001/2026"

    db.zaktualizuj_dokument(identyfikator, "Operat poprawiony", {"nr_roboty": "GK.2"},
                            "001.2026/spis_tresci.docx", "001.2026")
    wiersz = db.dokument(identyfikator)
    assert wiersz["tytul"] == "Operat poprawiony"
    assert wiersz["nr_operatu"] == "001/2026"          # numer się nie zmienia przy poprawce
    assert len(db.dokumenty()) == 1                    # i nie powstaje drugi wpis


def test_ustawienia_zapominaja_skasowane_klucze(srodowisko):
    db.zastap_ustawienia({"a": "1", "b": "2"})
    db.zastap_ustawienia({"a": "3"})
    assert db.wczytaj_ustawienia() == {"a": "3"}

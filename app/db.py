"""Warstwa danych: SQLite bez ORM-a, bo tabele są trzy i takie zostaną."""
import json
import sqlite3
from datetime import datetime
from typing import Any

from .config import BAZA_DANYCH

SCHEMAT = """
CREATE TABLE IF NOT EXISTS dokumenty (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    szablon      TEXT NOT NULL,
    tytul        TEXT NOT NULL,
    plik_docx    TEXT NOT NULL,
    plik_pdf     TEXT,
    dane_json    TEXT NOT NULL,
    utworzono    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ustawienia (
    klucz    TEXT PRIMARY KEY,
    wartosc  TEXT NOT NULL
);

-- liczniki numeracji, np. ("operat", 2026) -> 17
CREATE TABLE IF NOT EXISTS liczniki (
    nazwa  TEXT NOT NULL,
    rok    INTEGER NOT NULL,
    stan   INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (nazwa, rok)
);
"""


def polacz() -> sqlite3.Connection:
    con = sqlite3.connect(BAZA_DANYCH)
    con.row_factory = sqlite3.Row
    return con


def init() -> None:
    with polacz() as con:
        con.executescript(SCHEMAT)


# --- dokumenty ---------------------------------------------------------------

def zapisz_dokument(szablon: str, tytul: str, plik_docx: str, dane: dict[str, Any]) -> int:
    with polacz() as con:
        kursor = con.execute(
            "INSERT INTO dokumenty (szablon, tytul, plik_docx, dane_json, utworzono)"
            " VALUES (?, ?, ?, ?, ?)",
            (szablon, tytul, plik_docx, json.dumps(dane, ensure_ascii=False),
             datetime.now().isoformat(timespec="seconds")),
        )
        return int(kursor.lastrowid)


def ustaw_pdf(dokument_id: int, plik_pdf: str) -> None:
    with polacz() as con:
        con.execute("UPDATE dokumenty SET plik_pdf = ? WHERE id = ?", (plik_pdf, dokument_id))


def dokument(dokument_id: int) -> sqlite3.Row | None:
    with polacz() as con:
        return con.execute("SELECT * FROM dokumenty WHERE id = ?", (dokument_id,)).fetchone()


def dokumenty(limit: int = 100) -> list[sqlite3.Row]:
    with polacz() as con:
        return con.execute(
            "SELECT * FROM dokumenty ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()


def usun_dokument(dokument_id: int) -> None:
    with polacz() as con:
        con.execute("DELETE FROM dokumenty WHERE id = ?", (dokument_id,))


# --- ustawienia (dane stałe geodety, podstawiane do każdego dokumentu) -------

def wczytaj_ustawienia() -> dict[str, str]:
    with polacz() as con:
        return {w["klucz"]: w["wartosc"] for w in con.execute("SELECT * FROM ustawienia")}


def zastap_ustawienia(wartosci: dict[str, str]) -> None:
    """Formularz przysyła komplet pól, więc usunięte wiersze mają zniknąć z bazy."""
    with polacz() as con:
        con.execute("DELETE FROM ustawienia")
        con.executemany("INSERT INTO ustawienia (klucz, wartosc) VALUES (?, ?)",
                        list(wartosci.items()))


def zapisz_ustawienia(wartosci: dict[str, str]) -> None:
    with polacz() as con:
        con.executemany(
            "INSERT INTO ustawienia (klucz, wartosc) VALUES (?, ?)"
            " ON CONFLICT(klucz) DO UPDATE SET wartosc = excluded.wartosc",
            list(wartosci.items()),
        )


# --- numeracja ---------------------------------------------------------------

def nastepny_numer(nazwa: str, rok: int) -> int:
    """Zwiększa i zwraca licznik. Transakcja, więc bezpieczne przy kilku kartach."""
    with polacz() as con:
        con.execute(
            "INSERT INTO liczniki (nazwa, rok, stan) VALUES (?, ?, 1)"
            " ON CONFLICT(nazwa, rok) DO UPDATE SET stan = stan + 1",
            (nazwa, rok),
        )
        return int(con.execute(
            "SELECT stan FROM liczniki WHERE nazwa = ? AND rok = ?", (nazwa, rok)
        ).fetchone()["stan"])


def podglad_numeru(nazwa: str, rok: int) -> int:
    """Jaki numer zostanie nadany następnym razem (bez zużywania go)."""
    with polacz() as con:
        wiersz = con.execute(
            "SELECT stan FROM liczniki WHERE nazwa = ? AND rok = ?", (nazwa, rok)
        ).fetchone()
        return (wiersz["stan"] if wiersz else 0) + 1

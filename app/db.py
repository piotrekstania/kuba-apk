"""Warstwa danych: SQLite bez ORM-a, bo tabele są trzy i takie zostaną."""
import json
import shutil
import sqlite3
from datetime import datetime
from typing import Any

from .config import BAZA_DANYCH, DANE

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

-- TERYT: województwa, powiaty i jednostki ewidencyjne (gminy) z pliku GUS-u.
-- `rodzic` wiąże poziomy: '1201' -> '12', '120102_2' -> '1201'.
CREATE TABLE IF NOT EXISTS teryt_jednostki (
    id      TEXT PRIMARY KEY,
    poziom  TEXT NOT NULL,             -- wojewodztwo | powiat | gmina
    rodzic  TEXT,
    nazwa   TEXT NOT NULL,
    rodzaj  TEXT
);
CREATE INDEX IF NOT EXISTS teryt_jednostki_rodzic ON teryt_jednostki (poziom, rodzic);

-- Obręby ewidencyjne z ULDK, dociągane dla gminy przy pierwszym jej wybraniu.
CREATE TABLE IF NOT EXISTS teryt_obreby (
    id     TEXT PRIMARY KEY,           -- np. '120102_2.0001'
    gmina  TEXT NOT NULL,
    nazwa  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS teryt_obreby_gmina ON teryt_obreby (gmina);

-- kiedy pobrano listę jednostek i na jaki dzień jest aktualna
CREATE TABLE IF NOT EXISTS teryt_stan (
    klucz    TEXT PRIMARY KEY,
    wartosc  TEXT NOT NULL
);
"""


# Numer schematu trzymamy w `PRAGMA user_version` samej bazy. Dzięki temu nowa wersja
# programu potrafi doprowadzić starą bazę do porządku, zamiast wywalić się na brakującej
# kolumnie — a baza u brata jest jedynym miejscem, gdzie siedzi historia i numeracja.
WERSJA_SCHEMATU = 1

# Kolejne kroki dopisujemy tutaj: {2: ["ALTER TABLE dokumenty ADD COLUMN status TEXT"]}
# i podnosimy WERSJA_SCHEMATU. Kroki muszą być odporne na powtórzenie i nie mogą
# kasować danych.
MIGRACJE: dict[int, list[str]] = {}


def polacz() -> sqlite3.Connection:
    con = sqlite3.connect(BAZA_DANYCH)
    con.row_factory = sqlite3.Row
    return con


def _kopia_przed_migracja(wersja: int) -> None:
    if not BAZA_DANYCH.exists():
        return
    katalog = DANE / "kopie"
    katalog.mkdir(parents=True, exist_ok=True)
    shutil.copy2(BAZA_DANYCH,
                 katalog / f"operaty-schemat{wersja}-{datetime.now():%Y%m%d-%H%M%S}.sqlite3")


def init() -> None:
    with polacz() as con:
        con.executescript(SCHEMAT)
        wersja = int(con.execute("PRAGMA user_version").fetchone()[0])
        if wersja == 0:
            # Bazy sprzed wprowadzenia numeracji mają komplet tabel wersji 1 —
            # `SCHEMAT` wyżej właśnie się o to zatroszczył.
            wersja = 1
            con.execute(f"PRAGMA user_version = {wersja}")

    if wersja >= WERSJA_SCHEMATU:
        return

    _kopia_przed_migracja(wersja)
    with polacz() as con:
        for nastepna in range(wersja + 1, WERSJA_SCHEMATU + 1):
            for polecenie in MIGRACJE.get(nastepna, []):
                con.execute(polecenie)
            con.execute(f"PRAGMA user_version = {nastepna}")   # int, nie da się tu podstawić ?


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


def zwolnij_numer(nazwa: str, rok: int, stan: int) -> bool:
    """Cofa licznik po nieudanym generowaniu. True = numer wrócił do puli.

    Warunek `stan = ?` jest tu istotny: jeśli w międzyczasie powstał kolejny dokument,
    licznik stoi już gdzie indziej i cofanie go zdublowałoby numer. Wtedy wolimy dziurę
    w numeracji niż dwa operaty o tym samym numerze.
    """
    with polacz() as con:
        kursor = con.execute(
            "UPDATE liczniki SET stan = stan - 1 WHERE nazwa = ? AND rok = ? AND stan = ?",
            (nazwa, rok, stan),
        )
        return kursor.rowcount > 0


def podglad_numeru(nazwa: str, rok: int) -> int:
    """Jaki numer zostanie nadany następnym razem (bez zużywania go)."""
    with polacz() as con:
        wiersz = con.execute(
            "SELECT stan FROM liczniki WHERE nazwa = ? AND rok = ?", (nazwa, rok)
        ).fetchone()
        return (wiersz["stan"] if wiersz else 0) + 1

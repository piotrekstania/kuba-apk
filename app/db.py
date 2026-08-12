"""Warstwa danych: SQLite bez ORM-a, bo tabele są trzy i takie zostaną."""
import json
import shutil
import sqlite3
from contextlib import contextmanager
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

-- Gotowe opisy do sprawozdania: `nazwa` służy do rozpoznania na liście, `opis` to treść.
-- Osobna tabela, a nie klucz w `ustawienia`, bo tego jest wiele i dochodzi po jednym.
-- Nowa tabela nie wymaga migracji: `init()` puszcza cały SCHEMAT przy każdym starcie,
-- a `IF NOT EXISTS` dokłada ją też do bazy, która powstała wcześniej.
CREATE TABLE IF NOT EXISTS opisy_sprawozdania (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    nazwa  TEXT NOT NULL,
    opis   TEXT NOT NULL
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

-- Liczniki pracy programu: ile operatów założono, ile dokumentów wypełniono,
-- ile PDF-ów złożono danego dnia. Liczymy **w chwili zdarzenia**, bo katalogi
-- z gotowymi operatami brat przenosi na dysk archiwalny — liczenie plików
-- na dysku cofałoby licznik po każdej archiwizacji (patrz app/statystyki.py).
CREATE TABLE IF NOT EXISTS zdarzenia (
    dzien   TEXT NOT NULL,               -- '2026-08-02'
    rodzaj  TEXT NOT NULL,               -- operat | dokument | pdf
    ile     INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (dzien, rodzaj)
);
"""


# Numer schematu trzymamy w `PRAGMA user_version` samej bazy. Dzięki temu nowa wersja
# programu potrafi doprowadzić starą bazę do porządku, zamiast wywalić się na brakującej
# kolumnie — a baza u brata jest jedynym miejscem, gdzie siedzi historia i numeracja.
WERSJA_SCHEMATU = 4

# Kolejne kroki dopisujemy tutaj: {2: ["ALTER TABLE dokumenty ADD COLUMN status TEXT"]}
# i podnosimy WERSJA_SCHEMATU. Kroki muszą być odporne na powtórzenie i nie mogą
# kasować danych.
MIGRACJE: dict[int, list[str]] = {
    # 2: każdy operat dostał własny katalog w wyniki/. `plik_docx` trzyma teraz ścieżkę
    # względem wyniki/ (np. "001-2026/spis_tresci.docx"), a `katalog` samą nazwę folderu.
    # Stare wiersze zostają z pustym `katalog` — pliki leżą tam, gdzie leżały.
    2: ["ALTER TABLE dokumenty ADD COLUMN katalog TEXT"],
    # 3: numer operatu na liście dokumentów. Wyliczanie go z nazwy katalogu działa tylko
    # dla wzorca 001-2026, a wzorzec numeru siedzi w .json szablonu i może być inny.
    3: ["ALTER TABLE dokumenty ADD COLUMN nr_operatu TEXT"],
    # 4: notatka użytkownika do operatu (w interfejsie „Opis”). Nazwa kolumny jest inna
    # niż etykieta, bo `operaty.opis()` znaczy w tym programie co innego — zawartość
    # `operat.json`, czyli akurat tego pliku, w którym notatka też siedzi.
    4: ["ALTER TABLE dokumenty ADD COLUMN notatka TEXT"],
}


def polacz() -> sqlite3.Connection:
    con = sqlite3.connect(BAZA_DANYCH)
    con.row_factory = sqlite3.Row
    return con


@contextmanager
def polaczenie():
    """Połączenie z bazą, **zamykane** po wyjściu z bloku.

    `with sqlite3.connect(...)` zatwierdza transakcję, ale pliku nie zamyka. Na Linuksie
    nie widać tego wcale — otwarty uchwyt nie przeszkadza skasować ani podmienić pliku.
    Na Windowsie (czyli u brata) zablokowana baza to `PermissionError` przy każdej próbie
    ruszenia pliku: przywróceniu kopii zapasowej, podmianie bazy, sprzątaniu katalogu.
    """
    con = polacz()
    try:
        with con:                     # commit przy wyjściu, rollback przy wyjątku
            yield con
    finally:
        con.close()


ILE_KOPII_BAZY = 5      # tyle ostatnich kopii sprzed migracji zostaje w dane/kopie/


def sprzataj_kopie_bazy() -> None:
    """Zostawia `ILE_KOPII_BAZY` ostatnich kopii sprzed migracji, starsze kasuje.

    Wołane przy każdym starcie programu, nie tylko przy migracji — inaczej u kogoś,
    kto migracji już nie ma przed sobą, stare pliki leżałyby w nieskończoność.
    Ratunkowa jest ta ostatnia: gdyby migracja coś zepsuła, widać to przy pierwszym
    uruchomieniu, a nie po pięciu kolejnych. Nazwa ma na końcu znacznik czasu,
    a numer schematu tylko rośnie, więc sortowanie po nazwie jest chronologiczne.
    """
    katalog = DANE / "kopie"
    try:
        stare = sorted(katalog.glob("operaty-schemat*.sqlite3"))[:-ILE_KOPII_BAZY]
    except OSError:
        return
    for kopia in stare:
        kopia.unlink(missing_ok=True)


def _kopia_przed_migracja(wersja: int) -> None:
    if not BAZA_DANYCH.exists():
        return
    katalog = DANE / "kopie"
    katalog.mkdir(parents=True, exist_ok=True)
    shutil.copy2(BAZA_DANYCH,
                 katalog / f"operaty-schemat{wersja}-{datetime.now():%Y%m%d-%H%M%S}.sqlite3")
    sprzataj_kopie_bazy()


def init() -> None:
    with polaczenie() as con:
        # Czy to my zakładamy tę bazę w tej chwili? Sprawdzamy **przed** `SCHEMAT`,
        # bo po nim tabele są już zawsze.
        swieza = not int(con.execute(
            "SELECT COUNT(*) AS ile FROM sqlite_master WHERE type = 'table'").fetchone()["ile"])
        con.executescript(SCHEMAT)
        wersja = int(con.execute("PRAGMA user_version").fetchone()[0])
        if wersja == 0:
            # Bazy sprzed wprowadzenia numeracji mają komplet tabel wersji 1 —
            # `SCHEMAT` wyżej właśnie się o to zatroszczył.
            wersja = 1
            con.execute(f"PRAGMA user_version = {wersja}")

    if wersja >= WERSJA_SCHEMATU:
        return

    # `SCHEMAT` opisuje schemat 1 — kolumny `katalog` i `nr_operatu` dokładają dopiero
    # migracje. Przez ten sam kod przechodzi więc i baza brata sprzed roku, i baza
    # założona przed sekundą. Kopię robimy tylko tej pierwszej: w bazie, która powstała
    # w tym samym wywołaniu, nie ma czego ratować, a plik w `dane/kopie/` po każdej
    # świeżej instalacji tylko myli — jego to co najwyżej zdziwi, ale testom podkładał
    # nogę na serio (patrz `test_migracja_zostawia_kopie_bazy`).
    if not swieza:
        _kopia_przed_migracja(wersja)
    with polaczenie() as con:
        for nastepna in range(wersja + 1, WERSJA_SCHEMATU + 1):
            for polecenie in MIGRACJE.get(nastepna, []):
                con.execute(polecenie)
            con.execute(f"PRAGMA user_version = {nastepna}")   # int, nie da się tu podstawić ?


# --- dokumenty ---------------------------------------------------------------

def zapisz_dokument(szablon: str, tytul: str, plik_docx: str, dane: dict[str, Any],
                    katalog: str = "", nr_operatu: str = "", notatka: str = "") -> int:
    with polaczenie() as con:
        kursor = con.execute(
            "INSERT INTO dokumenty (szablon, tytul, plik_docx, dane_json, utworzono,"
            " katalog, nr_operatu, notatka) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (szablon, tytul, plik_docx, json.dumps(dane, ensure_ascii=False),
             datetime.now().isoformat(timespec="seconds"), katalog, nr_operatu, notatka),
        )
        return int(kursor.lastrowid)


def zaktualizuj_dokument(dokument_id: int, tytul: str, dane: dict[str, Any],
                         plik_docx: str, katalog: str, notatka: str) -> None:
    """Poprawiony operat zostaje tym samym wpisem — nie zakładamy nowego.

    `notatka` celowo bez wartości domyślnej: UPDATE nadpisuje istniejący wpis, więc
    wywołanie bez niej kasowałoby notatkę brata po cichu. Przy INSERT (`zapisz_dokument`)
    domyślne puste nic nie niszczy, tu by niszczyło.

    Ścieżki też odświeżamy: gdy ktoś skasuje katalog operatu z Eksploratora, poprawianie
    zakłada go od nowa i wpis musi wskazywać to, co naprawdę leży na dysku.
    """
    with polaczenie() as con:
        con.execute(
            "UPDATE dokumenty SET tytul = ?, dane_json = ?, plik_docx = ?, katalog = ?,"
            " notatka = ? WHERE id = ?",
            (tytul, json.dumps(dane, ensure_ascii=False), plik_docx, katalog, notatka,
             dokument_id))


def ustaw_pdf(dokument_id: int, plik_pdf: str) -> None:
    with polaczenie() as con:
        con.execute("UPDATE dokumenty SET plik_pdf = ? WHERE id = ?", (plik_pdf, dokument_id))


def dokument(dokument_id: int) -> sqlite3.Row | None:
    with polaczenie() as con:
        return con.execute("SELECT * FROM dokumenty WHERE id = ?", (dokument_id,)).fetchone()


def dokumenty(limit: int = 100) -> list[sqlite3.Row]:
    with polaczenie() as con:
        return con.execute(
            "SELECT * FROM dokumenty ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()


def usun_dokument(dokument_id: int) -> None:
    with polaczenie() as con:
        con.execute("DELETE FROM dokumenty WHERE id = ?", (dokument_id,))


# --- opisy sprawozdania ------------------------------------------------------
#
# Biblioteka gotowych opisów: brat pisze je raz, żeby nie przepisywać tego samego przy
# każdej robocie. Trzymamy je w bazie, a nie w plikach — baza leży w `dane/`, więc
# przeżywa aktualizację programu i wchodzi do kopii zapasowej.


def opisy_sprawozdania() -> list[sqlite3.Row]:
    """Wszystkie opisy, po nazwie — lista rośnie, a szuka się po nazwie, nie po dacie."""
    with polaczenie() as con:
        return con.execute(
            "SELECT id, nazwa, opis FROM opisy_sprawozdania ORDER BY nazwa COLLATE NOCASE"
        ).fetchall()


def dodaj_opis_sprawozdania(nazwa: str, opis: str) -> int:
    with polaczenie() as con:
        kursor = con.execute(
            "INSERT INTO opisy_sprawozdania (nazwa, opis) VALUES (?, ?)",
            (nazwa.strip(), opis.strip()))
        return int(kursor.lastrowid)


def usun_opis_sprawozdania(opis_id: int) -> None:
    with polaczenie() as con:
        con.execute("DELETE FROM opisy_sprawozdania WHERE id = ?", (opis_id,))


# --- ustawienia (dane stałe geodety, podstawiane do każdego dokumentu) -------

def wczytaj_ustawienia() -> dict[str, str]:
    with polaczenie() as con:
        return {w["klucz"]: w["wartosc"] for w in con.execute("SELECT * FROM ustawienia")}


def zastap_ustawienia(wartosci: dict[str, str]) -> None:
    """Formularz przysyła komplet pól, więc usunięte wiersze mają zniknąć z bazy."""
    with polaczenie() as con:
        con.execute("DELETE FROM ustawienia")
        con.executemany("INSERT INTO ustawienia (klucz, wartosc) VALUES (?, ?)",
                        list(wartosci.items()))


def zapisz_ustawienia(wartosci: dict[str, str]) -> None:
    with polaczenie() as con:
        con.executemany(
            "INSERT INTO ustawienia (klucz, wartosc) VALUES (?, ?)"
            " ON CONFLICT(klucz) DO UPDATE SET wartosc = excluded.wartosc",
            list(wartosci.items()),
        )


# --- numeracja ---------------------------------------------------------------

def nastepny_numer(nazwa: str, rok: int) -> int:
    """Zwiększa i zwraca licznik. Transakcja, więc bezpieczne przy kilku kartach."""
    with polaczenie() as con:
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
    with polaczenie() as con:
        kursor = con.execute(
            "UPDATE liczniki SET stan = stan - 1 WHERE nazwa = ? AND rok = ? AND stan = ?",
            (nazwa, rok, stan),
        )
        return kursor.rowcount > 0


def podglad_numeru(nazwa: str, rok: int) -> int:
    """Jaki numer zostanie nadany następnym razem (bez zużywania go)."""
    with polaczenie() as con:
        wiersz = con.execute(
            "SELECT stan FROM liczniki WHERE nazwa = ? AND rok = ?", (nazwa, rok)
        ).fetchone()
        return (wiersz["stan"] if wiersz else 0) + 1

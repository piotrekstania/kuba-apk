"""Liczniki pracy programu — ile operatów, dokumentów i złożonych PDF-ów.

Liczymy **w chwili zdarzenia**, a nie plikami na dysku, z dwóch powodów, które wyszły
dopiero z tego, jak brat naprawdę pracuje:

* gotowe operaty przenosi na dysk archiwalny — liczenie katalogów cofałoby licznik
  po każdej archiwizacji, aż w końcu pokazywałby zero mimo setki zrobionych robót;
* do katalogu operatu dokłada swoje pliki (mapy, skany, dokumenty od zamawiającego).
  Policzone z dysku wpadłyby jako „wygenerowane przez program”, choć program ich
  nigdy nie widział.

W tabeli siedzą **wyłącznie liczby**: dzień, rodzaj, ile. Ani numeru operatu, ani działki,
ani nazwiska, ani godziny — po tych danych nie da się odtworzyć żadnej roboty.
"""
from __future__ import annotations

from datetime import date

from .db import polaczenie

OPERAT = "operat"
DOKUMENT = "dokument"
PDF = "pdf"


def zlicz(rodzaj: str, ile: int = 1) -> None:
    """Dokłada zdarzenia do dzisiejszego dnia.

    Nigdy nie przerywa pracy programu — statystyka nie jest powodem, żeby brat
    nie dostał swojego operatu. `ile = ile + excluded.ile` jest niepodzielne,
    więc dwie karty przeglądarki naraz nie zgubią sobie zliczeń.
    """
    if ile <= 0:
        return
    try:
        with polaczenie() as con:
            con.execute(
                "INSERT INTO zdarzenia (dzien, rodzaj, ile) VALUES (?, ?, ?)"
                " ON CONFLICT(dzien, rodzaj) DO UPDATE SET ile = ile + excluded.ile",
                (date.today().isoformat(), rodzaj, ile),
            )
    except Exception:
        pass


def podsumowanie() -> dict[str, int]:
    """Liczby do stopki. Przy pustej bazie oddaje zera, a nie wyjątek."""
    puste = {OPERAT: 0, DOKUMENT: 0, PDF: 0}
    try:
        with polaczenie() as con:
            wiersze = con.execute(
                "SELECT rodzaj, SUM(ile) AS razem FROM zdarzenia GROUP BY rodzaj").fetchall()
    except Exception:
        return puste
    return {**puste, **{w["rodzaj"]: int(w["razem"]) for w in wiersze}}


def zasiej_z_historii() -> bool:
    """Jednorazowo odtwarza liczniki z tego, co program już u siebie ma.

    Bez tego brat po aktualizacji zobaczyłby „0 operatów”, mając ich pięćdziesiąt —
    licznik wyglądałby na zepsuty i przestałby cokolwiek znaczyć.

    Skąd bierzemy przeszłość:
    * **operaty** — z tabeli `dokumenty`, która pamięta każdy wygenerowany operat wraz
      z datą, także te, których katalogi są już na dysku archiwalnym;
    * **dokumenty i PDF-y** — z katalogów, które jeszcze leżą w `wyniki/`, i tylko te
      pliki, których nazwy program sam nadaje (`spis_tresci.docx`, `sprawozdanie…`).
      Dzięki temu pliki dołożone przez brata nie wpadają do licznika nawet ten jeden raz.

    Liczby sprzed tej wersji są więc dokładne dla operatów i zaniżone dla dokumentów
    z operatów już zarchiwizowanych. To świadomy kompromis: lepiej zacząć od prawdziwej
    historii niż od zera, a wymyślać brakujących liczb nie będziemy.
    """
    from . import operaty, szablony

    with polaczenie() as con:
        if con.execute("SELECT COUNT(*) AS n FROM zdarzenia").fetchone()["n"]:
            return False                       # już zasiane albo już coś naliczone

    naliczone: dict[tuple[str, str], int] = {}

    with polaczenie() as con:
        for wiersz in con.execute(
                "SELECT substr(utworzono, 1, 10) AS dzien, COUNT(*) AS ile"
                " FROM dokumenty GROUP BY dzien"):
            if wiersz["dzien"]:
                naliczone[(wiersz["dzien"], OPERAT)] = int(wiersz["ile"])

    nasze_nazwy = {operaty.nazwa_dokumentu(szablon.id)
                   for szablon in szablony.lista_szablonow()}
    for katalog in operaty.WYNIKI.iterdir() if operaty.WYNIKI.is_dir() else []:
        if not katalog.is_dir() or not (katalog / operaty.PLIK_OPISU).exists():
            continue
        dzien = (operaty.opis(katalog).get("utworzono") or "")[:10]
        if not dzien:
            continue
        dokumentow = sum(1 for plik in katalog.iterdir()
                         if plik.is_file() and plik.name in nasze_nazwy)
        if dokumentow:
            naliczone[(dzien, DOKUMENT)] = naliczone.get((dzien, DOKUMENT), 0) + dokumentow
        if (katalog / operaty.nazwa_wyniku(katalog)).exists():
            naliczone[(dzien, PDF)] = naliczone.get((dzien, PDF), 0) + 1

    if not naliczone:
        return False
    with polaczenie() as con:
        con.executemany(
            "INSERT INTO zdarzenia (dzien, rodzaj, ile) VALUES (?, ?, ?)"
            " ON CONFLICT(dzien, rodzaj) DO UPDATE SET ile = ile + excluded.ile",
            [(dzien, rodzaj, ile) for (dzien, rodzaj), ile in naliczone.items()])
    return True

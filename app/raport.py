"""Wysyłka trzech liczb do arkusza autora — żeby wiedział, czy program żyje.

Co wychodzi z komputera brata: identyfikator instalacji, etykieta, numer wersji
i **trzy sumy** (operaty, dokumenty, złożone PDF-y). Nic więcej. Ani numeru operatu,
ani działki, ani nazwiska, ani nazwy pliku, ani ścieżki — po tym, co wysyłamy, nie da
się powiedzieć nic o żadnej robocie. Brat wie, że to się dzieje; jest o tym w pomocy.

Dwie decyzje, które zdejmują większość problemów:

* **wysyłamy sumy od początku, nie przyrosty.** Zgubiony pakiet niczego nie kosztuje,
  bo następny niesie pełną prawdę — nie ma po co budować kolejki, ponawiania ani
  potwierdzeń. Przy przyrostach każde nieudane wysłanie gubiłoby dane bezpowrotnie;
* **raz na uruchomienie**, w tle, z krótkim czasem oczekiwania. Statystyka nie ma prawa
  opóźnić startu programu ani go wywalić, więc każdy wyjątek jest tu połykany.

Stoi na samej bibliotece standardowej — tak jak `teryt.py` i `aktualizacja.py`.
"""
from __future__ import annotations

import os
import urllib.parse
import urllib.request
import uuid

from .config import BAZA, DANE

# Arkusz Google + Apps Script. Adres i token są jawne (repozytorium jest publiczne)
# i takie mają być: token jest sitem na przypadkowe boty, a nie zabezpieczeniem.
# Chroni to, że sam arkusz pozostaje prywatny.
ADRES = ("https://script.google.com/macros/s/"
         "AKfycbzL41wc7jxpQ0WzNWeMFN7bawFcpD9D5R0tooUOaO_sCLFR5C1PS0MZ71FIKaLMZpDC/exec")
TOKEN = "qrrXNpkcVUehb6X3ja6PJQHHaaHMtw"
LIMIT_CZASU = 8

PLIK_ID = DANE / "instalacja.txt"        # losowy identyfikator, nadawany raz
PLIK_ETYKIETY = DANE / "etykieta.txt"    # opcjonalny opis instalacji, wpisywany ręcznie

WYLACZNIK = "GENERATOR_BEZ_STATYSTYK"    # =1 wyłącza wysyłkę bez wydawania nowej wersji


def identyfikator() -> str:
    """Losowy identyfikator tej instalacji, nadawany raz i zapamiętany w `dane/`.

    `dane/` przeżywa aktualizacje, więc identyfikator jest stały. Nie ma w nim niczego
    o komputerze ani o użytkowniku — to zwykły losowy ciąg, żeby dało się odróżnić
    instalację brata od instalacji testowych.
    """
    try:
        zapisany = PLIK_ID.read_text(encoding="utf-8").strip()
        if zapisany:
            return zapisany
    except OSError:
        pass
    nowy = uuid.uuid4().hex[:12]
    try:
        PLIK_ID.parent.mkdir(parents=True, exist_ok=True)
        PLIK_ID.write_text(nowy, encoding="utf-8")
    except OSError:
        pass                              # bez zapisu identyfikator będzie inny za każdym
    return nowy                           # razem; szkoda, ale to nie powód do awarii


def etykieta() -> str:
    """Opis instalacji: z pliku, a gdy go nie ma — rozpoznany automatycznie.

    Kopię roboczą gita poznajemy po katalogu `.git` obok programu. Dzięki temu maszyna
    deweloperska oznacza się sama i nie trzeba pamiętać o wpisywaniu etykiet tam, gdzie
    i tak wszystko się zmienia.
    """
    try:
        wpisana = PLIK_ETYKIETY.read_text(encoding="utf-8").strip()
        if wpisana:
            return wpisana[:60]
    except OSError:
        pass
    return "kopia-robocza" if (BAZA / ".git").exists() else ""


def wyslij(wersja: str, podsumowanie: dict[str, int]) -> bool:
    """Jedno żądanie z sumami. True = wysłane; wszystko inne kończy się cicho."""
    if os.environ.get(WYLACZNIK) == "1":
        return False
    dane = {
        "token": TOKEN,
        "id": identyfikator(),
        "etykieta": etykieta(),
        "wersja": wersja,
        "operaty": podsumowanie.get("operat", 0),
        "dokumenty": podsumowanie.get("dokument", 0),
        "pdfy": podsumowanie.get("pdf", 0),
    }
    try:
        with urllib.request.urlopen(ADRES + "?" + urllib.parse.urlencode(dane),
                                    timeout=LIMIT_CZASU) as odpowiedz:
            odpowiedz.read(200)
        return True
    except Exception:
        return False                      # brak sieci, arkusz nie odpowiada — trudno

"""Wysyłka trzech liczb do arkusza autora — żeby wiedział, czy program żyje.

Co wychodzi z komputera brata: identyfikator instalacji, etykieta (domyślnie **nazwa
komputera**), numer wersji i **trzy sumy** (operaty, dokumenty, złożone PDF-y). Nic
więcej. Ani numeru operatu, ani działki, ani nazwiska klienta, ani nazwy pliku, ani
ścieżki — po tym, co wysyłamy, nie da się powiedzieć nic o żadnej robocie.

Nazwa komputera bywa imieniem właściciela (`Kuba-PC`), więc jest daną osobową — brat
musi o niej wiedzieć, a nie się domyślić. Jest o tym w pomocy i w opisie wydania.

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
import platform
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

    Kolejność jest celowa:

    1. `dane/etykieta.txt`, jeśli ktoś wpisał coś ręcznie — zawsze wygrywa,
    2. **nazwa komputera** (`Kuba-PC`), bo bez niej wszystkie nieopisane instalacje
       wyglądają w arkuszu tak samo i trzeba je rozróżniać po identyfikatorze,
    3. dopisek „kopia robocza”, gdy obok programu jest katalog `.git` — maszyna
       deweloperska oznacza się sama, bez pamiętania o etykietach.

    Nazwa komputera zwykle zawiera imię właściciela, więc **jest to dana osobowa** —
    dlatego mówimy o niej wprost w pomocy (sekcja „Co program o sobie wysyła”)
    i w opisie wydania, a nie tylko w kodzie.
    """
    try:
        wpisana = PLIK_ETYKIETY.read_text(encoding="utf-8").strip()
        if wpisana:
            return wpisana[:60]
    except OSError:
        pass

    try:
        # platform.node() bierze nazwę z systemu i — w odróżnieniu od socket.getfqdn() —
        # nie odpytuje przy tym DNS-u, więc nie zawiesi się przy kiepskiej sieci
        nazwa = platform.node().strip()
    except Exception:
        nazwa = ""
    if (BAZA / ".git").exists():
        return (f"{nazwa} (kopia robocza)" if nazwa else "kopia robocza")[:60]
    return nazwa[:60]


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

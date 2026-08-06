"""Stempluje nowe wydanie: ustala numer, zapisuje `WERSJA` i przebudowuje `ZMIANY.md`.

    python narzedzia/wydaj.py "Opis dla brata, jednym akapitem."

Numer ma postać `rok.miesiąc.dzień-kolejny`, np. `2026.08.06-82`: data z dnia wydania
i **numer po kolei od pierwszego wydania**. Oba człony liczy skrypt — data z zegara,
numer z historii pliku `WERSJA` w gicie — bo oba wpisywane ręcznie już się myliły:
raz weszła data z poprzedniej sesji, raz numer zajęty przez wydanie zrobione
na drugim komputerze. Jedyne, co trzeba napisać samemu, to opis dla użytkownika.

Numer porządkowy zastąpił licznik wydań w danym dniu. Niesie tę samą informację
(dwa wydania jednego dnia mają różne numery), a przy okazji mówi, które to wydanie
z rzędu — więc na stronie historii nie trzeba go liczyć osobno.

Sam skrypt niczego nie commituje ani nie wypycha: wydanie to świadoma decyzja,
a `git push` z pliku, który właśnie się zmienił, byłby o jeden krok za daleko.
"""
import argparse
import sys
from datetime import date
from pathlib import Path

KORZEN = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KORZEN / "narzedzia"))

import zbuduj_zmiany  # noqa: E402

PLIK = KORZEN / "WERSJA"


def numer_wydania(dzien: date, kolejne: int) -> str:
    """`2026.08.06-82` — data wydania i numer po kolei od początku."""
    return f"{dzien:%Y.%m.%d}-{kolejne}"


def nastepny_numer(dzien: date | None = None) -> str:
    """Numer, który dostanie najbliższe wydanie.

    Liczymy wyłącznie po wydaniach **zacommitowanych**: to, co leży w katalogu
    roboczym, jest właśnie tym wydaniem, które stemplujemy. Dzięki temu powtórne
    uruchomienie skryptu przed commitem nadaje ten sam numer, a nie kolejny.
    """
    return numer_wydania(dzien or date.today(),
                         len(zbuduj_zmiany.wydania_zacommitowane()) + 1)


def wydaj(opis: str, dzien: date | None = None) -> str:
    numer = nastepny_numer(dzien)
    PLIK.write_text(f"{numer}\n{opis.strip()}\n", encoding="utf-8")
    zbuduj_zmiany.zapisz()
    return numer


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("opis", help="opis zmian dla użytkownika, w cudzysłowie")
    argumenty = parser.parse_args()

    nadany = wydaj(argumenty.opis)
    print(f"Wydanie {nadany}. Zapisane: WERSJA i ZMIANY.md.")
    print("Teraz: sprawdź `git diff`, zacommituj oba pliki i wypchnij.")

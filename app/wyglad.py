"""Kolor programu — motyw wybierany w Ustawieniach.

Sześć palet w stylu Androida: kolor przewodni i jego odcienie. Sam motyw to klasa na
`<body>` (`motyw-zielony` itd.), a kolory siedzą w `style.css` — tutaj jest wyłącznie
lista nazw i zapamiętany wybór.

Wybór leży w osobnym pliku `dane/motyw.txt`, **a nie w tabeli `ustawienia`**.
`generator.przygotuj_kontekst` zaczyna od `dict(ustawienia)`, więc każdy klucz z tej
tabeli trafia do danych, którymi wypełniane są formatki Worda. Kolor okna programu
nie ma prawa dotknąć dokumentów ani złożonych PDF-ów — osobny plik gwarantuje to
z samej budowy, bez pilnowania, czy ktoś kiedyś nie nazwie pola w formatce tak samo.
Przy okazji strona błędu pokazuje się w wybranym kolorze nawet wtedy, gdy baza jest
uszkodzona. `dane/` przeżywa aktualizacje, więc wybór też.
"""
import contextlib
from pathlib import Path

from .config import DANE

# kolejność = kolejność próbek w Ustawieniach; pierwsze cztery brat widział w PDF-ie
MOTYWY: dict[str, str] = {
    "niebieski": "Niebieski",
    "zielony": "Zielony",
    "fioletowy": "Fioletowy",
    "pomaranczowy": "Pomarańczowy",
    "morski": "Morski",
    "grafitowy": "Grafitowy",
}
DOMYSLNY = "niebieski"
PLIK: Path = DANE / "motyw.txt"


def biezacy() -> str:
    """Zapamiętany motyw. Brak pliku, śmieci w środku albo błąd dysku — domyślny.

    Czytane przy każdej stronie, także przy stronie błędu, więc nie wolno tu rzucić
    wyjątkiem: zepsuty kolor nie może zabrać bratu programu.
    """
    try:
        klucz = PLIK.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeDecodeError):
        return DOMYSLNY
    return klucz if klucz in MOTYWY else DOMYSLNY


def zapisz(klucz: str) -> None:
    """Zapamiętuje motyw. `ValueError` przy nazwie spoza listy.

    Zapis przez plik tymczasowy i podmianę: przerwany w połowie nie zostawi pliku
    z połową nazwy (a nawet gdyby — `biezacy` wróciłby wtedy do domyślnego).
    """
    if klucz not in MOTYWY:
        raise ValueError(f"Nie ma takiego koloru: {klucz!r}")
    tymczasowy = PLIK.with_name(PLIK.name + ".tmp")
    try:
        tymczasowy.write_text(klucz + "\n", encoding="utf-8")
        tymczasowy.replace(PLIK)
    except OSError:
        # np. `motyw.txt` z atrybutem „tylko do odczytu” — Windows takiego pliku nie
        # podmieni. Tymczasowego nie zostawiamy: leżałby w `dane/` przy każdej próbie.
        with contextlib.suppress(OSError):
            tymczasowy.unlink(missing_ok=True)
        raise

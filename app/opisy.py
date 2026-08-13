"""Opisy sprawozdania dostarczane razem z programem.

Brat ma mieć swój standardowy opis przebiegu prac **od razu po aktualizacji**, bez
przepisywania go ręcznie na każdej instalacji. Treść jedzie w `szablony/`, czyli tam,
gdzie i formatki: ten katalog jest lustrzany i przy aktualizacji podmienia się w całości.

Zasiewamy **raz na pozycję**, a nie przy każdym starcie — i to jest tu cała trudność.
Opis w bazie jest jego: może go poprawić pod siebie albo skasować, bo mu nie pasuje.
Gdyby wracał przy każdym uruchomieniu, skasowanie byłoby nie do przeprowadzenia,
a poprawki znikałyby pod nadpisaną kopią. Dlatego zapamiętujemy w ustawieniach nazwy
już zasianych pozycji i więcej do nich nie wracamy:

* nowa pozycja w pliku → dojedzie przy najbliższym starcie po aktualizacji;
* pozycja skasowana przez brata → **zostaje skasowana**;
* zmiana treści pozycji, którą już ma → nie rusza jego kopii (mogła być poprawiona).

Nic tutaj nie może zatrzymać startu programu: to wygoda, a nie funkcja, bez której
program nie działa. Każdy błąd (brak pliku, literówka w JSON-ie) połykamy.
"""
from __future__ import annotations

import json

from . import db
from .config import SZABLONY

PLIK = "opisy_sprawozdania.json"
KLUCZ_USTAWIEN = "opisy_zasiane"


def wzorcowe() -> list[dict[str, str]]:
    """Opisy dostarczone z programem. Zły plik = pusta lista, a nie awaria startu."""
    try:
        dane = json.loads((SZABLONY / PLIK).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    if not isinstance(dane, list):
        return []
    # Obcinamy **przed** sprawdzeniem, czy pozycja jest kompletna: samo `"   "` jest
    # w Pythonie prawdziwe, więc filtr na surowych wartościach przepuszczał opis,
    # z którego po obcięciu zostawała pustka.
    pozycje = [{"nazwa": str(p.get("nazwa", "")).strip(), "opis": str(p.get("opis", "")).strip()}
               for p in dane if isinstance(p, dict)]
    return [p for p in pozycje if p["nazwa"] and p["opis"]]


def _zasiane() -> set[str]:
    try:
        return set(json.loads(db.wczytaj_ustawienia().get(KLUCZ_USTAWIEN, "[]")))
    except ValueError:
        return set()


def zasiej() -> int:
    """Dokłada brakujące opisy wzorcowe. Zwraca, ile doszło — do testów i śladu w logu."""
    juz = _zasiane()
    do_zasiania = [p for p in wzorcowe() if p["nazwa"] not in juz]
    if not do_zasiania:
        return 0

    # Nazwy, które brat już ma — mógł dopisać swój opis o tej samej nazwie, zanim
    # dostał nasz. Wtedy jego zostaje, a my tylko odhaczamy pozycję jako zasianą.
    istniejace = {w["nazwa"] for w in db.opisy_sprawozdania()}
    dodane = 0
    for pozycja in do_zasiania:
        if pozycja["nazwa"] not in istniejace:
            db.dodaj_opis_sprawozdania(pozycja["nazwa"], pozycja["opis"])
            dodane += 1
        juz.add(pozycja["nazwa"])

    db.zapisz_ustawienia({KLUCZ_USTAWIEN: json.dumps(sorted(juz), ensure_ascii=False)})
    return dodane

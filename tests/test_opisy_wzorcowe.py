"""Opisy sprawozdania dostarczane razem z programem.

Brat ma dostać swój standardowy opis przebiegu prac **od razu po aktualizacji**.
Cała trudność jest w tym, żeby zasiać go **raz**: opis w bazie jest jego, może go
poprawić albo skasować, a wracająca przy każdym starcie kopia byłaby nie do usunięcia.
"""
from __future__ import annotations

import json

from app import db, opisy


def _wzorcowe(srodowisko, pozycje: list[dict[str, str]]) -> None:
    (srodowisko.szablony / opisy.PLIK).write_text(
        json.dumps(pozycje, ensure_ascii=False), encoding="utf-8")


def test_opis_dostarczony_z_programem_pojawia_sie_sam(srodowisko):
    _wzorcowe(srodowisko, [{"nazwa": "Opis standardowy", "opis": "Pomiar metodą RTN GNSS."}])

    assert opisy.zasiej() == 1

    zapisane = db.opisy_sprawozdania()
    assert [(w["nazwa"], w["opis"]) for w in zapisane] == \
        [("Opis standardowy", "Pomiar metodą RTN GNSS.")]


def test_drugi_start_nie_dubluje(srodowisko):
    """Program uruchamia się codziennie — lista opisów nie może przy tym puchnąć."""
    _wzorcowe(srodowisko, [{"nazwa": "Opis standardowy", "opis": "Treść."}])
    opisy.zasiej()

    assert opisy.zasiej() == 0
    assert len(db.opisy_sprawozdania()) == 1


def test_skasowany_opis_nie_wraca(srodowisko):
    """Najważniejszy test w tym pliku.

    Skoro opis wraca przy starcie, to skasowanie go jest niewykonalne — brat kasuje,
    a nazajutrz znowu tam jest i nie wie dlaczego.
    """
    _wzorcowe(srodowisko, [{"nazwa": "Opis standardowy", "opis": "Treść."}])
    opisy.zasiej()
    db.usun_opis_sprawozdania(db.opisy_sprawozdania()[0]["id"])

    assert opisy.zasiej() == 0
    assert db.opisy_sprawozdania() == []


def test_poprawiona_kopia_nie_jest_nadpisywana(srodowisko):
    """Brat dopasowuje opis pod siebie — nasza wersja nie ma prawa tego cofnąć."""
    _wzorcowe(srodowisko, [{"nazwa": "Opis standardowy", "opis": "Wersja z programu."}])
    opisy.zasiej()
    wpis = db.opisy_sprawozdania()[0]
    db.usun_opis_sprawozdania(wpis["id"])
    db.dodaj_opis_sprawozdania("Opis standardowy", "Moja poprawiona wersja.")

    opisy.zasiej()

    assert [w["opis"] for w in db.opisy_sprawozdania()] == ["Moja poprawiona wersja."]


def test_nowa_pozycja_dojezdza_przy_kolejnej_aktualizacji(srodowisko):
    _wzorcowe(srodowisko, [{"nazwa": "Pierwszy", "opis": "a"}])
    opisy.zasiej()

    _wzorcowe(srodowisko, [{"nazwa": "Pierwszy", "opis": "a"},
                           {"nazwa": "Drugi", "opis": "b"}])

    assert opisy.zasiej() == 1
    assert sorted(w["nazwa"] for w in db.opisy_sprawozdania()) == ["Drugi", "Pierwszy"]


def test_wlasne_opisy_brata_zostaja_nietkniete(srodowisko):
    db.dodaj_opis_sprawozdania("Mój własny", "Moja treść.")
    _wzorcowe(srodowisko, [{"nazwa": "Opis standardowy", "opis": "Treść."}])

    opisy.zasiej()

    assert sorted(w["nazwa"] for w in db.opisy_sprawozdania()) == ["Mój własny", "Opis standardowy"]


def test_wlasny_opis_o_tej_samej_nazwie_ma_pierwszenstwo(srodowisko):
    """Brat mógł nazwać swój opis tak samo, **zanim** dostał nasz.

    Wtedy jego zostaje nietknięty, a pozycja i tak liczy się jako zasiana — inaczej
    przy każdym starcie dokładałaby się druga pozycja o tej samej nazwie i nie dałoby
    się ich odróżnić na liście.
    """
    db.dodaj_opis_sprawozdania("Opis standardowy", "Moja własna treść.")
    _wzorcowe(srodowisko, [{"nazwa": "Opis standardowy", "opis": "Treść z programu."}])

    assert opisy.zasiej() == 0

    zapisane = db.opisy_sprawozdania()
    assert [(w["nazwa"], w["opis"]) for w in zapisane] == \
        [("Opis standardowy", "Moja własna treść.")]
    assert opisy.zasiej() == 0, "przy kolejnym starcie też nic nie dochodzi"


# --- nic tu nie może zatrzymać startu programu -------------------------------

def test_brak_pliku_nie_wywala_startu(srodowisko):
    assert opisy.wzorcowe() == []
    assert opisy.zasiej() == 0


def test_polamany_json_nie_wywala_startu(srodowisko):
    (srodowisko.szablony / opisy.PLIK).write_text("{to nie jest json", encoding="utf-8")

    assert opisy.zasiej() == 0


def test_pozycje_bez_nazwy_albo_tresci_pomijamy(srodowisko):
    _wzorcowe(srodowisko, [{"nazwa": "", "opis": "bez nazwy"},
                           {"nazwa": "bez treści", "opis": "   "},
                           {"nazwa": "Dobry", "opis": "Treść."}])

    assert opisy.zasiej() == 1
    assert [w["nazwa"] for w in db.opisy_sprawozdania()] == ["Dobry"]


# --- to, co naprawdę jedzie do brata -----------------------------------------

def test_plik_wydany_z_programem_da_sie_wczytac():
    """Nie atrapa, tylko `szablony/opisy_sprawozdania.json` z repozytorium.

    Literówka w tym pliku nie wywali programu (błąd jest połykany), więc brat po prostu
    nie dostałby opisu i nikt by się nie dowiedział dlaczego — stąd ten test.
    """
    pozycje = opisy.wzorcowe()

    assert pozycje, "z programem nie jedzie żaden opis wzorcowy"
    for pozycja in pozycje:
        assert pozycja["nazwa"] and pozycja["opis"]

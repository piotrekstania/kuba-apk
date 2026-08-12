"""Szablon .docx → formularz. To tu żyje zasada „źródłem prawdy jest plik Worda”."""
from __future__ import annotations

from pathlib import Path

import pytest

from app import szablony

PRAWDZIWE = sorted((Path(__file__).resolve().parent.parent / "szablony").glob("*.docx"))


# --- prawdziwe formatki brata ------------------------------------------------

@pytest.mark.parametrize("plik", PRAWDZIWE, ids=lambda p: p.stem)
def test_prawdziwa_formatka_daje_sie_wczytac(plik):
    """Każda formatka w szablony/ musi się otworzyć i wyprodukować listę pól.

    To jest test-strażnik przy podmianie formatki od brata: literówka w znaczniku
    albo plik zapisany przez Worda w dziwny sposób wychodzi tutaj, a nie u niego.
    """
    szablon = szablony.wczytaj_szablon(plik)
    assert not szablon.opis.startswith("⚠"), szablon.opis
    assert szablon.pola, "szablon bez ani jednego pola — czy na pewno ma znaczniki {{ }}?"
    assert all(pole.klucz for pole in szablon.pola)


@pytest.mark.parametrize("plik", PRAWDZIWE, ids=lambda p: p.stem)
def test_glowna_formatka_nie_ma_pol_nieopisanych(plik):
    """W szablonie z własnym formularzem nic nie powinno wpaść do „Pozostałych pól”.

    Ta grupa to worek na znaczniki, których nie ma w .json — czyli albo literówka
    w Wordzie, albo nowy znacznik wyliczany, którego zapomniano dopisać do
    `POLA_WYLICZANE` / `SUFIKSY_*`. Jedno i drugie widać u brata jako puste pole
    „Polozenie gmina teryt”, którego nikt nie ma wypełniać.

    Dokumenty dodatkowe (`glowny: false`) mają `"pola": []` z założenia — biorą dane
    z formularza operatu. Pilnuje ich osobny test niżej.
    """
    szablon = szablony.wczytaj_szablon(plik)
    if not szablon.glowny:
        pytest.skip("dokument dodatkowy — dane bierze z formularza operatu")
    nieopisane = [p.klucz for p in szablon.pola if p.grupa == "Pozostałe pola z szablonu"]
    assert nieopisane == []


def _kontekst_operatu(szablon: szablony.Szablon) -> set[str]:
    """Klucze, które trafią do kontekstu przy generowaniu z tego szablonu."""
    dostepne = set(szablony.POLA_WYLICZANE)
    for pole in szablon.pola:
        dostepne.add(pole.klucz)
        # `<klucz>_jest` wylicza generator dla każdego pola — formatka pyta o to
        # w `{%p if ... %}`, wybierając między treścią a słowem „brak”
        dostepne.add(pole.klucz + szablony.SUFIKS_JEST)
        if pole.typ == "teryt":
            dostepne.update(pole.klucz + s for s in szablony.SUFIKSY_TERYT)
        elif pole.typ == "date":
            dostepne.update(pole.klucz + s for s in szablony.SUFIKSY_DATY)
        elif pole.typ == "wybor_wielokrotny":
            dostepne.update(pole.klucz + s for s in szablony.SUFIKSY_WYBORU)
    return dostepne


@pytest.mark.parametrize("plik", PRAWDZIWE, ids=lambda p: p.stem)
def test_dokument_dodatkowy_nie_uzywa_znacznikow_spoza_formularza(plik):
    """Znaczniki dokumentu dodatkowego muszą być pokryte przez formularz operatu.

    `dopisz_dokument` wypełnia je **tym samym kontekstem** co spis treści, więc
    znacznik, którego formularz nie zbiera, nie zgłosi żadnego błędu — po prostu
    zostawi w gotowym dokumencie puste miejsce. To najcichszy możliwy sposób
    zepsucia operatu, więc niech pilnuje go test.
    """
    szablon = szablony.wczytaj_szablon(plik)
    if szablon.glowny:
        pytest.skip("to jest szablon główny, ma własny formularz")
    glowne = [s for s in szablony.lista_szablonow() if s.glowny]
    assert glowne, "żaden szablon nie jest oznaczony jako główny"
    dostepne: set[str] = set()
    for glowny in glowne:
        dostepne |= _kontekst_operatu(glowny)
    brakujace = sorted({p.klucz for p in szablon.pola} - dostepne)
    assert brakujace == [], (
        f"{plik.name} używa znaczników, których formularz operatu nie zbiera: {brakujace}")


# --- mechanizm wykrywania pól ------------------------------------------------

def test_nowy_znacznik_w_wordzie_daje_nowe_pole(srodowisko):
    """Dopisanie {{ }} w Wordzie ma dołożyć pole bez zmian w kodzie."""
    srodowisko.dodaj_szablon("proba", ["Numer: {{ nr_roboty }}", "Uwagi: {{ swieze_pole }}"])
    szablon = szablony.szablon_po_id("proba")
    klucze = [p.klucz for p in szablon.pola]
    assert "nr_roboty" in klucze
    assert "swieze_pole" in klucze


def test_json_ustala_etykiety_kolejnosc_i_grupy(srodowisko):
    srodowisko.dodaj_szablon(
        "proba", ["{{ b }} {{ a }}"],
        opis={"nazwa": "Próbka", "pola": [
            {"klucz": "a", "etykieta": "Pierwsze", "grupa": "Robota", "wymagane": True},
            {"klucz": "b", "etykieta": "Drugie", "grupa": "Robota"},
        ]})
    szablon = szablony.szablon_po_id("proba")
    assert szablon.nazwa == "Próbka"
    assert [p.klucz for p in szablon.pola] == ["a", "b"]      # kolejność z .json, nie z .docx
    assert szablon.pola[0].etykieta == "Pierwsze"
    assert szablon.pola[0].wymagane
    assert list(szablon.grupy) == ["Robota"]


def test_znaczniki_wyliczane_nie_trafiaja_do_formularza(srodowisko):
    """`_gmina`, `_teryt`, `_slownie`, `data_dzisiaj` wypełnia program, nie człowiek."""
    srodowisko.dodaj_szablon(
        "proba",
        ["{{ polozenie_gmina }} {{ polozenie_obreb_teryt }} {{ data_zakonczenia_slownie }} "
         "{{ data_dzisiaj }} {{ rok }} {{ bazy_pliki }}"],
        opis={"pola": [
            {"klucz": "polozenie", "typ": "teryt"},
            {"klucz": "data_zakonczenia", "typ": "date"},
            {"klucz": "bazy", "typ": "wybor_wielokrotny", "opcje": ["EGiB"]},
        ]})
    szablon = szablony.szablon_po_id("proba")
    nieopisane = [p.klucz for p in szablon.pola if p.grupa == "Pozostałe pola z szablonu"]
    assert nieopisane == []


def test_pole_z_ustawien_nie_pokazuje_sie_w_formularzu(srodowisko):
    srodowisko.dodaj_szablon(
        "proba", ["{{ jawne }} {{ ukryte }}"],
        opis={"pola": [{"klucz": "jawne"}, {"klucz": "ukryte", "zrodlo": "ustawienia"}]})
    szablon = szablony.szablon_po_id("proba")
    widoczne = [p.klucz for grupa in szablon.grupy.values() for p in grupa]
    assert widoczne == ["jawne"]
    assert "ukryte" in [p.klucz for p in szablon.pola]        # ale nadal jest w kontekście


def test_uszkodzony_plik_nie_wywala_listy(srodowisko):
    """Jeden zepsuty .docx nie może zabrać całej strony głównej."""
    srodowisko.dodaj_szablon("dobry", ["{{ a }}"])
    (srodowisko.szablony / "zepsuty.docx").write_bytes(b"to nie jest docx")
    lista = szablony.lista_szablonow()
    identyfikatory = {s.id for s in lista}
    assert identyfikatory == {"dobry", "zepsuty"}
    zepsuty = next(s for s in lista if s.id == "zepsuty")
    assert zepsuty.opis.startswith("⚠")


def test_pliki_tymczasowe_worda_sa_pomijane(srodowisko):
    """Otwarty w Wordzie dokument zostawia obok „~$nazwa.docx” — to nie szablon."""
    srodowisko.dodaj_szablon("dobry", ["{{ a }}"])
    (srodowisko.szablony / "~$dobry.docx").write_bytes(b"smiec")
    assert [s.id for s in szablony.lista_szablonow()] == ["dobry"]
    assert [s["id"] for s in szablony.lista_skrocona()] == ["dobry"]

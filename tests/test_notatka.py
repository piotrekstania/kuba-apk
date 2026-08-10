"""Opis operatu — notatki brata do roboty.

Pole nazywa się w interfejsie **„Opis”**, a w kodzie `notatka`: `operaty.opis()` znaczy
w tym programie co innego (zawartość `operat.json`, czyli akurat tego pliku, w którym
notatka też siedzi), więc jedna nazwa na dwie rzeczy prosiłaby się o pomyłkę.

Warunek, od którego zaczęła się ta funkcja: **opis nie wchodzi do dokumentu**. To są
uwagi do roboty („czekam na wypis”), a nie dane do formatki — gdyby wyszły w spisie
treści albo w sprawozdaniu, brat oddałby je do ośrodka razem z operatem.

Zapisujemy go w dwóch miejscach naraz — w bazie i w `operat.json` — z tego samego
powodu co numer operatu: katalog bywa przenoszony do archiwum (zostaje wtedy sam wpis
w historii) albo kopiowany na inny komputer (zostaje sam katalog).
"""
from __future__ import annotations

import json

from docx import Document

from app import db, operaty
from tests.test_trasy import FORMULARZ, OPIS_OPERATU

OPIS = "Czekam na wypis z KW.\nMapę oddać do 15.09."


def _dodaj_operat(klient):
    klient.srodowisko.dodaj_szablon(
        "spis_tresci_wzor",
        ["Robota: {{ nr_roboty }}", "Operat: {{ nr_operatu }}", "Uwagi: {{ uwagi }}"],
        opis=OPIS_OPERATU, tabela=True)


def _wyslij(klient, **zmiany):
    """POST kompletu pól formularza — przeglądarka wysyła też te puste."""
    return klient.post("/generuj/spis_tresci_wzor", data=dict(FORMULARZ, **zmiany),
                       follow_redirects=False)


def _tekst_dokumentu(katalog) -> str:
    return "\n".join(a.text for a in Document(katalog / "spis_tresci.docx").paragraphs)


# --- to jest cała rzecz: opis zostaje poza dokumentem ------------------------

def test_opis_nie_wchodzi_do_dokumentu(klient):
    """Warunek postawiony przez brata. Reszta testów w tym pliku jest przy okazji."""
    _dodaj_operat(klient)

    _wyslij(klient, notatka=OPIS)

    katalog = klient.srodowisko.wyniki / db.dokumenty()[0]["katalog"]
    tresc = _tekst_dokumentu(katalog)
    assert "Czekam na wypis" not in tresc
    assert "Mapę oddać" not in tresc
    assert "GK.6640.1.2026" in tresc, "a dane dokumentu mają być na miejscu"


def test_opis_nie_przecieka_nawet_do_znacznika_o_tej_samej_nazwie(klient):
    """Mocniejsza wersja poprzedniego testu.

    Formatka bez `{{ notatka }}` nie pokazałaby niczego tak czy inaczej, więc sam brak
    tekstu w dokumencie nic jeszcze nie dowodzi. Tutaj znacznik w szablonie **jest** —
    i ma zostać pusty, bo to osobne pole formularza (`pole__notatka`), a notatka jedzie
    poza tą przestrzenią nazw.
    """
    klient.srodowisko.dodaj_szablon(
        "spis_tresci_wzor",
        ["Robota: {{ nr_roboty }}", "Notatka w szablonie: [{{ notatka }}]"],
        opis=OPIS_OPERATU, tabela=True)

    _wyslij(klient, notatka=OPIS, pole__notatka="")

    katalog = klient.srodowisko.wyniki / db.dokumenty()[0]["katalog"]
    assert "Notatka w szablonie: []" in _tekst_dokumentu(katalog)
    assert "Czekam na wypis" not in _tekst_dokumentu(katalog)


def test_opis_nie_jest_polem_szablonu(klient):
    """Notatka jedzie poza `pole__`, więc nie miesza się ze znacznikami z .docx.

    Gdyby wpadła do danych formularza, pokazałaby się na stronie operatu jako
    kolejne wypełnione pole — i pojechałaby do szablonu, który akurat ma znacznik
    o tej samej nazwie.
    """
    _dodaj_operat(klient)

    _wyslij(klient, notatka=OPIS)

    dane = json.loads(db.dokumenty()[0]["dane_json"])
    assert "notatka" not in dane and "opis" not in dane


# --- gdzie widać ------------------------------------------------------------

def test_opis_widac_na_liscie_operatow(klient):
    _dodaj_operat(klient)
    _wyslij(klient, notatka=OPIS)

    strona = klient.get("/").text

    assert "Czekam na wypis z KW." in strona
    assert "Mapę oddać do 15.09." in strona


def test_operat_bez_opisu_nie_dostaje_pustego_wiersza(klient):
    """Pusty wiersz pod danymi wyglądałby jak usterka tabeli."""
    _dodaj_operat(klient)
    _wyslij(klient, notatka="")

    strona = klient.get("/").text

    assert 'class="notatka"' not in strona
    assert "z-notatka" not in strona


def test_opis_wraca_do_formularza_przy_poprawianiu(klient):
    """Bez tego „Popraw” kasowałby notatkę, bo formularz odesłałby puste pole."""
    _dodaj_operat(klient)
    _wyslij(klient, notatka=OPIS)
    wpis = db.dokumenty()[0]

    formularz = klient.get(f"/nowy/spis_tresci_wzor?edytuj={wpis['id']}").text

    assert "Czekam na wypis z KW." in formularz
    assert 'name="notatka"' in formularz


def test_powielenie_przenosi_opis(klient):
    """Kolejne zlecenie zaczyna się zwykle od tych samych uwag — skasować łatwiej."""
    _dodaj_operat(klient)
    _wyslij(klient, notatka=OPIS)
    wpis = db.dokumenty()[0]

    formularz = klient.get(f"/nowy/spis_tresci_wzor?kopiuj={wpis['id']}").text

    assert "Czekam na wypis z KW." in formularz


# --- zmiana i kasowanie ------------------------------------------------------

def test_poprawka_zmienia_opis(klient):
    _dodaj_operat(klient)
    _wyslij(klient, notatka=OPIS)
    wpis = db.dokumenty()[0]

    klient.post(f"/generuj/spis_tresci_wzor?edytuj={wpis['id']}",
                data=dict(FORMULARZ, notatka="Wypis odebrany, zostaje mapa."),
                follow_redirects=False)

    assert db.dokumenty()[0]["notatka"] == "Wypis odebrany, zostaje mapa."
    assert len(db.dokumenty()) == 1, "poprawka założyła drugi wpis"


def test_wyczyszczony_opis_znika(klient):
    """Świadome skasowanie notatki musi zadziałać — także w `operat.json`.

    `zaloz()` przenosi notatkę ze starego pliku, żeby nie zginęła przypadkiem;
    ten test pilnuje, żeby nie robiła się przez to nieusuwalna.
    """
    _dodaj_operat(klient)
    _wyslij(klient, notatka=OPIS)
    wpis = db.dokumenty()[0]

    klient.post(f"/generuj/spis_tresci_wzor?edytuj={wpis['id']}",
                data=dict(FORMULARZ, notatka=""), follow_redirects=False)

    katalog = klient.srodowisko.wyniki / wpis["katalog"]
    assert db.dokumenty()[0]["notatka"] == ""
    assert operaty.opis(katalog).get("notatka") == ""
    assert "Czekam na wypis" not in klient.get("/").text


def test_opis_przezywa_blad_walidacji(klient):
    """Formularz wraca z kompletem danych — notatka nie może być wyjątkiem."""
    _dodaj_operat(klient)

    odpowiedz = klient.post("/generuj/spis_tresci_wzor",
                            data=dict(FORMULARZ, pole__nr_roboty="", notatka=OPIS))

    assert "Uzupełnij wymagane pola" in odpowiedz.text
    assert "Czekam na wypis z KW." in odpowiedz.text


# --- przeżywa archiwum i przeprowadzkę na inny komputer ----------------------

def test_opis_zapisuje_sie_takze_w_katalogu_operatu(klient):
    """`operat.json` jedzie razem z folderem — to jedyny nośnik przy kopiowaniu."""
    _dodaj_operat(klient)
    _wyslij(klient, notatka=OPIS)

    katalog = klient.srodowisko.wyniki / db.dokumenty()[0]["katalog"]

    assert operaty.opis(katalog)["notatka"] == OPIS


def test_operat_spoza_historii_pokazuje_swoj_opis(klient):
    """Katalog skopiowany z innego komputera: jest folder, nie ma wpisu w bazie."""
    _dodaj_operat(klient)
    _wyslij(klient, notatka=OPIS)
    db.usun_dokument(db.dokumenty()[0]["id"])

    strona = klient.get("/").text

    assert "spoza historii" in strona
    assert "Czekam na wypis z KW." in strona


def test_zaloz_nie_kasuje_notatki(srodowisko):
    """Poprawianie operatu przepisuje `operat.json` od nowa — tak jak przy układzie
    kafelków, notatka musi to przeżyć, choćby nikt jej w tym przebiegu nie podał."""
    katalog, _ = operaty.zaloz("001/2026", "GK.1", "spis_tresci_wzor", {})
    operaty.zapisz_notatke(katalog, OPIS)

    operaty.zaloz("001/2026", "GK.1", "spis_tresci_wzor", {"nr_roboty": "GK.1"})

    assert operaty.opis(katalog)["notatka"] == OPIS


def test_notatka_w_katalogu_ktorego_nie_ma_nie_wywala_programu(srodowisko):
    """Katalog zniknął w trakcie (archiwizacja z Eksploratora) — to nie powód do awarii."""
    operaty.zapisz_notatke(srodowisko.wyniki / "nie ma takiego", OPIS)

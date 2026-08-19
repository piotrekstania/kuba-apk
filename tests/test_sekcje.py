"""Powtarzalne sekcje formularza — wykazy zmian danych budynku.

W jednym operacie takich wykazów bywa kilka, każdy z własnym kompletem 15 atrybutów
w dwóch stanach. To za dużo na wiersz tabeli (30 kolumn), więc powtarzamy **komplet
pól**: jedna karta w formularzu = jeden wykaz = jedna tabela w gotowym dokumencie.

Do formatki jedzie lista słowników — dokładnie taka sama jak z pola typu `tabela` —
więc `{%p for %}` w Wordzie obsługuje jedno i drugie tak samo.
"""
from __future__ import annotations

import pathlib
import tempfile

from docx import Document

from app import db, generator, szablony

PODPOLA = [{"klucz": "adres_dotychczas", "etykieta": "Adres — dotychczasowy"},
           {"klucz": "adres_nowy", "etykieta": "Adres — nowy"}]


def _operat_z_sekcjami(klient):
    klient.srodowisko.dodaj_szablon(
        "spis_tresci_wzor", ["{{ nr_roboty }}"],
        opis={"nazwa": "Operat", "glowny": True,
              "pola": [{"klucz": "nr_roboty", "etykieta": "Nr roboty"},
                       {"klucz": "wykazy", "etykieta": "Wykazy", "typ": "sekcje",
                        "etykieta_pozycji": "Wykaz", "podpola": PODPOLA}]})


def _wyslij(klient, **pola):
    dane = {"pole__nr_roboty": "GK.1", "notatka": ""}
    dane.update(pola)
    return klient.post("/generuj/spis_tresci_wzor", data=dane, follow_redirects=False)


# --- odczyt z formularza -----------------------------------------------------

def test_sekcje_wracaja_jako_lista_slownikow(klient):
    """Ten sam kształt co przy tabeli — żeby formatka nie musiała ich rozróżniać."""
    _operat_z_sekcjami(klient)

    _wyslij(klient,
            **{"sek__wykazy__0__adres_dotychczas": "Polna 7",
               "sek__wykazy__0__adres_nowy": "Polna 7a",
               "sek__wykazy__1__adres_nowy": "Leśna 3"})

    import json
    zapisane = json.loads(db.dokumenty()[0]["dane_json"])["wykazy"]
    assert zapisane == [{"adres_dotychczas": "Polna 7", "adres_nowy": "Polna 7a"},
                        {"adres_nowy": "Leśna 3"}]


def test_pusta_sekcja_nie_jedzie_do_dokumentu(klient):
    """Formularz startuje z jedną pustą kartą; niewypełniona nie ma po co dawać
    pustej strony w wykazie."""
    _operat_z_sekcjami(klient)

    _wyslij(klient, **{"sek__wykazy__0__adres_dotychczas": "Polna 7",
                       "sek__wykazy__1__adres_dotychczas": "",
                       "sek__wykazy__1__adres_nowy": ""})

    import json
    assert len(json.loads(db.dokumenty()[0]["dane_json"])["wykazy"]) == 1


def test_kolejnosc_sekcji_idzie_po_indeksie_a_nie_po_kolejnosci_pol(klient):
    """Przeglądarka wysyła pola w kolejności DOM-u; po usunięciu karty numery
    przenumerowuje JS, ale kolejność ma wynikać z indeksu, nie z wysyłki."""
    _operat_z_sekcjami(klient)

    _wyslij(klient, **{"sek__wykazy__1__adres_nowy": "drugi",
                       "sek__wykazy__0__adres_nowy": "pierwszy"})

    import json
    assert [w["adres_nowy"] for w in json.loads(db.dokumenty()[0]["dane_json"])["wykazy"]] \
        == ["pierwszy", "drugi"]


# --- formularz ---------------------------------------------------------------

def test_formularz_pokazuje_zapisane_sekcje(klient):
    _operat_z_sekcjami(klient)
    _wyslij(klient, **{"sek__wykazy__0__adres_nowy": "Polna 7",
                       "sek__wykazy__1__adres_nowy": "Leśna 3"})

    formularz = klient.get(f"/nowy/spis_tresci_wzor?edytuj={db.dokumenty()[0]['id']}").text

    assert 'name="sek__wykazy__0__adres_nowy"' in formularz
    assert 'name="sek__wykazy__1__adres_nowy"' in formularz
    assert "Polna 7" in formularz and "Leśna 3" in formularz


def test_pusty_formularz_ma_jedna_karte_i_wzorzec(klient):
    """Bez ani jednej karty formularz wygląda, jakby czegoś brakowało; wzorzec
    w `<template>` sprawia, że JS nie musi znać listy podpól."""
    _operat_z_sekcjami(klient)

    formularz = klient.get("/nowy/spis_tresci_wzor").text

    assert formularz.count('class="sekcja"') == 2, "jedna karta + wzorzec do klonowania"
    assert "wzorzec-sekcji" in formularz


# --- droga do dokumentu ------------------------------------------------------

def _wykaz_z_danymi(wykazy: list[dict]) -> Document:
    glowny = szablony.szablon_po_id("spis_tresci_wzor")
    sz = szablony.szablon_po_id("wykaz_zmian_budynku_wzor")
    kontekst = generator.przygotuj_kontekst(
        glowny, {"nr_roboty": "G.1", "wykazy_budynkow": wykazy}, {})
    return Document(generator.dopisz_dokument(sz, kontekst,
                                              pathlib.Path(tempfile.mkdtemp())))


def test_kazdy_wykaz_to_osobna_tabela():
    """Sedno tej zmiany: kilka wykazów w jednym operacie, każdy ze swoimi danymi."""
    d = _wykaz_z_danymi([
        {"identyfikator_dzialki_dotychczas": "123/4", "uwagi_nowy": "przebudowa"},
        {"identyfikator_dzialki_dotychczas": "123/5", "uwagi_nowy": "wyburzony"},
    ])

    assert len(d.tables) == 2
    assert d.tables[0].rows[1].cells[3].text == "123/4"
    assert d.tables[1].rows[1].cells[3].text == "123/5"
    assert d.tables[0].rows[15].cells[4].text == "przebudowa"
    assert d.tables[1].rows[15].cells[4].text == "wyburzony"


def test_naglowek_powtarza_sie_przy_kazdym_wykazie():
    """Każdy wykaz to osobna kartka do ośrodka — musi mieć swój numer roboty."""
    d = _wykaz_z_danymi([{"adres_nowy": "a"}, {"adres_nowy": "b"}])

    assert sum(1 for p in d.paragraphs if "G.1" in p.text) == 2
    assert sum(1 for p in d.paragraphs if "WYKAZ ZMIAN" in p.text) == 2


def test_lamanie_strony_miedzy_wykazami_a_nie_po_ostatnim():
    """Łamanie po ostatnim wykazie zostawiałoby w operacie pustą kartkę."""
    import zipfile
    glowny = szablony.szablon_po_id("spis_tresci_wzor")
    sz = szablony.szablon_po_id("wykaz_zmian_budynku_wzor")

    def lamania(ile: int) -> int:
        kontekst = generator.przygotuj_kontekst(
            glowny, {"nr_roboty": "G.1",
                     "wykazy_budynkow": [{"adres_nowy": str(i)} for i in range(ile)]}, {})
        plik = generator.dopisz_dokument(sz, kontekst, pathlib.Path(tempfile.mkdtemp()))
        return zipfile.ZipFile(plik).read("word/document.xml").decode().count('w:type="page"')

    assert lamania(1) == 0
    assert lamania(2) == 1
    assert lamania(3) == 2


def test_wartosc_dziedziczy_krój_z_etykiety_obok():
    """Wartość ma wyglądać jak opis w sąsiedniej kolumnie, a nie jak domyślna
    czcionka dokumentu — to ta sama pułapka co przy opisie przebiegu prac."""
    d = _wykaz_z_danymi([{"identyfikator_dzialki_dotychczas": "123/4"}])

    wartosc = d.tables[0].rows[1].cells[3].paragraphs[0].runs[0]
    etykieta = d.tables[0].rows[1].cells[1].paragraphs[0].runs[0]
    assert (wartosc.font.name, wartosc.font.size) == (etykieta.font.name, etykieta.font.size)


def test_formatka_nie_zostawia_niewypelnionych_znacznikow():
    d = _wykaz_z_danymi([{"adres_nowy": "Polna 7"}])
    tekst = "\n".join(p.text for p in d.paragraphs)
    tekst += "\n".join(c.text for t in d.tables for w in t.rows for c in w.cells)

    assert "{{" not in tekst and "{%" not in tekst


# --- układ tabelaryczny ------------------------------------------------------

def test_nazwa_atrybutu_pojawia_sie_raz_a_nie_przy_kazdym_polu(klient):
    """Pierwsza wersja powtarzała nazwę przy obu stanach („Adres — dotychczasowy”,
    „Adres — nowy”) i przy piętnastu atrybutach robiła się ściana tekstu.

    Teraz sekcja wygląda jak tabela w dokumencie: nazwa raz, obok pole na każdy stan.
    """
    klient.srodowisko.dodaj_szablon(
        "spis_tresci_wzor", ["{{ nr_roboty }}"],
        opis={"nazwa": "Operat", "glowny": True,
              "pola": [{"klucz": "nr_roboty", "etykieta": "Nr roboty"},
                       {"klucz": "wykazy", "etykieta": "Wykazy", "typ": "sekcje",
                        "kolumny": [{"klucz": "dotychczas", "etykieta": "Stan dotychczasowy"},
                                    {"klucz": "nowy", "etykieta": "Stan nowy"}],
                        "podpola": [
                            {"klucz": "adres_dotychczas", "wiersz": "Adres budynku",
                             "kolumna": "dotychczas"},
                            {"klucz": "adres_nowy", "wiersz": "Adres budynku",
                             "kolumna": "nowy"}]}]})

    formularz = klient.get("/nowy/spis_tresci_wzor").text

    assert formularz.count("Adres budynku</th>") == 2, "raz w karcie, raz we wzorcu"
    assert "Stan dotychczasowy" in formularz and "Stan nowy" in formularz
    # nazwy pól się nie zmieniły, więc odczyt danych działa tak samo
    assert 'name="sek__wykazy__0__adres_dotychczas"' in formularz


def test_grupowanie_zachowuje_kolejnosc_atrybutow():
    """Kolejność ma być ta sama co w dokumencie — dlatego grupujemy w Pythonie,
    a nie `groupby` w Jinji, które najpierw sortuje."""
    pole = szablony.Pole(
        klucz="w", etykieta="W", typ="sekcje",
        podpola=[{"klucz": "b_nowy", "wiersz": "Beta", "kolumna": "nowy"},
                 {"klucz": "a_nowy", "wiersz": "Alfa", "kolumna": "nowy"},
                 {"klucz": "b_stary", "wiersz": "Beta", "kolumna": "dotychczas"}])

    wiersze = pole.wiersze_sekcji

    assert [w["etykieta"] for w in wiersze] == ["Beta", "Alfa"]
    assert sorted(wiersze[0]["pola"]) == ["dotychczas", "nowy"]

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


# --- pusty wykaz nie powstaje ------------------------------------------------

def _operat_z_wykazem(klient):
    """Operat główny plus dokument dodatkowy, który bez danych nie ma sensu."""
    klient.srodowisko.dodaj_szablon(
        "spis_tresci_wzor", ["{{ nr_roboty }}"],
        opis={"nazwa": "Operat", "glowny": True,
              "pola": [{"klucz": "nr_roboty", "etykieta": "Nr roboty"},
                       {"klucz": "wykazy", "etykieta": "Wykazy", "typ": "sekcje",
                        "podpola": PODPOLA},
                       {"klucz": "dokumenty_wykazy", "etykieta": "Wygeneruj",
                        "typ": "dokumenty", "tylko": ["wykaz_wzor"]}]})
    klient.srodowisko.dodaj_szablon(
        "wykaz_wzor", ["{%p for w in wykazy %}", "{{ w.adres_nowy }}", "{%p endfor %}"],
        opis={"nazwa": "Wykaz zmian", "wymaga": "wykazy"})


def _pliki_operatu(klient) -> list[str]:
    katalog = klient.srodowisko.wyniki / db.dokumenty()[0]["katalog"]
    return sorted(p.name for p in katalog.iterdir() if p.suffix == ".docx")


def test_wykaz_bez_danych_w_ogole_nie_powstaje(klient):
    """Dokument będący samą pętlą po pustej liście wychodził jako plik bez jednej
    litery — w składaniu operatu pusty kafelek, po którym nie wiadomo, czy to usterka."""
    _operat_z_wykazem(klient)

    klient.post("/generuj/spis_tresci_wzor",
                data={"pole__nr_roboty": "GK.1", "notatka": "",
                      "pole__dokumenty_wykazy": "wykaz_wzor",
                      "sek__wykazy__0__adres_nowy": ""},
                follow_redirects=False)

    assert _pliki_operatu(klient) == ["spis_tresci.docx"]


def test_program_mowi_dlaczego_wykazu_nie_ma(klient):
    """Ciche pominięcie jest gorsze niż pusty plik: brat zaznaczył dokument i ma prawo
    wiedzieć, czemu go nie widzi."""
    _operat_z_wykazem(klient)

    odpowiedz = klient.post("/generuj/spis_tresci_wzor",
                            data={"pole__nr_roboty": "GK.1", "notatka": "",
                                  "pole__dokumenty_wykazy": "wykaz_wzor",
                                  "sek__wykazy__0__adres_nowy": ""},
                            follow_redirects=False)

    from urllib.parse import unquote
    komunikat = unquote(odpowiedz.headers["location"])
    assert "nie powstał, bo nie wypełniłeś ani jednej pozycji" in komunikat
    assert "Wykaz zmian" in komunikat, "brat ma wiedzieć, którego dokumentu to dotyczy"


def test_wykaz_z_danymi_powstaje_normalnie(klient):
    _operat_z_wykazem(klient)

    klient.post("/generuj/spis_tresci_wzor",
                data={"pole__nr_roboty": "GK.1", "notatka": "",
                      "pole__dokumenty_wykazy": "wykaz_wzor",
                      "sek__wykazy__0__adres_nowy": "Polna 7"},
                follow_redirects=False)

    assert _pliki_operatu(klient) == ["spis_tresci.docx", "wykaz.docx"]


def test_dokument_bez_deklaracji_wymaga_powstaje_zawsze(klient):
    """`wymaga` jest wpisem w `.json`, a nie regułą zgadującą po treści — dokument,
    który jej nie ma, zachowuje się dokładnie jak dotąd."""
    klient.srodowisko.dodaj_szablon(
        "spis_tresci_wzor", ["{{ nr_roboty }}"],
        opis={"nazwa": "Operat", "glowny": True,
              "pola": [{"klucz": "nr_roboty", "etykieta": "Nr roboty"},
                       {"klucz": "dokumenty_inne", "etykieta": "Wygeneruj",
                        "typ": "dokumenty", "tylko": ["notatka_wzor"]}]})
    klient.srodowisko.dodaj_szablon("notatka_wzor", ["{{ nr_roboty }}"],
                                    opis={"nazwa": "Notatka"})

    klient.post("/generuj/spis_tresci_wzor",
                data={"pole__nr_roboty": "GK.1", "notatka": "",
                      "pole__dokumenty_inne": "notatka_wzor"}, follow_redirects=False)

    assert _pliki_operatu(klient) == ["notatka.docx", "spis_tresci.docx"]


# --- spis treści jest jedynym włącznikiem dokumentów -------------------------
#
# Wcześniej pozycja w spisie treści i checkbox „Wygeneruj” w karcie dokumentu pytały
# o to samo dwa razy — dało się je ustawić sprzecznie: dokument w spisie, a pliku brak.

def _operat_ze_spisem(klient):
    klient.srodowisko.dodaj_szablon(
        "spis_tresci_wzor", ["{{ nr_roboty }}"],
        opis={"nazwa": "Operat", "glowny": True,
              "pola": [{"klucz": "nr_roboty", "etykieta": "Nr roboty"},
                       {"klucz": "spis_tresci", "etykieta": "Co wchodzi", "grupa": "Spis treści",
                        "typ": "wybor_wielokrotny",
                        "opcje": ["Spis treści", "Sprawozdanie techniczne", "Mapa"],
                        "zawsze": ["Spis treści"],
                        "dokumenty": {"Sprawozdanie techniczne": "sprawozdanie_wzor"}},
                       {"klucz": "uwagi", "etykieta": "Uwagi", "typ": "textarea",
                        "aktywne_gdy": "spis_tresci:Sprawozdanie techniczne"}]})
    klient.srodowisko.dodaj_szablon("sprawozdanie_wzor", ["{{ nr_roboty }} {{ uwagi }}"],
                                    opis={"nazwa": "Sprawozdanie techniczne"})


def test_zaznaczenie_w_spisie_tresci_generuje_dokument(klient):
    _operat_ze_spisem(klient)

    klient.post("/generuj/spis_tresci_wzor",
                data={"pole__nr_roboty": "GK.1", "notatka": "",
                      "pole__spis_tresci": "Sprawozdanie techniczne",
                      "pole__uwagi": "treść"},
                follow_redirects=False)

    assert _pliki_operatu(klient) == ["spis_tresci.docx", "sprawozdanie.docx"]


def test_brak_pozycji_w_spisie_tresci_to_brak_dokumentu(klient):
    """Sedno zmiany: nie ma osobnego „wygeneruj”, więc nie da się mieć dokumentu
    w spisie treści bez pliku ani pliku bez pozycji w spisie."""
    _operat_ze_spisem(klient)

    klient.post("/generuj/spis_tresci_wzor",
                data={"pole__nr_roboty": "GK.1", "notatka": "",
                      "pole__spis_tresci": "Mapa", "pole__uwagi": ""},
                follow_redirects=False)

    assert _pliki_operatu(klient) == ["spis_tresci.docx"]


def test_pola_dokumentu_wisza_na_pozycji_ze_spisu_tresci(klient):
    """Zaznaczenie w spisie treści ma **włączać pola** tego dokumentu."""
    _operat_ze_spisem(klient)

    formularz = klient.get("/nowy/spis_tresci_wzor").text

    assert 'data-aktywne-gdy="spis_tresci:Sprawozdanie techniczne"' in formularz


def test_dokument_ze_spisu_nie_wraca_do_karty_inne_dokumenty(klient):
    """Szablon, który ma już włącznik w spisie treści, nie może dać się włączyć
    drugi raz gdzie indziej — inaczej dwa miejsca mówiłyby co innego."""
    klient.srodowisko.dodaj_szablon(
        "spis_tresci_wzor", ["{{ nr_roboty }}"],
        opis={"nazwa": "Operat", "glowny": True,
              "pola": [{"klucz": "nr_roboty", "etykieta": "Nr roboty"},
                       {"klucz": "spis_tresci", "etykieta": "Co wchodzi",
                        "typ": "wybor_wielokrotny", "opcje": ["Sprawozdanie techniczne"],
                        "dokumenty": {"Sprawozdanie techniczne": "sprawozdanie_wzor"}},
                       {"klucz": "dokumenty", "etykieta": "Wygeneruj też",
                        "typ": "dokumenty"}]})
    klient.srodowisko.dodaj_szablon("sprawozdanie_wzor", ["{{ nr_roboty }}"],
                                    opis={"nazwa": "Sprawozdanie techniczne"})
    klient.srodowisko.dodaj_szablon("inny_wzor", ["{{ nr_roboty }}"],
                                    opis={"nazwa": "Inny dokument"})

    formularz = klient.get("/nowy/spis_tresci_wzor").text
    lista_innych = formularz.split('name="pole__dokumenty"')

    assert "Inny dokument" in formularz, "szablon bez pozycji w spisie ma zostać do wyboru"
    assert formularz.count('value="sprawozdanie_wzor"') == 0, \
        "sprawozdanie ma włącznik w spisie treści — w „Innych dokumentach” nie ma czego dublować"


# --- wykaz działki: kolejne działki to kolejne WIERSZE jednej tabeli ---------
#
# Inaczej niż przy budynku, gdzie każdy wykaz to osobna strona z własną tabelą.
# Formularz wygląda tak samo (karta na działkę), bo o formie decyduje typ pola,
# a o dokumencie — znacznik w formatce: tam `{%tr for %}` zamiast `{%p for %}`.

def _wykaz_dzialek(dzialki: list[dict]) -> Document:
    glowny = szablony.szablon_po_id("spis_tresci_wzor")
    sz = szablony.szablon_po_id("wykaz_zmian_dzialki_wzor")
    kontekst = generator.przygotuj_kontekst(
        glowny, {"nr_roboty": "G.1", "wykazy_dzialek": dzialki}, {})
    return Document(generator.dopisz_dokument(sz, kontekst,
                                              pathlib.Path(tempfile.mkdtemp())))


def test_kazda_dzialka_to_kolejny_wiersz_jednej_tabeli():
    d = _wykaz_dzialek([{"numer_dotychczas": "1765/311"},
                        {"numer_dotychczas": "1765/312"},
                        {"numer_dotychczas": "1765/99"}])

    assert len(d.tables) == 1, "działki nie mają robić kolejnych tabel ani stron"
    tabela = d.tables[0]
    assert len(tabela.rows) == 6, "trzy wiersze nagłówka plus trzy działki"
    assert [w.cells[1].text for w in tabela.rows[3:]] == ["1765/311", "1765/312", "1765/99"]


def test_lp_numeruje_sie_samo():
    """Numer porządkowy bierze się z pętli — nie ma po co pytać o niego w formularzu."""
    d = _wykaz_dzialek([{"numer_nowy": "a"}, {"numer_nowy": "b"}, {"numer_nowy": "c"}])

    assert [w.cells[0].text for w in d.tables[0].rows[3:]] == ["1", "2", "3"]


def test_oba_stany_trafiaja_do_swoich_kolumn():
    d = _wykaz_dzialek([{
        "numer_dotychczas": "1765/311", "pow_ewidencyjna_dotychczas": "0,2140",
        "ofu_dotychczas": "R", "ozu_dotychczas": "IV", "ozk_dotychczas": "a",
        "pow_uzytkow_dotychczas": "0,2140",
        "numer_nowy": "1765/312", "pow_ewidencyjna_nowy": "0,1070",
        "ofu_nowy": "B", "ozu_nowy": "V", "ozk_nowy": "b", "pow_uzytkow_nowy": "0,1070"}])

    wiersz = [c.text.strip() for c in d.tables[0].rows[3].cells]
    assert wiersz[1:7] == ["1765/311", "0,2140", "R", "IV", "a", "0,2140"]
    assert wiersz[7:13] == ["1765/312", "0,1070", "B", "V", "b", "0,1070"]


def test_jedna_dzialka_nie_zostawia_pustych_wierszy():
    """Wiersze sterujące `{%tr for %}` i `{%tr endfor %}` mają zniknąć w całości."""
    d = _wykaz_dzialek([{"numer_dotychczas": "1765/311"}])

    tabela = d.tables[0]
    assert len(tabela.rows) == 4
    assert not any("{%" in c.text for w in tabela.rows for c in w.cells)


def test_wykaz_dzialek_bez_danych_nie_powstaje():
    """Ta sama zasada co przy budynku — deklaracja `wymaga` w `.json` szablonu."""
    assert szablony.szablon_po_id("wykaz_zmian_dzialki_wzor").wymaga == "wykazy_dzialek"


def test_naglowek_tabeli_powtarza_sie_na_kolejnych_stronach():
    """Odkąd działki mogą przelać się na następną stronę, kontynuacja bez opisu kolumn
    byłaby gołymi kratkami — a ten dokument idzie do ośrodka."""
    from docx.oxml.ns import qn

    tabela = Document(str(szablony.szablon_po_id(
        "wykaz_zmian_dzialki_wzor").plik)).tables[0]

    for nr in range(3):
        trPr = tabela.rows[nr]._tr.find(qn("w:trPr"))
        assert trPr is not None and trPr.find(qn("w:tblHeader")) is not None, \
            f"wiersz nagłówka {nr} nie jest oznaczony jako powtarzany"


def test_pod_tabela_nie_ma_pustych_akapitow():
    """Puste akapity między tabelą a podpisem spychały go na osobną, pustą kartkę.

    Podpis ma iść zaraz pod tabelą i rosnąć razem z nią (decyzja brata).
    """
    from docx.oxml.ns import qn

    d = Document(str(szablony.szablon_po_id("wykaz_zmian_dzialki_wzor").plik))
    elementy = list(d.element.body)
    tabela = next(i for i, el in enumerate(elementy) if el.tag.endswith("}tbl"))
    podpis = next(i for i, el in enumerate(elementy)
                  if el.tag.endswith("}p")
                  and "Sporządził" in "".join(t.text or "" for t in el.iter(qn("w:t"))))

    assert podpis == tabela + 1, "między tabelą a podpisem nie ma prawa nic stać"

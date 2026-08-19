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


def test_kazdy_wykaz_to_osobna_tabela(baza):
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


def test_naglowek_powtarza_sie_przy_kazdym_wykazie(baza):
    """Każdy wykaz to osobna kartka do ośrodka — musi mieć swój numer roboty."""
    d = _wykaz_z_danymi([{"adres_nowy": "a"}, {"adres_nowy": "b"}])

    assert sum(1 for p in d.paragraphs if "G.1" in p.text) == 2
    assert sum(1 for p in d.paragraphs if "WYKAZ ZMIAN" in p.text) == 2


def test_lamanie_strony_miedzy_wykazami_a_nie_po_ostatnim(baza):
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


def test_wartosc_dziedziczy_krój_z_etykiety_obok(baza):
    """Wartość ma wyglądać jak opis w sąsiedniej kolumnie, a nie jak domyślna
    czcionka dokumentu — to ta sama pułapka co przy opisie przebiegu prac."""
    d = _wykaz_z_danymi([{"identyfikator_dzialki_dotychczas": "123/4"}])

    wartosc = d.tables[0].rows[1].cells[3].paragraphs[0].runs[0]
    etykieta = d.tables[0].rows[1].cells[1].paragraphs[0].runs[0]
    assert (wartosc.font.name, wartosc.font.size) == (etykieta.font.name, etykieta.font.size)


def test_formatka_nie_zostawia_niewypelnionych_znacznikow(baza):
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


# --- poprawianie operatu sprząta dokumenty odznaczone w tej rundzie ----------
#
# Poprawianie nadpisuje pliki nazwa po nazwie, więc dokument odznaczony (albo pominięty
# przez `wymaga`) zostawał w katalogu z danymi z poprzedniej rundy. Szedł potem do
# scalonego PDF-a, choć spis treści o nim milczał — a przy pustym wykazie program
# ogłaszał „nie powstał”, mając jego starą wersję na dysku.

def _wygeneruj_z_wykazem(klient) -> int:
    _operat_z_wykazem(klient)
    klient.post("/generuj/spis_tresci_wzor",
                data={"pole__nr_roboty": "GK.1", "notatka": "",
                      "pole__dokumenty_wykazy": "wykaz_wzor",
                      "sek__wykazy__0__adres_nowy": "Polna 7"},
                follow_redirects=False)
    assert _pliki_operatu(klient) == ["spis_tresci.docx", "wykaz.docx"]
    return db.dokumenty()[0]["id"]


def test_poprawianie_sprzata_odznaczony_dokument(klient):
    """Odznaczony przy poprawianiu dokument znika z katalogu razem z podglądem."""
    identyfikator = _wygeneruj_z_wykazem(klient)
    katalog = db.dokumenty()[0]["katalog"]
    podglad = klient.srodowisko.dane / "podglad" / katalog / "wykaz.pdf"
    podglad.parent.mkdir(parents=True, exist_ok=True)
    podglad.write_bytes(b"stary podglad")

    klient.post(f"/generuj/spis_tresci_wzor?edytuj={identyfikator}",
                data={"pole__nr_roboty": "GK.1", "notatka": "",
                      "sek__wykazy__0__adres_nowy": "Polna 7"},
                follow_redirects=False)

    assert _pliki_operatu(klient) == ["spis_tresci.docx"], \
        "stary wykaz został w katalogu i poszedłby do scalonego PDF-a"
    assert not podglad.exists(), "podgląd skasowanego dokumentu został w dane/podglad"


def test_poprawianie_z_oproznionym_wykazem_sprzata_stary_plik(klient):
    """Komunikat „nie powstał” nie może kłamać: stary plik z poprzednimi danymi
    ma zniknąć, skoro tym razem nie ma go z czego zrobić."""
    identyfikator = _wygeneruj_z_wykazem(klient)

    klient.post(f"/generuj/spis_tresci_wzor?edytuj={identyfikator}",
                data={"pole__nr_roboty": "GK.1", "notatka": "",
                      "pole__dokumenty_wykazy": "wykaz_wzor",
                      "sek__wykazy__0__adres_nowy": ""},
                follow_redirects=False)

    assert _pliki_operatu(klient) == ["spis_tresci.docx"]


def test_poprawianie_nie_rusza_plikow_dolozonych_recznie(klient):
    """Sprzątanie obejmuje wyłącznie nazwy nadawane przez program — mapa dołożona
    Eksploratorem, nawet jako .docx, zostaje."""
    identyfikator = _wygeneruj_z_wykazem(klient)
    katalog = klient.srodowisko.wyniki / db.dokumenty()[0]["katalog"]
    (katalog / "mapa_do_celow_projektowych.docx").write_bytes(b"od brata")

    klient.post(f"/generuj/spis_tresci_wzor?edytuj={identyfikator}",
                data={"pole__nr_roboty": "GK.1", "notatka": "",
                      "sek__wykazy__0__adres_nowy": "Polna 7"},
                follow_redirects=False)

    pliki = _pliki_operatu(klient)
    assert "mapa_do_celow_projektowych.docx" in pliki
    assert "wykaz.docx" not in pliki


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


# --- wykaz działki: każda działka to PARA WIERSZY jednej tabeli --------------
#
# Inaczej niż przy budynku, gdzie każdy wykaz to osobna strona z własną tabelą.
# Formularz wygląda tak samo (karta na działkę), bo o formie decyduje typ pola,
# a o dokumencie — znacznik w formatce: tam `{%tr for %}` zamiast `{%p for %}`.
#
# Od 19.08.2026 formatka jest **pionowa**: zamiast trzynastu kolumn (sześć na stan
# dotychczasowy i sześć na nowy, obok siebie) ma osiem, a stany leżą jeden pod drugim.

def _wykaz_dzialek(dzialki: list[dict]) -> Document:
    glowny = szablony.szablon_po_id("spis_tresci_wzor")
    sz = szablony.szablon_po_id("wykaz_zmian_dzialki_wzor")
    kontekst = generator.przygotuj_kontekst(
        glowny, {"nr_roboty": "G.1", "wykazy_dzialek": dzialki}, {})
    return Document(generator.dopisz_dokument(sz, kontekst,
                                              pathlib.Path(tempfile.mkdtemp())))


def test_kazda_dzialka_to_para_wierszy_jednej_tabeli(baza):
    d = _wykaz_dzialek([{"numer_dotychczas": "1765/311"},
                        {"numer_dotychczas": "1765/312"},
                        {"numer_dotychczas": "1765/99"}])

    assert len(d.tables) == 1, "działki nie mają robić kolejnych tabel ani stron"
    tabela = d.tables[0]
    assert len(tabela.rows) == 2 + 2 * 3, "dwa wiersze nagłówka i po dwa na działkę"
    assert [w.cells[1].text.strip() for w in tabela.rows[2:]] == \
        ["Dotychczasowy", "Nowy"] * 3
    assert [w.cells[2].text.strip() for w in tabela.rows[2:]] == \
        ["1765/311", "", "1765/312", "", "1765/99", ""]


def test_lp_numeruje_sie_samo(baza):
    """Numer porządkowy bierze się z pętli — nie ma po co pytać o niego w formularzu."""
    d = _wykaz_dzialek([{"numer_nowy": "a"}, {"numer_nowy": "b"}, {"numer_nowy": "c"}])

    # komórka L.p. jest scalona przez oba wiersze pary, więc numer powtarza się dwa razy;
    # kropka po numerze jest taka sama jak w wykazie budynku
    assert [w.cells[0].text.strip() for w in d.tables[0].rows[2:]] == \
        ["1.", "1.", "2.", "2.", "3.", "3."]


def test_oba_stany_trafiaja_do_swoich_wierszy(baza):
    d = _wykaz_dzialek([{
        "numer_dotychczas": "1765/311", "pow_ewidencyjna_dotychczas": "0,2140",
        "ofu_dotychczas": "R", "ozu_dotychczas": "IV", "ozk_dotychczas": "a",
        "pow_uzytkow_dotychczas": "0,2140",
        "numer_nowy": "1765/312", "pow_ewidencyjna_nowy": "0,1070",
        "ofu_nowy": "B", "ozu_nowy": "V", "ozk_nowy": "b", "pow_uzytkow_nowy": "0,1070"}])

    dotychczasowy = [c.text.strip() for c in d.tables[0].rows[2].cells]
    nowy = [c.text.strip() for c in d.tables[0].rows[3].cells]
    assert dotychczasowy[1:] == ["Dotychczasowy", "1765/311", "0,2140", "R", "IV", "a",
                                 "0,2140"]
    assert nowy[1:] == ["Nowy", "1765/312", "0,1070", "B", "V", "b", "0,1070"]


def test_jedna_dzialka_nie_zostawia_pustych_wierszy(baza):
    """Wiersze sterujące `{%tr for %}` i `{%tr endfor %}` mają zniknąć w całości."""
    d = _wykaz_dzialek([{"numer_dotychczas": "1765/311"}])

    tabela = d.tables[0]
    assert len(tabela.rows) == 2 + 2, "dwa wiersze nagłówka i para wierszy jednej działki"
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

    for nr in range(2):
        trPr = tabela.rows[nr]._tr.find(qn("w:trPr"))
        assert trPr is not None and trPr.find(qn("w:tblHeader")) is not None, \
            f"wiersz nagłówka {nr} nie jest oznaczony jako powtarzany"


def test_pod_tabela_jest_dokladnie_jeden_pusty_akapit():
    """Stos pustych akapitów spychał podpis na osobną, pustą kartkę — ale podpis
    przyklejony do dolnej krawędzi tabeli wyglądał źle (obejrzane na wydruku).

    Stanęło na jednym akapicie odstępu: widać, że to osobny blok, a dokument
    dalej rośnie razem z tabelą i mieści się na jednej stronie.
    """
    from docx.oxml.ns import qn

    d = Document(str(szablony.szablon_po_id("wykaz_zmian_dzialki_wzor").plik))
    elementy = list(d.element.body)
    tabela = next(i for i, el in enumerate(elementy) if el.tag.endswith("}tbl"))
    podpis = next(i for i, el in enumerate(elementy)
                  if el.tag.endswith("}p")
                  and "Sporządził" in "".join(t.text or "" for t in el.iter(qn("w:t"))))

    assert podpis == tabela + 2, "między tabelą a podpisem ma stać jeden pusty akapit"
    odstep = elementy[tabela + 1]
    assert odstep.tag.endswith("}p")
    assert not "".join(t.text or "" for t in odstep.iter(qn("w:t"))), \
        "akapit odstępu ma być pusty"


def test_pogrubienia_w_tabeli_dzialki():
    """Wytłuszczony nagłówek i kolumna „Stan", zwykłe dane — decyzja brata.

    „Dotychczasowy" i „Nowy" rozdzielają parę wierszy jednej działki, więc mają być
    mocniejsze niż liczby obok. Dane pogrubione były kiedyś w całej tabeli i to właśnie
    kazał zdjąć; pogrubienie ma odróżniać opis od treści, a nie zamalowywać kartkę.
    """
    d = Document(str(szablony.szablon_po_id("wykaz_zmian_dzialki_wzor").plik))
    tabela = d.tables[0]

    def pogrubione(komorka) -> bool:
        biegi = [b for akapit in komorka.paragraphs for b in akapit.runs if b.text.strip()]
        return bool(biegi) and all(b.bold for b in biegi)

    for wiersz in tabela.rows[:2]:
        for komorka in wiersz.cells:
            if komorka.text.strip():
                assert pogrubione(komorka), \
                    f"nagłówek {komorka.text.strip()!r} bez pogrubienia"

    dotychczasowy, nowy = tabela.rows[3], tabela.rows[4]
    assert [w.cells[1].text.strip() for w in (dotychczasowy, nowy)] == \
        ["Dotychczasowy", "Nowy"]
    assert all(pogrubione(w.cells[1]) for w in (dotychczasowy, nowy))

    pogrubione_dane = [k.text.strip() for w in (dotychczasowy, nowy)
                       for k in w.cells[2:] if pogrubione(k)]
    assert not pogrubione_dane, f"dane w tabeli wciąż pogrubione: {pogrubione_dane}"


def test_dzialki_oddziela_grubsza_kreska():
    """Bez tego dwa wiersze jednej działki zlewają się z następną parą."""
    from docx.oxml.ns import qn

    tabela = Document(str(szablony.szablon_po_id(
        "wykaz_zmian_dzialki_wzor").plik)).tables[0]

    def dolna(wiersz) -> int:
        brzegi = wiersz._tr.findall(qn("w:tc"))[1].find(qn("w:tcPr")).find(qn("w:tcBorders"))
        return int(brzegi.find(qn("w:bottom")).get(qn("w:sz")))

    assert dolna(tabela.rows[4]) > dolna(tabela.rows[3]), \
        "kreska po wierszu „Nowy” ma być grubsza niż ta wewnątrz pary"


def test_wykaz_dzialki_jest_na_pionowej_kartce():
    """Cały sens przebudowy z 19.08.2026. Tabela szersza niż tekst wychodziłaby poza
    margines i Word łamałby ją na drugą stronę — dlatego mierzymy jedno i drugie."""
    from docx.enum.section import WD_ORIENT
    from docx.oxml.ns import qn

    d = Document(str(szablony.szablon_po_id("wykaz_zmian_dzialki_wzor").plik))
    sekcja = d.sections[0]

    assert sekcja.orientation == WD_ORIENT.PORTRAIT
    assert sekcja.page_width < sekcja.page_height
    szerokosc_tekstu = int((sekcja.page_width - sekcja.left_margin
                            - sekcja.right_margin) / 914400 * 1440)
    kolumny = [int(k.get(qn("w:w"))) for k in d.tables[0]._tbl.find(qn("w:tblGrid"))]
    assert sum(kolumny) <= szerokosc_tekstu

    # W poziomej formatce (do 19.08.2026) kolumny miały: numer 851, pole 1416,
    # OFU/OZU/OZK po ~709, użytki 1701. Węższa kartka nie może oznaczać ciaśniejszych
    # kolumn — inaczej ta zmiana nie miałaby sensu.
    numer, pole, ofu, ozu, ozk, uzytki = kolumny[2:]
    assert (numer, pole, ofu, ozu, ozk, uzytki) >= (851, 1416, 709, 709, 708, 1701)


def test_liczby_porzadkowe_wykazu_budynku_stoja_na_srodku_komorki():
    """Cyfry L.p. siadały na różnych wysokościach — najbardziej w wierszach niższych.

    Winne były dwie rzeczy naraz: część akapitów miała interlinię z własnego
    ustawienia, a część brała ją ze stylu, i **znacznik końca akapitu był większy
    niż cyfra** (12 pt przy 7-punktowej cyfrze). Wyśrodkowanie w pionie centruje
    wiersz tekstu, a nie same cyfry, więc rozdmuchany znacznik podnosił je nad
    środek komórki. Zmierzone na wydruku: odchyłka do 3 pt, po poprawce ±0,7 pt.
    """
    from docx.oxml.ns import qn

    d = Document(str(szablony.szablon_po_id("wykaz_zmian_budynku_wzor").plik))
    rozmiar = lambda el: (el.find(qn("w:sz")).get(qn("w:val"))     # noqa: E731
                          if el is not None and el.find(qn("w:sz")) is not None else None)

    interlinie, znaczniki = set(), set()
    for wiersz in d.tables[0]._tbl.findall(qn("w:tr")):
        komorka = wiersz.findall(qn("w:tc"))[0]
        tcPr = komorka.find(qn("w:tcPr"))
        vAlign = tcPr.find(qn("w:vAlign")) if tcPr is not None else None
        assert vAlign is not None and vAlign.get(qn("w:val")) == "center", \
            "komórka L.p. bez wyśrodkowania w pionie"

        for akapit in komorka.findall(qn("w:p")):
            pPr = akapit.find(qn("w:pPr"))
            jc = pPr.find(qn("w:jc")) if pPr is not None else None
            assert jc is not None and jc.get(qn("w:val")) == "center", \
                "cyfra L.p. nie jest wyśrodkowana w poziomie"
            odstep = pPr.find(qn("w:spacing"))
            interlinie.add((odstep.get(qn("w:line")), odstep.get(qn("w:lineRule")))
                           if odstep is not None else None)
            znacznik = rozmiar(pPr.find(qn("w:rPr")))
            znaczniki.add(znacznik)
            bieg = akapit.find(qn("w:r"))
            if bieg is not None:
                assert znacznik == rozmiar(bieg.find(qn("w:rPr"))), \
                    "znacznik akapitu większy niż cyfra — podniesie ją nad środek"

    assert len(interlinie) == 1, f"różne interlinie w kolumnie L.p.: {interlinie}"
    assert len(znaczniki) == 1, f"różne rozmiary znaczników akapitu: {znaczniki}"


def test_identyfikator_dzialki_wchodzi_do_naglowka_wykazu():
    """Numer działki dopisuje się za identyfikatorem obrębu, przed nawiasem zamykającym.

    Jest **jeden na cały wykaz**, niezależnie od liczby wierszy w tabeli — stoi
    w nagłówku, czyli poza pętlą `{%tr for %}`.
    """
    sz = szablony.szablon_po_id("wykaz_zmian_dzialki_wzor")
    kontekst = {"nr_roboty": "G.1", "polozenie_obreb_teryt": "247301_1.0112",
                "wykaz_identyfikator_dzialki": "1765/311",
                "wykazy_dzialek": [{"numer_nowy": "a"}, {"numer_nowy": "b"}]}

    d = Document(generator.dopisz_dokument(sz, kontekst,
                                           pathlib.Path(tempfile.mkdtemp())))

    naglowek = next(p.text for p in d.paragraphs if "Identyfikator działki ewidencyjnej" in p.text)
    assert naglowek.endswith("[247301_1.0112.1765/311]")
    assert len(d.tables[0].rows) == 2 + 2 * 2, \
        "dwie działki po dwa wiersze, identyfikator poza tabelą"


def test_pusty_identyfikator_zostawia_sam_obreb_z_kropka():
    """Tak jak było przed tą zmianą — brat dopisze numer w Wordzie, gdy go nie poda."""
    sz = szablony.szablon_po_id("wykaz_zmian_dzialki_wzor")

    d = Document(generator.dopisz_dokument(
        sz, {"polozenie_obreb_teryt": "247301_1.0112", "wykaz_identyfikator_dzialki": "",
             "wykazy_dzialek": [{"numer_nowy": "a"}]},
        pathlib.Path(tempfile.mkdtemp())))

    naglowek = next(p.text for p in d.paragraphs if "Identyfikator działki ewidencyjnej" in p.text)
    assert naglowek.endswith("[247301_1.0112.]")


# --- listy wyboru w sekcji (KŚT) ---------------------------------------------

# Klasyfikacja Środków Trwałych, podgrupy 10 i 11 — słowo w słowo z rozporządzenia
# (KŚT 2016, Dz.U. 2016 poz. 1864; w KŚT 2010 te same nazwy). Brat wpisywał to z ręki,
# a nazwa rodzaju musi zgadzać się co do znaku, bo idzie do dokumentu składanego
# w ośrodku. Podgrupy 12 (rodzaje 121 i 122) **nie ma na liście**: to lokale, a nie
# budynki — geodety w wykazie zmian danych budynku nie dotyczą (decyzja brata).
KST = [
    "101 - BUDYNKI PRZEMYSŁOWE",
    "102 - BUDYNKI TRANSPORTU I ŁĄCZNOŚCI",
    "103 - BUDYNKI HANDLOWO-USŁUGOWE",
    "104 - ZBIORNIKI, SILOSY I BUDYNKI MAGAZYNOWE",
    "105 - BUDYNKI BIUROWE",
    "106 - BUDYNKI SZPITALI I INNE BUDYNKI OPIEKI ZDROWOTNEJ",
    "107 - BUDYNKI OŚWIATY, NAUKI I KULTURY ORAZ BUDYNKI SPORTOWE",
    "108 - BUDYNKI PRODUKCYJNE, USŁUGOWE I GOSPODARCZE DLA ROLNICTWA",
    "109 - POZOSTAŁE BUDYNKI NIEMIESZKALNE",
    "110 - BUDYNKI MIESZKALNE",
]


def _podpola_kst() -> list[dict]:
    pole = next(p for p in szablony.szablon_po_id("spis_tresci_wzor").pola
                if p.klucz == "wykazy_budynkow")
    return [pod for pod in pole.podpola if pod["klucz"].startswith("rodzaj_kst")]


def test_rodzaj_kst_ma_liste_z_rozporzadzenia():
    """Nazwy rodzajów muszą zgadzać się co do znaku — dokument idzie do ośrodka."""
    podpola = _podpola_kst()

    assert len(podpola) == 2, "KŚT ma być w obu stanach"
    for pod in podpola:
        assert pod["opcje"][0] == "", "pierwsza pozycja pusta — wiersz wolno zostawić bez wpisu"
        assert pod["opcje"][1:] == KST
        assert not [o for o in pod["opcje"] if o.startswith(("121", "122"))], \
            "lokale to nie budynki — podgrupa 12 nie ma czego szukać w tym wykazie"


def test_oba_stany_kst_biora_te_sama_liste():
    """Dwie kopie listy w `.json` rozjechałyby się przy pierwszej poprawce, a wykaz
    z dwiema wersjami tej samej klasyfikacji to dokument nie do przyjęcia."""
    dotychczas, nowy = _podpola_kst()

    assert dotychczas["opcje"] == nowy["opcje"]


def test_lista_wyboru_w_sekcji_to_select_a_nie_pole_tekstowe(klient):
    """Nazwa rodzaju ma 60 znaków i trzy przecinki — z ręki nikt tego nie wpisze
    bez literówki."""
    klient.srodowisko.dodaj_szablon(
        "spis_tresci_wzor", ["{{ nr_roboty }}"],
        opis={"nazwa": "Operat", "glowny": True,
              "listy": {"kst": ["", "101 - BUDYNKI PRZEMYSŁOWE", "110 - BUDYNKI MIESZKALNE"]},
              "pola": [{"klucz": "nr_roboty", "etykieta": "Nr roboty"},
                       {"klucz": "wykazy", "etykieta": "Wykazy", "typ": "sekcje",
                        "kolumny": [{"klucz": "dotychczas", "etykieta": "Stan dotychczasowy"},
                                    {"klucz": "nowy", "etykieta": "Stan nowy"}],
                        "podpola": [
                            {"klucz": "kst_dotychczas", "wiersz": "Rodzaj budynku według KŚT",
                             "kolumna": "dotychczas", "opcje": "kst"},
                            {"klucz": "kst_nowy", "wiersz": "Rodzaj budynku według KŚT",
                             "kolumna": "nowy", "opcje": "kst"},
                            {"klucz": "uwagi_nowy", "wiersz": "Uwagi", "kolumna": "nowy"}]}]})

    formularz = klient.get("/nowy/spis_tresci_wzor").text

    assert formularz.count('<option value="101 - BUDYNKI PRZEMYSŁOWE"') == 4, \
        "dwie kolumny w karcie i dwie we wzorcu do klonowania"
    assert 'name="sek__wykazy__0__uwagi_nowy"' in formularz
    assert '<input name="sek__wykazy__0__uwagi_nowy"' in formularz, \
        "podpole bez listy ma zostać zwykłym polem tekstowym"


def test_wartosc_spoza_listy_nie_ginie_przy_poprawianiu(klient):
    """Operaty sprzed tej zmiany mają w tym miejscu tekst wpisany z ręki. Samo otwarcie
    „Popraw ten operat” podstawiłoby pierwszą pozycję listy i skasowało jego wpis."""
    klient.srodowisko.dodaj_szablon(
        "spis_tresci_wzor", ["{{ nr_roboty }}"],
        opis={"nazwa": "Operat", "glowny": True,
              "listy": {"kst": ["", "101 - BUDYNKI PRZEMYSŁOWE"]},
              "pola": [{"klucz": "nr_roboty", "etykieta": "Nr roboty"},
                       {"klucz": "wykazy", "etykieta": "Wykazy", "typ": "sekcje",
                        "podpola": [{"klucz": "kst_nowy", "etykieta": "KŚT",
                                     "opcje": "kst"}]}]})
    _wyslij(klient, **{"sek__wykazy__0__kst_nowy": "budynek gospodarczy"})
    wpis = db.dokumenty()[0]

    formularz = klient.get(f"/nowy/spis_tresci_wzor?edytuj={wpis['id']}").text

    assert '<option value="budynek gospodarczy" selected>' in formularz


# --- strona operatu ----------------------------------------------------------

def _operat_z_kolumnami(klient):
    klient.srodowisko.dodaj_szablon(
        "spis_tresci_wzor", ["{{ nr_roboty }}"],
        opis={"nazwa": "Operat", "glowny": True,
              "pola": [{"klucz": "nr_roboty", "etykieta": "Nr roboty"},
                       {"klucz": "wykazy", "etykieta": "Wykazy", "typ": "sekcje",
                        "etykieta_pozycji": "Wykaz",
                        "kolumny": [{"klucz": "dotychczas", "etykieta": "Stan dotychczasowy"},
                                    {"klucz": "nowy", "etykieta": "Stan nowy"}],
                        "podpola": [
                            {"klucz": "adres_dotychczas", "wiersz": "Adres budynku",
                             "kolumna": "dotychczas"},
                            {"klucz": "adres_nowy", "wiersz": "Adres budynku",
                             "kolumna": "nowy"},
                            {"klucz": "pole_dotychczas", "wiersz": "Pole zabudowy",
                             "kolumna": "dotychczas"},
                            {"klucz": "pole_nowy", "wiersz": "Pole zabudowy",
                             "kolumna": "nowy"}]}]})


def test_strona_operatu_pokazuje_wpisane_wiersze(klient):
    """„2 wierszy” nie mówiło nic — a po to właśnie wchodzi się w gotowy operat.

    Wykazów w operacie bywa kilka, więc każdy dostaje własny nagłówek z numerem;
    inaczej nie wiadomo, który adres należy do którego budynku.
    """
    _operat_z_kolumnami(klient)

    _wyslij(klient, **{"sek__wykazy__0__adres_nowy": "Polna 7a",
                       "sek__wykazy__1__pole_dotychczas": "148",
                       "sek__wykazy__1__pole_nowy": "162"})
    strona = klient.get(f"/dokument/{db.dokumenty()[0]['id']}").text

    assert "wierszy" not in strona, "została sama liczba zamiast danych"
    assert "Polna 7a" in strona and "148" in strona and "162" in strona
    assert "Wykaz 1" in strona and "Wykaz 2" in strona
    assert strona.index("Polna 7a") < strona.index("Wykaz 2"), \
        "dane wpadły do niewłaściwego wykazu"


def test_strona_operatu_pomija_niewypelnione_atrybuty(klient):
    """Wykaz budynku ma piętnaście atrybutów, a wypełnione bywają dwa.

    Wypisywanie wszystkich dałoby ścianę kresek zasłaniającą to, co istotne.
    """
    _operat_z_kolumnami(klient)

    _wyslij(klient, **{"sek__wykazy__0__adres_nowy": "Polna 7a"})
    strona = klient.get(f"/dokument/{db.dokumenty()[0]['id']}").text

    assert "Adres budynku" in strona
    assert "Pole zabudowy" not in strona, "pusty atrybut trafił na stronę operatu"


def test_sekcja_bez_kolumn_tez_sie_pokazuje(klient):
    """Nie każda sekcja ma układ tabelaryczny — płaską wypisujemy etykietami podpól."""
    _operat_z_sekcjami(klient)          # `podpola` bez `wiersz`/`kolumna`

    _wyslij(klient, **{"sek__wykazy__0__adres_nowy": "Leśna 3"})
    strona = klient.get(f"/dokument/{db.dokumenty()[0]['id']}").text

    assert "Adres — nowy" in strona and "Leśna 3" in strona
    assert "Adres — dotychczasowy" not in strona

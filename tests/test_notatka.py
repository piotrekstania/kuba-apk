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


def test_opis_siedzi_w_tej_samej_grupie_co_dane_operatu(klient):
    """Pierwsza wersja stawiała opis w luźnym wierszu i czytał się jak osobna pozycja
    listy — brat zgłosił to od razu.

    Sprawdzamy mechanizm, który to trzyma: opis i dane są w jednym `<tbody>`, więc
    kreska rozdzielająca pozycje idzie pod grupą, a nie między nimi. Samego wyglądu
    test nie obroni, ale tę strukturę owszem — i to ona się wtedy popsuła.
    """
    _dodaj_operat(klient)
    _wyslij(klient, notatka=OPIS)

    tabela = klient.get("/").text.split(">Operaty</h")[1]
    grupa = tabela.split("<tbody")[1].split("</tbody>")[0]

    assert "Czekam na wypis z KW." in grupa, "opis wypadł poza grupę swojego operatu"
    assert "GK.6640.1.2026" in grupa, "…a to ma być ta sama grupa co dane operatu"


# --- strona operatu ----------------------------------------------------------

def test_opis_widac_po_wejsciu_w_operat(klient):
    """Druga rzecz zgłoszona przez brata: po kliknięciu w operat opisu nie było wcale."""
    _dodaj_operat(klient)
    _wyslij(klient, notatka=OPIS)
    wpis = db.dokumenty()[0]

    strona = klient.get(f"/dokument/{wpis['id']}").text

    assert "Czekam na wypis z KW." in strona
    assert "Mapę oddać do 15.09." in strona
    assert "opis-operatu" in strona


def test_opis_stoi_nad_wpisanymi_danymi(klient):
    """Kolejność sekcji na stronie operatu (decyzja brata).

    Opis to też dane operatu — tyle że wpisane dla siebie, a nie do dokumentu — więc
    idzie własną kartą tuż nad kartami z wpisanymi danymi, w tym samym stroju co one
    i co karty formularza: niebieski tytuł na krawędzi białej ramki.
    """
    _dodaj_operat(klient)
    _wyslij(klient, notatka=OPIS)
    wpis = db.dokumenty()[0]

    strona = klient.get(f"/dokument/{wpis['id']}").text

    assert strona.index("<legend>Opis</legend>") < strona.index("<legend>Dane</legend>"), \
        "opis ma stać nad kartami z wpisanymi danymi"
    assert strona.index("opis-operatu") < strona.index("<legend>Dane</legend>")
    # …a nie gdziekolwiek wyżej: nad paskiem przycisków opis też jest „nad wpisanymi
    # danymi”, a to jest właśnie miejsce, z którego go zabraliśmy
    assert strona.index('class="pasek"') < strona.index("<legend>Opis</legend>"), \
        "opis wrócił nad przyciski — sekcje mają iść po akcjach, nie przed nimi"


def test_opis_zaczyna_sie_w_tej_samej_linii_co_dane(klient):
    """Notatka stoi w tej samej siatce co wartości pól niżej.

    Zaczynała się przy lewej krawędzi karty, a wszystkie dane 190 px dalej — strona
    traciła pionową linię, wzdłuż której się ją czyta. Kolumna podpisów nie zostaje
    pusta: stoi w niej nazwa tej danej, tak samo jak przy polach z dokumentu.
    """
    _dodaj_operat(klient)
    _wyslij(klient, notatka=OPIS)

    strona = klient.get(f"/dokument/{db.dokumenty()[0]['id']}").text
    karta = strona.split("<legend>Opis</legend>")[1].split("</fieldset>")[0]

    assert '<th class="waski"' in karta, "opis poza siatką — nie trafi w kolumnę wartości"
    assert "<td>" in karta.split("opis-operatu")[0], "opis nie stoi w kolumnie wartości"
    assert ">opis</th>" in karta, "zniknął podpis kolumny przy opisie"


def test_karty_na_stronie_operatu_sa_pozamykane(klient):
    """Niedomknięta karta wciąga w siebie wszystkie następne.

    Zdarzyło się to przy przejściu z `section` na `fieldset`: zamiana objęła znacznik
    otwierający, a zamykający `</section>` został — i cała strona operatu wjechała
    do środka karty „Opis”. Testy tego nie widziały, bo sprawdzały obecność napisów,
    a nie strukturę.
    """
    _dodaj_operat(klient)
    _wyslij(klient, notatka=OPIS)

    strona = klient.get(f"/dokument/{db.dokumenty()[0]['id']}").text

    assert strona.count("<fieldset") == strona.count("</fieldset>"), \
        "karta bez zamknięcia — reszta strony wpadnie do środka"
    assert "</section>" not in strona, "została sierota po dawnym znaczniku"


def test_sciezka_katalogu_nie_krzyczy_glosniej_niz_opis(klient):
    """Ścieżka do katalogu była niebieskim pudełkiem `komunikat` — najgłośniejszą rzeczą
    na stronie, choć mówi to samo przy każdym operacie od zawsze.

    Klasa `komunikat` zostaje zarezerwowana dla rzeczy, które naprawdę się wydarzyły
    (błędy, wynik składania) — stała informacja o katalogu ma być cicha.
    """
    _dodaj_operat(klient)
    _wyslij(klient, notatka=OPIS)
    wpis = db.dokumenty()[0]

    strona = klient.get(f"/dokument/{wpis['id']}").text

    assert "wyniki\\" in strona, "ścieżka do katalogu ma zostać — brat tam wkłada mapy"
    assert 'class="komunikat"' not in strona


def test_operat_bez_opisu_nie_ma_pustej_sekcji(klient):
    """Nagłówek „Opis” nad pustką wygląda, jakby program coś zgubił."""
    _dodaj_operat(klient)
    _wyslij(klient, notatka="")
    wpis = db.dokumenty()[0]

    strona = klient.get(f"/dokument/{wpis['id']}").text

    assert "opis-operatu" not in strona


def test_opis_wraca_do_formularza_przy_poprawianiu(klient):
    """Bez tego „Popraw” kasowałby notatkę, bo formularz odesłałby puste pole."""
    _dodaj_operat(klient)
    _wyslij(klient, notatka=OPIS)
    wpis = db.dokumenty()[0]

    formularz = klient.get(f"/nowy/spis_tresci_wzor?edytuj={wpis['id']}").text

    assert "Czekam na wypis z KW." in formularz
    assert 'name="notatka"' in formularz


def test_opis_stoi_na_gorze_formularza(klient):
    """Po to najczęściej wchodzi się w operat ponownie — pod czternastoma polami
    wymagałoby to przewinięcia całego formularza (decyzja brata)."""
    _dodaj_operat(klient)

    formularz = klient.get("/nowy/spis_tresci_wzor").text

    assert formularz.index('name="notatka"') < formularz.index('name="pole__'), \
        "opis wylądował pod polami dokumentu"


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


def test_wielolinijkowe_dane_zachowuja_akapity_na_stronie_operatu(klient):
    """Opis przebiegu prac bywa kilkoma akapitami.

    Na liście „Wpisane dane” zlewały się w jeden ciąg — jedyne miejsce w programie,
    gdzie akapity naprawdę ginęły (w polu formularza i w gotowym Wordzie były całe),
    więc wyglądało to jak zgubione formatowanie w całym programie.
    """
    klient.srodowisko.dodaj_szablon(
        "spis_tresci_wzor", ["{{ nr_roboty }} {{ opis_przebiegu }}"],
        opis={"nazwa": "Operat", "glowny": True,
              "pola": [{"klucz": "nr_roboty", "etykieta": "Nr roboty"},
                       {"klucz": "opis_przebiegu", "etykieta": "Przebieg", "typ": "textarea"}]})
    klient.post("/generuj/spis_tresci_wzor",
                data={"pole__nr_roboty": "GK.1", "notatka": "",
                      "pole__opis_przebiegu": "Pierwszy akapit.\nDrugi akapit."},
                follow_redirects=False)

    strona = klient.get(f"/dokument/{db.dokumenty()[0]['id']}").text

    assert "Pierwszy akapit.\nDrugi akapit." in strona, "łamanie wierszy zniknęło z HTML-a"
    assert "wielolinijkowa" in strona, "…a bez tej klasy przeglądarka i tak je sklei"

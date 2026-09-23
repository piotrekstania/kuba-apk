"""Poprawianie operatu nie gubi tego, co brat kiedyś wpisał.

Dwie drogi, którymi dane znikały po cichu przy „Popraw”: lista wyboru, w której
zapisanej wartości nie ma już wśród opcji, i sekcja wyłączona odznaczeniem pozycji
w spisie treści — przeglądarka nie wysyła wyłączonych pól, więc zapis kasował ich
zawartość. Dokumenty mają przy tym wychodzić dokładnie takie jak dotąd: wyłączona
sekcja do dokumentu nie wchodzi.
"""
from __future__ import annotations

import json
import re
import zipfile

from app import db, main
from test_trasy import FORMULARZ, OPIS_OPERATU   # tests/ nie jest pakietem

OPIS = {
    **OPIS_OPERATU,
    "pola": OPIS_OPERATU["pola"] + [
        {"klucz": "rodzaj", "typ": "select", "opcje": ["pomiar", "wznowienie"]},
        {"klucz": "sprawozdanie", "typ": "checkbox", "etykieta": "Sprawozdanie"},
        {"klucz": "opis_prac", "etykieta": "Opis prac", "aktywne_gdy": "sprawozdanie"},
        {"klucz": "spis", "typ": "wybor_wielokrotny", "opcje": ["Mapa", "Wykaz"],
         "zawsze": ["Mapa"]},
        {"klucz": "wykaz_uwagi", "etykieta": "Uwagi do wykazu", "aktywne_gdy": "spis:Wykaz"},
        {"klucz": "wykaz_zmiany", "typ": "checkbox", "etykieta": "Zmiany",
         "aktywne_gdy": "spis:Wykaz"},
        {"klucz": "wykaz_szczegoly", "etykieta": "Szczegóły", "aktywne_gdy": "wykaz_zmiany"},
    ]}
AKAPITY = ["Robota: {{ nr_roboty }}", "Rodzaj: {{ rodzaj }}", "Opis: {{ opis_prac }}",
           "Uwagi: {{ wykaz_uwagi }}", "Szczegóły: {{ wykaz_szczegoly }}"]


def _szablon(klient):
    klient.srodowisko.dodaj_szablon("spis_tresci_wzor", AKAPITY, opis=OPIS)


def _tekst(klient, wpis) -> str:
    plik = klient.srodowisko.wyniki / wpis["katalog"] / "spis_tresci.docx"
    with zipfile.ZipFile(plik) as archiwum:
        return re.sub(r"<[^>]+>", "", archiwum.read("word/document.xml").decode("utf-8"))


def _wartosc_pola(strona: str, nazwa: str) -> str | None:
    znalezione = re.search(r'name="pole__' + nazwa + r'"[^>]*value="([^"]*)"', strona)
    return znalezione.group(1) if znalezione else None


# --- lista wyboru -------------------------------------------------------------

def test_wartosc_listy_spoza_opcji_zostaje_przy_poprawianiu(klient):
    """Opcje listy siedzą w `.json` formatki i zmieniają się z wersjami programu.
    Wartość zapisana kiedyś, której dziś na liście nie ma, ginęła przy samym otwarciu
    „Popraw”: przeglądarka zaznaczała pierwszą opcję i zapis ją utrwalał. Pole w karcie
    sekcji zachowywało ją od dawna — zwykła lista nie."""
    _szablon(klient)
    klient.post("/generuj/spis_tresci_wzor", follow_redirects=False,
                data={**FORMULARZ, "pole__rodzaj": "pomiar"})
    wpis = db.dokumenty()[0]
    dane = json.loads(wpis["dane_json"])
    dane["rodzaj"] = "podział"                         # wartość sprzed zmiany listy
    db.zaktualizuj_dokument(wpis["id"], wpis["tytul"], dane, wpis["plik_docx"],
                            wpis["katalog"], "")

    strona = klient.get(f"/nowy/spis_tresci_wzor?edytuj={wpis['id']}").text

    lista = strona.split('name="pole__rodzaj"')[1].split("</select>")[0]
    assert '<option value="podział" selected>' in lista
    assert lista.count("selected") == 1


# --- sekcje wyłączone odznaczeniem ---------------------------------------------

def test_odznaczona_sekcja_nie_traci_danych_przy_poprawianiu(klient):
    """Brat odznacza „Sprawozdanie”, zapisuje — i przy następnym „Popraw” opisu prac
    już nie było: wyłączonego pola przeglądarka nie wysyła, a zapis nadpisywał dane
    tym, co przyszło. Teraz dane wyłączonej sekcji zostają w historii, a gdy zaznaczy
    ją z powrotem, formularz ma je na miejscu. Do dokumentu dalej nie wchodzą."""
    _szablon(klient)
    klient.post("/generuj/spis_tresci_wzor", follow_redirects=False,
                data={**FORMULARZ, "pole__sprawozdanie": "on", "pole__opis_prac": "Pomiar"})
    wpis = db.dokumenty()[0]
    assert "Opis: Pomiar" in _tekst(klient, wpis)

    # tak wysyła przeglądarka: bez odznaczonego przełącznika i bez wyłączonego pola
    odpowiedz = klient.post(f"/generuj/spis_tresci_wzor?edytuj={wpis['id']}",
                            data=FORMULARZ, follow_redirects=False)

    assert odpowiedz.status_code == 303
    assert "Pomiar" not in _tekst(klient, wpis), "wyłączona sekcja weszła do dokumentu"
    assert json.loads(db.dokument(wpis["id"])["dane_json"])["opis_prac"] == "Pomiar"
    # `operat.json` ma przeżyć utratę bazy, więc mówi to samo co historia
    opis = klient.srodowisko.wyniki / wpis["katalog"] / "operat.json"
    assert json.loads(opis.read_text(encoding="utf-8"))["dane"]["opis_prac"] == "Pomiar"
    strona = klient.get(f"/nowy/spis_tresci_wzor?edytuj={wpis['id']}").text
    assert _wartosc_pola(strona, "opis_prac") == "Pomiar"


def test_pole_przyslane_przez_przegladarke_nie_jest_zastepowane(klient):
    """Zachowujemy wyłącznie to, czego przeglądarka nie przysłała. Gdy pole przyszło —
    choćby puste, bo przeglądarka bez skryptów niczego nie wyszarza — brat mógł je
    świadomie wyczyścić i zapisujemy to, co przyszło, a nie starą wartość."""
    _szablon(klient)
    klient.post("/generuj/spis_tresci_wzor", follow_redirects=False,
                data={**FORMULARZ, "pole__sprawozdanie": "on", "pole__opis_prac": "Pomiar"})
    wpis = db.dokumenty()[0]

    klient.post(f"/generuj/spis_tresci_wzor?edytuj={wpis['id']}", follow_redirects=False,
                data={**FORMULARZ, "pole__opis_prac": ""})

    assert not json.loads(db.dokument(wpis["id"])["dane_json"]).get("opis_prac")


def test_formularz_po_bledzie_ma_dane_wylaczonej_sekcji(klient):
    """Po „Uzupełnij wymagane pola” formularz wraca z tym, co przyszło — a wyłączonej
    sekcji przeglądarka nie przysłała. Gdyby wróciła pusta, brat zaznaczyłby pozycję
    z powrotem i zobaczył, że opis zniknął, choć w historii nadal jest."""
    _szablon(klient)
    klient.post("/generuj/spis_tresci_wzor", follow_redirects=False,
                data={**FORMULARZ, "pole__sprawozdanie": "on", "pole__opis_prac": "Pomiar"})
    wpis = db.dokumenty()[0]

    strona = klient.post(f"/generuj/spis_tresci_wzor?edytuj={wpis['id']}",
                         data={**FORMULARZ, "pole__nr_roboty": ""}).text

    assert "Uzupełnij wymagane pola" in strona
    assert _wartosc_pola(strona, "opis_prac") == "Pomiar"


def test_strona_operatu_nie_pokazuje_danych_wylaczonej_sekcji(klient):
    """Zachowane dane nie wchodzą do dokumentu, więc strona operatu, która mówi, co w nim
    jest, też ich nie pokazuje — inaczej brat szukałby w dokumencie opisu, którego tam nie ma."""
    _szablon(klient)
    klient.post("/generuj/spis_tresci_wzor", follow_redirects=False,
                data={**FORMULARZ, "pole__sprawozdanie": "on", "pole__opis_prac": "Pomiar"})
    wpis = db.dokumenty()[0]
    assert "Pomiar" in klient.get(f"/dokument/{wpis['id']}").text

    klient.post(f"/generuj/spis_tresci_wzor?edytuj={wpis['id']}", data=FORMULARZ,
                follow_redirects=False)

    assert "Pomiar" not in klient.get(f"/dokument/{wpis['id']}").text


def test_dane_sekcji_pozycji_spisu_i_lancuch_przelacznikow_zostaja(klient):
    """To samo dla pozycji spisu treści (`spis:Wykaz`) i dla łańcucha: przełącznik,
    który sam jest wyłączony, liczy się jak odznaczony (tak samo jak w przeglądarce),
    więc zależne od niego pole też zachowuje dane."""
    _szablon(klient)
    klient.post("/generuj/spis_tresci_wzor", follow_redirects=False, data={
        **FORMULARZ, "pole__spis": "Wykaz", "pole__wykaz_uwagi": "Dwa budynki",
        "pole__wykaz_zmiany": "on", "pole__wykaz_szczegoly": "Nowa bryła"})
    wpis = db.dokumenty()[0]

    klient.post(f"/generuj/spis_tresci_wzor?edytuj={wpis['id']}", data=FORMULARZ,
                follow_redirects=False)

    zapisane = json.loads(db.dokument(wpis["id"])["dane_json"])
    assert zapisane["wykaz_uwagi"] == "Dwa budynki"
    assert zapisane["wykaz_zmiany"] is True and zapisane["wykaz_szczegoly"] == "Nowa bryła"
    tekst = _tekst(klient, wpis)
    assert "Dwa budynki" not in tekst and "Nowa bryła" not in tekst


def test_pole_aktywne_czyta_przelaczniki_jak_przegladarka():
    """Serwer musi rozstrzygać o aktywności tak samo jak skrypt formularza — inaczej
    zachowałby dane pól, które przeglądarka wysłała, albo zgubił te, których nie wysłała.
    Pozycja „zawsze” jest w formularzu wyłączona (zaznaczona na stałe), więc skrypt
    traktuje ją jak odznaczoną; nieznany przełącznik niczego nie wyłącza."""
    from app import szablony

    pola = {p["klucz"]: szablony.Pole(etykieta=p["klucz"], **{
                k: v for k, v in p.items()
                if k in ("klucz", "typ", "opcje", "zawsze", "aktywne_gdy")})
            for p in OPIS["pola"]}
    szablon = szablony.Szablon(id="x", plik=None, nazwa="x", pola=list(pola.values()))
    aktywne = lambda klucz, dane: main._pole_aktywne(szablon, pola[klucz], dane)  # noqa: E731

    assert aktywne("opis_prac", {"sprawozdanie": True})
    assert not aktywne("opis_prac", {"sprawozdanie": False})
    assert aktywne("wykaz_uwagi", {"spis": ["Mapa", "Wykaz"]})
    assert not aktywne("wykaz_uwagi", {"spis": ["Mapa"]})
    assert not aktywne("wykaz_szczegoly", {"spis": ["Mapa"], "wykaz_zmiany": True})
    assert aktywne("wykaz_szczegoly", {"spis": ["Wykaz"], "wykaz_zmiany": True})
    zawsze = szablony.Pole(klucz="z", etykieta="z", aktywne_gdy="spis:Mapa")
    assert not main._pole_aktywne(szablon, zawsze, {"spis": ["Mapa"]})
    obcy = szablony.Pole(klucz="o", etykieta="o", aktywne_gdy="nie_ma_takiego")
    assert main._pole_aktywne(szablon, obcy, {})


def test_poprawka_przy_danych_niebedacych_slownikiem(klient):
    """Pułapka 36: poprawny JSON to nie zawsze słownik. Wpis z `null` w danych (ręczna
    edycja bazy, przerwany zapis) nie może wywracać poprawki — zachowywać nie ma czego."""
    _szablon(klient)
    klient.post("/generuj/spis_tresci_wzor", follow_redirects=False, data=FORMULARZ)
    wpis = db.dokumenty()[0]
    with db.polaczenie() as polaczenie:
        polaczenie.execute("UPDATE dokumenty SET dane_json = 'null' WHERE id = ?", (wpis["id"],))

    odpowiedz = klient.post(f"/generuj/spis_tresci_wzor?edytuj={wpis['id']}", data=FORMULARZ,
                            follow_redirects=False)

    assert odpowiedz.status_code == 303

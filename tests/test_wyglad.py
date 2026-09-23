"""Kolor programu (motywy w Ustawieniach), ikony w przyciskach i zakładka „tu jesteś”.

Najważniejszy test w tym pliku to `test_kolor_nie_zmienia_dokumentow`: wygląd okna
programu nie ma prawa dotknąć tego, co idzie do ośrodka.
"""
from __future__ import annotations

import re
import zipfile
from urllib.parse import unquote

import pytest

import jinja2

from app import db, main, wyglad
from app.config import WEB
from test_trasy import FORMULARZ, _dodaj_operat, _prawdziwy_pdf   # tests/ nie jest pakietem


def _klasa_body(strona: str) -> str:
    znalezione = re.search(r'<body class="([^"]*)"', strona)
    assert znalezione, "strona nie ma klasy motywu na <body>"
    return znalezione.group(1)


def _zapisz_kolor(klient, klucz: str):
    return klient.post("/ustawienia/wyglad", data={"motyw": klucz}, follow_redirects=False)


# --- wybór koloru ------------------------------------------------------------

def test_bez_wyboru_program_jest_niebieski(klient):
    assert _klasa_body(klient.get("/").text) == "motyw-niebieski"


def test_wybrany_kolor_obowiazuje_na_kazdej_stronie(klient):
    """Kolor wybrany raz ma być wszędzie — także na stronie błędu, bo to ona
    powinna wyglądać najbardziej „jak program”, a nie jak goły komunikat."""
    _dodaj_operat(klient)

    odpowiedz = _zapisz_kolor(klient, "zielony")

    assert odpowiedz.status_code == 303
    # bez kotwicy: przewinięcie do karty chowało komunikat nad krawędzią okna
    assert odpowiedz.headers["location"].startswith("/ustawienia?komunikat=")
    assert "#" not in odpowiedz.headers["location"]
    for adres in ("/", "/nowy/spis_tresci_wzor", "/ustawienia", "/pomoc", "/pomoc/historia",
                  "/nie-ma-takiej-strony"):
        assert _klasa_body(klient.get(adres).text) == "motyw-zielony", adres


def test_kolor_przezywa_ponowne_uruchomienie(klient):
    """Wybór leży na dysku, a nie w pamięci serwera — brat zamyka program codziennie."""
    _zapisz_kolor(klient, "morski")

    assert wyglad.PLIK.read_text(encoding="utf-8").strip() == "morski"
    assert wyglad.biezacy() == "morski"


def test_ustawienia_pokazuja_szesc_probek_z_zaznaczonym_wyborem(klient):
    _zapisz_kolor(klient, "fioletowy")

    strona = klient.get("/ustawienia").text

    karta = strona.split('<fieldset id="wyglad">')[1].split("</fieldset>")[0]
    for klucz, nazwa in wyglad.MOTYWY.items():
        assert f'class="motyw-probka motyw-{klucz}"' in karta, f"brak próbki {klucz}"
        assert nazwa in karta
    assert len(wyglad.MOTYWY) == 6
    zaznaczone = re.findall(r'value="(\w+)" checked', karta)
    assert zaznaczone == ["fioletowy"]


def test_nieznany_kolor_nie_psuje_wyboru(klient):
    """Ręcznie sklejony adres albo stara zakładka z nieistniejącym kolorem — komunikat
    po polsku, a dotychczasowy wybór zostaje."""
    _zapisz_kolor(klient, "pomaranczowy")

    odpowiedz = _zapisz_kolor(klient, "tęczowy")

    assert odpowiedz.status_code == 303
    assert "blad=" in odpowiedz.headers["location"]
    assert _klasa_body(klient.get("/").text) == "motyw-pomaranczowy"


def test_nieudany_zapis_koloru_mowi_co_sprawdzic_i_nie_zostawia_smieci(klient, monkeypatch):
    """Windows nie podmieni pliku z atrybutem „tylko do odczytu” (np. `dane` odtworzone
    z kopii na płycie) — `PermissionError`. Brat ma dostać komunikat, który mówi,
    co sprawdzić, dotychczasowy kolor ma zostać, a w `dane/` nie może zostać plik
    tymczasowy, który przy każdej kolejnej próbie leżałby tam dalej."""
    _zapisz_kolor(klient, "zielony")

    def odmowa(self, cel):
        raise PermissionError(13, "Odmowa dostępu")

    # `context()`, a nie `undo()`: to drugie cofnęłoby też podmienione przez fixture
    # ścieżki i dalsza część testu czytałaby prawdziwe `dane/`
    with monkeypatch.context() as podmiana:
        podmiana.setattr(type(wyglad.PLIK), "replace", odmowa)
        odpowiedz = _zapisz_kolor(klient, "morski")

    assert odpowiedz.status_code == 303
    adres = unquote(odpowiedz.headers["location"])
    assert "blad=" in adres and "tylko do odczytu" in adres and "motyw.txt" in adres
    assert wyglad.biezacy() == "zielony"
    assert [p.name for p in wyglad.PLIK.parent.iterdir() if p.name.startswith("motyw")] == ["motyw.txt"]


@pytest.mark.parametrize("zawartosc", [b"", b"\xff\xfe\x00zepsute", "zółty".encode()])
def test_zepsuty_plik_koloru_daje_kolor_domyslny(klient, zawartosc):
    """Plik z koloru czyta każda strona, także strona błędu — śmieci w nim nie mogą
    zabrać bratu programu."""
    wyglad.PLIK.write_bytes(zawartosc)

    strona = klient.get("/")

    assert strona.status_code == 200
    assert _klasa_body(strona.text) == "motyw-niebieski"


def test_kazdy_motyw_ma_palete_w_arkuszu():
    """Lista kolorów siedzi w Pythonie, a same kolory w CSS-ie. Motyw bez palety
    po cichu wyglądałby jak domyślny — brat wybrałby zielony i zobaczył niebieski."""
    style = (WEB / "static" / "style.css").read_text(encoding="utf-8")

    for klucz in wyglad.MOTYWY:
        znalezione = re.search(r"\.motyw-" + klucz + r"\s*\{([^}]*)\}", style)
        assert znalezione, f"brak palety .motyw-{klucz} w style.css"
        for zmienna in ("--tlo", "--akcent", "--akcent-kontener", "--na-akcent-kontenerze",
                        "--drugi-kontener", "--panel-sredni", "--tekst", "--szary"):
            assert zmienna + ":" in znalezione.group(1), f"motyw {klucz} bez {zmienna}"


def _czesci_dokumentu(sciezka) -> dict[str, bytes]:
    with zipfile.ZipFile(sciezka) as archiwum:
        return {nazwa: archiwum.read(nazwa) for nazwa in archiwum.namelist()}


def test_kolor_nie_zmienia_dokumentow(klient):
    """Wygląd okna i dokument dla ośrodka to dwie osobne rzeczy — i mają takie zostać.

    Wszystko z tabeli `ustawienia` trafia do danych formatek Worda
    (`generator.przygotuj_kontekst`), więc kolor zapisany tam dojechałby do dokumentu.
    Sprawdzamy na efekcie, a nie na budowie: ten sam operat poprawiony po zmianie
    koloru daje dokument identyczny co do bajtu w każdej części pliku.
    """
    _dodaj_operat(klient)
    klient.post("/generuj/spis_tresci_wzor", data=FORMULARZ, follow_redirects=False)
    wpis = db.dokumenty()[0]
    katalog = klient.srodowisko.wyniki / wpis["katalog"]
    przed = {plik.name: _czesci_dokumentu(plik) for plik in katalog.glob("*.docx")}
    assert przed, "nie powstał żaden dokument"
    ustawienia_przed = db.wczytaj_ustawienia()

    _zapisz_kolor(klient, "grafitowy")
    # Tabela `ustawienia` to dane formatek, więc nie może się zmienić w ogóle — samo
    # porównanie dokumentów by tego nie złapało: żadna formatka nie ma znacznika
    # z kolorem, więc kolor zapisany w tabeli przeszedłby przez nie bez śladu
    assert db.wczytaj_ustawienia() == ustawienia_przed
    klient.post(f"/generuj/spis_tresci_wzor?edytuj={wpis['id']}", data=FORMULARZ,
                follow_redirects=False)

    po = {plik.name: _czesci_dokumentu(plik) for plik in katalog.glob("*.docx")}
    assert po == przed


# --- zakładka „tu jesteś” ----------------------------------------------------

def _aktywne(strona: str) -> list[str]:
    naglowek = strona.split("<header>")[1].split("</header>")[0]
    return re.findall(r'class="aktywny"[^>]*>([^<]+)<', naglowek)


def test_swieci_zakladka_strony_na_ktorej_jestes(klient):
    _dodaj_operat(klient)

    assert _aktywne(klient.get("/").text) == ["Dokumenty"]
    assert _aktywne(klient.get("/nowy/spis_tresci_wzor").text) == ["Dokumenty"]
    assert _aktywne(klient.get("/ustawienia").text) == ["Ustawienia"]
    assert _aktywne(klient.get("/pomoc").text) == ["Pomoc"]
    assert _aktywne(klient.get("/pomoc/historia").text) == ["Pomoc"]
    assert _aktywne(klient.get("/nie-ma-takiej-strony").text) == []


# --- ikony -------------------------------------------------------------------

def _ikona(nazwa: str) -> str:
    return str(main.widoki.env.get_template("_ikony.html").module.ikona(nazwa))


def test_ikona_to_ozdoba_schowana_przed_czytnikiem_ekranu():
    znacznik = _ikona("zapisz")

    assert znacznik.startswith('<svg class="ik"') and znacznik.endswith("</svg>")
    assert 'aria-hidden="true"' in znacznik
    assert "<path" in znacznik


def test_kazda_ikona_wolana_w_szablonach_ma_ksztalt():
    """Literówka w nazwie ikony dałaby pusty przycisk — i wyszłaby dopiero u brata.
    Makro nie może rzucić wyjątkiem (patrz niżej, stary proces), więc pilnuje test."""
    szablony = WEB / "templates"
    ksztalty = set(re.findall(r'^\s*"(\w+)": \'', (szablony / "_ikony.html").read_text(encoding="utf-8"),
                              re.MULTILINE))
    wolane = {nazwa for plik in szablony.glob("*.html")
              for nazwa in re.findall(r"ikona\(\s*'(\w+)'", plik.read_text(encoding="utf-8"))}
    # wywołanie z wyrażeniem (base.html: stan konwertera) — obie gałęzie wypisane wprost
    wolane |= {"ok", "uwaga"}

    assert len(wolane) > 10, "test nie znalazł wywołań ikon — zmienił się zapis?"
    assert wolane <= ksztalty, f"brak kształtu dla: {sorted(wolane - ksztalty)}"


def test_szablony_nie_polegaja_na_nowych_funkcjach_z_pythona():
    """Aktualizacja podmienia szablony także pod działającym jeszcze programem (brat
    zostawia go w schowanym oknie i klika skrót drugi raz), a Jinja w starym procesie
    sama wczytuje zmienione pliki. Szablon wołający funkcję, której stary proces nie
    zna, wywracał mu wtedy każdą stronę, łącznie ze stroną błędu — tak byłoby z `ikona()`
    jako funkcją z Pythona. Rzeczy pomocnicze dla szablonów mają być makrami."""
    domyslne = set(jinja2.Environment().globals) | {"url_for"}

    assert set(main.widoki.env.globals) - domyslne == {"POLA_DZIALKI"}


def test_stary_proces_z_nowymi_szablonami_nie_wywraca_stron(klient, monkeypatch):
    """Ten sam przypadek z drugiej strony: nowe szablony z kontekstem, jaki podaje stary
    proces — bez koloru i bez listy motywów. Każda strona ma przyjść cała (ze stylami
    i menu), a nie jako goły komunikat awaryjny."""
    _dodaj_operat(klient)
    prawdziwy = main.widoki.TemplateResponse

    def jak_stary_proces(request, nazwa, kontekst, **reszta):
        kontekst = {k: v for k, v in kontekst.items() if k not in ("motyw", "motywy")}
        return prawdziwy(request, nazwa, kontekst, **reszta)

    monkeypatch.setattr(main.widoki, "TemplateResponse", jak_stary_proces)
    for adres in ("/", "/nowy/spis_tresci_wzor", "/ustawienia", "/pomoc", "/nie-ma-takiej-strony"):
        strona = klient.get(adres).text
        assert strona.lstrip().lower().startswith("<!doctype html>"), adres
        assert "style.css" in strona and "<header>" in strona, adres
        assert "Coś poszło nie tak" not in strona, adres


def test_glowne_przyciski_maja_ikony(klient):
    _dodaj_operat(klient)

    lista = klient.get("/").text
    formularz = klient.get("/nowy/spis_tresci_wzor").text

    assert re.search(r'<a class="glowny" href="/nowy/spis_tresci_wzor"><svg class="ik".*?</svg>'
                     r"Nowy operat</a>", lista, re.DOTALL)
    assert formularz.count('<svg class="ik"') >= 2
    assert formularz.count(">Zapisz<") == 2


def test_przyciski_kafelkow_maja_opisy_i_obie_ikony_pomijania(klient, bez_konwertera):
    """Przycisk z samą ikoną musi mieć opis dla czytnika ekranu i dymek. „Pomiń”
    ma w sobie obie ikony (krzyżyk i strzałkę powrotu) — którą widać, przełącza sama
    klasa kafelka, więc skrypt nie musi znać żadnego rysunku."""
    _dodaj_operat(klient)
    klient.post("/generuj/spis_tresci_wzor", data=FORMULARZ, follow_redirects=False)
    wpis = db.dokumenty()[0]

    strona = klient.get(f"/scal/{wpis['katalog']}").text

    assert 'aria-label="Obróć w lewo"' in strona and 'aria-label="Obróć w prawo"' in strona
    kafelek = strona.split('class="pomin"')[1].split("</button>")[0]
    assert 'class="gdy-dolaczony"' in kafelek and 'class="gdy-pominiety"' in kafelek
    assert "closest('button')" in strona, "kliknięcie w ikonę nie trafi w przycisk"


def test_pelna_nazwa_pliku_zostaje_w_dymku(klient, bez_konwertera):
    """Na kafelku nazwa kończy się po dwóch linijkach wielokropkiem — pełna nie może
    zniknąć bez śladu, więc cała jest w `title` (dymek po najechaniu myszą)."""
    _dodaj_operat(klient)
    klient.post("/generuj/spis_tresci_wzor", data=FORMULARZ, follow_redirects=False)
    wpis = db.dokumenty()[0]
    dluga = "wykaz_wspolrzednych_punktow_szczegolow_terenowych_eksport_z_C-Geo.pdf"
    _prawdziwy_pdf(klient.srodowisko.wyniki / wpis["katalog"] / dluga)

    strona = klient.get(f"/scal/{wpis['katalog']}").text

    assert f'<p class="kafelek-nazwa" title="{dluga}">' in strona

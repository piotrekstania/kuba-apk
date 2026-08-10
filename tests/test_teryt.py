"""Jednostki TERYT z GUS-u i obręby z ULDK.

Sprawdzanie numeru działki ma własny plik (`test_uldk.py`) — tutaj jest reszta:
pobranie pliku TERC, czytanie go, cache obrębów i pobieranie hurtowe.

Trzy rzeczy, na których ten moduł może się wyłożyć po cichu, i dlatego mają tu
osobne testy:

* **GUS oddaje stronę zamiast ZIP-a** — pobieranie stoi na przycisku ASP.NET
  (`__VIEWSTATE` + `__EVENTTARGET`), więc przebudowa strony przestawi je bez
  ostrzeżenia. Program ma wtedy powiedzieć to po polsku i **zostawić w bazie to,
  co już ma**, a nie wywalić się z pustą tabelą.
* **gmina miejsko-wiejska (RODZ=3)** nie jest jednostką ewidencyjną i nie wolno jej
  wpuścić do bazy — ULDK oddaje dla niej niepełną listę obrębów, czyli objaw byłby
  „obrębu nie ma na liście", a nie błąd.
* **przerwane pobieranie hurtowe** ma zostawić pasek postępu przed końcem; dobity
  do stu procent wygląda jak udane pobranie.

Sieci tu nie ma — odpowiedzi GUS-u i ULDK są podstawiane.
"""
from __future__ import annotations

import io
import threading
import zipfile

import pytest

from app import db, teryt

# Fixture `srodowisko` podmienia `generator.teryt.jednostka` i `.obreb` na atrapy, żeby
# generator nie potrzebował bazy TERYT — a `generator.teryt` to **ten sam moduł**, więc
# atrapa obowiązuje wszędzie. Prawdziwe funkcje bierzemy tu przy imporcie pliku, czyli
# zanim fixture zdąży cokolwiek podmienić.
PRAWDZIWA_JEDNOSTKA = teryt.jednostka
PRAWDZIWY_OBREB = teryt.obreb

NAGLOWEK = "WOJ;POW;GMI;RODZ;NAZWA;NAZWA_DOD;STAN_NA"

# Fragment prawdziwego układu TERC: województwo, powiat i komplet rodzajów gmin.
# Nowy Wiśnicz jest gminą miejsko-wiejską, więc w ewidencji istnieje wyłącznie jako
# miasto (4) i obszar wiejski (5) — wiersz z RODZ=3 jest tu po to, żeby sprawdzić,
# że go pomijamy.
WIERSZE_TERC = [
    "12;;;;MAŁOPOLSKIE;województwo;2026-01-01",
    "12;01;;;bocheński;powiat;2026-01-01",
    "12;01;01;1;Bochnia;gmina miejska;2026-01-01",
    "12;01;02;2;Bochnia;gmina wiejska;2026-01-01",
    "12;01;03;3;Nowy Wiśnicz;gmina miejsko-wiejska;2026-01-01",
    "12;01;03;4;Nowy Wiśnicz;miasto;2026-01-01",
    "12;01;03;5;Nowy Wiśnicz;obszar wiejski;2026-01-01",
]


def _paczka_terc(wiersze: list[str] = None) -> bytes:
    """ZIP taki, jaki oddaje GUS: jeden plik CSV ze średnikami."""
    bufor = io.BytesIO()
    with zipfile.ZipFile(bufor, "w") as archiwum:
        archiwum.writestr(
            "TERC_Urzedowy_2026-01-01.csv",
            "\n".join([NAGLOWEK] + (WIERSZE_TERC if wiersze is None else wiersze))
            .encode("utf-8-sig"))
    return bufor.getvalue()


class _Odpowiedz(io.BytesIO):
    """Minimum tego, czego używa `urlopen` — raz przez `with`, raz przez `.read()`."""

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


class _Otwieracz:
    """Udaje `build_opener()`: GET oddaje stronę, POST — to, co GUS przysłał w odpowiedzi."""

    def __init__(self, strona: str, odpowiedz: bytes):
        self.strona, self.odpowiedz = strona, odpowiedz
        self.wyslane: bytes = b""

    def open(self, cel, timeout=None):
        if isinstance(cel, str):
            return _Odpowiedz(self.strona.encode("utf-8"))
        self.wyslane = cel.data
        return _Odpowiedz(self.odpowiedz)


STRONA_GUS = (
    '<html><form>'
    '<input type="hidden" name="__VIEWSTATE" id="__VIEWSTATE" value="/wEPDwUKMTQ4&amp;xyz" />'
    '<input type="hidden" name="__VIEWSTATEGENERATOR" id="__VIEWSTATEGENERATOR" value="CA0B0334" />'
    '<input type="hidden" name="__EVENTVALIDATION" id="__EVENTVALIDATION" value="/wEdAAY" />'
    '</form></html>'
)


def _podstaw_gus(monkeypatch, odpowiedz: bytes, strona: str = STRONA_GUS) -> _Otwieracz:
    otwieracz = _Otwieracz(strona, odpowiedz)
    monkeypatch.setattr(teryt.urllib.request, "build_opener", lambda *_: otwieracz)
    return otwieracz


@pytest.fixture(autouse=True)
def czysty_postep():
    """Postęp pobierania hurtowego jest globalny — test nie może go zostawić następnemu."""
    poprzedni = dict(teryt._postep)
    yield
    teryt._stop.clear()
    with teryt._zamek:
        teryt._postep.clear()
        teryt._postep.update(poprzedni)


# --- pobranie pliku z GUS-u --------------------------------------------------

def test_pobranie_odsyla_viewstate_i_nazwe_przycisku(srodowisko, monkeypatch):
    """Bez `__VIEWSTATE` ASP.NET odrzuci POST, a bez `__EVENTTARGET` odda samą stronę."""
    otwieracz = _podstaw_gus(monkeypatch, _paczka_terc())

    teryt.aktualizuj_jednostki()

    wyslane = otwieracz.wyslane.decode()
    assert "__EVENTTARGET=ctl00%24body%24BTERCUrzedowyPobierz" in wyslane
    assert "%2FwEPDwUKMTQ4%26xyz" in wyslane, "encje HTML w polu muszą być odkodowane"
    assert "CA0B0334" in wyslane and "%2FwEdAAY" in wyslane


def test_strona_zamiast_pliku_nie_kasuje_tego_co_juz_mamy(srodowisko, monkeypatch):
    """Najgorszy możliwy wynik zmiany na stronie GUS-u: pusta baza i angielski wyjątek.

    Ma być odwrotnie — polski komunikat i nietknięte dane, bo program działa
    w terenie właśnie z tego, co pobrał wcześniej.
    """
    _podstaw_gus(monkeypatch, _paczka_terc())
    teryt.aktualizuj_jednostki()
    przed = teryt.stan()["gmin"]

    _podstaw_gus(monkeypatch, b"<html>Przerwa techniczna</html>")
    with pytest.raises(teryt.BladPobierania) as awaria:
        teryt.aktualizuj_jednostki()

    assert "GUS zmienił sposób pobierania" in str(awaria.value)
    assert teryt.stan()["gmin"] == przed, "stare jednostki mają zostać w bazie"


def test_brak_internetu_mowi_po_polsku(srodowisko, monkeypatch):
    class _Padnietyd:
        def open(self, *_, **__):
            raise OSError("Network is unreachable")

    monkeypatch.setattr(teryt.urllib.request, "build_opener", lambda *_: _Padnietyd())

    with pytest.raises(teryt.BladPobierania) as awaria:
        teryt.aktualizuj_jednostki()

    assert "internet" in str(awaria.value)


def test_pusta_paczka_to_blad_a_nie_wyczyszczona_baza(srodowisko, monkeypatch):
    _podstaw_gus(monkeypatch, _paczka_terc([]))

    with pytest.raises(teryt.BladPobierania):
        teryt.aktualizuj_jednostki()


# --- czytanie TERC -----------------------------------------------------------

def test_gmina_miejsko_wiejska_nie_wchodzi_do_bazy(srodowisko, monkeypatch):
    """RODZ=3 nie jest jednostką ewidencyjną — dzieli się na miasto (4) i wieś (5).

    Gdyby weszła, brat mógłby ją wybrać, a ULDK oddałby dla niej po cichu tylko
    część obrębów — czyli objawem byłby brakujący obręb, nie żaden błąd.
    """
    _podstaw_gus(monkeypatch, _paczka_terc())

    teryt.aktualizuj_jednostki()

    gminy = {g["id"] for g in teryt.potomkowie("1201", "gmina")}
    assert gminy == {"120101_1", "120102_2", "120103_4", "120103_5"}
    assert "120103_3" not in gminy


def test_kaskada_wojewodztwo_powiat_gmina(srodowisko, monkeypatch):
    _podstaw_gus(monkeypatch, _paczka_terc())
    ile, stan_na = teryt.aktualizuj_jednostki()

    wojewodztwa = teryt.potomkowie(None, "wojewodztwo")
    assert [w["id"] for w in wojewodztwa] == ["12"]
    assert wojewodztwa[0]["nazwa"] == "małopolskie", "GUS pisze wersalikami, my małą literą"
    assert [p["id"] for p in teryt.potomkowie("12", "powiat")] == ["1201"]
    assert ile == 6 and stan_na == "2026-01-01"


def test_rodzaj_gminy_zostaje_do_rozroznienia(srodowisko, monkeypatch):
    """Dwie Bochnie różnią się tylko rodzajem — bez niego lista jest nie do wybrania."""
    _podstaw_gus(monkeypatch, _paczka_terc())
    teryt.aktualizuj_jednostki()

    bochnie = {g["id"]: g["rodzaj"] for g in teryt.potomkowie("1201", "gmina")
               if g["nazwa"] == "Bochnia"}

    assert bochnie == {"120101_1": "gmina miejska", "120102_2": "gmina wiejska"}


def test_ponowne_pobranie_nie_dubluje_jednostek(srodowisko, monkeypatch):
    _podstaw_gus(monkeypatch, _paczka_terc())
    teryt.aktualizuj_jednostki()
    teryt.aktualizuj_jednostki()

    assert teryt.stan()["gmin"] == 4


def test_stan_i_pusto_opisuja_co_program_ma(srodowisko, monkeypatch):
    assert teryt.pusto() is True

    _podstaw_gus(monkeypatch, _paczka_terc())
    teryt.aktualizuj_jednostki()

    stan = teryt.stan()
    assert teryt.pusto() is False
    assert (stan["wojewodztw"], stan["powiatow"], stan["gmin"]) == (1, 1, 4)
    assert stan["stan_na"] == "2026-01-01" and stan["pobrano"]


# --- obręby: cache, bo w terenie nie ma sieci --------------------------------

def _podstaw_uldk(monkeypatch, tresc: str, licznik: list | None = None):
    def udawany_urlopen(adres, timeout=None):
        if licznik is not None:
            licznik.append(adres)
        return _Odpowiedz(tresc.encode("utf-8"))

    monkeypatch.setattr(teryt.urllib.request, "urlopen", udawany_urlopen)


ODPOWIEDZ_ULDK = "0\n120102_2.0001|Baczków\n120102_2.0002|Bogucice\n"


def test_obreby_pobrane_raz_potem_ida_z_bazy(srodowisko, monkeypatch):
    """Warunek konieczny: po pierwszym pobraniu program działa bez internetu."""
    zapytania: list = []
    _podstaw_uldk(monkeypatch, ODPOWIEDZ_ULDK, zapytania)

    pierwsze = teryt.obreby("120102_2")

    def bez_sieci(*_, **__):
        raise AssertionError("obręby są w bazie, nie wolno pytać ULDK")

    monkeypatch.setattr(teryt.urllib.request, "urlopen", bez_sieci)
    drugie = teryt.obreby("120102_2")

    assert len(zapytania) == 1 and "GetRegionById" in zapytania[0]
    assert pierwsze == drugie == [
        {"id": "120102_2.0001", "nazwa": "Baczków"},
        {"id": "120102_2.0002", "nazwa": "Bogucice"},
    ]


def test_milczenie_uldk_nie_kasuje_zapamietanych_obrebow(srodowisko, monkeypatch):
    """13 jednostek ULDK po prostu nie zna. Odświeżenie nie może ich wtedy wymazać."""
    _podstaw_uldk(monkeypatch, ODPOWIEDZ_ULDK)
    teryt.obreby("120102_2")

    _podstaw_uldk(monkeypatch, "-1 brak wyników\n")
    teryt.obreby("120102_2", wymus=True)

    assert len(teryt.obreby("120102_2")) == 2


def test_obreb_i_jednostka_po_identyfikatorze(srodowisko, monkeypatch):
    """Tego używa generator, wstawiając do dokumentu nazwy zamiast identyfikatorów."""
    monkeypatch.setattr(teryt, "jednostka", PRAWDZIWA_JEDNOSTKA)
    monkeypatch.setattr(teryt, "obreb", PRAWDZIWY_OBREB)
    _podstaw_gus(monkeypatch, _paczka_terc())
    teryt.aktualizuj_jednostki()
    _podstaw_uldk(monkeypatch, ODPOWIEDZ_ULDK)
    teryt.obreby("120102_2")

    assert teryt.jednostka("120102_2")["nazwa"] == "Bochnia"
    assert teryt.obreb("120102_2.0001")["nazwa"] == "Baczków"
    assert teryt.jednostka("") is None and teryt.obreb("nie ma takiego") is None


# --- pobieranie obrębów dla całej Polski -------------------------------------

@pytest.fixture
def polska(srodowisko, monkeypatch):
    """Dwadzieścia gmin w bazie — tyle wystarczy, żeby przerwać pobieranie w połowie."""
    with db.polaczenie() as con:
        con.executemany(
            "INSERT INTO teryt_jednostki (id, poziom, rodzic, nazwa, rodzaj)"
            " VALUES (?, 'gmina', '1201', ?, '')",
            [(f"1201{i:02d}_2", f"Gmina {i}") for i in range(20)])
    return [f"1201{i:02d}_2" for i in range(20)]


def test_pobranie_hurtowe_zapisuje_wszystko(polska, monkeypatch):
    monkeypatch.setattr(teryt, "_pobierz_obreby",
                        lambda gmina: [(f"{gmina}.0001", "Baczków")])

    teryt.pobierz_wszystkie_obreby()

    postep = teryt.postep()
    assert (postep["zrobione"], postep["pobranych"]) == (20, 20)
    assert postep["przerwane"] is False and postep["trwa"] is False
    assert teryt.stan()["gmin_z_obrebami"] == 20


def test_przerwane_pobieranie_nie_dobija_paska_do_konca(polska, monkeypatch):
    """Pula ma już w kolejce wszystkie zadania.

    Gdyby zadanie po przerwaniu tylko szybko zwracało pustkę, licznik doliczyłby
    pominięte gminy i pasek pokazałby udane pobranie — dlatego wychodzimy z pętli
    po wynikach, a nie z samego zadania.
    """
    def zadanie(gmina: str):
        if gmina == polska[2]:
            teryt.przerwij_pobieranie()
        return [(f"{gmina}.0001", "Baczków")]

    monkeypatch.setattr(teryt, "_pobierz_obreby", zadanie)

    teryt.pobierz_wszystkie_obreby()

    postep = teryt.postep()
    assert postep["przerwane"] is True
    assert postep["zrobione"] < 20, "pasek dobity do końca wygląda jak udane pobranie"
    assert postep["trwa"] is False


def test_wznowienie_bierze_tylko_brakujace(polska, monkeypatch):
    """„Pobierz brakujące" po przerwanym pobieraniu — nie zaczynamy od zera."""
    monkeypatch.setattr(teryt, "_pobierz_obreby",
                        lambda gmina: [(f"{gmina}.0001", "Baczków")])
    with db.polaczenie() as con:
        con.execute("INSERT INTO teryt_obreby (id, gmina, nazwa)"
                    " VALUES ('x.0001', ?, 'Baczków')", (polska[0],))

    assert teryt._gminy_do_pobrania(od_nowa=False) == polska[1:]
    assert teryt._gminy_do_pobrania(od_nowa=True) == polska


def test_gmina_bez_obrebow_nie_zatrzymuje_reszty(polska, monkeypatch):
    """ULDK nie zna 13 jednostek w Polsce — to normalne, a nie powód do przerwania."""
    def zadanie(gmina: str):
        if gmina == polska[5]:
            raise teryt.BladPobierania("ULDK nie odpowiedział")
        return [(f"{gmina}.0001", "Baczków")]

    monkeypatch.setattr(teryt, "_pobierz_obreby", zadanie)

    teryt.pobierz_wszystkie_obreby()

    postep = teryt.postep()
    assert postep["zrobione"] == 20 and postep["pobranych"] == 19
    assert postep["blad"] == ""


def test_drugie_kliknieie_nie_startuje_drugiego_pobierania(polska, monkeypatch):
    """Znacznik „trwa" stawiamy pod zamkiem w funkcji startującej.

    Postawiony dopiero w wątku roboczym zostawia szparę, w którą wchodzi drugie
    kliknięcie — i dwa pobierania dopisują się do jednego licznika postępu.
    """
    trzymaj = threading.Event()

    def zadanie(gmina: str):
        trzymaj.wait(10)
        return [(f"{gmina}.0001", "Baczków")]

    monkeypatch.setattr(teryt, "_pobierz_obreby", zadanie)
    try:
        assert teryt.uruchom_pobieranie_obrebow() is True
        assert teryt.uruchom_pobieranie_obrebow() is False, "drugie kliknięcie ma odbić się"
        assert teryt.postep()["trwa"] is True
    finally:
        trzymaj.set()

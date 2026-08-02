"""Sprawdzanie numeru działki w ewidencji (ULDK).

Zasada, której pilnują te testy: to jest **podpowiedź, nie kontrola**. ULDK nie zna
wszystkich działek i bywa niedostępne, więc „nie wiem” nie może nigdy wyglądać jak
„zły numer”. Fałszywy alarm nauczyłby brata ignorowania komunikatów.

Sieci tu nie ma — odpowiedzi ULDK są podstawiane.
"""
from __future__ import annotations

import io

import pytest

from app import teryt


class _Odpowiedz(io.BytesIO):
    """Minimum tego, czego używa `urlopen` w `with`."""

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


def _podstaw(monkeypatch, tresc: str | Exception, zapamietaj: list | None = None):
    def udawany_urlopen(adres, timeout=None):
        if zapamietaj is not None:
            zapamietaj.append(adres)
        if isinstance(tresc, Exception):
            raise tresc
        return _Odpowiedz(tresc.encode("utf-8"))

    monkeypatch.setattr(teryt.urllib.request, "urlopen", udawany_urlopen)


def test_dzialka_znaleziona(monkeypatch):
    _podstaw(monkeypatch, "0\n120102_2.0001.123/4\n")
    assert teryt.sprawdz_dzialke("120102_2.0001", "123/4")["stan"] == teryt.DZIALKA_JEST


def test_dzialki_nie_ma(monkeypatch):
    """ULDK dokłada do „-1” swój komunikat o błędnym XML-u — patrzymy tylko na kod."""
    _podstaw(monkeypatch, "-1 brak wyników\nbłędny format odpowiedzi XML, usługa zwróciła\n")
    assert teryt.sprawdz_dzialke("120102_2.0001", "999")["stan"] == teryt.DZIALKA_BRAK


def test_brak_sieci_to_nie_jest_zly_numer(monkeypatch):
    """Najważniejszy test w tym pliku: milczenie usługi nie może oskarżać użytkownika."""
    _podstaw(monkeypatch, OSError("brak połączenia"))
    assert teryt.sprawdz_dzialke("120102_2.0001", "123/4")["stan"] == teryt.DZIALKA_NIEZNANE


def test_dziwna_odpowiedz_to_tez_nieznane(monkeypatch):
    _podstaw(monkeypatch, "<html>Serwis przerwa techniczna</html>")
    assert teryt.sprawdz_dzialke("120102_2.0001", "123/4")["stan"] == teryt.DZIALKA_NIEZNANE


def test_bez_obrebu_nie_pytamy_uldk(monkeypatch):
    """Bez obrębu identyfikator jest niepełny — pytanie i tak nie miałoby sensu."""
    zapytania: list = []
    _podstaw(monkeypatch, "0\n", zapytania)

    assert teryt.sprawdz_dzialke("", "123/4")["stan"] == teryt.DZIALKA_NIEZNANE
    assert zapytania == []


def test_identyfikator_sklada_sie_z_obrebu_i_numeru(monkeypatch):
    zapytania: list = []
    _podstaw(monkeypatch, "0\n", zapytania)

    teryt.sprawdz_dzialke("120102_2.0001", "123/4")

    assert "GetParcelById" in zapytania[0]
    assert "120102_2.0001.123%2F4" in zapytania[0]     # ukośnik musi być zakodowany


# --- trasa dla formularza ----------------------------------------------------

@pytest.fixture
def bez_uldk(monkeypatch):
    """Podstawia samo sprawdzanie: trasa ma być testowana bez sieci."""
    odpowiedzi = {"123/4": teryt.DZIALKA_JEST, "999": teryt.DZIALKA_BRAK}

    def udawane(obreb, numer, limit_czasu=8):
        return {"stan": odpowiedzi.get(numer, teryt.DZIALKA_NIEZNANE),
                "powierzchnia": 4159.0 if numer == "123/4" else None}

    from app import main
    monkeypatch.setattr(main.teryt, "sprawdz_dzialke", udawane)


def test_trasa_sprawdza_kilka_dzialek_naraz(klient, bez_uldk):
    """W jednym polu bywa kilka numerów: „123/4, 999”."""
    odpowiedz = klient.get("/teryt/dzialka?obreb=120102_2.0001&numery=123/4, 999")

    assert odpowiedz.status_code == 200
    assert odpowiedz.json()["wyniki"] == [
        {"numer": "123/4", "stan": "jest", "powierzchnia": 4159.0},
        {"numer": "999", "stan": "brak", "powierzchnia": None},
    ]


def test_trasa_znosi_puste_i_srednik(klient, bez_uldk):
    odpowiedz = klient.get("/teryt/dzialka?obreb=120102_2.0001&numery=123/4; ,, 999,")
    assert [w["numer"] for w in odpowiedz.json()["wyniki"]] == ["123/4", "999"]


def test_formularz_oznacza_pole_z_numerem_dzialki(klient):
    """Skrypt w przeglądarce szuka pola po tym znaczniku."""
    klient.srodowisko.dodaj_szablon(
        "spis_tresci_wzor", ["{{ nr_roboty }} {{ nr_dzialki }}"],
        opis={"nazwa": "Operat", "glowny": True,
              "pola": [{"klucz": "nr_roboty"}, {"klucz": "nr_dzialki"}]})

    tresc = klient.get("/nowy/spis_tresci_wzor").text

    assert 'data-dzialka="1"' in tresc
    assert 'class="uldk podpowiedz"' in tresc


def test_hektary_zaokraglone_do_dwoch_miejsc(klient):
    """Hektary są do rzutu oka, nie do rachunku — 0,42 ha zamiast 0,4159 ha.

    Dokładna liczba stoi obok w metrach kwadratowych i **ta zostaje bez zaokrąglania**,
    bo to ona służy do porównania z powierzchnią z dokumentów.
    """
    klient.srodowisko.dodaj_szablon(
        "spis_tresci_wzor", ["{{ nr_roboty }} {{ nr_dzialki }}"],
        opis={"nazwa": "Operat", "glowny": True,
              "pola": [{"klucz": "nr_roboty"}, {"klucz": "nr_dzialki"}]})

    tresc = klient.get("/nowy/spis_tresci_wzor").text

    assert "(m / 10000).toFixed(2)" in tresc, "hektary mają być zaokrąglone do 2 miejsc"
    assert "toFixed(4)" not in tresc
    assert "Math.round(w.powierzchnia)" in tresc, "metry kwadratowe zostają pełne"


# --- liczenie powierzchni z obrysu -------------------------------------------

def test_powierzchnia_prostego_wielokata():
    """PL-1992 jest metryczny, więc pole liczy się wprost ze współrzędnych."""
    assert teryt.powierzchnia_z_wkt(
        "SRID=2180;POLYGON((0 0,100 0,100 100,0 100,0 0))") == 10000


def test_dziura_w_dzialce_jest_odejmowana():
    """Enklawa w środku działki nie może zawyżać powierzchni."""
    assert teryt.powierzchnia_z_wkt(
        "POLYGON((0 0,100 0,100 100,0 100,0 0),(10 10,60 10,60 60,10 60,10 10))") == 7500


def test_dzialka_z_kilku_kawalkow_sumuje_sie():
    """MULTIPOLYGON wygląda w nawiasach jak wielokąt z dziurą — dlatego typ czytamy
    z tekstu WKT, a nie zgadujemy po zagnieżdżeniu (na tym poległa pierwsza wersja)."""
    assert teryt.powierzchnia_z_wkt(
        "MULTIPOLYGON(((0 0,100 0,100 100,0 100,0 0)),"
        "((200 0,300 0,300 100,200 100,200 0)))") == 20000


def test_kierunek_obrysu_nie_ma_znaczenia():
    zgodnie = teryt.powierzchnia_z_wkt("POLYGON((0 0,100 0,100 100,0 100,0 0))")
    przeciwnie = teryt.powierzchnia_z_wkt("POLYGON((0 0,0 100,100 100,100 0,0 0))")
    assert zgodnie == przeciwnie == 10000


def test_polamana_geometria_nie_wywala_sprawdzania():
    for smiec in ("", "POLYGON", "SRID=2180;POLYGON((niepoprawne", "POLYGON((0 0,1 1))"):
        assert teryt.powierzchnia_z_wkt(smiec) is None


def test_powierzchnia_wraca_ze_sprawdzenia_dzialki(monkeypatch):
    _podstaw(monkeypatch,
             "0\n120102_2.0001.123/4|SRID=2180;POLYGON((0 0,100 0,100 100,0 100,0 0))\n")

    wynik = teryt.sprawdz_dzialke("120102_2.0001", "123/4")

    assert wynik["stan"] == teryt.DZIALKA_JEST
    assert wynik["powierzchnia"] == 10000        # 1 ha


def test_brak_geometrii_nie_psuje_odpowiedzi(monkeypatch):
    """Gdyby ULDK kiedyś przestał oddawać obrys — stan „jest” ma zostać."""
    _podstaw(monkeypatch, "0\n120102_2.0001.123/4\n")

    wynik = teryt.sprawdz_dzialke("120102_2.0001", "123/4")

    assert wynik["stan"] == teryt.DZIALKA_JEST
    assert wynik["powierzchnia"] is None

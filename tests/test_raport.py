"""Wysyłka trzech liczb do arkusza autora.

Sieci tu nie ma — `urlopen` jest podstawiany. Fixture `bez_wysylki_statystyk`
z `conftest.py` domyślnie **wyłącza** wysyłkę we wszystkich testach; te, które jej
dotyczą, włączają ją u siebie z powrotem.
"""
from __future__ import annotations

import io
import urllib.parse

import pytest

from app import raport


class _Odpowiedz(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


@pytest.fixture
def wysylka_wlaczona(monkeypatch):
    monkeypatch.delenv(raport.WYLACZNIK, raising=False)


@pytest.fixture
def przechwycone(monkeypatch):
    """Podstawia sieć; zwraca listę adresów, pod które program próbował wysłać."""
    adresy: list[str] = []

    def udawany_urlopen(adres, timeout=None):
        adresy.append(adres)
        return _Odpowiedz(b"ok")

    monkeypatch.setattr(raport.urllib.request, "urlopen", udawany_urlopen)
    return adresy


def _parametry(adres: str) -> dict[str, str]:
    # keep_blank_values, bo pusta etykieta jest normalnym stanem (instalacja nieopisana),
    # a bez tego parametr po prostu znikałby z porównania
    rozbite = urllib.parse.parse_qs(urllib.parse.urlparse(adres).query, keep_blank_values=True)
    return {k: v[0] for k, v in rozbite.items()}


# --- co wychodzi z komputera brata -------------------------------------------

def test_wysylamy_trzy_liczby_i_nic_wiecej(srodowisko, wysylka_wlaczona, przechwycone):
    """Lista pól jest tu wypisana celowo: gdyby ktoś dołożył do wysyłki cokolwiek
    o robocie (numer działki, nazwisko, ścieżkę), ten test ma zaświecić na czerwono."""
    assert raport.wyslij("2026.08.02.13", {"operat": 128, "dokument": 512, "pdf": 96}) is True

    parametry = _parametry(przechwycone[0])
    assert set(parametry) == {"token", "id", "etykieta", "wersja",
                              "operaty", "dokumenty", "pdfy"}
    assert parametry["operaty"] == "128"
    assert parametry["dokumenty"] == "512"
    assert parametry["pdfy"] == "96"
    assert parametry["wersja"] == "2026.08.02.13"


def test_wysylamy_sumy_a_nie_przyrosty(srodowisko, wysylka_wlaczona, przechwycone):
    """Dzięki sumom zgubiony pakiet nic nie kosztuje — następny niesie pełną prawdę."""
    raport.wyslij("1", {"operat": 10, "dokument": 0, "pdf": 0})
    raport.wyslij("1", {"operat": 12, "dokument": 0, "pdf": 0})

    assert [_parametry(a)["operaty"] for a in przechwycone] == ["10", "12"]


# --- identyfikator instalacji ------------------------------------------------

def test_identyfikator_jest_staly(srodowisko):
    pierwszy = raport.identyfikator()
    assert pierwszy == raport.identyfikator()
    assert raport.PLIK_ID.read_text(encoding="utf-8").strip() == pierwszy


def test_identyfikator_nie_zdradza_komputera(srodowisko):
    """To ma być losowy ciąg, a nie nazwa maszyny czy użytkownika."""
    identyfikator = raport.identyfikator()
    assert identyfikator.isalnum() and 8 <= len(identyfikator) <= 32


def test_kopia_robocza_gita_oznacza_sie_sama(srodowisko):
    """Instalacja deweloperska ma się wyróżnić bez pamiętania o etykietach."""
    assert raport.etykieta() == ""

    (srodowisko.katalog / ".git").mkdir()
    assert raport.etykieta() == "kopia-robocza"


def test_wpisana_etykieta_ma_pierwszenstwo(srodowisko):
    (srodowisko.katalog / ".git").mkdir()
    raport.PLIK_ETYKIETY.write_text("  test-piotr\n", encoding="utf-8")

    assert raport.etykieta() == "test-piotr"


# --- nic nie może przewrócić programu ---------------------------------------

def test_wylacznik_zatrzymuje_wysylke(srodowisko, przechwycone, monkeypatch):
    monkeypatch.setenv(raport.WYLACZNIK, "1")

    assert raport.wyslij("1", {"operat": 1}) is False
    assert przechwycone == [], "wysyłka poszła mimo wyłącznika"


def test_brak_sieci_konczy_sie_cicho(srodowisko, wysylka_wlaczona, monkeypatch):
    def bez_sieci(adres, timeout=None):
        raise OSError("brak połączenia")

    monkeypatch.setattr(raport.urllib.request, "urlopen", bez_sieci)

    assert raport.wyslij("1", {"operat": 1}) is False       # bez wyjątku na zewnątrz


def test_start_programu_nie_czeka_na_arkusz(klient):
    """Cykl życia aplikacji odpala wysyłkę w wątku — strona ma odpowiadać od razu."""
    assert klient.get("/").status_code == 200

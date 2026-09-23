"""Zderzenia z tym, co brat robi obok programu.

Numer operatu wpisany z ręki, dokument otwarty w Wordzie, złożony PDF otwarty
w czytniku, plik przemianowany Eksploratorem, formatka wgrana w połowie. Żadna z tych
rzeczy nie jest błędem programu, ale każda kończyła się dotąd źle: nadpisanym cudzym
operatem, komunikatem o „literówce w formatce”, ogólną stroną błędu albo pół
skasowanym katalogiem. Tu pilnujemy, że program mówi, co zamknąć albo poprawić,
i że niczego po drodze nie psuje.

Plik otwarty w Wordzie albo w czytniku udaje atrybut „tylko do odczytu”: zapis kończy
się wtedy tym samym `PermissionError` co na Windowsie, bez prawdziwego Worda.
"""
from __future__ import annotations

import os
import re
import stat
from pathlib import Path
from urllib.parse import unquote

import pytest

from app import db, operaty
from test_trasy import FORMULARZ, OPIS_OPERATU, _dodaj_operat, _prawdziwy_pdf   # tests/ nie jest pakietem

# root zapisze także plik tylko do odczytu — wtedy nie ma czego sprawdzać
BEZ_ROOTA = pytest.mark.skipif(hasattr(os, "geteuid") and os.geteuid() == 0,
                               reason="root pisze także do plików tylko do odczytu")


def _jak_otwarty(plik: Path) -> None:
    plik.chmod(stat.S_IREAD)


def _nowy_operat(klient, **pola) -> dict:
    odpowiedz = klient.post("/generuj/spis_tresci_wzor", data={**FORMULARZ, **pola},
                            follow_redirects=False)
    assert odpowiedz.status_code == 303, odpowiedz.text[-400:]
    return db.dokumenty()[0]


def _adres(odpowiedz) -> str:
    return unquote(odpowiedz.headers["location"])


# --- numer operatu wpisany z ręki --------------------------------------------

def test_powielenie_nie_przenosi_recznie_wpisanego_numeru(klient):
    """Numer z licznika nie siedzi w danych formularza, ale wpisany kiedyś z ręki —
    siedzi. „Powiel” wnosił go do nowego operatu, a ten wchodził do katalogu starego
    i nadpisywał mu dokumenty."""
    _dodaj_operat(klient)
    wpis = _nowy_operat(klient, pole__nr_operatu="050/2026")
    assert wpis["katalog"] == "050.2026"

    formularz = klient.get(f"/nowy/spis_tresci_wzor?kopiuj={wpis['id']}").text

    pole = re.search(r'id="p_nr_operatu"[^>]*value="([^"]*)"', formularz)
    assert pole and pole.group(1) == "", "powielony operat startuje z numerem starego"
    assert 'value="GK.6640.1.2026"' in formularz, "reszta danych miała przyjść z powielanego"


def test_reczny_numer_innego_operatu_nie_wchodzi_do_jego_katalogu(klient):
    """Nowy operat z numerem, który ma już inny, przepisywał tamtemu `operat.json`
    i dokumenty, a jego mapy brał za swoje („Usuń” jednego kasowało potem oba)."""
    _dodaj_operat(klient)
    pierwszy = _nowy_operat(klient)                               # 001/2026 z licznika
    katalog = klient.srodowisko.wyniki / pierwszy["katalog"]
    opis_przed = (katalog / "operat.json").read_bytes()

    odpowiedz = klient.post("/generuj/spis_tresci_wzor", follow_redirects=False,
                            data={**FORMULARZ, "pole__nr_operatu": pierwszy["nr_operatu"],
                                  "pole__nr_roboty": "GK.9999.2026"})

    assert odpowiedz.status_code == 200
    assert "ma już inny operat" in odpowiedz.text and pierwszy["katalog"] in odpowiedz.text
    assert "GK.9999.2026" in odpowiedz.text, "wpisane dane miały zostać w formularzu"
    assert len(db.dokumenty()) == 1
    assert (katalog / "operat.json").read_bytes() == opis_przed


def test_poprawka_z_numerem_innego_operatu_nie_wchodzi_do_jego_katalogu(klient):
    _dodaj_operat(klient)
    pierwszy = _nowy_operat(klient)                                        # 001/2026
    drugi = _nowy_operat(klient, pole__nr_roboty="GK.2.2026")               # 002/2026
    opis_pierwszego = (klient.srodowisko.wyniki / pierwszy["katalog"] / "operat.json").read_bytes()

    odpowiedz = klient.post(f"/generuj/spis_tresci_wzor?edytuj={drugi['id']}",
                            follow_redirects=False,
                            data={**FORMULARZ, "pole__nr_operatu": pierwszy["nr_operatu"],
                                  "pole__nr_roboty": "GK.2.2026"})

    assert odpowiedz.status_code == 200 and "ma już inny operat" in odpowiedz.text
    assert (klient.srodowisko.wyniki / pierwszy["katalog"] / "operat.json").read_bytes() \
        == opis_pierwszego
    assert db.dokument(drugi["id"])["katalog"] == drugi["katalog"]


def test_poprawka_z_wlasnym_numerem_przechodzi(klient):
    """Strażnik zna „swój” katalog — poprawka z numerem własnego operatu to nie zderzenie."""
    _dodaj_operat(klient)
    wpis = _nowy_operat(klient)

    odpowiedz = klient.post(f"/generuj/spis_tresci_wzor?edytuj={wpis['id']}",
                            follow_redirects=False,
                            data={**FORMULARZ, "pole__nr_operatu": wpis["nr_operatu"],
                                  "pole__uwagi": "literówka poprawiona"})

    assert odpowiedz.status_code == 303
    assert [w["katalog"] for w in db.dokumenty()] == [wpis["katalog"]]


def test_katalog_zalozony_recznie_nie_jest_cudzym_operatem(klient):
    """Brat zakłada czasem katalog na nową robotę z góry i wrzuca tam mapy. Bez
    `operat.json` to nie jest operat programu, więc numer z ręki ma do niego trafić."""
    _dodaj_operat(klient)
    reczny = klient.srodowisko.wyniki / "070.2026"
    reczny.mkdir(parents=True)
    _prawdziwy_pdf(reczny / "mapa.pdf")

    wpis = _nowy_operat(klient, pole__nr_operatu="070/2026")

    assert wpis["katalog"] == "070.2026"
    assert (reczny / "mapa.pdf").exists() and (reczny / "spis_tresci.docx").exists()


# --- dokument otwarty w Wordzie ----------------------------------------------

@BEZ_ROOTA
def test_dokument_otwarty_w_wordzie_nie_udaje_literowki_w_formatce(klient):
    """„Popraw” przy dokumencie otwartym w Wordzie szło dotąd przez komunikat
    o literówce w znaczniku — brat szukał błędu w szablonie, zamiast zamknąć Worda."""
    _dodaj_operat(klient)
    wpis = _nowy_operat(klient)
    dokument = klient.srodowisko.wyniki / wpis["katalog"] / "spis_tresci.docx"
    _jak_otwarty(dokument)

    odpowiedz = klient.post(f"/generuj/spis_tresci_wzor?edytuj={wpis['id']}",
                            data=FORMULARZ, follow_redirects=False)

    assert odpowiedz.status_code == 200
    assert "spis_tresci.docx" in odpowiedz.text and "otwarty w innym programie" in odpowiedz.text
    assert "literówka" not in odpowiedz.text
    assert "5712345.12" in odpowiedz.text, "wpisane dane miały zostać w formularzu"


@BEZ_ROOTA
def test_nowy_operat_przy_zablokowanym_pliku_nie_zjada_numeru(klient):
    """Nieudany zapis oddaje zarezerwowany numer — kolejna próba dostaje ten sam."""
    _dodaj_operat(klient)
    katalog = klient.srodowisko.wyniki / "001.2026"
    katalog.mkdir(parents=True)
    (katalog / "spis_tresci.docx").write_bytes(b"stara wersja otwarta w Wordzie")
    _jak_otwarty(katalog / "spis_tresci.docx")

    odpowiedz = klient.post("/generuj/spis_tresci_wzor", data=FORMULARZ, follow_redirects=False)
    assert odpowiedz.status_code == 200 and "otwarty w innym programie" in odpowiedz.text
    assert db.dokumenty() == []

    (katalog / "spis_tresci.docx").chmod(stat.S_IREAD | stat.S_IWRITE)
    assert _nowy_operat(klient)["nr_operatu"] == "001/2026"


def _operat_ze_sprawozdaniem(klient) -> dict:
    klient.srodowisko.dodaj_szablon(
        "spis_tresci_wzor", ["{{ nr_roboty }} {{ nr_operatu }}"],
        opis={**OPIS_OPERATU,
              "pola": OPIS_OPERATU["pola"] + [{"klucz": "dokumenty", "typ": "dokumenty"}]})
    klient.srodowisko.dodaj_szablon("sprawozdanie_wzor", ["Operat {{ nr_operatu }}"],
                                    opis={"nazwa": "Sprawozdanie", "pola": []})
    return _nowy_operat(klient, pole__dokumenty="sprawozdanie_wzor")


@BEZ_ROOTA
def test_otwarty_dokument_dodatkowy_to_ostrzezenie_a_stary_plik_zostaje(klient):
    wpis = _operat_ze_sprawozdaniem(klient)
    sprawozdanie = klient.srodowisko.wyniki / wpis["katalog"] / "sprawozdanie.docx"
    przed = sprawozdanie.read_bytes()
    _jak_otwarty(sprawozdanie)

    odpowiedz = klient.post(f"/generuj/spis_tresci_wzor?edytuj={wpis['id']}",
                            data={**FORMULARZ, "pole__dokumenty": "sprawozdanie_wzor"},
                            follow_redirects=False)

    assert odpowiedz.status_code == 303
    assert "Sprawozdanie" in _adres(odpowiedz) and "otwarty w innym programie" in _adres(odpowiedz)
    assert sprawozdanie.read_bytes() == przed


def test_zepsuta_formatka_dodatkowa_nie_wywraca_operatu(klient):
    """Formatka wgrana w połowie (albo z błędem w `.json`) wywracała całą trasę **po**
    wygenerowaniu spisu treści: operat bez wpisu w historii i zużyty numer — a każda
    kolejna próba zjadała następny. Stary plik z poprzedniej rundy ma zostać."""
    wpis = _operat_ze_sprawozdaniem(klient)
    katalog = klient.srodowisko.wyniki / wpis["katalog"]
    przed = (katalog / "sprawozdanie.docx").read_bytes()
    (klient.srodowisko.szablony / "sprawozdanie_wzor.docx").write_bytes(b"to nie jest docx")

    poprawka = klient.post(f"/generuj/spis_tresci_wzor?edytuj={wpis['id']}",
                           data={**FORMULARZ, "pole__dokumenty": "sprawozdanie_wzor"},
                           follow_redirects=False)
    nowy = klient.post("/generuj/spis_tresci_wzor", follow_redirects=False,
                       data={**FORMULARZ, "pole__dokumenty": "sprawozdanie_wzor",
                             "pole__nr_roboty": "GK.2.2026"})

    for odpowiedz in (poprawka, nowy):
        assert odpowiedz.status_code == 303
        assert "sprawozdanie_wzor" in _adres(odpowiedz)
    assert (katalog / "sprawozdanie.docx").read_bytes() == przed
    assert sorted(w["nr_operatu"] for w in db.dokumenty()) == ["001/2026", "002/2026"]


# --- usuwanie operatu --------------------------------------------------------

def test_usuwanie_przy_otwartym_pliku_nie_kasuje_niczego(klient, monkeypatch):
    """Na Windowsie pliku otwartego w Wordzie albo w czytniku nie da się skasować.
    `rmtree(ignore_errors=True)` zostawiał wtedy pół katalogu — często już bez
    `operat.json`, czyli niewidocznego dla programu — i kasował wpis z historii.
    Katalogu z otwartym plikiem Windows nie da się też przemianować, i na tym stoi
    poprawka: najpierw zmiana nazwy, a dopiero potem kasowanie."""
    _dodaj_operat(klient)
    wpis = _nowy_operat(klient)
    katalog = klient.srodowisko.wyniki / wpis["katalog"]
    _prawdziwy_pdf(katalog / "mapa.pdf")                        # plik brata
    przed = sorted(p.name for p in katalog.iterdir())
    prawdziwa_zmiana_nazwy = Path.rename

    def jak_windows(sciezka, cel):
        if sciezka == katalog:
            raise PermissionError(13, "Proces nie może uzyskać dostępu do pliku", str(sciezka))
        return prawdziwa_zmiana_nazwy(sciezka, cel)

    monkeypatch.setattr(Path, "rename", jak_windows)
    odpowiedz = klient.post(f"/dokument/{wpis['id']}/usun", follow_redirects=False)

    assert odpowiedz.status_code == 303
    assert "Nie usunąłem operatu" in _adres(odpowiedz)
    assert db.dokument(wpis["id"]) is not None, "wpis zniknął z historii, a katalog został"
    assert sorted(p.name for p in katalog.iterdir()) == przed


def test_usuwanie_operatu_kasuje_katalog_bez_sladu(klient):
    """Druga strona poprawki: zwykłe usuwanie nie zostawia katalogu `….usuwany-…`."""
    _dodaj_operat(klient)
    wpis = _nowy_operat(klient)
    _prawdziwy_pdf(klient.srodowisko.wyniki / wpis["katalog"] / "mapa.pdf")

    klient.post(f"/dokument/{wpis['id']}/usun", follow_redirects=False)

    assert db.dokument(wpis["id"]) is None
    assert list(klient.srodowisko.wyniki.iterdir()) == []


# --- składanie PDF -----------------------------------------------------------

@BEZ_ROOTA
def test_zlozenie_przy_otwartym_wyniku_mowi_co_zamknac(klient):
    """Poprzedni złożony PDF otwarty w czytniku — Windows blokuje zapis. Dotąd kończyło
    się to ogólną stroną błędu, a ponowienie niczego nie zmieniało."""
    _dodaj_operat(klient)
    wpis = _nowy_operat(klient)
    katalog = klient.srodowisko.wyniki / wpis["katalog"]
    klient.post(f"/scal/{wpis['katalog']}", data={"plik": "spis_tresci.docx"},
                follow_redirects=False)
    wynik = katalog / "GK.6640.1.2026.pdf"
    _jak_otwarty(wynik)

    odpowiedz = klient.post(f"/scal/{wpis['katalog']}", data={"plik": "spis_tresci.docx"},
                            follow_redirects=False)

    assert odpowiedz.status_code == 303
    adres = _adres(odpowiedz)
    assert "blad=" in adres and "GK.6640.1.2026.pdf" in adres and "czytniku PDF" in adres
    assert "zlozono" not in adres


def test_skladanie_mowi_ktorego_pliku_zabraklo(klient):
    """Kafelek pliku, który brat w międzyczasie przemianował Eksploratorem: składamy
    bez niego, ale nie po cichu — „Złożone.” wyglądało dotąd na komplet."""
    _dodaj_operat(klient)
    wpis = _nowy_operat(klient)

    odpowiedz = klient.post(f"/scal/{wpis['katalog']}", follow_redirects=False,
                            data={"plik": ["spis_tresci.docx", "mapa.pdf"]})

    adres = _adres(odpowiedz)
    assert "zlozono=1" in adres, "reszta miała się złożyć"
    assert "blad=" in adres and "mapa.pdf" in adres


# --- formularz w przeglądarce ------------------------------------------------

def test_formularz_po_bledzie_pilnuje_niezapisanych_danych(klient):
    """Formularz odesłany z komunikatem („Uzupełnij wymagane pola”) niesie dane, których
    nikt jeszcze nie zapisał — ostrzeżenie przed wyjściem ma działać od razu, a nie
    dopiero po kolejnym dotknięciu pola. Świeży formularz nie pyta."""
    _dodaj_operat(klient)

    swiezy = klient.get("/nowy/spis_tresci_wzor").text
    po_bledzie = klient.post("/generuj/spis_tresci_wzor",
                             data={**FORMULARZ, "pole__nr_roboty": ""}).text

    assert "let zmienione = false;" in swiezy
    assert "Uzupełnij wymagane pola" in po_bledzie and "let zmienione = true;" in po_bledzie

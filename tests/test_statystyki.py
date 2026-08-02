"""Liczniki pracy programu.

Najważniejsze, czego pilnują: liczby **nie mogą znikać**, gdy brat przeniesie gotowe
operaty na dysk archiwalny, i **nie mogą rosnąć** od plików, które sam dołożył do katalogu.
Pierwsza wersja liczyła pliki na dysku i myliła się w obie strony.
"""
from __future__ import annotations

import shutil

from app import operaty, statystyki

from test_trasy import FORMULARZ, OPIS_OPERATU   # tests/ nie jest pakietem


def _dodaj_szablon(srodowisko):
    srodowisko.dodaj_szablon(
        "spis_tresci_wzor",
        ["Robota: {{ nr_roboty }}", "Operat: {{ nr_operatu }}", "Data: {{ data_zakonczenia }}"],
        opis=OPIS_OPERATU, tabela=True)


# --- samo zliczanie ----------------------------------------------------------

def test_zliczanie_sumuje_sie(srodowisko):
    statystyki.zlicz(statystyki.OPERAT)
    statystyki.zlicz(statystyki.OPERAT)
    statystyki.zlicz(statystyki.DOKUMENT, 3)

    assert statystyki.podsumowanie() == {
        statystyki.OPERAT: 2, statystyki.DOKUMENT: 3, statystyki.PDF: 0}


def test_pusta_baza_daje_zera_a_nie_wyjatek(srodowisko):
    assert statystyki.podsumowanie() == {
        statystyki.OPERAT: 0, statystyki.DOKUMENT: 0, statystyki.PDF: 0}


# --- to, co obalilo liczenie z dysku ----------------------------------------

def test_archiwizacja_operatu_nie_cofa_licznika(klient):
    """Brat przenosi gotowe operaty na dysk archiwalny — licznik ma to przeżyć.

    To jest powód, dla którego liczymy zdarzenia, a nie pliki: wcześniejsza wersja
    po przeniesieniu katalogów pokazywałaby zero mimo setki zrobionych robót.
    """
    _dodaj_szablon(klient.srodowisko)
    klient.post("/generuj/spis_tresci_wzor", data=FORMULARZ, follow_redirects=False)
    przed = statystyki.podsumowanie()
    assert przed[statystyki.OPERAT] == 1

    for katalog in klient.srodowisko.wyniki.iterdir():      # „przeniósł do archiwum”
        if katalog.is_dir():
            shutil.rmtree(katalog)
    assert not any(klient.srodowisko.wyniki.iterdir())

    assert statystyki.podsumowanie() == przed


def test_wlasne_pliki_brata_nie_wpadaja_do_licznika(klient):
    """Mapy, skany i dokumenty od zamawiającego nie są „wygenerowane przez program”."""
    _dodaj_szablon(klient.srodowisko)
    klient.post("/generuj/spis_tresci_wzor", data=FORMULARZ, follow_redirects=False)
    przed = statystyki.podsumowanie()

    katalog = next(k for k in klient.srodowisko.wyniki.iterdir() if k.is_dir())
    for nazwa in ("mapa_zasadnicza.pdf", "wypis_z_rejestru.docx", "szkic_polowy.docx"):
        (katalog / nazwa).write_bytes(b"plik brata")

    assert statystyki.podsumowanie() == przed


# --- co dokładnie się liczy --------------------------------------------------

def test_poprawianie_operatu_nie_dokłada_operatu(klient):
    """Tak samo jak nie zużywa numeru — poprawka to ten sam operat."""
    _dodaj_szablon(klient.srodowisko)
    klient.post("/generuj/spis_tresci_wzor", data=FORMULARZ, follow_redirects=False)

    klient.post("/generuj/spis_tresci_wzor?edytuj=1",
                data=dict(FORMULARZ, pole__uwagi="poprawione"), follow_redirects=False)

    podsumowanie = statystyki.podsumowanie()
    assert podsumowanie[statystyki.OPERAT] == 1        # nadal jeden operat
    assert podsumowanie[statystyki.DOKUMENT] == 2      # ale dokument wypełniony dwa razy


def test_zlozenie_pdf_liczy_sie_dopiero_po_udanym_sklejeniu(klient):
    _dodaj_szablon(klient.srodowisko)
    klient.post("/generuj/spis_tresci_wzor", data=FORMULARZ, follow_redirects=False)
    assert statystyki.podsumowanie()[statystyki.PDF] == 0

    katalog = next(k for k in klient.srodowisko.wyniki.iterdir() if k.is_dir())
    klient.post(f"/scal/{katalog.name}", data={"plik": "spis_tresci.docx"},
                follow_redirects=False)

    assert statystyki.podsumowanie()[statystyki.PDF] == 1


def test_nieudane_sklejenie_nie_zwieksza_licznika(klient):
    """Nie wybrano plików → nie ma PDF-a, więc licznik stoi."""
    _dodaj_szablon(klient.srodowisko)
    klient.post("/generuj/spis_tresci_wzor", data=FORMULARZ, follow_redirects=False)
    katalog = next(k for k in klient.srodowisko.wyniki.iterdir() if k.is_dir())

    klient.post(f"/scal/{katalog.name}", data={}, follow_redirects=False)

    assert statystyki.podsumowanie()[statystyki.PDF] == 0


# --- odtworzenie historii przy pierwszym uruchomieniu nowej wersji -----------

def test_zasiew_odtwarza_operaty_z_bazy_i_dokumenty_z_dysku(srodowisko):
    """Po aktualizacji licznik ma pokazać dorobek brata, a nie zero."""
    from app import db

    _dodaj_szablon(srodowisko)
    katalog, _ = operaty.zaloz("001/2026", "GK.1.2026", "spis_tresci_wzor", {})
    (katalog / "spis_tresci.docx").write_bytes(b"x")          # plik programu
    (katalog / "wypis.docx").write_bytes(b"x")                # plik brata — nie liczymy
    (katalog / operaty.nazwa_wyniku(katalog)).write_bytes(b"%PDF-1.4\n")
    db.zapisz_dokument("spis_tresci_wzor", "GK.1.2026", "001.2026/spis_tresci.docx", {},
                       katalog.name, "001/2026")
    # operat już zarchiwizowany: wpis w bazie jest, katalogu nie ma
    db.zapisz_dokument("spis_tresci_wzor", "GK.9.2025", "009.2025/spis_tresci.docx", {},
                       "009.2025", "009/2025")

    assert statystyki.zasiej_z_historii() is True

    podsumowanie = statystyki.podsumowanie()
    assert podsumowanie[statystyki.OPERAT] == 2      # także ten z archiwum
    assert podsumowanie[statystyki.DOKUMENT] == 1    # tylko plik o nazwie nadanej programem
    assert podsumowanie[statystyki.PDF] == 1


def test_zasiew_robi_sie_tylko_raz(srodowisko):
    """Drugie uruchomienie nie może podwoić dorobku."""
    from app import db

    db.zapisz_dokument("spis_tresci_wzor", "GK.1.2026", "001.2026/spis_tresci.docx", {},
                       "001.2026", "001/2026")

    assert statystyki.zasiej_z_historii() is True
    pierwsze = statystyki.podsumowanie()

    assert statystyki.zasiej_z_historii() is False
    assert statystyki.podsumowanie() == pierwsze


def test_stopka_pokazuje_liczniki(klient):
    """Brat widzi te liczby na każdej stronie — muszą trafić do HTML-a."""
    _dodaj_szablon(klient.srodowisko)
    klient.post("/generuj/spis_tresci_wzor", data=FORMULARZ, follow_redirects=False)

    tresc = klient.get("/").text
    assert "<strong>1</strong> operatów" in tresc
    assert "<strong>1</strong> dokumentów Worda" in tresc
    assert "<strong>0</strong> złożonych PDF-ów" in tresc

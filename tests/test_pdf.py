"""Sklejanie PDF-ów i wykrywanie konwertera.

Sama konwersja DOCX→PDF wymaga Worda albo LibreOffice'a, więc jest tu tylko jeden
test oznaczony markerem `konwerter` — pomija się sam, gdy nie ma czym konwertować.
"""
from __future__ import annotations

import pytest
from pathlib import Path
from pypdf import PdfReader, PdfWriter

from app import pdf


def _pdf(sciezka, stron: int = 1, wysokosc: int = 842):
    zapis = PdfWriter()
    for _ in range(stron):
        zapis.add_blank_page(width=595, height=wysokosc)
    sciezka.parent.mkdir(parents=True, exist_ok=True)
    with open(sciezka, "wb") as wyjscie:
        zapis.write(wyjscie)
    return sciezka


def test_sklejanie_zachowuje_kolejnosc_i_liczbe_stron(tmp_path):
    a = _pdf(tmp_path / "a.pdf", stron=2)
    b = _pdf(tmp_path / "b.pdf", stron=3)
    wynik = pdf.polacz_pdf([a, b], tmp_path / "wynik.pdf")
    assert len(PdfReader(str(wynik)).pages) == 5


def test_sklejanie_bez_plikow_zglasza_blad(tmp_path):
    with pytest.raises(ValueError):
        pdf.polacz_pdf([], tmp_path / "wynik.pdf")


def test_uszkodzony_plik_mowi_po_polsku_i_podaje_nazwe(tmp_path):
    """Przy kilkunastu załącznikach brat musi wiedzieć, który plik jest do wymiany."""
    dobry = _pdf(tmp_path / "dobry.pdf")
    zepsuty = tmp_path / "roboczy-20260801.pdf"
    zepsuty.write_bytes(b"to nie jest PDF")

    with pytest.raises(pdf.BladPliku) as awaria:
        pdf.polacz_pdf([dobry, zepsuty], tmp_path / "wynik.pdf",
                       etykiety={zepsuty: "mapa zasadnicza.pdf"})
    komunikat = str(awaria.value)
    assert "mapa zasadnicza.pdf" in komunikat        # nazwa, którą on zna
    assert "roboczy-20260801" not in komunikat       # nie nazwa robocza z dysku
    assert "PDF" in komunikat and "hasłem" in komunikat


def test_obrot_zapisuje_sie_w_wyniku(tmp_path):
    zrodlo = _pdf(tmp_path / "lezacy.pdf")
    wynik = pdf.polacz_pdf([zrodlo], tmp_path / "wynik.pdf", obroty={zrodlo: 90})
    assert PdfReader(str(wynik)).pages[0].get("/Rotate") == 90


def test_wykrywanie_konwertera_zwraca_znana_wartosc():
    assert pdf.dostepny_konwerter() in {"word", "libreoffice", "brak"}


@pytest.fixture
def katalog_konwersji():
    """Katalog roboczy **wewnątrz projektu**, a nie w /tmp.

    LibreOffice ze Snapa/Flatpaka ma własny, odizolowany `/tmp` — pliku z `tmp_path`
    w ogóle nie widzi i konwersja kończy się „nie utworzył PDF-a”. W programie nigdy
    nie konwertujemy z `/tmp` (dokumenty leżą w `wyniki/`), więc test też nie powinien.
    """
    import shutil
    import tempfile

    from app.config import DANE

    katalog = Path(tempfile.mkdtemp(dir=DANE, prefix="test-konwersji-"))
    yield katalog
    shutil.rmtree(katalog, ignore_errors=True)


@pytest.mark.konwerter
def test_konwersja_docx_na_pdf(katalog_konwersji):
    """Jedyny test dotykający prawdziwego konwertera — reszta chodzi na atrapie."""
    if pdf.dostepny_konwerter() == "brak":
        pytest.skip("brak Worda i LibreOffice'a")
    from docx import Document

    zrodlo = katalog_konwersji / "dokument.docx"
    dokument = Document()
    dokument.add_paragraph("Operat techniczny 001/2026")
    dokument.save(zrodlo)

    wynik = pdf.docx_na_pdf(zrodlo, katalog_konwersji / "dokument.pdf")
    assert wynik.exists()
    tekst = "".join(strona.extract_text() for strona in PdfReader(str(wynik)).pages)
    assert "001/2026" in tekst


def test_zlozony_pdf_ma_numer_roboty_w_tytule(tmp_path):
    """Czytnik PDF-a nazywa kartę tytułem z metadanych, a bez niego — ostatnim członem
    adresu. U brata wychodziło z tego „wynik”, choć plik nazywa się numerem roboty.

    Tytuł jedzie razem z plikiem, więc numer widać też we właściwościach dokumentu
    po wysłaniu go do ośrodka.
    """
    a = _pdf(tmp_path / "a.pdf")
    wynik = pdf.polacz_pdf([a], tmp_path / "G.05.06.06.2026.pdf",
                           tytul="G.05.06.06.2026")

    assert PdfReader(str(wynik)).metadata.title == "G.05.06.06.2026"


def test_sklejanie_bez_tytulu_nie_dopisuje_metadanych(tmp_path):
    """Sklejanie służy też do innych rzeczy — pusty tytuł ma zostawić plik w spokoju."""
    a = _pdf(tmp_path / "a.pdf")
    wynik = pdf.polacz_pdf([a], tmp_path / "wynik.pdf")

    assert not (PdfReader(str(wynik)).metadata or {}).get("/Title")

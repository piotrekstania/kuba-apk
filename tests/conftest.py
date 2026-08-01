"""Wspólne rusztowanie testów.

Najważniejsza sztuczka: moduły robią `from .config import WYNIKI`, więc ścieżki są
**przywiązane do modułu w chwili importu**. Podmiana samego `app.config` niczego by nie
dała — trzeba podmienić nazwę w każdym module, który ją u siebie trzyma. Robi to
fixture `srodowisko`, dzięki czemu żaden test nie dotyka prawdziwych `wyniki/` i `dane/`.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from docx import Document
from docx.shared import Pt

KORZEN = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KORZEN))


# --- pomocnicze budowanie dokumentów -----------------------------------------

def zbuduj_docx(sciezka: Path, akapity: list[str | tuple], **kwargs) -> Path:
    """Prosty dokument z listy akapitów.

    Element listy to napis albo krotka (tekst, rozmiar_pt, pogrubienie).
    """
    dokument = Document()
    for pozycja in akapity:
        tekst, rozmiar, pogrubienie = (
            pozycja if isinstance(pozycja, tuple) else (pozycja, 10, False))
        akapit = dokument.add_paragraph()
        bieg = akapit.add_run(tekst)
        bieg.font.size = Pt(rozmiar)
        bieg.bold = pogrubienie
    if kwargs.get("tabela"):
        tabela = dokument.add_table(rows=4, cols=2)
        tabela.rows[0].cells[0].text = "Nagłówek A"
        tabela.rows[0].cells[1].text = "Nagłówek B"
        tabela.rows[1].cells[0].text = "{%tr for w in wiersze %}"
        tabela.rows[2].cells[0].text = "{{ w.a }}"
        tabela.rows[2].cells[1].text = "{{ w.b }}"
        tabela.rows[3].cells[0].text = "{%tr endfor %}"
    sciezka.parent.mkdir(parents=True, exist_ok=True)
    dokument.save(sciezka)
    return sciezka


@pytest.fixture
def srodowisko(tmp_path, monkeypatch):
    """Izolowana instalacja programu: własne szablony/, wyniki/, dane/ i baza.

    Zwraca obiekt z gotowymi ścieżkami i skrótem `dodaj_szablon`.
    """
    from app import aktualizacja, config, db, generator, main, operaty, pdf, szablony

    szablony_kat = tmp_path / "szablony"
    wyniki_kat = tmp_path / "wyniki"
    dane_kat = tmp_path / "dane"
    for katalog in (szablony_kat, wyniki_kat, dane_kat):
        katalog.mkdir(parents=True, exist_ok=True)
    baza = dane_kat / "operaty.sqlite3"

    monkeypatch.setattr(config, "BAZA", tmp_path, raising=False)
    monkeypatch.setattr(config, "SZABLONY", szablony_kat, raising=False)
    monkeypatch.setattr(config, "WYNIKI", wyniki_kat, raising=False)
    monkeypatch.setattr(config, "DANE", dane_kat, raising=False)
    monkeypatch.setattr(config, "BAZA_DANYCH", baza, raising=False)

    monkeypatch.setattr(db, "BAZA_DANYCH", baza)
    monkeypatch.setattr(db, "DANE", dane_kat)
    monkeypatch.setattr(szablony, "SZABLONY", szablony_kat)
    monkeypatch.setattr(operaty, "WYNIKI", wyniki_kat)
    monkeypatch.setattr(operaty, "DANE", dane_kat)
    monkeypatch.setattr(operaty, "PODGLADY", dane_kat / "podglad")
    monkeypatch.setattr(pdf, "KATALOG_ROBOCZY", dane_kat / "konwersja")
    monkeypatch.setattr(main, "WYNIKI", wyniki_kat)
    monkeypatch.setattr(main, "DANE", dane_kat)
    monkeypatch.setattr(main, "DZIENNIK_BLEDOW", dane_kat / "bledy.log")
    monkeypatch.setattr(aktualizacja, "BAZA", tmp_path)
    monkeypatch.setattr(aktualizacja, "DANE", dane_kat)
    monkeypatch.setattr(aktualizacja, "BAZA_DANYCH", baza)
    monkeypatch.setattr(aktualizacja, "PLIK_WERSJI", tmp_path / "WERSJA")
    monkeypatch.setattr(aktualizacja, "KOPIE", dane_kat / "kopie")
    monkeypatch.setattr(aktualizacja, "ZNACZNIK_NOWOSCI", dane_kat / "co_nowego.txt")

    db.init()

    class Srodowisko:
        katalog = tmp_path
        szablony = szablony_kat
        wyniki = wyniki_kat
        dane = dane_kat
        baza_danych = baza

        @staticmethod
        def dodaj_szablon(nazwa: str, akapity: list, opis: dict | None = None, **kwargs):
            import json
            plik = zbuduj_docx(szablony_kat / f"{nazwa}.docx", akapity, **kwargs)
            if opis is not None:
                plik.with_suffix(".json").write_text(
                    json.dumps(opis, ensure_ascii=False), encoding="utf-8")
            return plik

    # Generator woła teryt.jednostka() przy polach typu „teryt” — bez bazy TERYT
    # oddaje puste napisy i to nam w testach wystarczy.
    monkeypatch.setattr(generator.teryt, "jednostka", lambda identyfikator: None)
    monkeypatch.setattr(generator.teryt, "obreb", lambda identyfikator: None)
    return Srodowisko


@pytest.fixture
def bez_konwertera(monkeypatch):
    """Podmienia konwersję DOCX→PDF na atrapę: testy mają chodzić bez Worda i LibreOffice."""
    from app import operaty, pdf

    def atrapa(zrodlo, cel=None):
        """Udaje konwersję, ale oddaje **prawdziwy** jednostronicowy PDF.

        Zaślepka w rodzaju `b"%PDF-1.4"` przechodzi przez `exists()`, ale wykłada się
        dopiero w pypdf przy sklejaniu — test przechodziłby wtedy z niewłaściwego powodu.
        """
        from pypdf import PdfWriter
        cel = Path(cel) if cel else Path(zrodlo).with_suffix(".pdf")
        cel.parent.mkdir(parents=True, exist_ok=True)
        zapis = PdfWriter()
        zapis.add_blank_page(width=595, height=842)      # A4 w punktach
        with open(cel, "wb") as wyjscie:
            zapis.write(wyjscie)
        return cel

    monkeypatch.setattr(pdf, "docx_na_pdf", atrapa)
    monkeypatch.setattr(pdf, "docx_na_pdf_wsad",
                        lambda pary: [atrapa(z, c) for z, c in pary])
    monkeypatch.setattr(pdf, "dostepny_konwerter", lambda: "libreoffice")
    monkeypatch.setattr(operaty.pdf, "docx_na_pdf", atrapa)
    monkeypatch.setattr(operaty.pdf, "docx_na_pdf_wsad",
                        lambda pary: [atrapa(z, c) for z, c in pary])
    return atrapa


@pytest.fixture
def klient(srodowisko, bez_konwertera, monkeypatch):
    """TestClient z wyłączonym pobieraniem TERYT-u (żaden test nie rusza sieci)."""
    from fastapi.testclient import TestClient

    from app import main, teryt

    monkeypatch.setattr(teryt, "pusto", lambda: False)
    monkeypatch.setattr(main.teryt, "pusto", lambda: False)
    with TestClient(main.app, raise_server_exceptions=False) as klient_testowy:
        klient_testowy.srodowisko = srodowisko
        yield klient_testowy

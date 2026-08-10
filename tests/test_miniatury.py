"""Miniatury stron PDF — podglądy do układania kolejności przed sklejeniem operatu.

Dwie rzeczy, które psują się tu cicho i dlatego mają osobne testy:

* **równoległe renderowanie**. Strona składania pobiera kilkanaście miniatur naraz,
  a silnik pdfium nie jest bezpieczny wielowątkowo — wejście w niego dwoma wątkami
  potrafi wywalić **cały proces**, bez żadnego wyjątku w Pythonie. Objawem u brata
  byłby zgaszony program, a nie komunikat, więc na to musi być strażnik.
* **plik, który nie jest PDF-em**. Brat dokłada do katalogu operatu, co uzna za
  potrzebne; strona z układaniem ma wtedy dalej działać, a nie pokazać stronę błędu.
"""
from __future__ import annotations

import threading
import time
from pathlib import Path

from PIL import Image
from pypdf import PdfWriter

from app import miniatury

A4_PUNKTY = (595, 842)


def _pdf(sciezka: Path, stron: int = 1, poziomo: bool = False) -> Path:
    zapis = PdfWriter()
    szerokosc, wysokosc = reversed(A4_PUNKTY) if poziomo else A4_PUNKTY
    for _ in range(stron):
        zapis.add_blank_page(width=szerokosc, height=wysokosc)
    with open(sciezka, "wb") as wyjscie:
        zapis.write(wyjscie)
    return sciezka


def _rozmiar(png: bytes) -> tuple[int, int]:
    import io
    return Image.open(io.BytesIO(png)).size


# --- renderowanie ------------------------------------------------------------

def test_miniatura_to_png_pierwszej_strony(tmp_path):
    png = miniatury.miniatura(_pdf(tmp_path / "spis.pdf"))

    assert png[:8] == b"\x89PNG\r\n\x1a\n", "przeglądarka dostaje to jako obrazek"
    szerokosc, wysokosc = _rozmiar(png)
    assert wysokosc > szerokosc, "A4 pionowo ma zostać pionowo"
    assert 200 < szerokosc < 400, f"miniatura ma być mała i czytelna, wyszło {szerokosc} px"


def test_obrot_zamienia_boki(tmp_path):
    """Brat obraca kafelki myszą — skan wpięty bokiem musi dać się postawić prosto."""
    plik = _pdf(tmp_path / "skan.pdf")

    prosto = _rozmiar(miniatury.miniatura(plik))
    obrocone = _rozmiar(miniatury.miniatura(plik, obrot=90))

    assert obrocone == (prosto[1], prosto[0])


def test_obrot_liczy_sie_modulo(tmp_path):
    """Klikanie w kółko dobija do 360 — to ma być to samo co 0, a nie błąd."""
    plik = _pdf(tmp_path / "skan.pdf")

    assert (_rozmiar(miniatury.miniatura(plik, obrot=360))
            == _rozmiar(miniatury.miniatura(plik, obrot=0)))
    assert (_rozmiar(miniatury.miniatura(plik, obrot=450))
            == _rozmiar(miniatury.miniatura(plik, obrot=90)))


def test_strona_pozioma_zostaje_pozioma(tmp_path):
    """Wykaz zmian działki jest poziomy — miniatura ma to pokazywać."""
    szerokosc, wysokosc = _rozmiar(miniatury.miniatura(_pdf(tmp_path / "wykaz.pdf",
                                                            poziomo=True)))
    assert szerokosc > wysokosc


# --- liczenie stron ----------------------------------------------------------

def test_liczba_stron(tmp_path):
    assert miniatury.liczba_stron(_pdf(tmp_path / "operat.pdf", stron=7)) == 7


def test_plik_ktory_nie_jest_pdfem_daje_zero_stron(tmp_path):
    """Brat dokłada do katalogu operatu własne pliki — strona z układaniem ma przeżyć."""
    smieci = tmp_path / "notatka.pdf"
    smieci.write_bytes(b"to nie jest PDF")

    assert miniatury.liczba_stron(smieci) == 0
    assert miniatury.liczba_stron(tmp_path / "nie ma takiego.pdf") == 0


# --- pdfium tylko pojedynczo -------------------------------------------------

class _UdawanyDokument:
    """Udaje `PdfDocument` na tyle, żeby dało się policzyć wejścia do renderowania."""

    def __init__(self, wspolbieznie: list, szczyt: list, zamkniete: list):
        self.wspolbieznie, self.szczyt, self.zamkniete = wspolbieznie, szczyt, zamkniete

    def __getitem__(self, numer):
        return self

    def render(self, scale, rotation):
        self.wspolbieznie.append(1)
        self.szczyt.append(len(self.wspolbieznie))
        time.sleep(0.02)                 # bez tego wątki mijałyby się same z siebie
        self.wspolbieznie.pop()
        return self

    def to_pil(self):
        return Image.new("RGB", (10, 10))

    def close(self):
        self.zamkniete.append(1)


def test_renderowanie_nie_idzie_dwoma_watkami_naraz(tmp_path, monkeypatch):
    """Strona składania woła miniatury równolegle, a pdfium tego nie zniesie.

    Objawem nie byłby wyjątek, tylko zgaszony program — dlatego liczymy wejścia
    do renderowania, a nie czekamy na awarię.
    """
    wspolbieznie: list = []
    szczyt: list = []
    zamkniete: list = []
    monkeypatch.setattr(miniatury, "_dokument",
                        lambda plik: _UdawanyDokument(wspolbieznie, szczyt, zamkniete))
    plik = tmp_path / "operat.pdf"

    watki = [threading.Thread(target=miniatury.miniatura, args=(plik,)) for _ in range(6)]
    for watek in watki:
        watek.start()
    for watek in watki:
        watek.join(10)

    assert szczyt and max(szczyt) == 1, \
        "dwa wątki w pdfium naraz potrafią wywalić cały proces"
    assert len(zamkniete) == 6, "każdy dokument ma się zamknąć — na Windowsie blokuje plik"


def test_dokument_zamyka_sie_takze_po_bledzie(tmp_path, monkeypatch):
    """Blokada i uchwyt do pliku mają się zwolnić, choćby renderowanie padło."""
    zamkniete: list = []

    class Padajacy(_UdawanyDokument):
        def render(self, scale, rotation):
            raise RuntimeError("uszkodzona strona")

    monkeypatch.setattr(miniatury, "_dokument",
                        lambda plik: Padajacy([], [], zamkniete))

    try:
        miniatury.miniatura(tmp_path / "operat.pdf")
    except RuntimeError:
        pass

    assert zamkniete == [1]
    assert not miniatury._BLOKADA_RENDEROWANIA.locked(), \
        "zakleszczona blokada zawiesza całą stronę składania"

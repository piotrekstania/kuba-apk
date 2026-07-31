"""Miniatury pierwszej strony PDF-a — do układania kolejności przed sklejeniem.

Renderujemy po stronie programu, nie w przeglądarce: dzięki temu strona z układaniem
jest zwykłą listą obrazków, którą da się przeciągać myszą, zamiast kilkunastu ramek
z wbudowanym czytnikiem PDF, które połykają zdarzenia myszy.

`pypdfium2` to jedno koło z pip (silnik pdfium w środku, bez instalowania czegokolwiek
w systemie), `Pillow` zapisuje wynik do PNG.
"""
from __future__ import annotations

import io
from pathlib import Path

import pypdfium2 as pdfium

from .pdf import slad

SKALA = 0.45              # ok. 280 px szerokości dla A4 — czytelne i lekkie
LICZBA_STRON_W_OPISIE = True


def _dokument(plik: Path) -> pdfium.PdfDocument:
    return pdfium.PdfDocument(str(plik))


def miniatura(plik: Path, obrot: int = 0) -> bytes:
    """PNG pierwszej strony. `obrot` w stopniach: 0, 90, 180, 270."""
    slad(f"renderuję miniaturę: {plik.name}")
    dokument = _dokument(plik)
    try:
        obraz = dokument[0].render(scale=SKALA, rotation=obrot % 360).to_pil()
        bufor = io.BytesIO()
        obraz.save(bufor, format="PNG", optimize=True)
        return bufor.getvalue()
    finally:
        dokument.close()


def liczba_stron(plik: Path) -> int:
    try:
        dokument = _dokument(plik)
        try:
            return len(dokument)
        finally:
            dokument.close()
    except Exception:
        return 0

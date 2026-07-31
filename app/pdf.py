"""Konwersja DOCX -> PDF i łączenie plików PDF.

Kolejność wyboru konwertera:
1. Microsoft Word przez COM (docx2pdf) — jeśli jest zainstalowany, wygląd 1:1.
2. LibreOffice w trybie --headless — działa wszędzie, także bez Worda.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from pypdf import PdfReader, PdfWriter

from .config import BAZA, DANE

# Osobny profil LibreOffice — dzięki temu konwersja działa również wtedy,
# gdy użytkownik ma otwarty zwykły LibreOffice.
KATALOG_ROBOCZY = DANE / "konwersja"
KATALOG_ROBOCZY.mkdir(parents=True, exist_ok=True)
PROFIL_LIBREOFFICE = (KATALOG_ROBOCZY / "profil").as_uri()

KANDYDACI_LIBREOFFICE = [
    # 1. wersja przenośna dołożona obok programu — nic nie trzeba instalować
    str(BAZA / "libreoffice" / "program" / "soffice.exe"),
    str(BAZA / "libreoffice" / "App" / "libreoffice" / "program" / "soffice.exe"),
    str(BAZA / "LibreOfficePortable" / "App" / "libreoffice" / "program" / "soffice.exe"),
    str(BAZA / "libreoffice" / "program" / "soffice"),
    # 2. zwykła instalacja w systemie
    "soffice", "libreoffice",
    r"C:\Program Files\LibreOffice\program\soffice.exe",
    r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
    "/usr/bin/soffice", "/snap/bin/libreoffice",
    "/Applications/LibreOffice.app/Contents/MacOS/soffice",
]


class BrakKonwertera(RuntimeError):
    pass


def sciezka_libreoffice() -> str | None:
    for kandydat in KANDYDACI_LIBREOFFICE:
        znaleziony = shutil.which(kandydat) if os.sep not in kandydat else (
            kandydat if Path(kandydat).exists() else None)
        if znaleziony:
            return znaleziony
    return None


def _word_dostepny() -> bool:
    if sys.platform != "win32":
        return False
    try:
        import win32com.client  # noqa: F401  (dokładamy z docx2pdf)
        import winreg
        winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, "Word.Application")
        return True
    except Exception:
        return False


def dostepny_konwerter() -> str:
    """Zwraca 'word', 'libreoffice' albo 'brak' — do pokazania w interfejsie."""
    if _word_dostepny():
        return "word"
    if sciezka_libreoffice():
        return "libreoffice"
    return "brak"


def docx_na_pdf(zrodlo: Path, cel: Path | None = None) -> Path:
    cel = cel or zrodlo.with_suffix(".pdf")
    konwerter = dostepny_konwerter()

    if konwerter == "word":
        from docx2pdf import convert
        convert(str(zrodlo), str(cel))
        if cel.exists():
            return cel

    if konwerter == "libreoffice" or not cel.exists():
        soffice = sciezka_libreoffice()
        if not soffice:
            raise BrakKonwertera(
                "Nie znaleziono ani Microsoft Word, ani LibreOffice. "
                "Zainstaluj LibreOffice (darmowy), żeby generować PDF-y."
            )
        # Katalog roboczy wewnątrz projektu, a nie w /tmp: LibreOffice ze Snapa/Flatpaka
        # ma własny, odizolowany /tmp i gotowy plik byłby dla nas niewidoczny.
        with tempfile.TemporaryDirectory(dir=KATALOG_ROBOCZY) as tymczasowy:
            wynik = subprocess.run(
                [soffice, "--headless", "--norestore", "--nolockcheck",
                 f"-env:UserInstallation={PROFIL_LIBREOFFICE}",
                 "--convert-to", "pdf", "--outdir", tymczasowy, str(zrodlo)],
                capture_output=True, text=True, timeout=180,
            )
            powstaly = Path(tymczasowy) / (zrodlo.stem + ".pdf")
            if not powstaly.exists():                       # awaryjnie: cokolwiek co powstało
                inne = list(Path(tymczasowy).glob("*.pdf"))
                powstaly = inne[0] if inne else powstaly
            if not powstaly.exists():
                raise BrakKonwertera(
                    f"LibreOffice nie utworzył PDF-a.\n{wynik.stdout}\n{wynik.stderr}")
            cel.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(powstaly), cel)
    return cel


def polacz_pdf(pliki: list[Path], cel: Path) -> Path:
    """Skleja PDF-y w podanej kolejności."""
    if not pliki:
        raise ValueError("Nie wskazano żadnych plików do połączenia.")
    zapis = PdfWriter()
    for plik in pliki:
        for strona in PdfReader(str(plik)).pages:
            zapis.add_page(strona)
    cel.parent.mkdir(parents=True, exist_ok=True)
    with open(cel, "wb") as wyjscie:
        zapis.write(wyjscie)
    return cel


def liczba_stron(plik: Path) -> int:
    try:
        return len(PdfReader(str(plik)).pages)
    except Exception:
        return 0

"""Konwersja DOCX -> PDF i łączenie plików PDF.

Kolejność wyboru konwertera:
1. Microsoft Word przez COM — jeśli jest zainstalowany, wygląd 1:1 z dokumentem.
2. LibreOffice w trybie --headless — zapas na komputery bez Worda.

Word sterujemy sami (pywin32), a nie biblioteką docx2pdf, z dwóch powodów:
* docx2pdf woła `Dispatch` bez `CoInitialize()`, a trasy FastAPI wykonują się
  w wątkach roboczych — tam COM nie jest zainicjowany i konwersja pada;
* `ExportAsFixedFormat` daje kontrolę nad jakością PDF-a i zakładkami.
"""
from __future__ import annotations

import gc
import os
import shutil
import subprocess
import sys
import tempfile
import threading
from contextlib import contextmanager
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

# Konwersje puszczamy pojedynczo, **niezależnie od konwertera**. Word to jedna aplikacja
# na komputerze i dwie równoległe konwersje potrafią sobie zamknąć instancję, a dwa
# LibreOffice'y dzielące ten sam profil blokują się nawzajem. Sprawdzone: strona składania
# pobiera miniatury równolegle i potrafiła zawiesić obie konwersje naraz.
_BLOKADA_KONWERSJI = threading.Lock()

# stałe Worda (nie importujemy makr Office, żeby nie wymagać cache'u typów)
_WD_FORMAT_PDF = 17               # wdExportFormatPDF
_WD_JAKOSC_DRUK = 0               # wdExportOptimizeForPrint
_WD_CALY_DOKUMENT = 0             # wdExportAllDocument
_WD_TRESC_DOKUMENTU = 0           # wdExportDocumentContent
_WD_ZAKLADKI_NAGLOWKI = 1         # wdExportCreateHeadingBookmarks
_WD_NIE_ZAPISUJ = 0               # wdDoNotSaveChanges


class BrakKonwertera(RuntimeError):
    pass


class BladPliku(RuntimeError):
    """Plik, którego nie da się przeczytać jako PDF — uszkodzony albo zabezpieczony."""


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
        import winreg

        import win32com.client  # noqa: F401  (bez pywin32 nie ma czym sterować Wordem)
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


def slad(tekst: str) -> None:
    """Wypisuje krok konwersji, gdy włączona jest diagnostyka (`narzedzia/diagnostyka.bat`).

    Z `flush=True`, bo przy twardej awarii Worda bufor nie zdąży się opróżnić i ostatnia
    linia — ta najważniejsza, mówiąca, na czym program stanął — przepadłaby.
    """
    if os.environ.get("GENERATOR_DIAGNOSTYKA") == "1":
        print(f"[konwersja] {tekst}", flush=True)


@contextmanager
def _com():
    """Inicjuje COM dla bieżącego wątku (trasy FastAPI chodzą w puli wątków)."""
    import pythoncom
    pythoncom.CoInitialize()
    try:
        yield
    finally:
        pythoncom.CoUninitialize()


def _wordem_wsad(pary: list[tuple[Path, Path]]) -> None:
    """Eksportuje kilka dokumentów w **jednej** sesji Worda.

    Najdroższe w konwersji jest uruchomienie Worda, nie sam dokument. Przy operacie
    z czterema plikami osobne uruchomienia kosztowały cztery starty; tutaj jest jeden.
    """
    import win32com.client

    with _com():                      # szeregowanie robi już `docx_na_pdf`
        word = None
        try:
            # DispatchEx = własna instancja Worda; nie przejmujemy tej,
            # w której użytkownik ma właśnie otwarte swoje pliki.
            slad(f"otwieram Worda ({len(pary)} dok.)")
            word = win32com.client.DispatchEx("Word.Application")
            word.Visible = False
            word.DisplayAlerts = 0                       # wdAlertsNone

            for zrodlo, cel in pary:
                dokument = None
                try:
                    dokument = word.Documents.Open(
                        str(zrodlo), ReadOnly=True, AddToRecentFiles=False,
                        ConfirmConversions=False, Visible=False,
                    )
                    slad(f"eksportuję do PDF: {cel.name}")
                    dokument.ExportAsFixedFormat(
                        OutputFileName=str(cel),
                        ExportFormat=_WD_FORMAT_PDF,
                        OpenAfterExport=False,
                        OptimizeFor=_WD_JAKOSC_DRUK,
                        Range=_WD_CALY_DOKUMENT,
                        Item=_WD_TRESC_DOKUMENTU,
                        IncludeDocProps=True,
                        CreateBookmarks=_WD_ZAKLADKI_NAGLOWKI,
                        DocStructureTags=True,
                        BitmapMissingFonts=True,
                    )
                finally:
                    if dokument is not None:
                        try:
                            dokument.Close(_WD_NIE_ZAPISUJ)
                        except Exception:
                            pass
                    dokument = None
        finally:
            if word is not None:
                try:
                    word.Quit(_WD_NIE_ZAPISUJ)
                except Exception:
                    pass
            # Wskaźniki COM muszą zniknąć, **zanim** wyjdziemy z `_com()`. Zwykłe
            # wyjście z funkcji zwolniłoby je dopiero po `CoUninitialize`, a zwalnianie
            # interfejsu w wątku odłączonym już od COM-u potrafi wywalić cały proces
            # (naruszenie ochrony pamięci, bez żadnego wyjątku w Pythonie).
            word = None
            gc.collect()
            slad("zamknięto Worda")


def _konwersja_wordem(zrodlo: Path, cel: Path) -> None:
    _wordem_wsad([(zrodlo.resolve(), _przygotuj_cel(cel))])


def _przygotuj_cel(cel: Path) -> Path:
    cel = cel.resolve()
    cel.parent.mkdir(parents=True, exist_ok=True)
    return cel


def _libreoffice_wsad(pary: list[tuple[Path, Path]]) -> None:
    """To samo co wyżej, ale LibreOffice'em: jedno uruchomienie na komplet plików."""
    soffice = sciezka_libreoffice()
    if not soffice:
        raise BrakKonwertera(
            "Nie znaleziono ani Microsoft Word, ani LibreOffice. "
            "Zainstaluj LibreOffice (darmowy), żeby generować PDF-y."
        )
    slad(f"LibreOffice startuje ({len(pary)} dok.)")
    # Katalog roboczy wewnątrz projektu, a nie w /tmp: LibreOffice ze Snapa/Flatpaka
    # ma własny, odizolowany /tmp i gotowe pliki byłyby dla nas niewidoczne.
    with tempfile.TemporaryDirectory(dir=KATALOG_ROBOCZY) as tymczasowy:
        wynik = subprocess.run(
            [soffice, "--headless", "--norestore", "--nolockcheck",
             f"-env:UserInstallation={PROFIL_LIBREOFFICE}",
             "--convert-to", "pdf", "--outdir", tymczasowy] + [str(z) for z, _ in pary],
            capture_output=True, text=True, timeout=300,
        )
        for zrodlo, cel in pary:
            powstaly = Path(tymczasowy) / (zrodlo.stem + ".pdf")
            if not powstaly.exists():
                raise BrakKonwertera(
                    f"LibreOffice nie utworzył PDF-a z {zrodlo.name}.\n"
                    f"{wynik.stdout}\n{wynik.stderr}")
            shutil.move(str(powstaly), _przygotuj_cel(cel))
            slad(f"LibreOffice skończył: {cel.name}")


def _konwersja_libreoffice(zrodlo: Path, cel: Path) -> None:
    slad(f"LibreOffice startuje dla {zrodlo.name}")
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
        slad(f"LibreOffice skończył: {cel.name}")


def docx_na_pdf(zrodlo: Path, cel: Path | None = None) -> Path:
    cel = cel or zrodlo.with_suffix(".pdf")
    konwerter = dostepny_konwerter()
    slad(f"{zrodlo.name} -> {cel.name}, konwerter: {konwerter}")

    if konwerter == "brak":
        raise BrakKonwertera(
            "Nie znaleziono ani Microsoft Word, ani LibreOffice. "
            "Zainstaluj jeden z nich, żeby generować PDF-y."
        )

    with _BLOKADA_KONWERSJI:
        _konwertuj(zrodlo, cel, konwerter)

    if not cel.exists():
        raise BrakKonwertera(f"Konwersja się nie powiodła — nie powstał plik {cel.name}.")
    return cel


def docx_na_pdf_wsad(pary: list[tuple[Path, Path]]) -> list[Path]:
    """Konwertuje komplet dokumentów w jednym uruchomieniu konwertera.

    Zwraca listę tych, które się udały. Pojedyncza wywrotka nie przekreśla reszty:
    to jest używane do przygotowania podglądów w tle, więc lepiej mieć trzy miniatury
    z czterech niż żadnej.
    """
    if not pary:
        return []
    konwerter = dostepny_konwerter()
    slad(f"wsad: {len(pary)} dok., konwerter: {konwerter}")
    if konwerter == "brak":
        raise BrakKonwertera("Nie znaleziono ani Microsoft Word, ani LibreOffice.")

    with _BLOKADA_KONWERSJI:
        try:
            if konwerter == "word":
                _wordem_wsad([(z.resolve(), _przygotuj_cel(c)) for z, c in pary])
            else:
                _libreoffice_wsad(pary)
        except Exception as blad:
            slad(f"wsad nie wyszedł ({blad}) — próbuję pojedynczo")
            for zrodlo, cel in pary:
                try:
                    _konwertuj(zrodlo, cel, konwerter)
                except Exception:
                    pass
    return [c for _, c in pary if c.exists()]


def _konwertuj(zrodlo: Path, cel: Path, konwerter: str) -> None:
    """Sama konwersja — wołana już pod blokadą, więc nigdy nie chodzi równolegle."""
    if konwerter == "word":
        try:
            _konwersja_wordem(zrodlo, cel)
        except Exception as blad:
            # Word bywa zajęty (otwarte okno dialogowe, aktualizacja Office) —
            # jeśli obok jest LibreOffice, próbujemy nim, zamiast poddawać się.
            slad(f"Word nie dał rady ({blad}) — próbuję LibreOffice")
            if sciezka_libreoffice():
                _konwersja_libreoffice(zrodlo, cel)
            else:
                raise BrakKonwertera(
                    f"Microsoft Word nie zrobił PDF-a: {blad}\n"
                    "Sprawdź, czy Word nie czeka z otwartym oknem (np. aktywacja "
                    "albo pytanie o zapis) i spróbuj ponownie."
                ) from blad
    else:
        _konwersja_libreoffice(zrodlo, cel)


def polacz_pdf(pliki: list[Path], cel: Path,
               etykiety: dict[Path, str] | None = None,
               obroty: dict[Path, int] | None = None) -> Path:
    """Skleja PDF-y w podanej kolejności.

    `etykiety` to nazwy do pokazania użytkownikowi — pliki robocze mają na dysku
    nazwy ze znacznikiem czasu, a on musi rozpoznać swój załącznik po tym, jak
    go sam nazwał.
    """
    if not pliki:
        raise ValueError("Nie wskazano żadnych plików do połączenia.")
    zapis = PdfWriter()
    for plik in pliki:
        # Nazwa pliku w komunikacie jest tu najważniejsza: przy sklejaniu kilkunastu
        # załączników użytkownik musi wiedzieć, który z nich jest do wymiany.
        kat = (obroty or {}).get(plik, 0) % 360
        try:
            for strona in PdfReader(str(plik)).pages:
                if kat:
                    strona.rotate(kat)      # obrót zapisany w PDF-ie, bez przerysowywania
                zapis.add_page(strona)
        except Exception as blad:
            raise BladPliku(
                f"Nie udało się odczytać pliku „{(etykiety or {}).get(plik, plik.name)}” "
                "jako PDF. Bywa tak, gdy plik jest uszkodzony, niedokończony albo "
                "zabezpieczony hasłem — otwórz go i zapisz jeszcze raz jako PDF."
            ) from blad
    cel.parent.mkdir(parents=True, exist_ok=True)
    with open(cel, "wb") as wyjscie:
        zapis.write(wyjscie)
    return cel


def liczba_stron(plik: Path) -> int:
    try:
        return len(PdfReader(str(plik)).pages)
    except Exception:
        return 0

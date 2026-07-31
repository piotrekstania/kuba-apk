"""Robi na dysku instalację taką, jaką ma brat — do testowania aktualizacji.

Kopia robocza gita nie aktualizuje się sama (chroni niezacommitowane zmiany), więc
żeby zobaczyć to, co zobaczy brat, trzeba mieć rozpakowany `.zip` bez katalogu `.git`.
Dokładnie to robi ten skrypt: pobiera bieżącą wersję z GitHuba i rozpakowuje ją
do wskazanego katalogu.

    python narzedzia/instalacja_testowa.py E:\\test-brata
    python narzedzia/instalacja_testowa.py E:\\test-brata --stara-wersja

Z `--stara-wersja` podmienia numer w pliku WERSJA na starszy, żeby przy pierwszym
uruchomieniu `start.bat` naprawdę wykonał aktualizację — łącznie z komunikatem
„co nowego" na stronie głównej.

Danych nie kasuje: jeśli w katalogu jest już `dane/`, `wyniki/` albo `szablony/`,
zostają nietknięte — po to, żeby dało się sprawdzić, czy aktualizacja ich nie zjada.
"""
import argparse
import shutil
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.aktualizacja import AKTUALIZOWANE, URL_PACZKA  # noqa: E402


def pobierz(katalog_roboczy: Path) -> Path:
    paczka = katalog_roboczy / "main.zip"
    print(f"Pobieram {URL_PACZKA} ...")
    with urllib.request.urlopen(URL_PACZKA, timeout=60) as odpowiedz:
        paczka.write_bytes(odpowiedz.read())
    with zipfile.ZipFile(paczka) as zip_plik:
        zip_plik.extractall(katalog_roboczy)
    return next(s for s in katalog_roboczy.iterdir() if s.is_dir())


def main() -> int:
    parser = argparse.ArgumentParser(description="Tworzy instalację testową jak u brata.")
    parser.add_argument("katalog", help="gdzie ma powstać instalacja")
    parser.add_argument("--stara-wersja", action="store_true",
                        help="cofnij numer w WERSJA, żeby start.bat zrobił aktualizację")
    argumenty = parser.parse_args()

    cel = Path(argumenty.katalog).resolve()
    cel.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tymczasowy:
        zrodlo = pobierz(Path(tymczasowy))
        for nazwa in AKTUALIZOWANE:
            skad = zrodlo / nazwa
            if not skad.exists():
                continue
            if skad.is_dir():
                shutil.copytree(skad, cel / nazwa, dirs_exist_ok=True)
            else:
                shutil.copy2(skad, cel / nazwa)

    if argumenty.stara_wersja:
        (cel / "WERSJA").write_text(
            "0000.00.00\nStara wersja testowa — start.bat powinien ją podmienić.",
            encoding="utf-8")

    print(f"\nGotowe: {cel}")
    print("Nie ma tam katalogu .git, więc program zachowuje się jak u brata.")
    if argumenty.stara_wersja:
        print("Numer wersji cofnięty — najbliższy start.bat pobierze aktualizację.")
    print(f"\nUruchom:  {cel / 'start.bat'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

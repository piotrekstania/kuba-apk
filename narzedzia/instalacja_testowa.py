"""Robi na dysku instalację taką, jaką ma brat — do testowania aktualizacji.

Kopia robocza gita nie aktualizuje się sama (chroni niezacommitowane zmiany), więc
żeby zobaczyć to, co zobaczy brat, trzeba mieć rozpakowany `.zip` bez katalogu `.git`.
Dokładnie to robi ten skrypt: pobiera bieżącą wersję z GitHuba i rozpakowuje ją
do wskazanego katalogu.

    python narzedzia/instalacja_testowa.py E:\\test-brata
    python narzedzia/instalacja_testowa.py E:\\test-brata --stara-wersja
    python narzedzia/instalacja_testowa.py E:\\test-brata --z-commita c3b1c98

Z `--stara-wersja` podmienia numer w pliku WERSJA na starszy, żeby przy pierwszym
uruchomieniu `start.bat` naprawdę wykonał aktualizację — łącznie z komunikatem
„co nowego" na stronie głównej.

Z `--z-commita` instalacja powstaje ze **starego** kodu (np. z commita ostatniego
wydania, czyli tego, co brat ma dziś u siebie), a numer wersji jest od razu cofnięty.
Pierwszy `start.bat` robi wtedy dokładnie to, co zrobi u brata: stary `start.bat`
i stary aktualizator ściągają nowy kod z `main`. Bez tej opcji po wypchnięciu nowego
kodu nie ma już skąd wziąć starego — a to przejście psuje się najczęściej (pułapki
7b i 37).

Danych nie kasuje: jeśli w katalogu jest już `dane/` albo `wyniki/`, zostają nietknięte —
po to, żeby dało się sprawdzić, czy aktualizacja ich nie zjada. `szablony/` **są**
podmieniane, bo jadą razem z kodem.
"""
import argparse
import shutil
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.aktualizacja import AKTUALIZOWANE, REPO, URL_PACZKA  # noqa: E402


def adres_paczki(commit: str | None) -> str:
    """Paczka gałęzi `main` albo konkretnego commita (`--z-commita`)."""
    return f"https://github.com/{REPO}/archive/{commit}.zip" if commit else URL_PACZKA


def pobierz(katalog_roboczy: Path, adres: str = URL_PACZKA) -> Path:
    paczka = katalog_roboczy / "main.zip"
    print(f"Pobieram {adres} ...")
    with urllib.request.urlopen(adres, timeout=60) as odpowiedz:
        paczka.write_bytes(odpowiedz.read())
    with zipfile.ZipFile(paczka) as zip_plik:
        zip_plik.extractall(katalog_roboczy)
    return next(s for s in katalog_roboczy.iterdir() if s.is_dir())


def main() -> int:
    parser = argparse.ArgumentParser(description="Tworzy instalację testową jak u brata.")
    parser.add_argument("katalog", help="gdzie ma powstać instalacja")
    parser.add_argument("--stara-wersja", action="store_true",
                        help="cofnij numer w WERSJA, żeby start.bat zrobił aktualizację")
    parser.add_argument("--z-commita", metavar="SHA",
                        help="zbuduj instalację ze starego commita (np. ostatniego wydania), "
                             "żeby sprawdzić przejście na nowy kod; cofa też numer wersji")
    argumenty = parser.parse_args()
    # instalacja ze starego kodu ma sens tylko wtedy, gdy start.bat ją zaktualizuje
    stara_wersja = argumenty.stara_wersja or bool(argumenty.z_commita)

    cel = Path(argumenty.katalog).resolve()
    cel.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tymczasowy:
        zrodlo = pobierz(Path(tymczasowy), adres_paczki(argumenty.z_commita))
        for nazwa in AKTUALIZOWANE:
            skad = zrodlo / nazwa
            if not skad.exists():
                continue
            if skad.is_dir():
                shutil.copytree(skad, cel / nazwa, dirs_exist_ok=True)
            else:
                shutil.copy2(skad, cel / nazwa)

    if stara_wersja:
        (cel / "WERSJA").write_text(
            "0000.00.00\nStara wersja testowa — start.bat powinien ją podmienić.",
            encoding="utf-8")

    print(f"\nGotowe: {cel}")
    print("Nie ma tam katalogu .git, więc program zachowuje się jak u brata.")
    if stara_wersja:
        print("Numer wersji cofnięty — najbliższy start.bat pobierze aktualizację.")
    print(f"\nUruchom:  {cel / 'start.bat'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

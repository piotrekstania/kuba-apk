"""Instalacja testowa „jak u brata” (`narzedzia/instalacja_testowa.py`).

Najważniejsze, co się na niej sprawdza, to **przejście** ze starej wersji na nową:
stary `start.bat` i stary aktualizator ściągają nowy kod — dokładnie tak, jak będzie
u brata (pułapki 7b i 37). Po wypchnięciu nowego `main` stary kod leży już tylko
w paczce konkretnego commita, stąd `--z-commita`.
"""
from __future__ import annotations

import io
import sys
import zipfile
from pathlib import Path

from app import aktualizacja

KORZEN = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KORZEN / "narzedzia"))

import instalacja_testowa  # noqa: E402


class _Odpowiedz(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


def _podstaw_github(monkeypatch) -> list[str]:
    """Paczka w układzie GitHuba — wszystko w jednym podkatalogu. Zwraca pobrane adresy."""
    adresy: list[str] = []

    def urlopen(adres, timeout=None):
        adresy.append(adres)
        bufor = io.BytesIO()
        with zipfile.ZipFile(bufor, "w") as archiwum:
            archiwum.writestr("kuba-apk-c3b1c98/WERSJA", "2026.09.23-113\nOpis.")
            archiwum.writestr("kuba-apk-c3b1c98/start.bat", "@echo off\r\n")
            archiwum.writestr("kuba-apk-c3b1c98/app/main.py", "# kod z paczki")
        return _Odpowiedz(bufor.getvalue())

    monkeypatch.setattr(instalacja_testowa.urllib.request, "urlopen", urlopen)
    return adresy


def test_instalacja_ze_starego_commita_do_sprawdzenia_przejscia(tmp_path, monkeypatch):
    """Z `--z-commita` instalacja powstaje z paczki tamtego commita i od razu ma cofnięty
    numer wersji — bez tego `start.bat` uznałby ją za aktualną i przejścia by nie było."""
    adresy = _podstaw_github(monkeypatch)
    cel = tmp_path / "brat"
    monkeypatch.setattr(sys, "argv", ["instalacja_testowa.py", str(cel), "--z-commita", "c3b1c98"])

    assert instalacja_testowa.main() == 0

    assert adresy == [f"https://github.com/{aktualizacja.REPO}/archive/c3b1c98.zip"]
    assert (cel / "app" / "main.py").read_text(encoding="utf-8") == "# kod z paczki"
    assert (cel / "WERSJA").read_text(encoding="utf-8").startswith("0000.00.00")


def test_bez_commita_instalacja_z_galezi_glownej(tmp_path, monkeypatch):
    adresy = _podstaw_github(monkeypatch)
    cel = tmp_path / "brat"
    monkeypatch.setattr(sys, "argv", ["instalacja_testowa.py", str(cel)])

    assert instalacja_testowa.main() == 0

    assert adresy == [aktualizacja.URL_PACZKA]
    assert (cel / "WERSJA").read_text(encoding="utf-8").startswith("2026.09.23-113")

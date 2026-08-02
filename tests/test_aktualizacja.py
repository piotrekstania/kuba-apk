"""Automatyczna aktualizacja z GitHuba.

GitHub jest tu podstawiony lokalnym plikiem (`file://`), więc testy nie ruszają sieci.
Sprawdzamy to, co przy aktualizacji jest nieodwracalne: że dane użytkownika przeżywają,
że powstaje kopia i że nieudana aktualizacja zostawia działający program.
"""
from __future__ import annotations

import shutil
import urllib.error
import zipfile
from pathlib import Path

import pytest

from app import aktualizacja


def _instalacja(srodowisko, wersja: str = "2026.01.01.1") -> None:
    """Buduje „instalację u brata”: kod, szablon, wynik i baza."""
    baza = srodowisko.katalog
    (baza / "WERSJA").write_text(f"{wersja}\nStara wersja.", encoding="utf-8")
    (baza / "app").mkdir(exist_ok=True)
    (baza / "app" / "main.py").write_text("# stary kod", encoding="utf-8")
    (baza / "uruchom.py").write_text("# stary starter", encoding="utf-8")
    (srodowisko.szablony / "stary_wzor.docx").write_bytes(b"stara formatka")
    (srodowisko.wyniki / "001.2026").mkdir(parents=True, exist_ok=True)
    (srodowisko.wyniki / "001.2026" / "operat.json").write_text("{}", encoding="utf-8")
    (srodowisko.dane / "operaty.sqlite3").write_bytes(b"baza brata")


def _paczka(tmp_path: Path, wersja: str, pliki: dict[str, str]) -> Path:
    """Zip w układzie GitHuba: wszystko w jednym podkatalogu `<repo>-<galaz>`."""
    korzen = tmp_path / "paczka"
    projekt = korzen / "kuba-apk-main"
    for sciezka, tresc in {"WERSJA": wersja, "uruchom.py": "# nowy starter", **pliki}.items():
        cel = projekt / sciezka
        cel.parent.mkdir(parents=True, exist_ok=True)
        cel.write_text(tresc, encoding="utf-8")
    archiwum = shutil.make_archive(str(tmp_path / "nowa"), "zip", root_dir=korzen)
    return Path(archiwum)


def _kopie_aktualizacji(srodowisko) -> list[Path]:
    """Kopie zrobione przez aktualizator — to katalogi.

    W `dane/kopie/` leżą też pojedyncze pliki .sqlite3 z migracji schematu bazy,
    które robi `db.init()`, i one nas tutaj nie interesują.
    """
    katalog = srodowisko.dane / "kopie"
    return sorted(p for p in katalog.iterdir() if p.is_dir()) if katalog.exists() else []


def _podstaw_github(monkeypatch, tmp_path, wersja: str, paczka: Path | None) -> None:
    plik_wersji = tmp_path / "WERSJA_ZDALNA"
    plik_wersji.write_text(wersja, encoding="utf-8")
    monkeypatch.setattr(aktualizacja, "URL_WERSJA_API", plik_wersji.as_uri())
    monkeypatch.setattr(aktualizacja, "URL_WERSJA_RAW", plik_wersji.as_uri())
    if paczka is not None:
        monkeypatch.setattr(aktualizacja, "URL_PACZKA", paczka.as_uri())


# --- czytanie numeru wersji --------------------------------------------------

def test_numer_wersji_i_opis():
    numer, opis = aktualizacja._czytaj_wersje("2026.08.01.10\nNaprawione to i tamto.\nI jeszcze to.")
    assert numer == "2026.08.01.10"
    assert opis == "Naprawione to i tamto. I jeszcze to."


def test_bom_z_notatnika_nie_psuje_porownania():
    """Notatnik zapisuje plik z BOM-em; niewidzialny znak w numerze = wieczna aktualizacja."""
    numer, _ = aktualizacja._czytaj_wersje("﻿2026.08.01.10\nOpis")
    assert numer == "2026.08.01.10"


# --- brak sieci --------------------------------------------------------------

def test_brak_internetu_nie_blokuje_startu(srodowisko, monkeypatch):
    _instalacja(srodowisko)

    def bez_sieci(*args, **kwargs):
        raise urllib.error.URLError("brak internetu")

    monkeypatch.setattr(aktualizacja.urllib.request, "urlopen", bez_sieci)
    assert aktualizacja.wersja_zdalna() is None
    assert aktualizacja.sprawdz_i_zaktualizuj() is False
    assert (srodowisko.katalog / "app" / "main.py").read_text() == "# stary kod"


def test_kopia_robocza_gita_jest_nietykalna(srodowisko, monkeypatch, tmp_path):
    """`./start.sh` u programisty nie może nadpisać niezacommitowanych zmian."""
    _instalacja(srodowisko)
    (srodowisko.katalog / ".git").mkdir()
    _podstaw_github(monkeypatch, tmp_path, "2026.09.09.9",
                    _paczka(tmp_path, "2026.09.09.9", {"app/main.py": "# nowy kod"}))

    assert aktualizacja.sprawdz_i_zaktualizuj() is False
    assert (srodowisko.katalog / "app" / "main.py").read_text() == "# stary kod"


def test_aktualna_wersja_nie_pobiera_niczego(srodowisko, monkeypatch, tmp_path):
    _instalacja(srodowisko, "2026.08.01.1")
    _podstaw_github(monkeypatch, tmp_path, "2026.08.01.1", None)
    assert aktualizacja.sprawdz_i_zaktualizuj() is False
    assert _kopie_aktualizacji(srodowisko) == []


# --- właściwa aktualizacja ---------------------------------------------------

def test_aktualizacja_podmienia_kod_i_szanuje_dane(srodowisko, monkeypatch, tmp_path):
    _instalacja(srodowisko, "2026.01.01.1")
    paczka = _paczka(tmp_path, "2026.09.09.9\nNowości.", {
        "app/main.py": "# nowy kod",
        "szablony/nowy_wzor.docx": "nowa formatka",
    })
    _podstaw_github(monkeypatch, tmp_path, "2026.09.09.9\nNowości.", paczka)

    assert aktualizacja.sprawdz_i_zaktualizuj() is True

    # przyszedł nowy kod...
    assert (srodowisko.katalog / "app" / "main.py").read_text() == "# nowy kod"
    assert aktualizacja.wersja_lokalna()[0] == "2026.09.09.9"
    # ...dane brata są nietknięte...
    assert (srodowisko.dane / "operaty.sqlite3").read_bytes() == b"baza brata"
    assert (srodowisko.wyniki / "001.2026" / "operat.json").exists()
    # ...powstała kopia poprzedniej wersji razem z bazą...
    kopie = _kopie_aktualizacji(srodowisko)
    assert len(kopie) == 1
    assert (kopie[0] / "app" / "main.py").read_text() == "# stary kod"
    assert (kopie[0] / "operaty.sqlite3").exists()
    # ...i jest jednorazowy komunikat „co nowego”
    assert "2026.09.09.9" in aktualizacja.co_nowego()
    assert aktualizacja.co_nowego() is None            # drugi raz się nie pokazuje


def test_szablony_sa_lustrzane(srodowisko, monkeypatch, tmp_path):
    """Formatka skasowana w repozytorium ma zniknąć też u brata.

    Bez tego szablon po zmianie nazwy zostawał u niego na zawsze i straszył na liście
    jako pozycja, której nikt już nie utrzymuje.
    """
    _instalacja(srodowisko)
    paczka = _paczka(tmp_path, "2026.09.09.9", {"szablony/nowy_wzor.docx": "nowa formatka"})
    _podstaw_github(monkeypatch, tmp_path, "2026.09.09.9", paczka)

    aktualizacja.sprawdz_i_zaktualizuj()

    assert (srodowisko.szablony / "nowy_wzor.docx").exists()
    assert not (srodowisko.szablony / "stary_wzor.docx").exists()
    # ...ale kopia starej formatki została, gdyby jednak była potrzebna
    kopia = _kopie_aktualizacji(srodowisko)[0]
    assert (kopia / "szablony" / "stary_wzor.docx").exists()


def test_dane_i_wyniki_nie_sa_aktualizowane():
    """Zabezpieczenie na przyszłość: nikt nie ma prawa dopisać ich do listy."""
    assert "dane" not in aktualizacja.AKTUALIZOWANE
    assert "wyniki" not in aktualizacja.AKTUALIZOWANE
    assert aktualizacja.LUSTRZANE == {"szablony"}, \
        "lustrzane kasowanie plików `app/` przy działającym procesie to proszenie się o kłopoty"


# --- awarie w trakcie --------------------------------------------------------

def test_uszkodzona_paczka_zostawia_dzialajacy_program(srodowisko, monkeypatch, tmp_path):
    _instalacja(srodowisko)
    zly_zip = tmp_path / "zly.zip"
    with zipfile.ZipFile(zly_zip, "w") as paczka:
        paczka.writestr("cos_innego/README.md", "to nie jest program")
    _podstaw_github(monkeypatch, tmp_path, "2026.09.09.9", zly_zip)

    assert aktualizacja.sprawdz_i_zaktualizuj() is False
    assert (srodowisko.katalog / "app" / "main.py").read_text() == "# stary kod"
    assert aktualizacja.wersja_lokalna()[0] == "2026.01.01.1"


def test_paczka_nie_do_pobrania_zostawia_dzialajacy_program(srodowisko, monkeypatch, tmp_path):
    _instalacja(srodowisko)
    _podstaw_github(monkeypatch, tmp_path, "2026.09.09.9",
                    tmp_path / "nie_ma_takiego_pliku.zip")

    assert aktualizacja.sprawdz_i_zaktualizuj() is False
    assert (srodowisko.katalog / "app" / "main.py").read_text() == "# stary kod"


def test_numer_wersji_bierze_sie_z_paczki_a_nie_z_zapowiedzi(srodowisko, monkeypatch, tmp_path):
    """raw.githubusercontent potrafi być kilka minut do tyłu.

    Użytkownik ma zobaczyć numer, który naprawdę u siebie ma — inaczej program
    ogłasza „masz 2026.09.09.9”, mając w środku coś innego.
    """
    _instalacja(srodowisko)
    paczka = _paczka(tmp_path, "2026.09.09.9\nPrawdziwa nowość.", {"app/main.py": "# nowy"})
    _podstaw_github(monkeypatch, tmp_path, "2026.09.09.8\nZapowiedź z cache.", paczka)

    aktualizacja.sprawdz_i_zaktualizuj()
    assert "2026.09.09.9" in aktualizacja.co_nowego()


@pytest.mark.parametrize("nazwa", ["app", "szablony", "WERSJA", "requirements.txt"])
def test_lista_aktualizowanych_obejmuje_to_co_trzeba(nazwa):
    assert nazwa in aktualizacja.AKTUALIZOWANE


def test_nowy_plik_dojezdza_juz_przy_tej_aktualizacji(srodowisko, monkeypatch, tmp_path):
    """Aktualizację wykonuje kod, który brat ma u siebie — czyli **stary**.

    Jego lista `AKTUALIZOWANE` nie zna plików dołożonych w nowym wydaniu, więc nowy
    plik nie dojeżdżał przy tej aktualizacji, która go wprowadza, tylko przy następnej.
    Kosztowało to `ZMIANY.md`: brat dostał wersję 2026.08.02.8 z menu „Historia wersji”
    i komunikatem, że pliku z historią nie ma. Dlatego listę czytamy z paczki.
    """
    _instalacja(srodowisko, "2026.01.01.1")
    # stara lista — dokładnie taka, jaka jechała w wydaniu sprzed ZMIANY.md
    monkeypatch.setattr(aktualizacja, "AKTUALIZOWANE",
                        ["app", "szablony", "uruchom.py", "WERSJA"])
    nowa_lista = ("AKTUALIZOWANE = [\n"
                  "    'app', 'szablony', 'uruchom.py', 'WERSJA', 'ZMIANY.md',\n"
                  "]\n")
    paczka = _paczka(tmp_path, "2026.09.09.9\nNowości.", {
        "app/aktualizacja.py": nowa_lista,
        "ZMIANY.md": "# Historia zmian\n\n## 2026.09.09.9 — 2026-09-09\n\nNowości.\n",
    })
    _podstaw_github(monkeypatch, tmp_path, "2026.09.09.9\nNowości.", paczka)

    assert aktualizacja.sprawdz_i_zaktualizuj() is True

    plik = srodowisko.katalog / "ZMIANY.md"
    assert plik.exists(), "nowy plik nie dojechał — brat zobaczy pustą stronę historii"
    assert "2026.09.09.9" in plik.read_text(encoding="utf-8")


def test_lista_z_paczki_nie_wypuszcza_poza_katalog_programu(tmp_path):
    """Paczka jest z internetu — ścieżka w rodzaju `../..` nie ma prawa przejść."""
    kod = tmp_path / "app"
    kod.mkdir()
    (kod / "aktualizacja.py").write_text(
        "AKTUALIZOWANE = ['app', '../../etc/passwd', 'C:/Windows/System32', 'WERSJA']\n",
        encoding="utf-8")

    lista = aktualizacja._lista_z_paczki(tmp_path)

    assert lista == ["app", "WERSJA"]


def test_nieczytelna_lista_w_paczce_nie_wywraca_aktualizacji(tmp_path):
    kod = tmp_path / "app"
    kod.mkdir()
    (kod / "aktualizacja.py").write_text("to nie jest ( poprawny python", encoding="utf-8")

    assert aktualizacja._lista_z_paczki(tmp_path) == aktualizacja.AKTUALIZOWANE

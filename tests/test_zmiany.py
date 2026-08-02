"""Historia wersji pokazywana bratu.

U brata nie ma gita — dostaje rozpakowany `.zip` — więc historia musi jechać z kodem
jako plik `ZMIANY.md`. Testy pilnują, żeby ten plik faktycznie do niego dotarł
i żeby zgadzał się z wydaną wersją.
"""
from __future__ import annotations

from app import aktualizacja, zmiany
from app.config import BAZA

PRZYKLAD = """# Historia zmian

Wstęp, który nie jest wydaniem.

## 2026.08.02.7 — 2026-08-02

Drobne sprzątanie przy pierwszym uruchomieniu.

## 2026.08.01.12 — 2026-08-01

Program pewniej zwalnia plik bazy danych.
Druga linia opisu.
"""


def test_czyta_wydania_od_najnowszego(tmp_path, monkeypatch):
    plik = tmp_path / "ZMIANY.md"
    plik.write_text(PRZYKLAD, encoding="utf-8")
    monkeypatch.setattr(zmiany, "PLIK", plik)

    wpisy = zmiany.wpisy()

    assert [w["wersja"] for w in wpisy] == ["2026.08.02.7", "2026.08.01.12"]
    assert wpisy[0]["data"] == "2026-08-02"
    assert wpisy[0]["opis"] == "Drobne sprzątanie przy pierwszym uruchomieniu."
    # kilka linii opisu skleja się w jedno zdanie, a wstęp nie udaje wydania
    assert wpisy[1]["opis"].endswith("Druga linia opisu.")


def test_brak_pliku_nie_wywraca_strony(tmp_path, monkeypatch):
    monkeypatch.setattr(zmiany, "PLIK", tmp_path / "nie-ma-mnie.md")
    assert zmiany.wpisy() == []


def test_plik_z_bom_em_czyta_sie_poprawnie(tmp_path, monkeypatch):
    """Notatnik zapisuje z BOM-em — na tym już raz poległ plik WERSJA."""
    plik = tmp_path / "ZMIANY.md"
    plik.write_text(PRZYKLAD, encoding="utf-8-sig")
    monkeypatch.setattr(zmiany, "PLIK", plik)

    assert zmiany.wpisy()[0]["wersja"] == "2026.08.02.7"


# --- to, co naprawdę może się rozjechać przy wydaniu -------------------------

def test_historia_jedzie_do_brata_przy_aktualizacji():
    """Bez tego wpisu historia zostałaby u autora, a brat miałby pustą stronę."""
    assert "ZMIANY.md" in aktualizacja.AKTUALIZOWANE


def test_wydana_wersja_ma_wpis_w_historii():
    """Najłatwiejszy błąd przy wydaniu: podbita WERSJA bez wpisu w ZMIANY.md.

    Sam program działałby dalej, ale brat po aktualizacji zobaczyłby komunikat
    „co nowego” i pustkę w historii — czyli dokładnie to, po co ta strona powstała.
    """
    monkeypatch_free_wpisy = zmiany.wpisy()          # prawdziwy plik z repozytorium
    assert monkeypatch_free_wpisy, "ZMIANY.md jest puste albo go nie ma"

    wersja = (BAZA / "WERSJA").read_text(encoding="utf-8-sig").strip().splitlines()[0].strip()
    assert monkeypatch_free_wpisy[0]["wersja"] == wersja, (
        "najnowszy wpis w ZMIANY.md nie odpowiada wydanej wersji — "
        "uruchom `python narzedzia/zbuduj_zmiany.py --zapisz` po podbiciu WERSJA")


def test_strona_historii_pokazuje_wydania(klient):
    odpowiedz = klient.get("/pomoc/historia")

    assert odpowiedz.status_code == 200
    assert "Historia wersji" in odpowiedz.text
    assert zmiany.wpisy()[0]["wersja"] in odpowiedz.text


def test_menu_pomocy_prowadzi_do_obu_stron(klient):
    tresc = klient.get("/").text

    assert 'href="/pomoc"' in tresc
    assert 'href="/pomoc/historia"' in tresc

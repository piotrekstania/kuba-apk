"""Start programu — kiedy wolno schować czarne okno konsoli.

Konsolę chowamy, bo stojąc na wierzchu wchodziła w kolejkę okien i po zamknięciu
katalogu wyskakiwała przed przeglądarkę. Ale **tylko po udanym starcie**: gdy serwer
się nie podniósł, okno z komunikatem jest jedyną rzeczą, jaką brat ma przed oczami.
"""
from __future__ import annotations

import http.server
import threading
from pathlib import Path

import uruchom

KORZEN = Path(__file__).resolve().parent.parent


def _mikroserwer(tresc: str):
    """Serwer HTTP na losowym wolnym porcie, oddający zadaną treść."""
    class Uchwyt(http.server.BaseHTTPRequestHandler):
        def do_GET(self):                                     # noqa: N802 (API stdlib)
            dane = tresc.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Length", str(len(dane)))
            self.end_headers()
            self.wfile.write(dane)

        def log_message(self, *_args):                        # cisza w testach
            pass

    serwer = http.server.HTTPServer(("127.0.0.1", 0), Uchwyt)
    threading.Thread(target=serwer.serve_forever, daemon=True).start()
    return serwer


def test_obcy_serwer_na_porcie_nie_uchodzi_za_nasz_program(monkeypatch):
    """Sam otwarty port to za mało — może na nim siedzieć cokolwiek.

    Tak właśnie wyszło przy pierwszej wersji: port trzymała zapomniana druga kopia
    programu, a sprawdzenie `connect` uznało to za udany start i schowało konsolę,
    choć nasz serwer właśnie się nie podniósł.
    """
    serwer = _mikroserwer("<html><title>Panel routera</title></html>")
    try:
        monkeypatch.setattr(uruchom, "HOST", "127.0.0.1")
        monkeypatch.setattr(uruchom, "PORT", serwer.server_address[1])
        assert uruchom.serwer_odpowiada(0.8) is False
    finally:
        serwer.shutdown()


def test_nasz_program_jest_rozpoznawany(monkeypatch):
    serwer = _mikroserwer(f"<html><title>{uruchom.ZNACZNIK}</title></html>")
    try:
        monkeypatch.setattr(uruchom, "HOST", "127.0.0.1")
        monkeypatch.setattr(uruchom, "PORT", serwer.server_address[1])
        assert uruchom.serwer_odpowiada(3.0) is True
    finally:
        serwer.shutdown()


def test_nieudany_start_zostawia_konsole_widoczna(monkeypatch):
    """Schowanie okna przy nieudanym starcie byłoby najgorsze z możliwych:
    brat widziałby pustą przeglądarkę i nic poza tym."""
    zrobione = []
    monkeypatch.setattr(uruchom, "serwer_odpowiada", lambda *_: False)
    monkeypatch.setattr(uruchom, "zminimalizuj_konsole",
                        lambda: zrobione.append("schowana"))
    monkeypatch.setattr(uruchom.webbrowser, "open", lambda _: zrobione.append("przeglądarka"))

    uruchom.po_starcie()

    assert zrobione == []


def test_udany_start_otwiera_przegladarke_i_chowa_konsole(monkeypatch):
    zrobione = []
    monkeypatch.setattr(uruchom, "serwer_odpowiada", lambda *_: True)
    monkeypatch.setattr(uruchom, "zminimalizuj_konsole",
                        lambda: zrobione.append("schowana"))
    monkeypatch.setattr(uruchom.webbrowser, "open", lambda _: zrobione.append("przeglądarka"))
    monkeypatch.setattr(uruchom.time, "sleep", lambda _: None)

    uruchom.po_starcie()

    # kolejność ma znaczenie: najpierw przeglądarka bierze pierwszy plan, potem chowamy okno
    assert zrobione == ["przeglądarka", "schowana"]


# --- ikona programu na Windowsie ---------------------------------------------

def test_ikona_ma_rozmiary_ktorych_szuka_windows():
    """16 px na pasku zadań, 32 i 48 na pulpicie, 256 w podglądzie dużych ikon."""
    from PIL import Image

    from app.config import WEB
    with Image.open(WEB / "static" / "logo.ico") as ikona:
        rozmiary = set(ikona.ico.sizes())
    assert {(16, 16), (32, 32), (48, 48), (256, 256)} <= rozmiary


def test_ikona_zgadza_sie_ze_skryptem(tmp_path):
    """Plik w repozytorium musi być tym, co wypluwa `narzedzia/utworz_ikone.py`.

    Oba pliki znaku — `logo.svg` i `logo.ico` — opisują tę samą geometrię dwa razy,
    bo Pillow nie czyta SVG. Rozjazd między nimi byłby niewidoczny do chwili, w której
    ktoś zobaczyłby na pasku zadań co innego niż na stronie.
    """
    import sys

    sys.path.insert(0, str(KORZEN / "narzedzia"))
    import utworz_ikone

    from app.config import WEB
    swiezy = utworz_ikone.zapisz(tmp_path / "logo.ico")
    assert swiezy.read_bytes() == (WEB / "static" / "logo.ico").read_bytes(), \
        "uruchom `python narzedzia/utworz_ikone.py` i zacommituj wynik"


def test_start_bat_zaklada_skrot_z_ikona():
    """Skrót jest jedynym sposobem, żeby program miał na Windowsie własną ikonę."""
    tresc = (KORZEN / "start.bat").read_text(encoding="utf-8")

    assert "Generator operatow.lnk" in tresc
    assert "logo.ico" in tresc
    assert 'if not exist "Generator operatow.lnk"' in tresc, \
        "skrót ma powstać raz — inaczej każdy start kasowałby zmiany użytkownika"
    assert ">nul 2>&1" in tresc, "nieudane tworzenie skrótu nie może zatrzymać startu"

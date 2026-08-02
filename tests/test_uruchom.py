"""Start programu — kiedy wolno schować czarne okno konsoli.

Konsolę chowamy, bo stojąc na wierzchu wchodziła w kolejkę okien i po zamknięciu
katalogu wyskakiwała przed przeglądarkę. Ale **tylko po udanym starcie**: gdy serwer
się nie podniósł, okno z komunikatem jest jedyną rzeczą, jaką brat ma przed oczami.
"""
from __future__ import annotations

import http.server
import threading

import uruchom


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

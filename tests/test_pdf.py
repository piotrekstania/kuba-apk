"""Sklejanie PDF-ów i wykrywanie konwertera.

Sama konwersja DOCX→PDF wymaga Worda albo LibreOffice'a, więc jest tu tylko jeden
test oznaczony markerem `konwerter` — pomija się sam, gdy nie ma czym konwertować.
"""
from __future__ import annotations

import pytest
from pathlib import Path
from pypdf import PdfReader, PdfWriter

from app import pdf


def _pdf(sciezka, stron: int = 1, wysokosc: int = 842):
    zapis = PdfWriter()
    for _ in range(stron):
        zapis.add_blank_page(width=595, height=wysokosc)
    sciezka.parent.mkdir(parents=True, exist_ok=True)
    with open(sciezka, "wb") as wyjscie:
        zapis.write(wyjscie)
    return sciezka


def test_sklejanie_zachowuje_kolejnosc_i_liczbe_stron(tmp_path):
    a = _pdf(tmp_path / "a.pdf", stron=2)
    b = _pdf(tmp_path / "b.pdf", stron=3)
    wynik = pdf.polacz_pdf([a, b], tmp_path / "wynik.pdf")
    assert len(PdfReader(str(wynik)).pages) == 5


def test_sklejanie_bez_plikow_zglasza_blad(tmp_path):
    with pytest.raises(ValueError):
        pdf.polacz_pdf([], tmp_path / "wynik.pdf")


def test_uszkodzony_plik_mowi_po_polsku_i_podaje_nazwe(tmp_path):
    """Przy kilkunastu załącznikach brat musi wiedzieć, który plik jest do wymiany."""
    dobry = _pdf(tmp_path / "dobry.pdf")
    zepsuty = tmp_path / "roboczy-20260801.pdf"
    zepsuty.write_bytes(b"to nie jest PDF")

    with pytest.raises(pdf.BladPliku) as awaria:
        pdf.polacz_pdf([dobry, zepsuty], tmp_path / "wynik.pdf",
                       etykiety={zepsuty: "mapa zasadnicza.pdf"})
    komunikat = str(awaria.value)
    assert "mapa zasadnicza.pdf" in komunikat        # nazwa, którą on zna
    assert "roboczy-20260801" not in komunikat       # nie nazwa robocza z dysku
    assert "PDF" in komunikat and "hasłem" in komunikat


def test_obrot_zapisuje_sie_w_wyniku(tmp_path):
    zrodlo = _pdf(tmp_path / "lezacy.pdf")
    wynik = pdf.polacz_pdf([zrodlo], tmp_path / "wynik.pdf", obroty={zrodlo: 90})
    assert PdfReader(str(wynik)).pages[0].get("/Rotate") == 90


def test_wykrywanie_konwertera_zwraca_znana_wartosc():
    assert pdf.dostepny_konwerter() in {"word", "libreoffice", "brak"}


@pytest.fixture
def katalog_konwersji():
    """Katalog roboczy **wewnątrz projektu**, a nie w /tmp.

    LibreOffice ze Snapa/Flatpaka ma własny, odizolowany `/tmp` — pliku z `tmp_path`
    w ogóle nie widzi i konwersja kończy się „nie utworzył PDF-a”. W programie nigdy
    nie konwertujemy z `/tmp` (dokumenty leżą w `wyniki/`), więc test też nie powinien.
    """
    import shutil
    import tempfile

    from app.config import DANE

    katalog = Path(tempfile.mkdtemp(dir=DANE, prefix="test-konwersji-"))
    yield katalog
    shutil.rmtree(katalog, ignore_errors=True)


@pytest.mark.konwerter
def test_konwersja_docx_na_pdf(katalog_konwersji):
    """Jedyny test dotykający prawdziwego konwertera — reszta chodzi na atrapie."""
    if pdf.dostepny_konwerter() == "brak":
        pytest.skip("brak Worda i LibreOffice'a")
    from docx import Document

    zrodlo = katalog_konwersji / "dokument.docx"
    dokument = Document()
    dokument.add_paragraph("Operat techniczny 001/2026")
    dokument.save(zrodlo)

    wynik = pdf.docx_na_pdf(zrodlo, katalog_konwersji / "dokument.pdf")
    assert wynik.exists()
    tekst = "".join(strona.extract_text() for strona in PdfReader(str(wynik)).pages)
    assert "001/2026" in tekst


def test_zlozony_pdf_ma_numer_roboty_w_tytule(tmp_path):
    """Czytnik PDF-a nazywa kartę tytułem z metadanych, a bez niego — ostatnim członem
    adresu. U brata wychodziło z tego „wynik”, choć plik nazywa się numerem roboty.

    Tytuł jedzie razem z plikiem, więc numer widać też we właściwościach dokumentu
    po wysłaniu go do ośrodka.
    """
    a = _pdf(tmp_path / "a.pdf")
    wynik = pdf.polacz_pdf([a], tmp_path / "G.05.06.06.2026.pdf",
                           tytul="G.05.06.06.2026")

    assert PdfReader(str(wynik)).metadata.title == "G.05.06.06.2026"


def test_sklejanie_bez_tytulu_nie_dopisuje_metadanych(tmp_path):
    """Sklejanie służy też do innych rzeczy — pusty tytuł ma zostawić plik w spokoju."""
    a = _pdf(tmp_path / "a.pdf")
    wynik = pdf.polacz_pdf([a], tmp_path / "wynik.pdf")

    assert not (PdfReader(str(wynik)).metadata or {}).get("/Title")


# --- Word, który stanął na oknie dialogowym ---------------------------------------
#
# Word bez okna potrafi stanąć na pytaniu, którego nikt nie widzi (aktywacja,
# naprawa pliku). Konwersja czekała wtedy w nieskończoność, trzymając blokadę
# konwersji — każde następne składanie i każdy podgląd stawały za nią. COM udajemy
# tu atrapą, więc testy chodzą także bez Windowsa; prawdziwego Worda sprawdza
# `test_word.py`.

import sys            # noqa: E402 (sekcja dopisana do pliku)
import threading      # noqa: E402
import time           # noqa: E402
import types          # noqa: E402


class _AtrapaDokumentu:
    def __init__(self, zawies: bool, zamkniety: threading.Event):
        self.zawies, self.zamkniety = zawies, zamkniety

    def ExportAsFixedFormat(self, OutputFileName, **_):          # noqa: N802 (API Worda)
        if self.zawies:
            # stoi, dopóki ktoś nie zamknie procesu — wtedy COM rzuca błędem RPC
            if not self.zamkniety.wait(10):
                raise AssertionError("strażnik nie zamknął zawieszonego Worda")
            raise OSError("(-2147023170, 'Wywołanie procedury zdalnej nie powiodło się.')")
        Path(OutputFileName).write_bytes(b"%PDF-1.4 atrapa")

    def Close(self, *_):                                            # noqa: N802
        pass


class _AtrapaWorda:
    Visible = True
    DisplayAlerts = 1

    def __init__(self, zawies: bool, zamkniety: threading.Event):
        self.Documents = types.SimpleNamespace(
            Open=lambda *a, **k: _AtrapaDokumentu(zawies, zamkniety))

    def Quit(self, *_):                                             # noqa: N802
        pass


def _podstaw_worda(monkeypatch, zawies: bool, procesy: list[set[int]]):
    zamkniety = threading.Event()
    zabite: list[int] = []
    klient = types.ModuleType("win32com.client")
    klient.DispatchEx = lambda nazwa: _AtrapaWorda(zawies, zamkniety)
    win32com = types.ModuleType("win32com")
    win32com.client = klient
    pythoncom = types.ModuleType("pythoncom")
    pythoncom.CoInitialize = pythoncom.CoUninitialize = lambda: None
    monkeypatch.setitem(sys.modules, "win32com", win32com)
    monkeypatch.setitem(sys.modules, "win32com.client", klient)
    monkeypatch.setitem(sys.modules, "pythoncom", pythoncom)
    kolejne = iter(procesy)
    monkeypatch.setattr(pdf, "_procesy_worda", lambda: next(kolejne, procesy[-1]))
    monkeypatch.setattr(pdf, "_zamknij_proces", lambda pid: (zabite.append(pid), zamkniety.set()))
    monkeypatch.setattr(pdf, "LIMIT_WORDA", 0.3)
    return zabite


def test_zawieszony_word_jest_zamykany_po_limicie_czasu(tmp_path, monkeypatch):
    """Po limicie czasu zamykamy **naszą** instancję Worda — COM rzuca wtedy błędem,
    konwersja kończy się polskim komunikatem, a blokada konwersji jest wolna."""
    zabite = _podstaw_worda(monkeypatch, zawies=True, procesy=[{100}, {100, 4242}])
    zrodlo = tmp_path / "spis.docx"
    zrodlo.write_bytes(b"docx")
    poczatek = time.monotonic()

    with pytest.raises(pdf.BrakKonwertera, match="nie skończył"):
        pdf._wordem_wsad([(zrodlo, tmp_path / "spis.pdf")])

    assert zabite == [4242], "zamknięty nie ten Word (100 to okno brata)"
    assert time.monotonic() - poczatek < 5
    assert pdf._BLOKADA_KONWERSJI.acquire(blocking=False)
    pdf._BLOKADA_KONWERSJI.release()


def test_szybki_word_nie_jest_zamykany(tmp_path, monkeypatch):
    zabite = _podstaw_worda(monkeypatch, zawies=False, procesy=[set(), {4242}])
    zrodlo = tmp_path / "spis.docx"
    zrodlo.write_bytes(b"docx")

    pdf._wordem_wsad([(zrodlo, tmp_path / "spis.pdf")])
    time.sleep(0.5)                                  # dłużej niż limit — strażnik odwołany?

    assert zabite == [] and (tmp_path / "spis.pdf").exists()


def test_po_zawieszeniu_wsad_nie_uruchamia_worda_drugi_raz(tmp_path, monkeypatch):
    """Po nieudanym wsadzie program próbował jeszcze każdy dokument z osobna. Po
    zawieszeniu każdy kolejny start Worda stanąłby na tym samym oknie — limit czasu
    razy liczba dokumentów, a przez cały ten czas blokada konwersji trzymała składanie."""
    _podstaw_worda(monkeypatch, zawies=True, procesy=[{100}, {100, 4242}])
    klient = sys.modules["win32com.client"]
    starty: list[str] = []
    uruchom = klient.DispatchEx
    klient.DispatchEx = lambda nazwa: (starty.append(nazwa), uruchom(nazwa))[1]
    monkeypatch.setattr(pdf, "dostepny_konwerter", lambda: "word")
    monkeypatch.setattr(pdf, "sciezka_libreoffice", lambda: None)
    pary = []
    for numer in range(3):
        (tmp_path / f"{numer}.docx").write_bytes(b"docx")
        pary.append((tmp_path / f"{numer}.docx", tmp_path / f"{numer}.pdf"))

    assert pdf.docx_na_pdf_wsad(pary) == []
    assert len(starty) == 1


def test_zawieszony_word_przy_skladaniu_mowi_co_zrobic(tmp_path, monkeypatch):
    """Komunikat o zawieszeniu idzie do brata bez doklejonego z przodu kodu błędu RPC."""
    _podstaw_worda(monkeypatch, zawies=True, procesy=[{100}, {100, 4242}])
    monkeypatch.setattr(pdf, "dostepny_konwerter", lambda: "word")
    monkeypatch.setattr(pdf, "sciezka_libreoffice", lambda: None)
    zrodlo = tmp_path / "spis.docx"
    zrodlo.write_bytes(b"docx")

    with pytest.raises(pdf.BrakKonwertera) as blad:
        pdf.docx_na_pdf(zrodlo, tmp_path / "spis.pdf")

    assert str(blad.value).startswith("Microsoft Word nie skończył"), str(blad.value)
    assert "-2147023170" not in str(blad.value)


def test_nie_zamykamy_worda_gdy_nie_wiadomo_ktory_jest_nasz():
    """Dwa nowe procesy naraz (brat właśnie otworzył Worda) — lepiej nie zamknąć
    niczego niż zamknąć mu okno z niezapisanym dokumentem."""
    assert pdf._nasz_proces({100}, {100, 4242}) == 4242
    assert pdf._nasz_proces({100}, {100, 4242, 4243}) is None
    assert pdf._nasz_proces(set(), set()) is None


def test_skladanie_nie_zamraza_reszty_programu(srodowisko, bez_konwertera, monkeypatch):
    """Składanie wołało konwersję wprost w pętli zdarzeń serwera: dopóki Word myślał —
    a przy oknie dialogowym w nieskończoność — program nie odpowiadał na nic, nawet
    na otwarcie Pomocy w drugiej karcie. Wyglądało to na zawieszony program."""
    import anyio
    import httpx

    from app import main, operaty

    katalog, _ = operaty.zaloz("001/2026", "GK.1", "spis_tresci_wzor", {})
    _pdf(katalog / "mapa.pdf")

    def wolna_konwersja(plik):
        time.sleep(1.5)                              # Word, który długo myśli
        return plik

    monkeypatch.setattr(operaty, "jako_pdf", wolna_konwersja)
    czasy: dict[str, float] = {}

    async def scenariusz():
        transport = httpx.ASGITransport(app=main.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as k:
            # zegar od początku scenariusza: przy zablokowanej pętli nawet `sleep`
            # w drugiej karcie budzi się dopiero po składaniu, więc pomiar od
            # obudzenia niczego by nie pokazał
            start = time.monotonic()

            async def zloz():
                await k.post(f"/scal/{katalog.name}", data={"plik": ["mapa.pdf"]})

            async def pomoc():
                await anyio.sleep(0.2)
                await k.get("/pomoc")
                czasy["pomoc"] = time.monotonic() - start

            async with anyio.create_task_group() as grupa:
                grupa.start_soon(zloz)
                grupa.start_soon(pomoc)

    anyio.run(scenariusz)

    assert czasy["pomoc"] < 1.0, f"Pomoc czekała {czasy['pomoc']:.1f} s na składanie"

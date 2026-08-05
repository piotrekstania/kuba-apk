"""Katalog operatu: nazwy, zawartość, kolejność sklejania."""
from __future__ import annotations

import json
import sys

import pytest

from app import operaty


def test_ukosnik_w_numerze_staje_sie_kropka():
    """Numer '001/2026' czyta ośrodek, katalog '001.2026' przyjmuje Windows."""
    assert operaty.nazwa_katalogu("001/2026") == "001.2026"
    assert operaty.nazwa_katalogu("12/2026") == "12.2026"


def test_nazwa_bezpieczna_zostawia_polskie_znaki():
    """Nazwa scalonego PDF-a ma być dokładnie numerem roboty — z ogonkami włącznie."""
    nazwa, podmieniono = operaty.nazwa_bezpieczna("P.1234.2026 Sułkowice")
    assert nazwa == "P.1234.2026 Sułkowice"
    assert podmieniono is False


def test_nazwa_bezpieczna_melduje_podmiane_znakow():
    nazwa, podmieniono = operaty.nazwa_bezpieczna("GK/6640:1")
    assert nazwa == "GK-6640-1"
    assert podmieniono is True


def test_nazwa_bezpieczna_ucina_kropke_na_koncu():
    """Windows nie przyjmie katalogu kończącego się kropką."""
    assert operaty.nazwa_bezpieczna("operat.")[0] == "operat"
    assert operaty.nazwa_bezpieczna("")[0] == "operat"


def test_nazwa_dokumentu_obcina_koncowke_wzor():
    assert operaty.nazwa_dokumentu("spis_tresci_wzor") == "spis_tresci.docx"
    assert operaty.nazwa_dokumentu("sprawozdanie_techniczne_wzor") == \
        "sprawozdanie_techniczne.docx"
    assert operaty.nazwa_dokumentu("cos_innego") == "cos_innego.docx"


def test_zalozenie_katalogu_zostawia_opis_i_znacznik(srodowisko):
    katalog, ostrzezenia = operaty.zaloz("001/2026", "GK.6640.1.2026", "spis_tresci_wzor",
                                         {"nr_roboty": "GK.6640.1.2026"})
    assert katalog.name == "001.2026"
    assert ostrzezenia == []
    opis = json.loads((katalog / "operat.json").read_text(encoding="utf-8"))
    assert opis["nr_operatu"] == "001/2026"
    znacznik = katalog / "GK.6640.1.2026"
    assert znacznik.is_file() and znacznik.stat().st_size == 0


def test_zmiana_numeru_roboty_sprzata_stary_znacznik(srodowisko):
    """Przy poprawianiu operatu w katalogu nie mogą leżeć dwa numery naraz."""
    katalog, _ = operaty.zaloz("001/2026", "GK.1.2026", "spis_tresci_wzor", {})
    operaty.zaloz("001/2026", "GK.2.2026", "spis_tresci_wzor", {},
                  poprzedni_numer_roboty="GK.1.2026")
    assert not (katalog / "GK.1.2026").exists()
    assert (katalog / "GK.2.2026").exists()


def test_zakazane_znaki_w_numerze_roboty_daja_ostrzezenie(srodowisko):
    """Przepisy każą nazwać PDF numerem KERG — gdy się nie da, brat ma o tym wiedzieć."""
    _, ostrzezenia = operaty.zaloz("001/2026", "GK/6640/1", "spis_tresci_wzor", {})
    assert len(ostrzezenia) == 1
    assert "GK-6640-1" in ostrzezenia[0]


def test_lista_plikow_do_sklejenia(srodowisko):
    katalog, _ = operaty.zaloz("001/2026", "GK.1.2026", "spis_tresci_wzor", {})
    (katalog / "spis_tresci.docx").write_bytes(b"x")
    (katalog / "sprawozdanie.docx").write_bytes(b"x")
    (katalog / "mapa.pdf").write_bytes(b"x")
    (katalog / "notatka.txt").write_bytes(b"x")          # nie do sklejenia
    (katalog / "~$spis_tresci.docx").write_bytes(b"x")   # plik tymczasowy Worda
    (katalog / operaty.nazwa_wyniku(katalog)).write_bytes(b"x")   # poprzedni wynik

    nazwy = [p.name for p in operaty.pliki(katalog)]
    assert nazwy[0] == "spis_tresci.docx"               # spis treści zawsze pierwszy
    assert set(nazwy) == {"spis_tresci.docx", "sprawozdanie.docx", "mapa.pdf"}
    assert "operat.json" not in nazwy
    assert "GK.1.2026" not in nazwy                     # znacznik bez rozszerzenia


def test_wynik_sklejania_nazywa_sie_numerem_roboty(srodowisko):
    katalog, _ = operaty.zaloz("001/2026", "P.1234.2026.123", "spis_tresci_wzor", {})
    assert operaty.nazwa_wyniku(katalog) == "P.1234.2026.123.pdf"


def test_katalog_po_nazwie_nie_wypuszcza_poza_wyniki(srodowisko):
    """Nazwa z adresu URL nie może wyprowadzić poza `wyniki/`."""
    operaty.zaloz("001/2026", "GK.1.2026", "spis_tresci_wzor", {})
    assert operaty.katalog_po_nazwie("001.2026") is not None
    assert operaty.katalog_po_nazwie("../..") is None
    assert operaty.katalog_po_nazwie("../../etc") is None
    assert operaty.katalog_po_nazwie("nie_ma_takiego") is None


def test_lista_operatow_od_najnowszego(srodowisko):
    operaty.zaloz("001/2026", "GK.1.2026", "spis_tresci_wzor", {})
    operaty.zaloz("002/2026", "GK.2.2026", "spis_tresci_wzor", {})
    # Daty wpisujemy ręcznie: `utworzono` ma dokładność do sekundy, więc dwa operaty
    # założone w tej samej sekundzie mają identyczny klucz sortowania i o kolejności
    # decyduje przypadek (kolejność z `iterdir`). Na dysku brata to bez znaczenia —
    # w teście dawało wynik zależny od maszyny.
    for nazwa, kiedy in (("001.2026", "2026-07-31T09:00:00"),
                         ("002.2026", "2026-08-01T09:00:00")):
        plik = srodowisko.wyniki / nazwa / "operat.json"
        plik.write_text(json.dumps({**json.loads(plik.read_text(encoding="utf-8")),
                                    "utworzono": kiedy}, ensure_ascii=False),
                        encoding="utf-8")
    # katalog bez operat.json nie jest operatem
    (srodowisko.wyniki / "przypadkowy_folder").mkdir()

    lista = operaty.lista()
    assert [o["nr_operatu"] for o in lista] == ["002/2026", "001/2026"]
    assert all("przypadkowy" not in o["katalog"] for o in lista)


def test_podglad_pdf_leży_poza_katalogiem_operatu(srodowisko, bez_konwertera):
    """Inaczej przy następnym sklejaniu ten sam dokument policzyłby się dwa razy."""
    katalog, _ = operaty.zaloz("001/2026", "GK.1.2026", "spis_tresci_wzor", {})
    dokument = katalog / "spis_tresci.docx"
    dokument.write_bytes(b"x")

    wynik = operaty.jako_pdf(dokument)
    assert wynik.exists()
    assert katalog not in wynik.parents
    assert [p.name for p in operaty.pliki(katalog)] == ["spis_tresci.docx"]


def test_pdf_nie_jest_konwertowany_ponownie(srodowisko, bez_konwertera):
    katalog, _ = operaty.zaloz("001/2026", "GK.1.2026", "spis_tresci_wzor", {})
    mapa = katalog / "mapa.pdf"
    mapa.write_bytes(b"%PDF-1.4\n")
    assert operaty.jako_pdf(mapa) == mapa



@pytest.mark.skipif(sys.platform != "win32", reason="wysuwanie okna dotyczy tylko Windowsa")
def test_otwarcie_katalogu_przezywa_awarie_wysuwania_okna(srodowisko, monkeypatch):
    """Wysuwanie okna na wierzch nie może przewrócić samego otwierania katalogu.

    Gdyby `SetForegroundWindow` albo brak pywin32 wywalił wyjątek, brat straciłby
    działającą funkcję w zamian za kosmetykę.
    """
    otwarte = []
    monkeypatch.setattr(operaty.os, "startfile", otwarte.append, raising=False)
    monkeypatch.setattr(operaty, "_na_pierwszy_plan",
                        lambda _: (_ for _ in ()).throw(RuntimeError("brak pywin32")))

    katalog, _ = operaty.zaloz("001/2026", "GK.1.2026", "spis_tresci_wzor", {})
    operaty.otworz_w_systemie(katalog)

    assert otwarte == [katalog]


# --- zapamiętany układ kafelków ---------------------------------------------

def test_zapamietany_uklad_wraca_przy_nastepnym_skladaniu(srodowisko):
    katalog, _ = operaty.zaloz("001/2026", "GK.1.2026", "spis_tresci_wzor", {})
    for nazwa in ("spis_tresci.docx", "mapa.pdf", "szkic.pdf"):
        (katalog / nazwa).write_bytes(b"x")

    operaty.zapisz_uklad(katalog, ["mapa.pdf", "spis_tresci.docx", "szkic.pdf"],
                         {"mapa.pdf": 90})

    ulozone = operaty.pliki_ulozone(katalog)
    assert [p.name for p, _ in ulozone] == ["mapa.pdf", "spis_tresci.docx", "szkic.pdf"]
    assert dict((p.name, kat) for p, kat in ulozone)["mapa.pdf"] == 90


def test_nowy_plik_ladnie_na_koncu_a_nie_w_srodku(srodowisko):
    """Brat dokłada skany Eksploratorem — nie mogą rozbijać ustawionej kolejności."""
    katalog, _ = operaty.zaloz("001/2026", "GK.1.2026", "spis_tresci_wzor", {})
    for nazwa in ("spis_tresci.docx", "mapa.pdf"):
        (katalog / nazwa).write_bytes(b"x")
    operaty.zapisz_uklad(katalog, ["mapa.pdf", "spis_tresci.docx"], {})

    (katalog / "aaa_dolozony_pozniej.pdf").write_bytes(b"x")   # alfabetycznie pierwszy

    assert [p.name for p, _ in operaty.pliki_ulozone(katalog)] == [
        "mapa.pdf", "spis_tresci.docx", "aaa_dolozony_pozniej.pdf"]


def test_znikniety_plik_nie_psuje_ukladu(srodowisko):
    katalog, _ = operaty.zaloz("001/2026", "GK.1.2026", "spis_tresci_wzor", {})
    (katalog / "spis_tresci.docx").write_bytes(b"x")
    operaty.zapisz_uklad(katalog, ["mapa.pdf", "spis_tresci.docx"], {"mapa.pdf": 180})

    assert [p.name for p, _ in operaty.pliki_ulozone(katalog)] == ["spis_tresci.docx"]


def test_poprawienie_operatu_nie_kasuje_ukladu(srodowisko):
    """`zaloz()` przepisuje operat.json od nowa — układ ustawiony myszą ma to przeżyć."""
    katalog, _ = operaty.zaloz("001/2026", "GK.1.2026", "spis_tresci_wzor", {})
    (katalog / "spis_tresci.docx").write_bytes(b"x")
    (katalog / "mapa.pdf").write_bytes(b"x")
    operaty.zapisz_uklad(katalog, ["mapa.pdf", "spis_tresci.docx"], {"mapa.pdf": 270})

    operaty.zaloz("001/2026", "GK.1.2026", "spis_tresci_wzor", {"uwagi": "poprawione"})

    assert [p.name for p, _ in operaty.pliki_ulozone(katalog)] == [
        "mapa.pdf", "spis_tresci.docx"]
    assert operaty.uklad(katalog)["obroty"] == {"mapa.pdf": 270}


def test_obroty_zerowe_nie_smieca_w_pliku(srodowisko):
    katalog, _ = operaty.zaloz("001/2026", "GK.1.2026", "spis_tresci_wzor", {})
    operaty.zapisz_uklad(katalog, ["a.pdf", "b.pdf"], {"a.pdf": 0, "b.pdf": 360})
    assert operaty.uklad(katalog)["obroty"] == {}


# --- podglądy po operatach, których już nie ma -------------------------------

def test_podglady_znikaja_gdy_operat_przeniesiony_do_archiwum(srodowisko, bez_konwertera):
    """Brat archiwizuje operaty Eksploratorem — program się o tym nie dowiaduje.

    Podglądy zostawały wtedy na zawsze: `dane/podglad/` rósł mimo znikających operatów.
    Kasowanie przyciskiem w programie sprzątało po sobie, ale on tego przycisku
    do archiwizacji nie używa.
    """
    import shutil

    katalog, _ = operaty.zaloz("001/2026", "GK.1.2026", "spis_tresci_wzor", {})
    (katalog / "spis_tresci.docx").write_bytes(b"x")
    operaty.jako_pdf(katalog / "spis_tresci.docx")
    podglad = operaty.PODGLADY / katalog.name
    assert podglad.is_dir(), "podgląd w ogóle nie powstał — test sprawdza co innego"

    shutil.rmtree(katalog)                       # „przeniósł do archiwum”

    assert operaty.sprzataj_podglady() == 1
    assert not podglad.exists()


def test_sprzatanie_nie_rusza_podgladow_zywych_operatow(srodowisko, bez_konwertera):
    katalog, _ = operaty.zaloz("001/2026", "GK.1.2026", "spis_tresci_wzor", {})
    (katalog / "spis_tresci.docx").write_bytes(b"x")
    operaty.jako_pdf(katalog / "spis_tresci.docx")

    assert operaty.sprzataj_podglady() == 0
    assert (operaty.PODGLADY / katalog.name).is_dir()


def test_usuniecie_operatu_bez_katalogu_tez_kasuje_podglady(klient):
    """Operat skasowany z historii, gdy jego folder już wcześniej zniknął z dysku."""
    import shutil

    from app import db

    katalog, _ = operaty.zaloz("001/2026", "GK.1.2026", "spis_tresci_wzor", {})
    (operaty.PODGLADY / katalog.name).mkdir(parents=True)
    (operaty.PODGLADY / katalog.name / "spis_tresci.pdf").write_bytes(b"%PDF-1.4\n")
    identyfikator = db.zapisz_dokument("spis_tresci_wzor", "GK.1.2026",
                                       f"{katalog.name}/spis_tresci.docx", {},
                                       katalog.name, "001/2026")
    shutil.rmtree(katalog)                       # folder już przeniesiony do archiwum

    klient.post(f"/dokument/{identyfikator}/usun", follow_redirects=False)

    assert not (operaty.PODGLADY / "001.2026").exists()

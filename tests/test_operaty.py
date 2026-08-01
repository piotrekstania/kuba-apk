"""Katalog operatu: nazwy, zawartość, kolejność sklejania."""
from __future__ import annotations

import json

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

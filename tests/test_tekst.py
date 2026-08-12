"""Tekst z formatowaniem: pogrubienie, kursywa, podkreślenie.

Opis przebiegu prac brat pisał wcześniej w Wordzie i chce zachować pogrubienia, więc
program trzyma go jako fragment HTML. Dwie rzeczy muszą tu być pewne:

* **do dokumentu wchodzi tylko to, co umiemy oddać** — pogrubienie, kursywa,
  podkreślenie i złamanie wiersza. Reszta (kolory, czcionki wklejone z Worda, skrypty)
  leci do kosza, zanim cokolwiek zapiszemy;
* **`{{r pole }}` w formatce wymaga `RichText`** — zwykły napis wjechałby w to miejsce
  bez ucieczek i pierwszy `<` w opisie zrobiłby plik, którego Word nie otworzy.
"""
from __future__ import annotations

import pathlib
import tempfile
import zipfile

import pytest
from docx import Document
from docxtpl import DocxTemplate

from app import tekst


# --- co przepuszczamy --------------------------------------------------------

def test_pogrubienie_kursywa_podkreslenie_zostaja():
    assert tekst.oczysc("<b>a</b><i>b</i><u>c</u>") == "<b>a</b><i>b</i><u>c</u>"


def test_warianty_znacznikow_sprowadzamy_do_jednego():
    """Przeglądarki i Word wstawiają to samo pod różnymi nazwami."""
    assert tekst.oczysc("<strong>a</strong><em>b</em><ins>c</ins>") == "<b>a</b><i>b</i><u>c</u>"


def test_akapity_staja_sie_zlamaniem_wiersza():
    """Formatka ma jeden akapit na opis, więc prawdziwe akapity nie mają gdzie wejść."""
    assert tekst.oczysc("<p>Pierwszy</p><p>Drugi</p>") == "Pierwszy<br>Drugi"


def test_zwykly_tekst_przechodzi_bez_zmian():
    """Opisy zapisane przed wprowadzeniem formatowania mają dalej działać."""
    assert tekst.oczysc("Pomiar wykonano metodą RTN GNSS.") == "Pomiar wykonano metodą RTN GNSS."


# --- czego nie przepuszczamy -------------------------------------------------

def test_skrypt_leci_razem_z_trescia():
    """Sam znacznik zdjęty to za mało — „alert(1)” w opisie wygląda jak usterka."""
    assert tekst.oczysc("<script>alert(1)</script>Opis") == "Opis"


def test_atrybuty_znikaja():
    """`onclick` w treści, która wraca na stronę jako HTML, byłby dziurą."""
    assert tekst.oczysc('<b onclick="zle()" style="color:red">Klik</b>') == "<b>Klik</b>"


def test_kolory_i_czcionki_z_worda_nie_wchodza_do_operatu():
    """Wklejka z Worda ciągnie style, które rozjechałyby wygląd dokumentu."""
    wklejka = '<span style="font-family:Arial;color:#ff0000">Czerwone</span> i <b>grube</b>'

    assert tekst.oczysc(wklejka) == "Czerwone i <b>grube</b>"


def test_niedomkniety_znacznik_zostaje_domkniety():
    """Otwarte pogrubienie rozlałoby się na resztę strony."""
    assert tekst.oczysc("<b>Bez końca") == "<b>Bez końca</b>"


def test_nawiasy_trojkatne_z_tekstu_nie_staja_sie_znacznikami():
    assert tekst.oczysc("pole a < b oraz a &amp; b") == "pole a &lt; b oraz a &amp; b"


# --- „czy cokolwiek wpisano” -------------------------------------------------

def test_sam_znacznik_bez_tekstu_liczy_sie_jako_pusty():
    """Edytor zostawia po sobie puste znaczniki — to nadal jest pusty opis, więc
    w sprawozdaniu ma wyjść „brak”, a nie pusta dziura."""
    assert tekst.na_zwykly_tekst("<b></b><br>") == ""
    assert tekst.na_zwykly_tekst("<b>Coś</b>") == "Coś"


# --- droga do Worda ----------------------------------------------------------

def _wypelnij(znacznik: str, wartosc) -> pathlib.Path:
    kat = pathlib.Path(tempfile.mkdtemp())
    dokument = Document()
    dokument.add_paragraph(f"Przebieg: {znacznik}")
    wzor = kat / "wzor.docx"
    dokument.save(wzor)

    szablon = DocxTemplate(wzor)
    szablon.render({"opis": wartosc}, autoescape=True)
    wynik = kat / "wynik.docx"
    szablon.save(wynik)
    return wynik


def test_formatowanie_dojezdza_do_dokumentu_jako_biegi_tekstu():
    plik = _wypelnij("{{r opis }}", tekst.na_richtext(
        "<b>Pomiar</b> zwykły <i>skos</i> <u>kreska</u>"))

    akapit = Document(plik).paragraphs[0]
    style = {b.text: (b.bold, b.italic, b.underline) for b in akapit.runs if b.text}

    assert style["Pomiar"] == (True, None, None)
    assert style["skos"] == (None, True, None)
    assert style["kreska"] == (None, None, True)
    assert style[" zwykły "] == (None, None, None)


def test_zlamanie_wiersza_dojezdza_do_dokumentu():
    plik = _wypelnij("{{r opis }}", tekst.na_richtext("Pierwszy<br>Drugi"))

    assert zipfile.ZipFile(plik).read("word/document.xml").decode().count("<w:br/>") == 1


def test_richtext_nie_wstawia_biegu_w_srodek_tekstu():
    """To jest ten błąd, o który tu chodzi.

    Przy zwykłym `{{ pole }}` docxtpl wstawia `<w:r>` w środek `<w:t>` — Word takiego
    pliku **nie otworzy**, a LibreOffice łyka go bez słowa, więc zielony PDF u autora
    niczego nie dowodzi (to samo ugryzło już raz przy `ujednolic_wyglad.py`).
    Dlatego formatka ma `{{r opis_przebiegu }}`.
    """
    import re

    dobry = zipfile.ZipFile(_wypelnij("{{r opis }}", tekst.na_richtext("<b>a</b>b"))
                            ).read("word/document.xml").decode()
    assert re.search(r"<w:t[^>]*>[^<]*<w:r", dobry) is None

    zly = zipfile.ZipFile(_wypelnij("{{ opis }}", tekst.na_richtext("<b>a</b>b"))
                          ).read("word/document.xml").decode()
    assert re.search(r"<w:t[^>]*>[^<]*<w:r", zly) is not None, (
        "gdyby docxtpl przestał tak robić, ten test straciłby sens — sprawdź, czy "
        "formatka nadal musi mieć `{{r }}`")


@pytest.mark.parametrize("pusty", ["", "<b></b>", "<br>"])
def test_pusty_opis_nie_wywala_wypelniania(pusty):
    plik = _wypelnij("{{r opis }}", tekst.na_richtext(tekst.oczysc(pusty)))

    assert Document(plik).paragraphs[0].text.strip() == "Przebieg:"

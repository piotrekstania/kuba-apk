"""Tworzy przykładowy szablon operatu (szablony/operat_wzor.docx) wraz z opisem pól.

To tylko rusztowanie do testów — docelowy szablon brat robi sam w Wordzie,
wklejając swoje formatki i wstawiając w nich tagi {{ }}. Uruchomienie:

    python narzedzia/utworz_wzor_szablonu.py

Wzór jest celowo **ubogi**: dane roboty i położenie działki. Resztę sekcji dokładamy
po kolei, po omówieniu z bratem, jak ma naprawdę wyglądać jego operat. Danych stałych
(nazwisko, uprawnienia, pieczątka firmy) tu nie ma — brat woli je mieć wpisane na sztywno
we własnym szablonie, bo to i tak nie zmienia się między robotami. Wykazu współrzędnych
też nie ma: przychodzi osobnym PDF-em z C-Geo i dokleja się przez „Łączenie PDF”.
"""
import json
import sys
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.config import SZABLONY  # noqa: E402


def akapit(dokument, tekst, rozmiar=11, pogrubienie=False, wyrownanie=None, odstep_przed=0):
    element = dokument.add_paragraph()
    element.paragraph_format.space_before = Pt(odstep_przed)
    bieg = element.add_run(tekst)
    bieg.bold = pogrubienie
    bieg.font.size = Pt(rozmiar)
    if wyrownanie is not None:
        element.alignment = wyrownanie
    return element


def zbuduj() -> Path:
    dokument = Document()
    styl = dokument.styles["Normal"]
    styl.font.name = "Times New Roman"
    styl.font.size = Pt(11)

    SRODEK = WD_ALIGN_PARAGRAPH.CENTER
    PRAWA = WD_ALIGN_PARAGRAPH.RIGHT

    akapit(dokument, "{{ data_dokumentu }}", 10, wyrownanie=PRAWA, odstep_przed=6)

    akapit(dokument, "OPERAT TECHNICZNY", 20, pogrubienie=True, wyrownanie=SRODEK,
           odstep_przed=48)
    akapit(dokument, "{{ cel_opracowania }}", 13, wyrownanie=SRODEK, odstep_przed=8)

    akapit(dokument, "Nr roboty (KERG): {{ nr_roboty }}", 12, pogrubienie=True,
           wyrownanie=SRODEK, odstep_przed=36)
    akapit(dokument, "Nr operatu: {{ nr_operatu }}", 12, wyrownanie=SRODEK)

    akapit(dokument, "Województwo: {{ polozenie_wojewodztwo }}    "
                     "Powiat: {{ polozenie_powiat }}", 12, wyrownanie=SRODEK, odstep_przed=24)
    akapit(dokument, "Jednostka ewidencyjna: {{ polozenie_gmina_teryt }} {{ polozenie_gmina }}",
           12, wyrownanie=SRODEK)
    akapit(dokument, "Obręb: {{ polozenie_obreb_numer }} {{ polozenie_obreb }} "
                     "({{ polozenie_obreb_teryt }})", 12, wyrownanie=SRODEK)

    akapit(dokument, "Zgłoszono w: {{ osrodek }}", 11, wyrownanie=SRODEK, odstep_przed=36)
    akapit(dokument, "dnia {{ data_zgloszenia }}", 11, wyrownanie=SRODEK)

    akapit(dokument, "Położenie: {{ polozenie }}", 10, odstep_przed=60)

    plik = SZABLONY / "operat_wzor.docx"
    dokument.save(plik)
    return plik


# Na razie tylko „Robota” i położenie działki. Kolejne sekcje (zamawiający, opis techniczny,
# uwagi) dojdą po ustaleniu z bratem, jak mają wyglądać — dlatego nie ma tu ich atrap.
OPIS_POL = {
    "nazwa": "Operat techniczny (wzór testowy)",
    "opis": "Dane roboty i położenie działki. Szkielet do rozbudowy — "
            "kolejne sekcje dokładamy po ustaleniach.",
    "wzor_nazwy": "Operat_{nr_roboty}_{polozenie_obreb}",
    "licznik": "operat",
    "pola": [
        {"klucz": "nr_roboty", "etykieta": "Nr roboty / KERG", "wymagane": True,
         "grupa": "Robota", "szerokosc": "trzecia"},
        {"klucz": "nr_operatu", "etykieta": "Nr operatu", "typ": "auto_numer",
         "domyslnie": "{numer3}.{rok}", "grupa": "Robota", "szerokosc": "trzecia"},
        {"klucz": "data_dokumentu", "etykieta": "Data dokumentu", "typ": "date",
         "domyslnie": "dzisiaj", "grupa": "Robota", "szerokosc": "trzecia"},
        {"klucz": "cel_opracowania", "etykieta": "Cel opracowania", "typ": "select",
         "grupa": "Robota", "szerokosc": "polowa",
         "opcje": ["Mapa do celów projektowych",
                   "Mapa z projektem podziału nieruchomości",
                   "Wznowienie znaków granicznych / wyznaczenie punktów granicznych",
                   "Geodezyjna inwentaryzacja powykonawcza",
                   "Tyczenie obiektu budowlanego",
                   "Ustalenie przebiegu granic działek ewidencyjnych"]},
        {"klucz": "osrodek", "etykieta": "Ośrodek dokumentacji (PODGiK)",
         "grupa": "Robota", "szerokosc": "polowa"},
        {"klucz": "data_zgloszenia", "etykieta": "Data zgłoszenia pracy", "typ": "date",
         "grupa": "Robota", "szerokosc": "trzecia"},

        {"klucz": "polozenie", "etykieta": "Położenie działki", "typ": "teryt",
         "wymagane": True, "grupa": "Robota",
         "podpowiedz": "Wybierz z list — do dokumentu trafiają i nazwy, "
                       "i identyfikatory TERYT."},
    ],
}


if __name__ == "__main__":
    plik = zbuduj()
    opis = plik.with_suffix(".json")
    opis.write_text(json.dumps(OPIS_POL, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Utworzono:")
    print(" ", plik)
    print(" ", opis)

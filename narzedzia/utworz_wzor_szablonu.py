"""Tworzy przykładowy szablon spisu treści (szablony/spis_tresci_wzor.docx) z opisem pól.

To rusztowanie do podmiany: brat wkleja tu swoją formatkę Worda i przenosi do niej tagi
{{ }}, zamiast wymyślać ich nazwy od zera. Uruchomienie:

    python narzedzia/utworz_wzor_szablonu.py

Zakres jest celowo wąski — karta „Robota” i położenie działki. Kolejne sekcje dokładamy
po ustaleniach. Danych stałych (nazwisko, uprawnienia, pieczątka) tu nie ma: brat woli je
mieć wpisane na sztywno we własnym szablonie. Wykazu współrzędnych też nie ma — przychodzi
osobnym PDF-em z C-Geo i dokleja się przez „Złóż PDF”.
"""
import json
import sys
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.config import SZABLONY  # noqa: E402

# Pozycje spisu treści operatu. Dwie pierwsze są w każdym operacie, więc w formularzu
# stoją zaznaczone i wyłączone — widać je, ale nie da się ich odznaczyć.
SPIS_TRESCI = [
    "Spis treści",
    "Sprawozdanie techniczne",
    "Mapa porównania z terenem",
    "Szkic ilustrujący rozmieszczenie punktów szczegółów terenowych",
    "Wykaz pomierzonych lub obliczonych współrzędnych punktów szczegółów terenowych",
    "Wykaz zmian danych ewidencyjnych budynku",
    "Wykaz zmian danych ewidencyjnych",
    "Protokół ustalenia przebiegu granic działek ewidencyjnych",
    "Protokół wznowienia znaków granicznych, wyznaczenie punktów granicznych",
    "Protokół z czynności przyjęcia granic nieruchomości",
    "Mapa z projektem podziału nieruchomości",
    "Zawiadomienia stron",
    "Pełnomocnictwa stron",
]
SPIS_ZAWSZE = SPIS_TRESCI[:2]

# Rodzaje prac geodezyjnych — nazewnictwo z formularza zgłoszenia pracy geodezyjnej.
# Ostatnia pozycja jest tak długa celowo: to pełne brzmienie przepisu i w dokumencie
# ma się wydrukować w całości.
RODZAJE_PRACY = [
    "Sporządzenie mapy do celów projektowych",
    "Geodezyjna inwentaryzacja powykonawcza obiektów budowlanych",
    "Wznowienie znaków granicznych, wyznaczenie punktów granicznych lub ustalenie "
    "przebiegu granic działek ewidencyjnych",
    "Sporządzenie mapy z projektem podziału nieruchomości",
    "Sporządzenie projektu scalenia i podziału nieruchomości",
    "Sporządzenie innej mapy do celów prawnych",
    "Sporządzenie projektu scalenia lub wymiany gruntów",
    "Sporządzenie dokumentacji geodezyjnej na potrzeby rozgraniczenia nieruchomości",
    "Wykonanie innych czynności niż wymienione powyżej lub dokumentacji geodezyjnej "
    "w postaci map, rejestrów lub wykazów, których wykonanie może skutkować zmianą "
    "w bazach danych, o których mowa w art. 4 ust. 1a pkt 2, 3, 10 lub 12 ustawy, "
    "z wyjątkiem prac wykonywanych na zamówienie organu Służby Geodezyjnej "
    "i Kartograficznej.",
]


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

    akapit(dokument, "OPERAT TECHNICZNY", 20, pogrubienie=True, wyrownanie=SRODEK,
           odstep_przed=48)
    akapit(dokument, "{{ rodzaj_pracy }}", 12, wyrownanie=SRODEK, odstep_przed=10)

    akapit(dokument, "Nr roboty: {{ nr_roboty }}", 12, pogrubienie=True,
           wyrownanie=SRODEK, odstep_przed=36)
    akapit(dokument, "Nr operatu: {{ nr_operatu }}", 12, wyrownanie=SRODEK)
    akapit(dokument, "I.Z.P.G: {{ izpg }}", 12, wyrownanie=SRODEK)

    akapit(dokument, "Województwo: {{ polozenie_wojewodztwo }}    "
                     "Powiat: {{ polozenie_powiat }}", 12, wyrownanie=SRODEK, odstep_przed=24)
    akapit(dokument, "Jednostka ewidencyjna: {{ polozenie_gmina_teryt }} {{ polozenie_gmina }}",
           12, wyrownanie=SRODEK)
    akapit(dokument, "Obręb: {{ polozenie_obreb_numer }} {{ polozenie_obreb }} "
                     "({{ polozenie_obreb_teryt }})", 12, wyrownanie=SRODEK)
    akapit(dokument, "Działki nr: {{ nr_dzialki }}", 12, pogrubienie=True, wyrownanie=SRODEK)

    akapit(dokument, "Zgłoszenie pracy geodezyjnej: {{ data_zgloszenia }}", 11,
           wyrownanie=SRODEK, odstep_przed=36)
    akapit(dokument, "Zakończenie pracy geodezyjnej: {{ data_zakonczenia }}", 11,
           wyrownanie=SRODEK)
    akapit(dokument, "({{ data_zakonczenia_slownie }})", 10, wyrownanie=SRODEK)

    akapit(dokument, "SPIS TREŚCI", 14, pogrubienie=True, wyrownanie=SRODEK, odstep_przed=48)
    # {%p for %} kasuje cały akapit ze znacznikiem, więc pętla i treść muszą być osobno
    akapit(dokument, "{%p for pozycja in spis_tresci %}")
    akapit(dokument, "{{ loop.index }}. {{ pozycja }}", 12, odstep_przed=4)
    akapit(dokument, "{%p endfor %}")

    akapit(dokument, "Położenie: {{ polozenie }}", 10, odstep_przed=60)

    plik = SZABLONY / "spis_tresci_wzor.docx"
    dokument.save(plik)
    return plik


OPIS_POL = {
    "nazwa": "Spis treści operatu (wzór)",
    "opis": "Strona tytułowa i spis treści. Szkielet do podmiany na własną formatkę.",
    "wzor_nazwy": "Operat_{nr_roboty}",
    "licznik": "operat",
    "pola": [
        {"klucz": "nr_roboty", "etykieta": "Nr roboty", "wymagane": True,
         "grupa": "Robota", "szerokosc": "trzecia"},
        {"klucz": "nr_operatu", "etykieta": "Nr operatu", "typ": "auto_numer",
         "wymagane": True, "domyslnie": "{numer3}/{rok}",
         "grupa": "Robota", "szerokosc": "trzecia"},
        {"klucz": "izpg", "etykieta": "I.Z.P.G", "wymagane": True,
         "grupa": "Robota", "szerokosc": "trzecia"},

        # obie daty w jednym rzędzie: „polowa” to trzy z sześciu kolumn siatki
        {"klucz": "data_zgloszenia", "etykieta": "Data zgłoszenia pracy geodezyjnej",
         "typ": "date", "wymagane": True, "grupa": "Robota", "szerokosc": "polowa"},
        {"klucz": "data_zakonczenia", "etykieta": "Data zakończenia pracy geodezyjnej",
         "typ": "date", "wymagane": True, "grupa": "Robota", "szerokosc": "polowa"},

        {"klucz": "rodzaj_pracy", "etykieta": "Rodzaj pracy", "typ": "select",
         "grupa": "Robota", "szerokosc": "pelna", "opcje": RODZAJE_PRACY},

        {"klucz": "polozenie", "etykieta": "Położenie działki", "typ": "teryt",
         "wymagane": True, "grupa": "Położenie",
         "podpowiedz": "Wybierz z list — do dokumentu trafiają i nazwy, "
                       "i identyfikatory TERYT."},
        {"klucz": "nr_dzialki", "etykieta": "Nr działki", "wymagane": True,
         "grupa": "Położenie", "szerokosc": "polowa",
         "podpowiedz": "np. 123/4 albo kilka po przecinku: 123/4, 123/5, 124"},

        {"klucz": "spis_tresci", "etykieta": "Co wchodzi do operatu",
         "typ": "wybor_wielokrotny", "grupa": "Spis treści",
         "opcje": SPIS_TRESCI, "zawsze": SPIS_ZAWSZE,
         "podpowiedz": "Do dokumentu trafią tylko zaznaczone pozycje, w tej kolejności."},
    ],
}


if __name__ == "__main__":
    plik = zbuduj()
    opis = plik.with_suffix(".json")
    opis.write_text(json.dumps(OPIS_POL, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Utworzono:")
    print(" ", plik)
    print(" ", opis)

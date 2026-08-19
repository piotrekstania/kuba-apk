"""Rejestr szablonów.

Zasada działania: źródłem prawdy jest plik .docx. Formularz w przeglądarce
powstaje z tagów Jinja znalezionych w szablonie, więc dodanie {{ nowe_pole }}
w Wordzie automatycznie dokłada pole w aplikacji — bez ruszania kodu.

Obok szablonu może (nie musi) leżeć plik .json o tej samej nazwie. Opisuje
etykiety, typy pól, kolejność i grupy. Pola nieopisane trafiają na koniec
formularza jako zwykłe pola tekstowe.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from docxtpl import DocxTemplate

from .config import SZABLONY

TYPY_PROSTE = {"text", "textarea", "date", "number", "select", "checkbox"}

# Znaczniki, które program **wylicza sam** z innych pól — nie wolno ich pokazać
# w formularzu jako pustych pól do wpisania. Muszą się zgadzać z tym, co dokłada
# `generator.przygotuj_kontekst` i `generator.pola_teryt`.
SUFIKSY_TERYT = ("_wojewodztwo", "_wojewodztwo_teryt", "_powiat", "_powiat_teryt",
                 "_gmina", "_gmina_teryt", "_obreb", "_obreb_teryt", "_obreb_numer")
SUFIKSY_DATY = ("_iso", "_slownie")
SUFIKSY_WYBORU = ("_pliki",)
# `<klucz>_jest` — czy pole zostało wypełnione. Dla **każdego** pola, bo to zwykły
# warunek do `{%p if ... %}` w formatce: „wpisał coś, to pokaż; nie wpisał, to napisz
# «brak»”. Powstało, gdy z formularza zniknął checkbox „Opis przebiegu”: formatka pytała
# o `opis_przebiegu_jest`, a odpowiedź na to pytanie widać po samej treści opisu, więc
# osobne pole do klikania było pytaniem o to, co program i tak wie.
SUFIKS_JEST = "_jest"
POLA_WYLICZANE = {"data_dzisiaj", "data_dzisiaj_slownie", "rok"}

# Pola, przy których warto podpowiedzieć, czy ULDK zna taką działkę. Rozpoznajemy po
# kluczu, a nie po wpisie w `.json`: formatki utrzymuje autor, a dopisywanie do nich
# opcji technicznej po to, żeby program zapytał usługę GUGiK-u, tylko zaśmiecałoby
# opis pola. Sprawdzenie jest wyłącznie podpowiedzią, więc nietrafienie nic nie psuje.
POLA_DZIALKI = {"nr_dzialki", "nr_dzialek", "dzialki", "dzialka", "numer_dzialki"}


@dataclass
class Pole:
    klucz: str
    etykieta: str
    typ: str = "text"
    wymagane: bool = False
    grupa: str = "Dane"
    podpowiedz: str = ""
    opcje: list[str] = field(default_factory=list)
    zawsze: list[str] = field(default_factory=list)   # pozycje zaznaczone na stałe
    domyslne: list[str] = field(default_factory=list)  # zaznaczone na start, ale odklikywalne
    wzor_wartosci: str = ""     # np. "{nr_roboty}-{opcja}.gml" — wynik pod kluczem <pole>_pliki
    tylko: list[str] = field(default_factory=list)    # typ "dokumenty": które szablony pokazać
    # typ "wybor_wielokrotny": które zaznaczenie uruchamia który dokument, np.
    # {"Sprawozdanie techniczne": "sprawozdanie_techniczne_wzor"}. Dzięki temu spis treści
    # jest **jedynym** włącznikiem: pozycja w spisie i osobny checkbox „wygeneruj” pytały
    # o to samo dwa razy i dało się je ustawić sprzecznie.
    dokumenty: dict[str, str] = field(default_factory=dict)
    aktywne_gdy: str = ""       # pole jest wyszarzone, dopóki wskazany przełącznik
                                # nie jest zaznaczony; "dokumenty:id" celuje w pozycję listy
    kolumny: list[dict[str, str]] = field(default_factory=list)   # tylko dla typ="tabela"
    # tylko dla typ="sekcje": pola powtarzane w każdym powtórzeniu. Wykaz zmian danych
    # budynku to 15 atrybutów w dwóch stanach — jako tabela miałby 30 kolumn i nie dałoby
    # się go wypełnić, więc powtarzamy **komplet pól**, a nie wiersz.
    podpola: list[dict[str, str]] = field(default_factory=list)
    etykieta_pozycji: str = ""  # nagłówek jednego powtórzenia, np. „Wykaz”
    etykieta_dodaj: str = ""    # napis na przycisku dokładającym powtórzenie

    @property
    def wiersze_sekcji(self) -> list[dict[str, Any]]:
        """Podpola pogrupowane w wiersze — do układu takiego jak tabela w dokumencie.

        Gdy podpole ma `wiersz` (nazwę atrybutu) i `kolumna` (np. „dotychczas”), formularz
        rysuje je jak tabelę w wykazie: nazwa atrybutu **raz**, obok pola dla każdego stanu.
        Pierwsza wersja powtarzała nazwę przy obu polach („Adres budynku — dotychczasowy”,
        „Adres budynku — nowy”) i przy piętnastu atrybutach robiła się z tego ściana tekstu.

        Grupujemy tutaj, a nie w szablonie: `groupby` w Jinji wymaga posortowania, a to
        rozsypałoby kolejność atrybutów — a ona ma być ta sama co w dokumencie.
        """
        wiersze: list[dict[str, Any]] = []
        gdzie: dict[str, dict[str, Any]] = {}
        for podpole in self.podpola:
            nazwa = podpole.get("wiersz", "")
            if not nazwa:
                continue
            if nazwa not in gdzie:
                gdzie[nazwa] = {"etykieta": nazwa, "pola": {}}
                wiersze.append(gdzie[nazwa])
            gdzie[nazwa]["pola"][podpole.get("kolumna", "")] = podpole
        return wiersze
    domyslnie: str = ""
    zrodlo: str = ""            # "ustawienia" = bierz z danych stałych, nie pokazuj w formularzu
    szerokosc: str = "pelna"    # "pelna" | "polowa" | "trzecia"
    biblioteka: str = ""        # nad polem staje lista gotowych tekstów z Ustawień
                                # ("sprawozdanie") i przycisk wklejający wybrany
    formatowanie: bool = False  # pole przyjmuje pogrubienie/kursywę/podkreślenie
                                # (wtedy znacznik w formatce musi być `{{r pole }}`)


@dataclass
class Szablon:
    id: str                     # nazwa pliku bez rozszerzenia
    plik: Path
    nazwa: str
    # Nazwa **samego dokumentu**, gdy różni się od nazwy szablonu. Kafelek na stronie
    # głównej i tytuł formularza mówią „Operat”, bo tam zaczyna się cała robota,
    # ale plik, który z tego szablonu powstaje, to spis treści — i tak ma się nazywać
    # na listach formatek. Puste = ta sama nazwa co szablonu.
    nazwa_dokumentu: str = ""
    opis: str = ""
    wzor_nazwy: str = "{id_szablonu}"
    licznik: str = ""           # nazwa licznika dla pola typu "auto_numer"
    glowny: bool = False        # kafelek na stronie głównej; reszta tylko jako dodatek
    # Klucz pola, bez którego ten dokument nie ma sensu. Wykaz zmian danych budynku
    # to sama pętla po wykazach — przy pustej liście powstawał **plik bez jednej litery**,
    # który szedł do konwersji i wychodził w składaniu operatu jako pusty kafelek.
    wymaga: str = ""
    pola: list[Pole] = field(default_factory=list)

    @property
    def grupy(self) -> dict[str, list[Pole]]:
        wynik: dict[str, list[Pole]] = {}
        for pole in self.pola:
            if pole.zrodlo == "ustawienia":
                continue
            wynik.setdefault(pole.grupa, []).append(pole)
        return wynik


def _etykieta_z_klucza(klucz: str) -> str:
    tekst = klucz.replace("_", " ").strip()
    return tekst[:1].upper() + tekst[1:]


def _zmienne_szablonu(plik: Path) -> list[str]:
    """Nazwy zmiennych użytych w .docx, w kolejności wystąpienia w dokumencie."""
    dokument = DocxTemplate(plik)
    znalezione = dokument.get_undeclared_template_variables()
    # get_undeclared_template_variables zwraca zbiór — porządkujemy wg pozycji w tekście
    dokument.init_docx(reload=False)
    tekst = dokument.get_xml()
    def pozycja(nazwa: str) -> int:
        trafienie = re.search(rf"\b{re.escape(nazwa)}\b", tekst)
        return trafienie.start() if trafienie else 10**9
    return sorted(znalezione, key=pozycja)


def wczytaj_szablon(plik: Path) -> Szablon:
    opis_json = plik.with_suffix(".json")
    meta: dict[str, Any] = {}
    if opis_json.exists():
        meta = json.loads(opis_json.read_text(encoding="utf-8"))

    szablon = Szablon(
        id=plik.stem,
        plik=plik,
        nazwa=meta.get("nazwa", _etykieta_z_klucza(plik.stem)),
        nazwa_dokumentu=meta.get("nazwa_dokumentu", "") or meta.get(
            "nazwa", _etykieta_z_klucza(plik.stem)),
        opis=meta.get("opis", ""),
        wzor_nazwy=meta.get("wzor_nazwy", plik.stem + "_{data_dokumentu}"),
        licznik=meta.get("licznik", ""),
        glowny=bool(meta.get("glowny", False)),
        wymaga=meta.get("wymaga", ""),
    )

    # Listy wielokrotnego użytku: `"listy": {"kst": [...]}` w `.json`, a pole albo podpole
    # mówi tylko `"opcje": "kst"`. Klasyfikacja KŚT stoi przy **dwóch** podpolach (stan
    # dotychczasowy i nowy) i musi być w obu identyczna co do znaku — dwie kopie w pliku
    # rozjechałyby się przy pierwszej poprawce, a wykaz z dwiema różnymi wersjami tej samej
    # klasyfikacji to dokument, którego ośrodek nie przyjmie.
    listy = {nazwa: list(pozycje) for nazwa, pozycje in (meta.get("listy") or {}).items()}

    def opcje_pola(surowe: dict[str, Any]) -> list[str]:
        """Lista wprost w polu albo nazwa listy z `"listy"`."""
        opcje = surowe.get("opcje", [])
        return list(listy.get(opcje, [])) if isinstance(opcje, str) else list(opcje)

    opisane: dict[str, Pole] = {}
    for surowe in meta.get("pola", []):
        klucz = surowe["klucz"]
        opisane[klucz] = Pole(
            klucz=klucz,
            etykieta=surowe.get("etykieta", _etykieta_z_klucza(klucz)),
            typ=surowe.get("typ", "text"),
            wymagane=bool(surowe.get("wymagane", False)),
            grupa=surowe.get("grupa", "Dane"),
            podpowiedz=surowe.get("podpowiedz", ""),
            opcje=opcje_pola(surowe),
            zawsze=list(surowe.get("zawsze", [])),
            domyslne=list(surowe.get("domyslne", [])),
            wzor_wartosci=surowe.get("wzor_wartosci", ""),
            tylko=list(surowe.get("tylko", [])),
            dokumenty=dict(surowe.get("dokumenty", {})),
            aktywne_gdy=surowe.get("aktywne_gdy", ""),
            kolumny=list(surowe.get("kolumny", [])),
            domyslnie=str(surowe.get("domyslnie", "")),
            zrodlo=surowe.get("zrodlo", ""),
            szerokosc=surowe.get("szerokosc", "pelna"),
            podpola=[{**pod, "opcje": opcje_pola(pod)}
                     for pod in surowe.get("podpola", [])],
            etykieta_pozycji=surowe.get("etykieta_pozycji", ""),
            etykieta_dodaj=surowe.get("etykieta_dodaj", ""),
            biblioteka=surowe.get("biblioteka", ""),
            formatowanie=bool(surowe.get("formatowanie")),
        )

    # kolejność: najpierw pola opisane w .json, potem reszta wykryta w szablonie
    szablon.pola = list(opisane.values())
    znane = set(opisane) | POLA_WYLICZANE
    # `<klucz>_jest` przysługuje każdemu polu — patrz `SUFIKS_JEST`
    znane.update(klucz + SUFIKS_JEST for klucz in opisane)
    for pole in opisane.values():
        if pole.typ == "teryt":
            znane.update(pole.klucz + sufiks for sufiks in SUFIKSY_TERYT)
        elif pole.typ == "date":
            znane.update(pole.klucz + sufiks for sufiks in SUFIKSY_DATY)
        elif pole.typ == "wybor_wielokrotny":
            znane.update(pole.klucz + sufiks for sufiks in SUFIKSY_WYBORU)
    for nazwa in _zmienne_szablonu(plik):
        if nazwa not in znane:
            szablon.pola.append(Pole(klucz=nazwa, etykieta=_etykieta_z_klucza(nazwa),
                                     grupa="Pozostałe pola z szablonu"))
    return szablon


def lista_skrocona() -> list[dict[str, str]]:
    """Same identyfikatory i nazwy szablonów, bez otwierania plików .docx.

    Potrzebne do listy „co jeszcze wygenerować”. Pełne `lista_szablonow()` czyta każdy
    dokument Worda, a tutaj wystarczy nazwa — no i wołanie go z `wczytaj_szablon`
    zapętliłoby się.
    """
    wynik = []
    for plik in sorted(SZABLONY.glob("*.docx")):
        if plik.name.startswith("~$"):
            continue
        nazwa = nazwa_dokumentu = _etykieta_z_klucza(plik.stem)
        opis_json = plik.with_suffix(".json")
        if opis_json.exists():
            try:
                meta = json.loads(opis_json.read_text(encoding="utf-8"))
                nazwa = meta.get("nazwa", nazwa)
                nazwa_dokumentu = meta.get("nazwa_dokumentu", "") or nazwa
            except ValueError:
                pass
        wynik.append({"id": plik.stem, "nazwa": nazwa, "nazwa_dokumentu": nazwa_dokumentu})
    return wynik


def lista_szablonow() -> list[Szablon]:
    pliki = sorted(p for p in SZABLONY.glob("*.docx") if not p.name.startswith("~$"))
    wynik = []
    for plik in pliki:
        try:
            wynik.append(wczytaj_szablon(plik))
        except Exception as blad:                      # uszkodzony plik nie może wywalić listy
            wynik.append(Szablon(id=plik.stem, plik=plik,
                                 nazwa=plik.stem, opis=f"⚠ Nie udało się wczytać: {blad}"))
    return wynik


def szablon_po_id(identyfikator: str) -> Szablon | None:
    plik = SZABLONY / f"{identyfikator}.docx"
    if not plik.exists():
        return None
    return wczytaj_szablon(plik)

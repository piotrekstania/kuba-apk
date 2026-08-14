"""Tekst z formatowaniem: pogrubienie, kursywa, podkreślenie, przekreślenie, indeksy.

Brat pisze opisy przebiegu prac raz i wkleja je do kolejnych sprawozdań — a pisał je
wcześniej w Wordzie, więc wklejka ma zachować to, co w niej widać. Program trzyma opis
jako fragment HTML i przenosi go do dokumentu jako sformatowane biegi tekstu.

**Czego nie przenosimy: rozmiaru i kroju czcionki oraz kolorów.** To nie jest brak, tylko
decyzja: krój i rozmiary w operacie ustala formatka i pilnuje ich `ujednolic_wyglad.py`,
żeby wszystkie dokumenty wyglądały jak jeden komplet. Wklejka z Worda ciągnie za sobą
„Times New Roman 11 pt", a wklejka ze strony — kolory tła; przepuszczone rozjechałyby
dokument dokładnie w tym, co skrypt osobno prostuje.

Reszta przechodzi, bo `RichText` z docxtpl umie to wprost oddać.

Trudność, przez którą to nie jest samo przepisanie znaczników: **Word i przeglądarki
zapisują pogrubienie na kilka sposobów**. Raz jest to `<b>`, raz `<strong>`, a najczęściej
(przy kopiowaniu z Worda) `<span style="font-weight:700">`. Dlatego czytamy i znaczniki,
i `style` — inaczej wklejone pogrubienie ginęłoby bez śladu, a to jest właśnie ten
przypadek, dla którego cała ta funkcja powstała.

Wszystko na bibliotece standardowej: `html.parser` to zwykły automat stanowy, a doproszenie
tu zewnętrznego sanitizera oznaczałoby kolejną zależność do pilnowania.
"""
from __future__ import annotations

import html
import re
from html.parser import HTMLParser

from docxtpl import RichText

# Nazwa stylu → znacznik, którym go zapisujemy. Kolejność ma znaczenie tylko dla wyglądu
# gotowego HTML-a, nie dla dokumentu.
STYLE = ("b", "i", "u", "s", "sup", "sub")

# Znacznik → styl, który włącza. Warianty tego samego (`strong`, `em`, `del`…) sprowadzamy
# do jednego, bo edytory i Word używają ich wymiennie.
ZNACZNIKI = {
    "b": "b", "strong": "b",
    "i": "i", "em": "i",
    "u": "u", "ins": "u",
    "s": "s", "strike": "s", "del": "s",
    "sup": "sup", "sub": "sub",
}

# Akapity z wklejanego tekstu zamieniamy na złamanie wiersza: formatka ma jeden akapit
# na opis, więc prawdziwe akapity i tak nie miałyby gdzie wejść.
BLOKOWE = ("p", "div", "li", "tr", "br")

# Znaczniki bez domknięcia. **Nie odkładamy ich na stos stylów**: `<br>` nie ma `</br>`,
# więc kolejne `</p>` zdejmowałoby ramkę po nim zamiast po akapicie, a styl akapitu
# zostawał włączony do końca tekstu. Objaw: wklejka z Worda w postaci
# `<p style="font-weight:700">pierwsza<br>druga</p><p>zwykła</p>` wychodziła pogrubiona
# w całości — i to akurat przy tym, po co ta obsługa powstała.
PUSTE = ("br", "img", "hr", "col", "input", "meta", "link", "source", "wbr")

# Znaczniki wyrzucane **razem z treścią**. Przy pozostałych zdejmujemy sam znacznik
# i zostawiamy tekst — ale ciało `<script>` to nie jest tekst, który ktoś chciał wkleić.
Z_TRESCIA = ("script", "style", "head", "title")

# To samo pogrubienie Word potrafi zapisać jako `<b>` albo jako `style="font-weight:700"`.
# Bez czytania stylów wklejka z Worda traciłaby całe formatowanie — czyli dokładnie to,
# po co ta obsługa powstała.
_STYL_CSS = (
    ("b", re.compile(r"font-weight\s*:\s*(bold|[6-9]\d\d)", re.I)),
    ("i", re.compile(r"font-style\s*:\s*italic", re.I)),
    ("u", re.compile(r"text-decoration[^;]*:\s*[^;]*underline", re.I)),
    ("s", re.compile(r"text-decoration[^;]*:\s*[^;]*line-through", re.I)),
)


def _style_z_atrybutow(atrybuty: list[tuple[str, str | None]]) -> list[str]:
    css = " ".join(w or "" for nazwa, w in atrybuty if nazwa == "style")
    return [styl for styl, wzorzec in _STYL_CSS if wzorzec.search(css)]


class _Rozbior(HTMLParser):
    """Fragment HTML → lista kawałków `(tekst, zestaw stylów)`; `\\n` znaczy nowy wiersz."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.kawalki: list[tuple[str, frozenset[str]]] = []
        self.stos: list[list[str]] = []      # style wniesione przez kolejne znaczniki
        self.pomijane = 0

    def _aktywne(self) -> frozenset[str]:
        return frozenset(s for poziom in self.stos for s in poziom)

    def _zlamanie(self) -> None:
        """`<br>` — zawsze nowy wiersz, także drugi z rzędu.

        Dwa `<br>` obok siebie to **pusta linia**, czyli świadomy odstęp: brat oddziela
        nimi akapity opisu. Pierwsza wersja zwijała je do jednego „żeby nie dublować”
        i po zapisaniu opis zlepiał się w jeden blok — dokładnie ta usterka, którą zgłosił.
        """
        self.kawalki.append(("\n", frozenset()))

    def _granica_bloku(self) -> None:
        """Koniec/początek `<p>` albo `<div>` — nowy wiersz, ale bez mnożenia.

        Tu zwijanie jest na miejscu: `</div><div>` to jedna granica opisana dwoma
        znacznikami, a nie dwie puste linie.
        """
        if self.kawalki and self.kawalki[-1][0] != "\n":
            self.kawalki.append(("\n", frozenset()))

    def handle_starttag(self, tag, atrybuty):
        if tag in Z_TRESCIA:
            self.pomijane += 1
            return
        if self.pomijane:
            return
        if tag in PUSTE:
            if tag == "br":
                self._zlamanie()
            return                       # bez domknięcia, więc nic nie wnosi na stos
        style = _style_z_atrybutow(atrybuty)
        if tag in ZNACZNIKI:
            style.append(ZNACZNIKI[tag])
        if tag in BLOKOWE:
            self._granica_bloku()
        self.stos.append(style)

    def handle_startendtag(self, tag, atrybuty):
        if tag == "br" and not self.pomijane:
            self._zlamanie()

    def handle_endtag(self, tag):
        if tag in Z_TRESCIA:
            self.pomijane = max(0, self.pomijane - 1)
            return
        if self.pomijane:
            return
        if tag in BLOKOWE and tag != "br":
            self._granica_bloku()
        if self.stos:
            self.stos.pop()

    def handle_data(self, dane):
        if dane and not self.pomijane:
            self.kawalki.append((dane, self._aktywne()))


def _kawalki(tresc: str) -> list[tuple[str, frozenset[str]]]:
    parser = _Rozbior()
    parser.feed(tresc or "")
    parser.close()
    kawalki = parser.kawalki
    while kawalki and kawalki[0][0] == "\n":      # puste wiersze na brzegach nic nie wnoszą
        kawalki.pop(0)
    while kawalki and kawalki[-1][0] == "\n":
        kawalki.pop()
    return kawalki


def oczysc(tresc: str) -> str:
    """Fragment HTML obcięty do tego, co program potrafi pokazać i wstawić do Worda."""
    wynik: list[str] = []
    otwarte: list[str] = []
    for tekst, style in _kawalki(tresc):
        if tekst == "\n":
            while otwarte:
                wynik.append(f"</{otwarte.pop()}>")
            wynik.append("<br>")
            continue
        # domykamy to, czego już nie ma, i otwieramy to, co doszło — dzięki temu
        # sąsiednie kawałki o tym samym stylu nie mnożą znaczników
        while otwarte and otwarte[-1] not in style:
            wynik.append(f"</{otwarte.pop()}>")
        for znacznik in STYLE:
            if znacznik in style and znacznik not in otwarte:
                otwarte.append(znacznik)
                wynik.append(f"<{znacznik}>")
        wynik.append(html.escape(tekst, quote=False))
    while otwarte:
        wynik.append(f"</{otwarte.pop()}>")
    return "".join(wynik).strip()


def na_zwykly_tekst(tresc: str) -> str:
    """Sam tekst, bez znaczników — do sprawdzenia „czy cokolwiek wpisano”."""
    return "".join(t for t, _ in _kawalki(tresc)).strip()


def na_richtext(tresc: str, krój: str = "", rozmiar: int = 0) -> RichText:
    """Fragment HTML → `RichText` docxtpl, czyli sformatowane biegi tekstu w Wordzie.

    W formatce znacznik musi mieć postać `{{r pole }}`. Przy zwykłym `{{ pole }}`
    docxtpl wstawia `<w:r>` w środek `<w:t>` — Word takiego pliku **nie otworzy**
    (sprawdzone), a LibreOffice łyka to bez słowa, więc zielony PDF niczego nie dowodzi.

    `krój` i `rozmiar` (w półpunktach, jak w OOXML) **odczytuje generator z samej
    formatki** — z biegu, w którym stoi znacznik — i podaje tutaj. Nie bierze się to
    z kodu: o wygląd dokumentu ma decydować formatka, tak jak wszędzie indziej.

    Bez tego wstawiony opis wychodził inną czcionką niż tekst obok: `RichText` zastępuje
    bieg ze znacznikiem własnymi biegami, a te bez ustawień spadają do domyślnej czcionki
    dokumentu, a nie do tej z akapitu. Brat zobaczył to od razu — dwa opisy obok siebie,
    każdy innym krojem.
    """
    bogaty = RichText()
    dodatkowe = {}
    if krój:
        dodatkowe["font"] = krój
    if rozmiar:
        dodatkowe["size"] = rozmiar
    for tekst, style in _kawalki(tresc):
        bogaty.add(tekst, bold="b" in style, italic="i" in style,
                   underline="u" in style, strike="s" in style,
                   superscript="sup" in style, subscript="sub" in style, **dodatkowe)
    return bogaty

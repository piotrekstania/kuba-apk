"""Tekst z formatowaniem: pogrubienie, kursywa, podkreślenie.

Brat pisze opisy przebiegu prac raz, żeby wklejać je do kolejnych sprawozdań — i pisze
je tak, jak pisał w Wordzie, czyli z pogrubieniami. Zwykłe pole tekstowe tego nie uniesie,
więc w przeglądarce stoi tam mały edytor, a program trzyma **fragment HTML**.

Dopuszczamy dokładnie cztery znaczniki: `<b>`, `<i>`, `<u>` i `<br>`. Wąska lista jest
tu celowa i pilnuje trzech rzeczy naraz:

* **czego umiemy dotrzymać w Wordzie** — tylko to, co da się wprost przełożyć na biegi
  tekstu (`RichText`). Listy punktowane i tabele wymagałyby przebudowy formatki, więc
  do niej nie wpuszczamy czegoś, czego i tak nie oddamy;
* **czego nie chcemy w gotowym dokumencie** — wklejenie z Worda albo ze strony ciągnie
  za sobą kolory, czcionki i style; przepuszczone dalej rozjechałyby wygląd operatu,
  o który skrypt `ujednolic_wyglad.py` walczy osobno;
* **bezpieczeństwo strony** — to, co brat wklei, wraca do przeglądarki jako HTML.
  Skrypt czy `onclick` w tym miejscu byłby dziurą, nawet w programie chodzącym na
  własnym komputerze.

Wszystko na bibliotece standardowej: `html.parser` to zwykły automat stanowy, a doproszenie
tu zewnętrznego sanitizera oznaczałoby kolejną zależność do pilnowania.
"""
from __future__ import annotations

import html
from html.parser import HTMLParser

from docxtpl import RichText

# `<b>`, `<i>`, `<u>` niosą formatowanie, `<br>` łamie wiersz.
DOZWOLONE = ("b", "i", "u")
# Przeglądarki i Word wstawiają to samo pod różnymi nazwami — sprowadzamy do jednej.
ZAMIENNIKI = {"strong": "b", "em": "i", "ins": "u"}
# Akapity z wklejanego tekstu zamieniamy na złamanie wiersza: formatka ma jeden akapit
# na opis, więc prawdziwe akapity i tak nie miałyby gdzie wejść.
BLOKOWE = ("p", "div", "li", "tr")
# Znaczniki, z których wyrzucamy także **treść**. Przy pozostałych zdejmujemy sam znacznik
# i zostawiamy tekst — ale ciało `<script>` to nie jest tekst, który brat chciał wkleić;
# przepuszczone zostawiłoby w opisie „alert(1)” i wyglądało jak usterka programu.
Z_TRESCIA = ("script", "style", "head", "title")


class _Czyszczenie(HTMLParser):
    """Przepuszcza tylko `<b>`, `<i>`, `<u>` i `<br>`; resztę znaczników zdejmuje."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.wynik: list[str] = []
        self.stos: list[str] = []
        self.pomijane = 0            # zagnieżdżenie znaczników wyrzucanych z treścią

    def _blok(self) -> None:
        """Złamanie wiersza między blokami — ale nie na samym początku i nie podwójne."""
        if self.wynik and not "".join(self.wynik).endswith("<br>"):
            self.wynik.append("<br>")

    def handle_starttag(self, tag, atrybuty):
        if tag in Z_TRESCIA:
            self.pomijane += 1
            return
        if self.pomijane:
            return
        tag = ZAMIENNIKI.get(tag, tag)
        if tag == "br":
            self.wynik.append("<br>")
        elif tag in DOZWOLONE:
            self.stos.append(tag)
            self.wynik.append(f"<{tag}>")
        elif tag in BLOKOWE:
            self._blok()
        # atrybuty odrzucamy zawsze — nie ma wśród dozwolonych znacznika,
        # któremu byłyby do czegokolwiek potrzebne

    def handle_startendtag(self, tag, atrybuty):
        if ZAMIENNIKI.get(tag, tag) == "br":
            self.wynik.append("<br>")

    def handle_endtag(self, tag):
        if tag in Z_TRESCIA:
            self.pomijane = max(0, self.pomijane - 1)
            return
        if self.pomijane:
            return
        tag = ZAMIENNIKI.get(tag, tag)
        if tag in DOZWOLONE and tag in self.stos:
            # domykamy wszystko, co zostało otwarte w środku — inaczej zostawiony
            # otwarty znacznik rozlałby pogrubienie na resztę strony
            while self.stos:
                otwarty = self.stos.pop()
                self.wynik.append(f"</{otwarty}>")
                if otwarty == tag:
                    break
        elif tag in BLOKOWE:
            self._blok()

    def handle_data(self, dane):
        if not self.pomijane:
            self.wynik.append(html.escape(dane, quote=False))

    def gotowe(self) -> str:
        while self.stos:
            self.wynik.append(f"</{self.stos.pop()}>")
        return "".join(self.wynik)


def oczysc(tresc: str) -> str:
    """Fragment HTML obcięty do tego, co program potrafi pokazać i wstawić do Worda."""
    parser = _Czyszczenie()
    parser.feed(tresc or "")
    parser.close()
    wynik = parser.gotowe()
    # puste złamania z początku i końca nic nie wnoszą, a w dokumencie robią dziury
    while wynik.startswith("<br>"):
        wynik = wynik[len("<br>"):]
    while wynik.endswith("<br>"):
        wynik = wynik[: -len("<br>")]
    return wynik.strip()


class _NaTekst(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.czesci: list[str] = []

    def handle_starttag(self, tag, atrybuty):
        if tag == "br":
            self.czesci.append("\n")

    handle_startendtag = handle_starttag

    def handle_data(self, dane):
        self.czesci.append(dane)


def na_zwykly_tekst(tresc: str) -> str:
    """Sam tekst, bez znaczników — do sprawdzenia „czy cokolwiek wpisano”."""
    parser = _NaTekst()
    parser.feed(tresc or "")
    parser.close()
    return "".join(parser.czesci).strip()


class _NaBiegi(HTMLParser):
    """Zbiera kawałki tekstu razem z tym, jak mają być sformatowane."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.kawalki: list[tuple[str, dict[str, bool]]] = []
        self.stos: list[str] = []

    def _styl(self) -> dict[str, bool]:
        return {"bold": "b" in self.stos, "italic": "i" in self.stos,
                "underline": "u" in self.stos}

    def handle_starttag(self, tag, atrybuty):
        if tag == "br":
            self.kawalki.append(("\n", self._styl()))
        elif tag in DOZWOLONE:
            self.stos.append(tag)

    handle_startendtag = handle_starttag

    def handle_endtag(self, tag):
        if tag in self.stos:
            self.stos.remove(tag)

    def handle_data(self, dane):
        if dane:
            self.kawalki.append((dane, self._styl()))


def na_richtext(tresc: str) -> RichText:
    """Fragment HTML → `RichText` docxtpl, czyli sformatowane biegi tekstu w Wordzie.

    W formatce znacznik musi mieć postać `{{r pole }}`. Przy zwykłym `{{ pole }}`
    docxtpl wstawia `<w:r>` w środek `<w:t>` — Word takiego pliku **nie otworzy**
    (sprawdzone), a LibreOffice łyka to bez słowa, więc zielony PDF niczego nie dowodzi.
    """
    bogaty = RichText()
    parser = _NaBiegi()
    parser.feed(tresc or "")
    parser.close()
    for tekst, styl in parser.kawalki:
        bogaty.add(tekst, **styl)
    return bogaty

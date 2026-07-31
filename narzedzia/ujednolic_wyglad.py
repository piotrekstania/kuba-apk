"""Nakłada wspólny wygląd na szablony operatu.

Zamysł: dokumenty w jednej teczce mają wyglądać jak komplet, a nie jak formatki robione
w różnych latach. Hierarchię buduje **rozmiar i grubość pisma**, a nie podkreślenia
i ozdobniki — stąd „minimalistycznie”.

Czego skrypt NIE rusza:

* słów — ani jednego znaku treści, także znaczników ``{{ }}`` i ``{%p %}``,
* czerwieni — numer roboty zostaje czerwony wszędzie, gdzie był,
* stopki, marginesów i rozmiaru strony — te są w obu plikach już zgodne.

Co ujednolica:

* **krój** — jeden na cały dokument, także w stylu bazowym, żeby dopisany później
  w Wordzie akapit nie wyszedł inną czcionką,
* **logo** — ta sama szerokość i to samo miejsce w każdym dokumencie; proporcje
  obrazka zostają nienaruszone,
* **hierarchię** — tytuł, nagłówek sekcji, etykieta, tekst; puste akapity dostają
  jeden mały rozmiar, więc odstępy między blokami są równe,
* **wcięcia** — akapit wcięty „pierwszym wierszem” dostaje wcięcie całego akapitu.
  To najczęstsza usterka tych formatek: druga linijka zdania wracała na margines
  i blok rozjeżdżał się w schodki,
* **tabulatory** — ciąg tabulatorów zastępuje jeden, z jawnym przystankiem, żeby
  wartości stały w jednej kolumnie niezależnie od długości etykiety,
* **łamańce** — zdanie rozbite na kilka akapitów wraca do jednego akapitu
  (patrz `_scal_ciagi`).

Role akapitów rozpoznaje po tym, co w dokumencie już jest, więc reguły zadziałają
też na formatkach dołożonych później.

    python narzedzia/ujednolic_wyglad.py                     # wszystkie wzory
    python narzedzia/ujednolic_wyglad.py szablony/inny.docx
"""
import argparse
import sys
from pathlib import Path

import docx
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Emu, Mm, Pt

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.config import SZABLONY  # noqa: E402

KROJ = "Bahnschrift SemiBold"

TYTUL = Pt(14)
NAGLOWEK = Pt(11)
TRESC = Pt(10)
PUSTY = Pt(6)              # wysokość pustego akapitu = odstęp między blokami

# Rozstrzelenie tytułu w dwudziestych częściach punktu. Drobiazg, ale to on sprawia,
# że wersaliki wyglądają na złożone, a nie na przypadkiem powiększone.
TYTUL_ROZSTRZELENIE = 12
ODSTEP_NAD_TYTULEM = Pt(8)      # oddziela tytuł od logo, gdy stoi zaraz pod nim
ODSTEP_POD_TYTULEM = Pt(14)

# Logo: szerokość i miejsce takie samo w każdym dokumencie (od marginesu, nie od
# krawędzi kartki — inaczej rozjechałoby się przy innych marginesach).
LOGO_SZEROKOSC = Mm(50)
LOGO_OD_LEWEJ = Mm(5.8)
LOGO_OD_GORY = Mm(4)

TABULATOR_WARTOSCI = Mm(50)     # kolumna wartości w blokach „Etykieta:  wartość”

PODPIS = "Stania"

ZAMYKA_ZDANIE = (".", ":", ";", "!", "?")
DLUGOSC_PELNEGO_WIERSZA = 60    # patrz `_scal_ciagi`


def _znacznik(tekst: str) -> bool:
    return "{{" in tekst or "{%" in tekst


def _czerwony(bieg) -> bool:
    return (bieg.font.color is not None and bieg.font.color.type is not None
            and str(bieg.font.color.rgb) == "FF0000")


def _rozmiar(akapit) -> float:
    return max((b.font.size.pt for b in akapit.runs if b.font.size), default=0)


# --- struktura -------------------------------------------------------------------

def _scal_ciagi(dokument) -> int:
    """Skleja zdanie rozbite na osobne akapity.

    W formatkach pisanych „na oko” dłuższy opis bywa wprowadzony Enterem zamiast
    zawinięciem wiersza. Word traktuje każdy kawałek jak osobny akapit, więc tekst
    czyta się jak kolumna urwanych linijek, a przy innej czcionce łamie się w losowych
    miejscach.

    Sklejamy tylko wtedy, gdy poprzedni akapit **wygląda na urwany w połowie zdania**:
    jest wyrównany do lewej, ma długość pełnego wiersza i nie kończy się kropką ani
    dwukropkiem. Dzięki temu krótkie, wyśrodkowane wpisy (adres firmy, NIP) zostają
    osobno — a to one ucierpiałyby najbardziej na błędnym sklejeniu.
    """
    scalone = 0
    poprzedni = None
    for akapit in list(dokument.paragraphs):
        tekst = akapit.text.strip()
        do_lewej = akapit.alignment in (None, WD_ALIGN_PARAGRAPH.LEFT,
                                        WD_ALIGN_PARAGRAPH.JUSTIFY)

        moze = (poprzedni is not None and tekst and do_lewej
                and not _znacznik(tekst) and not _znacznik(poprzedni.text)
                and len(poprzedni.text.strip()) >= DLUGOSC_PELNEGO_WIERSZA
                and not poprzedni.text.strip().endswith(ZAMYKA_ZDANIE))
        if moze:
            ostatni = poprzedni.runs[-1]
            if not ostatni.text.endswith(" "):
                ostatni.text += " "
            for bieg in akapit.runs:                       # przenosimy gotowe biegi,
                poprzedni._p.append(bieg._element)         # więc formaty zostają
            akapit._element.getparent().remove(akapit._element)
            scalone += 1
            continue

        if tekst:
            poprzedni = akapit
    return scalone


# --- wcięcia i tabulatory --------------------------------------------------------

def _popraw_wciecie(akapit) -> bool:
    """Wcięcie „pierwszego wiersza” zamienia na wcięcie całego akapitu.

    Zwisu (wartość ujemna, użytego w numerowanym spisie) nie rusza.
    """
    ustawienia = akapit.paragraph_format
    pierwszy = ustawienia.first_line_indent
    if pierwszy is None or pierwszy <= 0:
        return False
    ustawienia.left_indent = (ustawienia.left_indent or 0) + pierwszy
    ustawienia.first_line_indent = None
    return True


def _popraw_tabulatory(akapit) -> bool:
    """Ciąg tabulatorów → jeden tabulator z jawnym przystankiem.

    Przy domyślnych przystankach co 12,7 mm wartość ląduje w innym miejscu zależnie
    od tego, czy etykieta to „Działka:” czy „Obręb ewid.:”. Stąd schodki.
    """
    if "\t\t" not in akapit.text:
        return False

    # Word trzyma każdy tabulator w osobnym biegu, więc `\t\t` nie występuje wewnątrz
    # żadnego z nich — nadmiarowe tabulatory trzeba usuwać, idąc przez cały akapit.
    po_tabulatorze = False
    for bieg in akapit.runs:
        zostawione = []
        for znak in bieg.text:
            if znak == "\t" and po_tabulatorze:
                continue
            po_tabulatorze = znak == "\t"
            zostawione.append(znak)
        bieg.text = "".join(zostawione)

    ustawienia = akapit.paragraph_format
    przystanek = Emu(int(TABULATOR_WARTOSCI) + int(ustawienia.left_indent or 0))
    if all(t.position != przystanek for t in ustawienia.tab_stops):
        ustawienia.tab_stops.add_tab_stop(przystanek)
    return True


# --- typografia ------------------------------------------------------------------

def _rozstrzel(bieg, wartosc: int) -> None:
    rPr = bieg._element.get_or_add_rPr()
    for stary in rPr.findall(qn("w:spacing")):
        rPr.remove(stary)
    if wartosc:
        element = OxmlElement("w:spacing")
        element.set(qn("w:val"), str(wartosc))
        rPr.append(element)


def _ustaw(akapit, rozmiar, pogrubienie, *, rozstrzelenie=0) -> None:
    for bieg in akapit.runs:
        bieg.font.name = KROJ
        bieg.font.size = rozmiar
        # czerwień to numer roboty — zostaje czerwona i zawsze pogrubiona, bo to
        # jedyna rzecz w dokumencie, której szuka się wzrokiem
        bieg.bold = True if _czerwony(bieg) else pogrubienie
        bieg.underline = False
        _rozstrzel(bieg, rozstrzelenie)


# --- logo ------------------------------------------------------------------------

def _wlasny_akapit(dokument, akapit):
    """Przenosi logo do własnego, pustego akapitu tuż przed bieżącym.

    Kotwica wrzucona w akapit z tekstem (tak było w sprawozdaniu — logo siedziało
    w akapicie tytułu) potrafi wypchnąć ten tekst *nad* obrazek. Logo ma stać
    najwyżej, więc dostaje własny akapit.
    """
    if not akapit.text.strip():
        return akapit
    nowy = akapit.insert_paragraph_before()
    for bieg in akapit.runs:
        if bieg._element.findall(".//{*}anchor"):
            nowy._p.append(bieg._element)
    return nowy


def _oblewanie(dokument, akapit_logo) -> str:
    """„Z boku” tylko wtedy, gdy obok logo ma naprawdę coś stanąć.

    Rozpoznajemy to po najbliższym niepustym akapicie: wyrównany do prawej to blok
    firmówki (data, numery) — ten ma stać obok logo. Cokolwiek innego, na przykład
    wyśrodkowany tytuł, ma iść pod spodem, więc obrazek zajmuje własny pas.
    """
    # porównujemy po elemencie XML: `dokument.paragraphs` przy każdym wywołaniu
    # tworzy nowe obiekty opakowujące, więc porównanie po tożsamości nie zadziała
    akapity = [p._p for p in dokument.paragraphs]
    for dalszy in dokument.paragraphs[akapity.index(akapit_logo._p) + 1:]:
        if dalszy.text.strip():
            return ("wrapSquare" if dalszy.alignment == WD_ALIGN_PARAGRAPH.RIGHT
                    else "wrapTopAndBottom")
    return "wrapTopAndBottom"


def _ustaw_logo(dokument) -> int:
    """Ta sama szerokość i to samo miejsce w każdym dokumencie.

    Wysokość liczymy z proporcji obrazka, żeby logo się nie rozjechało.
    """
    zmienione = 0
    for akapit in list(dokument.paragraphs):
        if not akapit._p.findall(".//{*}anchor"):
            continue
        akapit = _wlasny_akapit(dokument, akapit)
        for kotwica in akapit._p.findall(".//{*}anchor"):
            rozmiar = kotwica.find(qn("wp:extent"))
            szer, wys = int(rozmiar.get("cx")), int(rozmiar.get("cy"))
            nowa_szer = int(LOGO_SZEROKOSC)
            nowa_wys = int(round(wys * nowa_szer / szer))

            rozmiar.set("cx", str(nowa_szer))
            rozmiar.set("cy", str(nowa_wys))
            for ext in kotwica.findall(".//" + qn("a:ext")):     # kopia w środku rysunku
                ext.set("cx", str(nowa_szer))
                ext.set("cy", str(nowa_wys))

            for os_, wartosc in ((qn("wp:positionH"), LOGO_OD_LEWEJ),
                                 (qn("wp:positionV"), LOGO_OD_GORY)):
                polozenie = kotwica.find(os_)
                polozenie.set("relativeFrom", "margin")
                for align in polozenie.findall(qn("wp:align")):  # „przy krawędzi”
                    polozenie.remove(align)                      # zastępujemy liczbą
                przesuniecie = polozenie.find(qn("wp:posOffset"))
                if przesuniecie is None:
                    przesuniecie = OxmlElement("wp:posOffset")
                    polozenie.append(przesuniecie)
                przesuniecie.text = str(int(wartosc))

            zadany = _oblewanie(dokument, akapit)
            for stare in [e for e in kotwica if e.tag.startswith(f"{{{kotwica.nsmap['wp']}}}wrap")]:
                kotwica.remove(stare)
            kotwica.append(OxmlElement(f"wp:{zadany}"))
            zmienione += 1
    return zmienione


# --- całość ----------------------------------------------------------------------

def _ujednolic_tabele(dokument) -> int:
    """Komórki tabel: ten sam krój i rozmiar, grubość zostaje.

    Nagłówek tabeli bywa pogrubiony celowo, a treść nie — tego nie ruszamy,
    bo w tabeli grubość niesie znaczenie, a nie tylko wygląd.
    """
    komorki = 0
    for tabela in dokument.tables:
        for wiersz in tabela.rows:
            for komorka in wiersz.cells:
                for akapit in komorka.paragraphs:
                    for bieg in akapit.runs:
                        bieg.font.name = KROJ
                        bieg.font.size = TRESC
                komorki += 1
    return komorki


def ujednolic(plik: Path) -> dict[str, int]:
    dokument = docx.Document(plik)
    licznik = dict.fromkeys(
        ("tytul", "naglowek", "etykieta", "tresc", "podpis", "pusty",
         "scalone", "wciecia", "tabulatory", "logo", "komorki"), 0)

    # styl bazowy: cokolwiek dopiszesz później w Wordzie, wyjdzie w tym samym kroju
    normalny = dokument.styles["Normal"]
    normalny.font.name = KROJ
    normalny.font.size = TRESC

    licznik["scalone"] = _scal_ciagi(dokument)
    licznik["logo"] = _ustaw_logo(dokument)
    licznik["komorki"] = _ujednolic_tabele(dokument)

    akapity = dokument.paragraphs
    z_trescia = [p for p in akapity if p.text.strip()]
    najwiekszy = max((_rozmiar(p) for p in z_trescia), default=0)
    ostatni = z_trescia[-1] if z_trescia else None

    for akapit in akapity:
        tekst = akapit.text.strip()

        if not tekst:
            # Pusty akapit w ramce (`w:framePr`) to nie odstęp między blokami, tylko
            # podkładka podnosząca przypięty podpis — patrz narzedzia/popraw_szablon.py.
            # Zmiana jego rozmiaru przesunęłaby podpis, więc go nie ruszamy.
            if akapit._p.find(qn("w:pPr") + "/" + qn("w:framePr")) is None:
                for bieg in akapit.runs:
                    bieg.font.name, bieg.font.size = KROJ, PUSTY
                licznik["pusty"] += 1
            continue

        licznik["wciecia"] += _popraw_wciecie(akapit)
        licznik["tabulatory"] += _popraw_tabulatory(akapit)

        if _rozmiar(akapit) == najwiekszy and najwiekszy > TRESC.pt:
            _ustaw(akapit, TYTUL, True, rozstrzelenie=TYTUL_ROZSTRZELENIE)
            akapit.alignment = WD_ALIGN_PARAGRAPH.CENTER
            akapit.paragraph_format.space_before = ODSTEP_NAD_TYTULEM
            akapit.paragraph_format.space_after = ODSTEP_POD_TYTULEM
            licznik["tytul"] += 1
        elif _rozmiar(akapit) > TRESC.pt:
            _ustaw(akapit, NAGLOWEK, True)
            akapit.paragraph_format.keep_with_next = True
            licznik["naglowek"] += 1
        elif akapit is ostatni and PODPIS in tekst:
            _ustaw(akapit, TRESC, False)
            akapit.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            akapit.paragraph_format.left_indent = None
            akapit.paragraph_format.first_line_indent = None
            licznik["podpis"] += 1
        elif tekst.endswith(":"):
            _ustaw(akapit, TRESC, True)
            # etykieta bez swojej wartości na dole strony wygląda na urwany dokument
            akapit.paragraph_format.keep_with_next = True
            licznik["etykieta"] += 1
        else:
            _ustaw(akapit, TRESC, False)
            licznik["tresc"] += 1

    dokument.save(plik)
    return licznik


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("szablony", nargs="*", help="pliki .docx; domyślnie wszystkie wzory")
    argumenty = parser.parse_args()

    pliki = [Path(s) for s in argumenty.szablony] or sorted(SZABLONY.glob("*_wzor.docx"))
    for plik in pliki:
        if not plik.exists():
            print(f"Nie ma pliku {plik}")
            continue
        podsumowanie = ujednolic(plik)
        print(f"{plik.name}: "
              + ", ".join(f"{n}: {i}" for n, i in podsumowanie.items() if i))

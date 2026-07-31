"""Nakłada na szablon ustawienia Worda, których nie da się wyklikać raz na zawsze.

Brat przysyła co jakiś czas nową wersję formatki. Przy każdej podmianie trzeba ustawić
dwie rzeczy, bo inaczej dokument wygląda źle przy dłuższym spisie treści:

1. **Pozycja spisu treści** — tabulator zamiast spacji po numerze, wcięcie wiszące
   i odstęp po akapicie. Bez tego „1.” i „13.” mają różną szerokość, więc tekst każdej
   pozycji zaczyna się gdzie indziej, a zawinięta pozycja chowa się pod numerem.
2. **Podpis przypięty do dołu strony** — ramka akapitu (`w:framePr`) zakotwiczona
   do dołu obszaru tekstu. Dzięki temu podpis stoi w tym samym miejscu niezależnie
   od tego, czy spis ma dwie pozycje, czy trzynaście.

Uruchomienie po wgraniu nowej formatki:

    python narzedzia/popraw_szablon.py szablony/spis_tresci_wzor.docx

Skrypt jest odporny na powtórzenie — puszczenie go dwa razy niczego nie psuje.
"""
import argparse
import sys
from pathlib import Path

import docx
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

WCIECIE = Cm(0.9)        # z zapasem na numery dwucyfrowe przy czcionce formatki
ODSTEP_PO = Pt(6)        # przerwa między pozycjami spisu
PODPIS_ZAWIERA = ("Stania", "upr")     # po czym poznajemy akapit z podpisem


def popraw_pozycje_spisu(akapit) -> bool:
    """Tabulator po numerze, wcięcie wiszące, odstęp, wyrównanie do lewej."""
    for bieg in akapit.runs:
        if "}}. {{" in bieg.text:
            bieg.text = bieg.text.replace("}}. {{", "}}.\t{{")

    format_ = akapit.paragraph_format
    format_.left_indent = WCIECIE
    format_.first_line_indent = -WCIECIE
    format_.space_after = ODSTEP_PO
    if len(format_.tab_stops) == 0:                # bez tego przystanki by się dublowały
        format_.tab_stops.add_tab_stop(WCIECIE, WD_TAB_ALIGNMENT.LEFT)
    # justowanie rozciągałoby zawiniętą pozycję na całą szerokość, robiąc dziury
    akapit.alignment = WD_ALIGN_PARAGRAPH.LEFT
    return True


def przypnij_do_dolu(akapit) -> bool:
    """Ramka akapitu zakotwiczona do dołu obszaru tekstu."""
    pPr = akapit._p.get_or_add_pPr()               # noqa: SLF001
    if pPr.find(qn("w:framePr")) is not None:
        return False                               # już przypięty

    # tabulatory wypychające podpis w prawo rozpychałyby ramkę na całą szerokość
    for bieg in list(akapit.runs):
        if bieg.text.strip() == "" and "\t" in bieg.text:
            bieg._element.getparent().remove(bieg._element)     # noqa: SLF001

    ramka = OxmlElement("w:framePr")
    for atrybut, wartosc in (("w:wrap", "around"), ("w:vAnchor", "margin"),
                             ("w:hAnchor", "margin"), ("w:xAlign", "right"),
                             ("w:yAlign", "bottom")):
        ramka.set(qn(atrybut), wartosc)
    pPr.insert(0, ramka)
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("szablon", nargs="?", default="szablony/spis_tresci_wzor.docx")
    argumenty = parser.parse_args()

    plik = Path(argumenty.szablon)
    if not plik.exists():
        print(f"Nie ma pliku {plik}")
        return 1

    dokument = docx.Document(plik)
    spisy = podpisy = 0
    for akapit in dokument.paragraphs:
        if "loop.index" in akapit.text and "pozycja" in akapit.text:
            spisy += popraw_pozycje_spisu(akapit)
        elif all(fragment in akapit.text for fragment in PODPIS_ZAWIERA):
            podpisy += przypnij_do_dolu(akapit)

    dokument.save(plik)
    print(f"{plik}:")
    print(f"  pozycji spisu treści sformatowanych: {spisy}")
    print(f"  podpisów przypiętych do dołu strony: {podpisy}")
    if not spisy:
        print("  UWAGA: nie znalazłem akapitu z pętlą spisu treści "
              "({%p for pozycja in spis_tresci %}) — sprawdź szablon.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

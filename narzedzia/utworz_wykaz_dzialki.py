"""Formatka wykazu zmian danych działki — zbudowana z formatki **wykazu budynku**.

Oba wykazy mają wyglądać jak jeden komplet: pionowa kartka, ta sama tabela („L.p. |
Oznaczenie atrybutu | STAN DOTYCHCZASOWY | STAN NOWY"), ten sam nagłówek, ta sama stopka
i **osobna strona na każdą pozycję** — jedna działka to jedna strona, dokładnie tak jak
jeden budynek. Dlatego nie budujemy tego dokumentu od zera: bierzemy formatkę budynku,
podmieniamy tytuł, dokładamy wiersz nagłówka z numerem działki i przebudowujemy wiersze
tabeli na atrybuty działki. Gdy brat kiedyś zmieni wygląd wykazu budynku, ten skrypt
odtworzy działkę w tym samym stylu.

    python narzedzia/utworz_wykaz_dzialki.py --wyjscie szablony/wykaz_zmian_dzialki_wzor.docx

Po zbudowaniu puść `ujednolic_wyglad.py` — przeliczy przystanki tabulatorów w nagłówku
i w podpisie, bo doszedł tam dłuższy wiersz.

Numer działki jest **podpolem każdego wykazu** (`dzialka.dzialka`), a nie jednym polem
na cały dokument: skoro każda działka ma własną stronę, to i własny numer w nagłówku.
Identyfikatorem jest dopiero całość — obręb, kropka i ten numer — i tak stoi w nagłówku.
"""
from __future__ import annotations

import argparse
import copy
import re
import sys
from pathlib import Path

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

KORZEN = Path(__file__).resolve().parent.parent
ZRODLO = KORZEN / "szablony" / "wykaz_zmian_budynku_wzor.docx"

TYTUL = ("WYKAZ ZMIAN DANYCH EWIDENCYJNYCH ", "DOTYCZĄCYCH DZIAŁKI EWIDENCYJNEJ")

# Wiersz nagłówka dokumentu z identyfikatorem działki. Numer bierze się z pętli, bo każda
# działka ma własną stronę; obręb jest wspólny dla całego operatu.
WIERSZ_IDENTYFIKATORA = ("Identyfikator działki ewidencyjnej:",
                         "[{{ polozenie_obreb_teryt }}.{{ dzialka.dzialka }}]")

# Atrybuty działki: (nazwa, klucz) albo (nazwa, [(podwiersz, klucz), …]) dla atrybutu
# rozpisanego na kilka linijek — jak „Liczba kondygnacji” w wykazie budynku.
ATRYBUTY: list[tuple[str, object]] = [
    ("Numer działki", "numer"),
    ("Pole powierzchni ewidencyjnej działki [ha]", "pow_ewidencyjna"),
    ("Użytki gruntowe i klasy bonitacyjne w działce",
     [("OFU", "ofu"), ("OZU", "ozu"), ("OZK", "ozk")]),
    ("Pole powierzchni użytków gruntowych i klas bonitacyjnych w obszarze działki [ha]",
     "pow_uzytkow"),
]


def _tekst_komorki(tc, tekst: str) -> None:
    """Zostawia w komórce jeden akapit z jednym biegiem o podanej treści.

    Formatowanie bierze się z komórki wzorcowej — dlatego klonujemy prawdziwe komórki
    formatki budynku, zamiast składać tabelę od zera.
    """
    akapity = tc.findall(qn("w:p"))
    for zbedny in akapity[1:]:
        tc.remove(zbedny)
    akapit = akapity[0]
    biegi = akapit.findall(qn("w:r"))
    for zbedny in biegi[1:]:
        akapit.remove(zbedny)
    if not tekst:
        for bieg in biegi:
            akapit.remove(bieg)
        return
    if not biegi:
        bieg = OxmlElement("w:r")
        akapit.append(bieg)
    else:
        bieg = biegi[0]
    for stary in bieg.findall(qn("w:t")):
        bieg.remove(stary)
    for stary in bieg.findall(qn("w:br")):
        bieg.remove(stary)
    w_t = OxmlElement("w:t")
    w_t.set(qn("xml:space"), "preserve")
    w_t.text = tekst
    bieg.append(w_t)


def _komorka(wzorzec, tekst: str):
    tc = copy.deepcopy(wzorzec)
    _tekst_komorki(tc, tekst)
    return tc


def _wiersz(wzorzec_tr, komorki):
    tr = copy.deepcopy(wzorzec_tr)
    for stara in tr.findall(qn("w:tc")):
        tr.remove(stara)
    for tc in komorki:
        tr.append(tc)
    return tr


def _zamien_w_akapicie(akapit, co: str, na: str) -> bool:
    """Podmiana tekstu w akapicie, którego Word potrafi trzymać w kilku biegach."""
    biegi = akapit.findall(qn("w:r"))
    tekst = "".join(t.text or "" for b in biegi for t in b.iter(qn("w:t")))
    if not biegi or co not in tekst:
        return False
    # zostawiamy pierwszy bieg (z jego krojem i kolorem), reszta idzie precz — Word tnie
    # tekst na biegi w przypadkowych miejscach, więc podmiana „w miejscu” bywa krucha
    for zbedny in biegi[1:]:
        akapit.remove(zbedny)
    bieg = biegi[0]
    for stary in bieg.findall(qn("w:t")):
        bieg.remove(stary)
    w_t = OxmlElement("w:t")
    w_t.set(qn("xml:space"), "preserve")
    w_t.text = tekst.replace(co, na)
    bieg.append(w_t)
    return True


def zbuduj(zrodlo: Path, wyjscie: Path) -> Path:
    dokument = Document(str(zrodlo))
    body = dokument.element.body

    # --- pętla i tytuł --------------------------------------------------------
    for akapit in body.iter(qn("w:p")):
        _zamien_w_akapicie(akapit, "{%p for wykaz in wykazy_budynkow %}",
                           "{%p for dzialka in wykazy_dzialek %}")
        _zamien_w_akapicie(akapit, "WYKAZ ZMIAN DANYCH EWIDENCYJNYCH ", TYTUL[0])
        _zamien_w_akapicie(akapit, "DOTYCZĄCYCH BUDYNKU", TYTUL[1])

    # --- wiersz nagłówka z numerem działki -------------------------------------
    wzorzec_naglowka = next(
        p for p in body.iter(qn("w:p"))
        if "Obręb ewidencyjny" in "".join(t.text or "" for t in p.iter(qn("w:t"))))
    nowy = copy.deepcopy(wzorzec_naglowka)
    _zamien_w_akapicie(
        nowy,
        "".join(t.text or "" for t in nowy.iter(qn("w:t"))),
        f"{WIERSZ_IDENTYFIKATORA[0]}\t{WIERSZ_IDENTYFIKATORA[1]}")
    wzorzec_naglowka.addnext(nowy)

    # --- tabela ---------------------------------------------------------------
    tabela = dokument.tables[0]._tbl
    wiersze = tabela.findall(qn("w:tr"))
    naglowek_wz, prosty_wz = wiersze[0], wiersze[1]
    z_podwierszami_wz, kontynuacja_wz = wiersze[6], wiersze[7]

    komorki_naglowka = naglowek_wz.findall(qn("w:tc"))
    komorki_proste = prosty_wz.findall(qn("w:tc"))
    komorki_pod = z_podwierszami_wz.findall(qn("w:tc"))
    komorki_kont = kontynuacja_wz.findall(qn("w:tc"))

    nowe = [_wiersz(naglowek_wz, [
        _komorka(komorki_naglowka[0], "L.p."),
        _komorka(komorki_naglowka[1], "Oznaczenie atrybutu działki"),
        _komorka(komorki_naglowka[2], "STAN DOTYCHCZASOWY"),
        _komorka(komorki_naglowka[3], "STAN NOWY"),
    ])]

    for numer, (nazwa, tresc) in enumerate(ATRYBUTY, start=1):
        if isinstance(tresc, str):
            nowe.append(_wiersz(prosty_wz, [
                _komorka(komorki_proste[0], f"{numer}."),
                _komorka(komorki_proste[1], nazwa),
                _komorka(komorki_proste[2], "{{ dzialka.%s_dotychczas }}" % tresc),
                _komorka(komorki_proste[3], "{{r dzialka.%s_nowy }}" % tresc),
            ]))
            continue
        for kolejny, (podwiersz, klucz) in enumerate(tresc):
            wzorzec = z_podwierszami_wz if kolejny == 0 else kontynuacja_wz
            komorki = komorki_pod if kolejny == 0 else komorki_kont
            nowe.append(_wiersz(wzorzec, [
                _komorka(komorki[0], f"{numer}." if kolejny == 0 else ""),
                _komorka(komorki[1], nazwa if kolejny == 0 else ""),
                _komorka(komorki[2], podwiersz),
                _komorka(komorki[3], "{{ dzialka.%s_dotychczas }}" % klucz),
                _komorka(komorki[4], "{{r dzialka.%s_nowy }}" % klucz),
            ]))

    for wiersz in wiersze:
        tabela.remove(wiersz)
    for wiersz in nowe:
        tabela.append(wiersz)

    wyjscie.parent.mkdir(parents=True, exist_ok=True)
    dokument.save(str(wyjscie))
    return wyjscie


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--wyjscie", required=True, type=Path)
    parser.add_argument("--zrodlo", type=Path, default=ZRODLO)
    argumenty = parser.parse_args()

    dokument = Document(str(argumenty.zrodlo))
    if "wykazy_budynkow" not in dokument.element.body.xml:
        print(f"{argumenty.zrodlo} to nie jest formatka wykazu budynku — "
              "z niej bierze się układ tabeli i indeksy wierszy wzorcowych.",
              file=sys.stderr)
        return 1

    plik = zbuduj(argumenty.zrodlo, argumenty.wyjscie)
    print(f"{plik}: {len(Document(str(plik)).tables[0].rows)} wierszy tabeli, "
          "jedna działka na stronę")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

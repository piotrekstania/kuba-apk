"""Liczniki pracy programu.

Najważniejsze, czego pilnują: liczby **nie mogą znikać**, gdy brat przeniesie gotowe
operaty na dysk archiwalny, i **nie mogą rosnąć** od plików, które sam dołożył do katalogu.
Pierwsza wersja liczyła pliki na dysku i myliła się w obie strony.
"""
from __future__ import annotations

import shutil

from app import operaty, statystyki

from test_trasy import FORMULARZ, OPIS_OPERATU   # tests/ nie jest pakietem


def _dodaj_szablon(srodowisko):
    srodowisko.dodaj_szablon(
        "spis_tresci_wzor",
        ["Robota: {{ nr_roboty }}", "Operat: {{ nr_operatu }}", "Data: {{ data_zakonczenia }}"],
        opis=OPIS_OPERATU, tabela=True)


# --- samo zliczanie ----------------------------------------------------------

def test_zliczanie_sumuje_sie(srodowisko):
    statystyki.zlicz(statystyki.OPERAT)
    statystyki.zlicz(statystyki.OPERAT)
    statystyki.zlicz(statystyki.DOKUMENT, 3)

    assert statystyki.podsumowanie() == {
        statystyki.OPERAT: 2, statystyki.DOKUMENT: 3, statystyki.PDF: 0}


def test_pusta_baza_daje_zera_a_nie_wyjatek(srodowisko):
    assert statystyki.podsumowanie() == {
        statystyki.OPERAT: 0, statystyki.DOKUMENT: 0, statystyki.PDF: 0}


# --- to, co obalilo liczenie z dysku ----------------------------------------

def test_archiwizacja_operatu_nie_cofa_licznika(klient):
    """Brat przenosi gotowe operaty na dysk archiwalny — licznik ma to przeżyć.

    To jest powód, dla którego liczymy zdarzenia, a nie pliki: wcześniejsza wersja
    po przeniesieniu katalogów pokazywałaby zero mimo setki zrobionych robót.
    """
    _dodaj_szablon(klient.srodowisko)
    klient.post("/generuj/spis_tresci_wzor", data=FORMULARZ, follow_redirects=False)
    przed = statystyki.podsumowanie()
    assert przed[statystyki.OPERAT] == 1

    for katalog in klient.srodowisko.wyniki.iterdir():      # „przeniósł do archiwum”
        if katalog.is_dir():
            shutil.rmtree(katalog)
    assert not any(klient.srodowisko.wyniki.iterdir())

    assert statystyki.podsumowanie() == przed


def test_wlasne_pliki_brata_nie_wpadaja_do_licznika(klient):
    """Mapy, skany i dokumenty od zamawiającego nie są „wygenerowane przez program”."""
    _dodaj_szablon(klient.srodowisko)
    klient.post("/generuj/spis_tresci_wzor", data=FORMULARZ, follow_redirects=False)
    przed = statystyki.podsumowanie()

    katalog = next(k for k in klient.srodowisko.wyniki.iterdir() if k.is_dir())
    for nazwa in ("mapa_zasadnicza.pdf", "wypis_z_rejestru.docx", "szkic_polowy.docx"):
        (katalog / nazwa).write_bytes(b"plik brata")

    assert statystyki.podsumowanie() == przed


# --- co dokładnie się liczy --------------------------------------------------

def test_poprawianie_operatu_nie_dokłada_operatu(klient):
    """Tak samo jak nie zużywa numeru — poprawka to ten sam operat."""
    _dodaj_szablon(klient.srodowisko)
    klient.post("/generuj/spis_tresci_wzor", data=FORMULARZ, follow_redirects=False)

    klient.post("/generuj/spis_tresci_wzor?edytuj=1",
                data=dict(FORMULARZ, pole__uwagi="poprawione"), follow_redirects=False)

    podsumowanie = statystyki.podsumowanie()
    assert podsumowanie[statystyki.OPERAT] == 1        # nadal jeden operat
    assert podsumowanie[statystyki.DOKUMENT] == 2      # ale dokument wypełniony dwa razy


def test_zlozenie_pdf_liczy_sie_dopiero_po_udanym_sklejeniu(klient):
    _dodaj_szablon(klient.srodowisko)
    klient.post("/generuj/spis_tresci_wzor", data=FORMULARZ, follow_redirects=False)
    assert statystyki.podsumowanie()[statystyki.PDF] == 0

    katalog = next(k for k in klient.srodowisko.wyniki.iterdir() if k.is_dir())
    klient.post(f"/scal/{katalog.name}", data={"plik": "spis_tresci.docx"},
                follow_redirects=False)

    assert statystyki.podsumowanie()[statystyki.PDF] == 1


def test_nieudane_sklejenie_nie_zwieksza_licznika(klient):
    """Nie wybrano plików → nie ma PDF-a, więc licznik stoi."""
    _dodaj_szablon(klient.srodowisko)
    klient.post("/generuj/spis_tresci_wzor", data=FORMULARZ, follow_redirects=False)
    katalog = next(k for k in klient.srodowisko.wyniki.iterdir() if k.is_dir())

    klient.post(f"/scal/{katalog.name}", data={}, follow_redirects=False)

    assert statystyki.podsumowanie()[statystyki.PDF] == 0


# --- odtworzenie historii przy pierwszym uruchomieniu nowej wersji -----------

def test_zasiew_odtwarza_operaty_z_bazy_i_dokumenty_z_dysku(srodowisko):
    """Po aktualizacji licznik ma pokazać dorobek brata, a nie zero."""
    from app import db

    _dodaj_szablon(srodowisko)
    katalog, _ = operaty.zaloz("001/2026", "GK.1.2026", "spis_tresci_wzor", {})
    (katalog / "spis_tresci.docx").write_bytes(b"x")          # plik programu
    (katalog / "wypis.docx").write_bytes(b"x")                # plik brata — nie liczymy
    (katalog / operaty.nazwa_wyniku(katalog)).write_bytes(b"%PDF-1.4\n")
    db.zapisz_dokument("spis_tresci_wzor", "GK.1.2026", "001.2026/spis_tresci.docx", {},
                       katalog.name, "001/2026")
    # operat już zarchiwizowany: wpis w bazie jest, katalogu nie ma
    db.zapisz_dokument("spis_tresci_wzor", "GK.9.2025", "009.2025/spis_tresci.docx", {},
                       "009.2025", "009/2025")

    assert statystyki.zasiej_z_historii() is True

    podsumowanie = statystyki.podsumowanie()
    assert podsumowanie[statystyki.OPERAT] == 2      # także ten z archiwum
    assert podsumowanie[statystyki.DOKUMENT] == 1    # tylko plik o nazwie nadanej programem
    assert podsumowanie[statystyki.PDF] == 1


def test_zasiew_robi_sie_tylko_raz(srodowisko):
    """Drugie uruchomienie nie może podwoić dorobku."""
    from app import db

    db.zapisz_dokument("spis_tresci_wzor", "GK.1.2026", "001.2026/spis_tresci.docx", {},
                       "001.2026", "001/2026")

    assert statystyki.zasiej_z_historii() is True
    pierwsze = statystyki.podsumowanie()

    assert statystyki.zasiej_z_historii() is False
    assert statystyki.podsumowanie() == pierwsze


def test_stopka_bez_numeru_wersji(klient):
    """Numer wersji i zdanie o aktualizacjach zniknęły ze stopki (decyzja brata).

    Mówiły to samo przy każdym wejściu na każdą stronę, i to o rzeczy, która dzieje się
    sama. Wersja zostaje tam, gdzie się jej szuka — w Pomocy, na liście zmian.

    Przy okazji pilnujemy znacznika, po którym `uruchom.py` poznaje, że **nasz** serwer
    wstał: sprząta się w stopce, a wywala się start programu (patrz pułapka 21).
    """
    import uruchom
    from app import aktualizacja

    numer = aktualizacja.wersja_lokalna()[0]
    tresc = klient.get("/").text

    assert "Nowe wersje program pobiera sam" not in tresc
    assert f"wersja {numer}" not in tresc
    assert uruchom.ZNACZNIK in tresc[:4096], \
        "zniknął znacznik z nagłówka — program po starcie uzna, że serwer nie wstał"
    assert numer in klient.get("/pomoc/historia").text, \
        "wersji nie ma już nigdzie — brat nie dopasuje zgłoszenia do wydania"


def test_numer_wersji_stoi_w_naglowku(klient):
    """Wersja przeniosła się ze stopki pod nazwę programu (decyzja brata).

    W stopce ginęła pod treścią i mówiła to samo przy każdym wejściu; w nagłówku stoi
    tam, gdzie i tak pada wzrok przy pytaniu „co to za program i który”.
    """
    from app import aktualizacja

    numer = aktualizacja.wersja_lokalna()[0]
    naglowek = klient.get("/").text.split("</header>")[0]

    assert numer in naglowek, "numer wersji zniknął z nagłówka"
    assert "logo-wersja" in naglowek


def test_kreska_stopki_ma_szerokosc_tresci():
    """Kreska nad licznikami kończy się tam, gdzie tabela nad nią.

    Postawiona na `footer` obejmowała też jego marginesy i wystawała wąsami po 28 px
    z każdej strony. Musi siedzieć na akapicie z licznikami — ten ma szerokość treści.
    """
    from app.config import WEB

    style = (WEB / "static" / "style.css").read_text(encoding="utf-8")

    stopka = style.split("footer {")[1].split("}")[0]
    assert "border-top" not in stopka, "kreska wróciła na ramkę stopki — będzie szersza"
    assert "border-top" in style.split("footer .stopka-tresc {")[1].split("}")[0]


def test_stopka_ma_stopke_firmy_z_biezacym_rokiem(klient):
    """Po lewej stronie stopki stoi firma — inaczej cała jej treść wisiała przy prawej
    krawędzi. Rok liczy się przy renderze, więc 1 stycznia zmienia się sam."""
    from datetime import date

    tresc = klient.get("/").text

    stopka = tresc.split("<footer>")[1]
    assert f"© {date.today().year}" in stopka
    assert 'href="https://www.procadgeodezja.pl"' in stopka, "firma bez linku do strony"
    assert 'target="_blank"' in stopka, "link zabrałby brata z programu"


def test_stopka_pokazuje_liczniki(klient):
    """Brat widzi te liczby na każdej stronie — muszą trafić do HTML-a."""
    _dodaj_szablon(klient.srodowisko)
    klient.post("/generuj/spis_tresci_wzor", data=FORMULARZ, follow_redirects=False)

    tresc = klient.get("/").text
    assert "<strong>1</strong> operatów" in tresc
    assert "<strong>1</strong> dokumentów Worda" in tresc
    assert "<strong>0</strong> złożonych PDF-ów" in tresc

"""Układ strony w prawdziwej przeglądarce — to, czego nie widać w samym HTML-u.

Testy tras sprawdzają, co serwer wysyła, ale nie to, jak przeglądarka to rozłoży.
Tu stronę z serwera testowego zapisujemy do pliku razem z prawdziwym arkuszem stylów
i mierzymy w Chrome (albo Chromium/Edge) bez okna: skrypt na stronie zapisuje wymiary
w atrybucie, a `--dump-dom` oddaje nam gotowe drzewo. Bez przeglądarki test się
pomija — na runnerze CI Chrome jest, więc tam zawsze pilnuje.
"""
from __future__ import annotations

import html
import json
import os
import re
import shutil
import subprocess

import pytest

from app import db
from app.config import WEB
from test_trasy import FORMULARZ, _dodaj_operat, _prawdziwy_pdf   # tests/ nie jest pakietem

KANDYDACI = ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser",
             "microsoft-edge", "msedge", "chrome")


def _przegladarka() -> str | None:
    for nazwa in KANDYDACI:
        sciezka = shutil.which(nazwa)
        # Chromium ze Snapa ma własny, odizolowany /tmp (jak LibreOffice — pułapka 3):
        # strony zapisanej w `tmp_path` w ogóle nie widzi i test padałby na „nic nie
        # zmierzyła”, zamiast się pominąć
        if sciezka and "/snap/" not in sciezka and not os.path.realpath(sciezka).endswith("/snap"):
            return sciezka
    return None


pytestmark = [pytest.mark.przegladarka,
              pytest.mark.skipif(_przegladarka() is None, reason="brak Chrome/Chromium")]

POMIAR = """<script>
window.addEventListener('load', () => {
  const wynik = (() => { %s })();
  document.documentElement.setAttribute('data-pomiar', JSON.stringify(wynik));
});
</script>"""


def _zmierz(tmp_path, strona: str, skrypt: str, szerokosc: int = 1280):
    """Rozkłada stronę w przeglądarce i oddaje to, co zwrócił `skrypt` (ciało funkcji JS)."""
    statyczne = (WEB / "static").as_uri()
    # /static/... na pliki z dysku; miniatury wyłączone — podgląd ma stałą wysokość,
    # więc brak obrazka niczego w pomiarze nie zmienia
    strona = re.sub(r'(href|src)="/static/([^"?]*)(\?[^"]*)?"',
                    lambda m: f'{m.group(1)}="{statyczne}/{m.group(2)}"', strona)
    strona = re.sub(r'src="/miniatura/[^"]*"', 'src=""', strona)
    plik = tmp_path / f"strona-{szerokosc}.html"
    plik.write_text(strona.replace("</body>", POMIAR % skrypt + "</body>"), encoding="utf-8")
    wynik = subprocess.run(
        [_przegladarka(), "--headless=new", "--disable-gpu", "--no-sandbox", "--no-first-run",
         f"--user-data-dir={tmp_path / 'profil'}", "--allow-file-access-from-files",
         "--hide-scrollbars", f"--window-size={szerokosc},1600", "--virtual-time-budget=5000",
         "--dump-dom", plik.as_uri()],
        capture_output=True, text=True, timeout=120)
    znalezione = re.search(r'data-pomiar="([^"]*)"', wynik.stdout)
    assert znalezione, f"przeglądarka nic nie zmierzyła: {wynik.stderr[-800:]}"
    return json.loads(html.unescape(znalezione.group(1)))


KAFELKI = """
  return [...document.querySelectorAll('.kafelek')].map(el => {
    const r = el.getBoundingClientRect();
    const nazwa = el.querySelector('.kafelek-nazwa');
    return {nazwa: el.dataset.nazwa, gora: Math.round(r.top), wysokosc: Math.round(r.height),
            przyciski: Math.round(el.querySelector('.kafelek-akcje').getBoundingClientRect().top - r.top),
            napis: Math.round(nazwa.getBoundingClientRect().height),
            linijka: parseFloat(getComputedStyle(nazwa).lineHeight),
            przyciety: nazwa.scrollHeight > nazwa.clientHeight + 1};
  });
"""


@pytest.mark.parametrize("szerokosc", [1280, 760])
def test_kafelki_maja_rowna_wysokosc_niezaleznie_od_dlugosci_nazwy(klient, tmp_path, szerokosc):
    """Kafelek z długą nazwą pliku był wyższy od sąsiadów, a przyciski obrotu skakały
    z kafelka na kafelek — brat zgłosił to przy składaniu operatu. Nazwa zajmuje teraz
    zawsze dwie linijki (dłuższa kończy się wielokropkiem, pełna jest w dymku), więc
    wszystkie kafelki mają tę samą wysokość, a przyciski stoją w jednej linii.

    Kafelków jest tyle, żeby wyszły co najmniej dwa rzędy: w jednym rzędzie siatka
    i tak wyrównuje wysokości, więc test nie odróżniłby przyciętej nazwy od nieprzyciętej
    — dlatego pytamy też wprost o wysokość samego napisu."""
    _dodaj_operat(klient)
    klient.post("/generuj/spis_tresci_wzor", data=FORMULARZ, follow_redirects=False)
    wpis = db.dokumenty()[0]
    katalog = klient.srodowisko.wyniki / wpis["katalog"]
    # pliki dokładane przez brata Eksploratorem — nazwy bywają krótkie i bardzo długie
    for nazwa in ("a.pdf", "mapa.pdf", "szkic.pdf", "zdjecia.pdf", "wypis.pdf",
                  "Mapa porownania z terenem - skan z 2026-09-01 po poprawkach w osrodku.pdf",
                  "wykaz_wspolrzednych_punktow_szczegolow_terenowych_eksport_z_C-Geo.pdf"):
        _prawdziwy_pdf(katalog / nazwa)

    kafelki = _zmierz(tmp_path, klient.get(f"/scal/{wpis['katalog']}").text, KAFELKI, szerokosc)

    assert len(kafelki) == 8, kafelki
    assert len({k["gora"] for k in kafelki}) >= 2, f"wszystkie kafelki w jednym rzędzie: {kafelki}"
    assert len({k["wysokosc"] for k in kafelki}) == 1, f"kafelki różnej wysokości: {kafelki}"
    assert len({k["przyciski"] for k in kafelki}) == 1, \
        f"przyciski obrotu nie stoją w jednej linii: {kafelki}"
    assert len({k["napis"] for k in kafelki}) == 1, f"nazwy różnej wysokości: {kafelki}"
    assert all(k["napis"] <= 2 * k["linijka"] + 1 for k in kafelki), \
        f"nazwa zajmuje więcej niż dwie linijki: {kafelki}"
    assert any(k["przyciety"] for k in kafelki), "długa nazwa miała się skończyć wielokropkiem"


LISTA = """
  const tabela = document.querySelector('table.lista.operaty').getBoundingClientRect();
  const przycisk = document.querySelector('.naglowek-listy .glowny').getBoundingClientRect();
  const strona = document.documentElement;
  const grupa = [...document.querySelectorAll('.akcje .grupa .wtorny')].map(el => {
    const styl = getComputedStyle(el);
    return {gora: Math.round(el.getBoundingClientRect().top),
            lewy: styl.borderTopLeftRadius, prawy: styl.borderTopRightRadius};
  });
  return {tabela: Math.round(tabela.right), przycisk: Math.round(przycisk.right),
          przewijanie: strona.scrollWidth - strona.clientWidth, grupa};
"""


@pytest.mark.parametrize("szerokosc, grupa_w_calosci", [(1280, True), (900, True), (700, False)])
def test_lista_operatow_nie_wystaje_poza_strone(klient, tmp_path, szerokosc, grupa_w_calosci):
    """Lista operatów kończy się tam, gdzie przycisk „Nowy operat” — to jedna prawa
    krawędź strony. Przy nowym, luźniejszym wyglądzie długi numer roboty wypychał
    tabelę za tę krawędź, a w oknie na pół ekranu cała strona główna dostawała
    poziomy pasek przewijania. Stary wygląd mieścił się w 900 px — nowy też ma,
    a w jeszcze węższym oknie przyciski schodzą niżej, zamiast przewijać stronę."""
    _dodaj_operat(klient)
    klient.post("/generuj/spis_tresci_wzor",
                data={**FORMULARZ, "pole__nr_roboty": "GK.6640.1.1234.2026"},
                follow_redirects=False)

    wymiary = _zmierz(tmp_path, klient.get("/").text, LISTA, szerokosc)

    assert wymiary["przewijanie"] == 0, f"strona przewija się w bok: {wymiary}"
    assert wymiary["tabela"] <= wymiary["przycisk"], f"lista wystaje za przycisk: {wymiary}"
    # „Otwórz katalog | Popraw | Powiel” to jeden kształt — w wąskim oknie schodzi
    # do drugiej linijki w całości, a nie rozpada się w połowie
    grupa = wymiary["grupa"]
    assert len(grupa) == 3, grupa
    assert [(g["lewy"], g["prawy"]) for g in grupa] == \
        [("999px", "6px"), ("6px", "6px"), ("6px", "999px")], grupa
    if grupa_w_calosci:
        assert len({g["gora"] for g in grupa}) == 1, f"grupa przycisków rozpadła się: {grupa}"


PROBKI = """
  return [...document.querySelectorAll('.motyw-probka')].map(el => {
    const r = el.getBoundingClientRect();
    const nazwa = el.querySelector('.motyw-nazwa');
    const srodek = [...el.querySelectorAll('*')].every(d => {
      const w = d.getBoundingClientRect();
      return w.left >= r.left - 1 && w.right <= r.right + 1;
    });
    return {klasa: el.className, gora: Math.round(r.top), miesci: srodek,
            napis: nazwa.scrollWidth <= nazwa.clientWidth + 1};
  });
"""


@pytest.mark.parametrize("szerokosc", [1280, 900, 600, 380])
def test_probki_koloru_mieszcza_sie_w_swoich_kartach(klient, tmp_path, szerokosc):
    """Sześć próbek w rzędzie ściskało w oknie na pół ekranu „Pomarańczowy” pod
    sąsiednią próbkę, a pasek próbki wystawał poza kartę. Węższe okno ma dostać
    mniej próbek w rzędzie, a każda ma się zmieścić w całości."""
    probki = _zmierz(tmp_path, klient.get("/ustawienia").text, PROBKI, szerokosc)

    assert len(probki) == 6
    assert all(p["miesci"] and p["napis"] for p in probki), f"coś wystaje z próbki: {probki}"


PODWOJNE = """
  const formularz = document.querySelector('form[action^="/generuj/"]');
  // zdarzenie z ręki uruchamia skrypty strony, ale niczego nie wysyła — i o to chodzi
  const wyslij = () => {
    const zdarzenie = new Event('submit', {cancelable: true});
    formularz.dispatchEvent(zdarzenie);
    return zdarzenie.defaultPrevented;
  };
  const pierwsze = wyslij();
  const drugie = wyslij();
  window.dispatchEvent(new PageTransitionEvent('pageshow', {persisted: true}));
  return {pierwsze, drugie, po_powrocie: wyslij()};
"""


def test_drugie_klikniecie_zapisz_nie_wysyla_formularza_drugi_raz(klient, tmp_path):
    """Podwójne kliknięcie „Zapisz” (w Chrome 120–250 ms między kliknięciami) wysyłało
    formularz dwa razy i zakładało dwa operaty z tymi samymi danymi. Drugie wysłanie
    jest odrzucane — ale po powrocie przyciskiem „wstecz” formularz znów ma działać."""
    _dodaj_operat(klient)

    wynik = _zmierz(tmp_path, klient.get("/nowy/spis_tresci_wzor").text, PODWOJNE)

    assert wynik == {"pierwsze": False, "drugie": True, "po_powrocie": False}


KSZTALTY_GRUP = """
  return [...document.querySelectorAll('.akcje .grupa')].map(grupa =>
    [...grupa.querySelectorAll('.wtorny')].map(el => {
      const styl = getComputedStyle(el);
      return [el.textContent.trim(), styl.borderTopLeftRadius, styl.borderTopRightRadius];
    }));
"""


def test_ksztalt_grupy_przyciskow_zgadza_sie_w_kazdym_wierszu(klient, tmp_path):
    """Grupa „Otwórz katalog | Popraw | Powiel” nie w każdym wierszu jest pełna: operat
    w archiwum nie ma czego otwierać, a operat spoza historii ma tylko „Otwórz katalog”.
    Zaokrąglenia liczą się po tym, co w grupie naprawdę stoi — skrajne przyciski mają
    koniec pastylki, a jedyny jest całą pastylką."""
    import shutil

    _dodaj_operat(klient)
    klient.post("/generuj/spis_tresci_wzor", data=FORMULARZ, follow_redirects=False)
    klient.post("/generuj/spis_tresci_wzor", data={**FORMULARZ, "pole__nr_roboty": "GK.2.2026"},
                follow_redirects=False)
    archiwalny = next(w for w in db.dokumenty() if w["tytul"] == "GK.2.2026")
    shutil.rmtree(klient.srodowisko.wyniki / archiwalny["katalog"])      # „do archiwum”
    spoza = klient.srodowisko.wyniki / "777.2026"
    spoza.mkdir()
    (spoza / "operat.json").write_text(
        json.dumps({"nr_operatu": "777/2026", "nr_roboty": "G.99.2026",
                    "utworzono": "2026-07-20T08:00:00", "dane": {}}), encoding="utf-8")

    grupy = _zmierz(tmp_path, klient.get("/").text, KSZTALTY_GRUP)

    pelna = [["Otwórz katalog", "999px", "6px"], ["Popraw", "6px", "6px"],
             ["Powiel", "6px", "999px"]]
    bez_katalogu = [["Popraw", "999px", "6px"], ["Powiel", "6px", "999px"]]
    sam_katalog = [["Otwórz katalog", "999px", "999px"]]
    assert sorted(grupy, key=len) == [sam_katalog, bez_katalogu, pelna], grupy

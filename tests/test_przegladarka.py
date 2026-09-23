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
from datetime import date

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
        [("18px", "6px"), ("6px", "6px"), ("6px", "18px")], grupa    # pół wysokości, nie 999 px
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

    # koniec pastylki to pół wysokości przycisku (36 px), a nie 999 px — patrz
    # `test_rogi_nie_ostrzeja_w_trakcie_zmiany_ksztaltu`
    pelna = [["Otwórz katalog", "18px", "6px"], ["Popraw", "6px", "6px"],
             ["Powiel", "6px", "18px"]]
    bez_katalogu = [["Popraw", "18px", "6px"], ["Powiel", "6px", "18px"]]
    sam_katalog = [["Otwórz katalog", "18px", "18px"]]
    assert sorted(grupy, key=len) == [sam_katalog, bez_katalogu, pelna], grupy


WYSOKI_NUMER = """
  const formularz = document.querySelector('form[action^="/generuj/"]');
  const pole = document.getElementById('p_nr_operatu');
  const pytania = [];
  window.confirm = tekst => { pytania.push(tekst); return false; };     // brat klika „Anuluj”
  const wyslij = () => {
    const zdarzenie = new Event('submit', {cancelable: true});
    formularz.dispatchEvent(zdarzenie);
    return zdarzenie.defaultPrevented;
  };
  const rok = new Date().getFullYear();
  pole.value = '0122/' + rok;                     // literówka zamiast 012
  const wysoki = wyslij();
  pole.value = '005/' + rok;                      // numer z ręki niedaleko kolejnego
  const niedaleki = wyslij();
  return {wysoki, niedaleki, pytan: pytania.length, kolejny: pole.dataset.kolejny,
          tresc: pytania[0] || ''};
"""


def test_numer_z_reki_duzo_wyzszy_od_kolejnego_wymaga_potwierdzenia(klient, tmp_path):
    """Licznik idzie od najwyższego znanego numeru, więc literówka „0122” zamiast „012”
    przesunęłaby numerację na resztę roku. Przy dużym skoku formularz pyta; odmowa nie
    wysyła formularza, ale też go nie blokuje (blokada podwójnego „Zapisz” nie może
    uznać, że poszedł), a numer niedaleko kolejnego przechodzi bez pytania."""
    _dodaj_operat(klient)

    wynik = _zmierz(tmp_path, klient.get("/nowy/spis_tresci_wzor").text, WYSOKI_NUMER)

    assert wynik["kolejny"] == f"001/{date.today().year}"
    assert wynik["wysoki"] is True and wynik["pytan"] == 1 and "0122/" in wynik["tresc"]
    assert wynik["niedaleki"] is False, "odmowa zablokowała formularz na dobre"


NIEZMIENIONY_NUMER = """
  const formularz = document.querySelector('form[action^="/generuj/"]');
  const pole = document.getElementById('p_nr_operatu');
  const pytania = [];
  window.confirm = tekst => { pytania.push(tekst); return false; };
  formularz.dispatchEvent(new Event('submit', {cancelable: true}));   // bez zmian w polu
  const bezZmian = pytania.length;
  pole.value = '0195/' + (new Date().getFullYear() - 1);                // zmieniony, zeszły rok
  formularz.dispatchEvent(new Event('submit', {cancelable: true}));
  const zeszlyRok = pytania.length;
  pole.value = '0122/' + new Date().getFullYear();
  formularz.dispatchEvent(new Event('submit', {cancelable: true}));
  return {bezZmian, zeszlyRok, poZmianie: pytania.length, wartosc: pole.defaultValue};
"""


def test_pytanie_o_wysoki_numer_nie_dotyczy_zeszlego_roku_ani_niezmienionego_pola(klient,
                                                                                 tmp_path):
    """Poprawka operatu z ręcznym numerem z zeszłego roku pytała przy każdym zapisie
    i twierdziła, że „następne operaty będą numerowane dalej od niego” — nieprawda,
    licznik liczy w bieżącym roku. Niezmienione pole nie pyta w ogóle."""
    from app import db

    _dodaj_operat(klient)
    rok = date.today().year
    klient.post("/generuj/spis_tresci_wzor", follow_redirects=False,
                data={**FORMULARZ, "pole__nr_operatu": f"090/{rok - 1}"})
    wpis = db.dokumenty()[0]

    wynik = _zmierz(tmp_path, klient.get(f"/nowy/spis_tresci_wzor?edytuj={wpis['id']}").text,
                    NIEZMIENIONY_NUMER)

    assert wynik["wartosc"] == f"090/{rok - 1}"
    assert (wynik["bezZmian"], wynik["zeszlyRok"], wynik["poZmianie"]) == (0, 0, 1)


ROGI = """
  // Promienie tak, jak rysuje je przeglądarka: gdy suma promieni na boku przekracza jego
  // długość, wszystkie cztery są skalowane w dół tym samym współczynnikiem (CSS Backgrounds,
  // „overlapping curves”). `getComputedStyle` pokazuje wartości sprzed skalowania.
  const KLUCZE = ['borderTopLeftRadius', 'borderTopRightRadius',
                  'borderBottomRightRadius', 'borderBottomLeftRadius'];
  const rysowane = el => {
    const styl = getComputedStyle(el), prostokat = el.getBoundingClientRect();
    const [lg, pg, pd, ld] = KLUCZE.map(k => parseFloat(styl[k]));
    const f = Math.min(1, prostokat.height / (lg + ld || 1), prostokat.height / (pg + pd || 1),
                       prostokat.width / (lg + pg || 1), prostokat.width / (ld + pd || 1));
    return {lg: lg * f, pg: pg * f, pd: pd * f, ld: ld * f, h: prostokat.height};
  };
  const najmniejszy = el => { const r = rysowane(el); return Math.min(r.lg, r.pg, r.pd, r.ld); };
  const nazwa = el => `${el.tagName.toLowerCase()}.${[...el.classList].join('.')} „${
    el.textContent.trim().slice(0, 20)}”`;

  // Pastylka w spoczynku: rogi co najmniej na pół wysokości (grupa — tylko rogi zewnętrzne,
  // a wewnętrzne lekko zaokrąglone, nie ostre).
  const pastylki = [];
  const pastylka = (el, rogi) => rogi.every(k => rysowane(el)[k] >= rysowane(el).h / 2 - 0.5);
  // w menu tylko pozycje główne — linki z rozwijanej „Pomocy” mają celowo 16 px
  document.querySelectorAll('.konwerter, nav > a, nav > .rozwijane > summary, '
                            + '.akcje .glowny, .akcje .niebezpieczny, '
                            + '.kafelki + .pasek .wtorny, .szczyt .glowny, .szczyt .wtorny, '
                            + '.pasek.do-prawej .glowny, .pasek.do-prawej .wtorny').forEach(el => {
    if (el.getClientRects().length) pastylki.push([nazwa(el), pastylka(el, ['lg', 'pg', 'pd', 'ld'])]);
  });
  document.querySelectorAll('.akcje .grupa, .kafelek-akcje').forEach(grupa => {
    const przyciski = [...grupa.querySelectorAll('.wtorny, button')];
    if (przyciski.length < 2) return;
    const [pierwszy, ostatni] = [przyciski[0], przyciski[przyciski.length - 1]];
    pastylki.push([nazwa(pierwszy), pastylka(pierwszy, ['lg', 'ld'])
                   && rysowane(pierwszy).pg >= 4 && rysowane(pierwszy).pd >= 4]);
    pastylki.push([nazwa(ostatni), pastylka(ostatni, ['pg', 'pd'])
                   && rysowane(ostatni).lg >= 4 && rysowane(ostatni).ld >= 4]);
  });

  // Zmiana kształtu pod kursorem i przy wciśnięciu (do 12 px) — przewijamy animację
  // klatka po klatce i pilnujemy najmniejszego rogu.
  const animacje = [];
  document.querySelectorAll('button, .glowny, .wtorny, nav a, .konwerter').forEach(el => {
    if (!el.getClientRects().length) return;
    if (!getComputedStyle(el).transitionProperty.includes('border-radius')) return;
    const naStart = najmniejszy(el);
    el.style.borderRadius = '12px';
    const przejscia = el.getAnimations();
    przejscia.forEach(a => a.pause());
    const koniec = Math.max(0, ...przejscia.map(a => a.effect.getComputedTiming().endTime));
    let wTrakcie = naStart;
    for (let t = 0; t <= koniec; t += 5) {
      przejscia.forEach(a => { a.currentTime = t; });
      wTrakcie = Math.min(wTrakcie, najmniejszy(el));
    }
    przejscia.forEach(a => a.cancel());
    el.style.borderRadius = '';
    animacje.push([nazwa(el), Math.round(naStart * 10) / 10, Math.round(wTrakcie * 10) / 10,
                   przejscia.length]);
  });
  return {pastylki, animacje};
"""


def test_rogi_nie_ostrzeja_w_trakcie_zmiany_ksztaltu(klient, tmp_path):
    """Pastylka przechodzi pod kursorem (albo przy wciśnięciu) w zaokrąglony prostokąt
    ze sprężystym „przestrzeleniem”. Z promienia 999 px nawet kilka procent przestrzelenia
    to wartość ujemna, którą przeglądarka przycina do zera — rogi robiły się na chwilę
    ostre, zanim się zaokrągliły (brat zauważył to na zielonej plakietce „PDF: …”).
    Pastylka ma więc promień z własnej wysokości, a nie 999 px — w spoczynku wygląda tak
    samo, a w trakcie ruchu żaden róg nie spada poniżej połowy tego, co było i co będzie.
    Przy okazji: z 999 px przeglądarka skalowała w dół **wszystkie** rogi, więc wewnętrzne
    rogi skrajnych przycisków w grupie wychodziły ostre zamiast lekko zaokrąglonych."""
    _dodaj_operat(klient)
    klient.post("/generuj/spis_tresci_wzor", data=FORMULARZ, follow_redirects=False)
    wpis = db.dokumenty()[0]
    _prawdziwy_pdf(klient.srodowisko.wyniki / wpis["katalog"] / "mapa.pdf")

    for adres in ("/", "/nowy/spis_tresci_wzor", f"/dokument/{wpis['id']}",
                  f"/scal/{wpis['katalog']}"):
        wynik = _zmierz(tmp_path, klient.get(adres).text, ROGI)

        assert wynik["animacje"], f"{adres}: nie znaleziono niczego, co zmienia kształt"
        ostre = [a for a in wynik["animacje"] if a[2] < 0.5 * min(a[1], 12)]
        assert not ostre, f"{adres}: rogi ostrzeją w trakcie animacji: {ostre}"
        nie_pastylki = [nazwa for nazwa, jest in wynik["pastylki"] if not jest]
        assert not nie_pastylki, f"{adres}: przestały być pastylkami: {nie_pastylki}"

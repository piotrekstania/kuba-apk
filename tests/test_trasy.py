"""Strony i formularze — smoke testy przez TestClient.

Konwersja PDF jest tu podmieniona na atrapę: testy mają chodzić w sekundy, bez Worda
i bez LibreOffice'a. Sprawdzamy zachowanie aplikacji, nie jakość PDF-a.
"""
from __future__ import annotations

import json
from pathlib import Path

from app import db, operaty

OPIS_OPERATU = {
    "nazwa": "Operat", "glowny": True, "licznik": "operat",
    # opis jest po to, żeby test szczytu formularza miał co sprawdzać — bez niego
    # asercja „opis nie wrócił na szczyt” przechodziła na pusto
    "opis": "Strona tytułowa operatu",
    "wzor_nazwy": "Operat_{nr_roboty}",
    "pola": [
        {"klucz": "nr_roboty", "etykieta": "Nr roboty", "wymagane": True},
        {"klucz": "nr_operatu", "typ": "auto_numer", "domyslnie": "{numer3}/{rok}"},
        {"klucz": "data_zakonczenia", "typ": "date"},
        {"klucz": "uwagi", "typ": "textarea"},
        {"klucz": "punkty", "typ": "tabela",
         "kolumny": [{"klucz": "numer", "etykieta": "Nr"}, {"klucz": "x", "etykieta": "X"}]},
    ]}

# Przeglądarka wysyła **każde** pole, także puste — testując curl-em albo klientem
# łatwo o tym zapomnieć i sprawdzić co innego, niż robi człowiek.
FORMULARZ = {
    "pole__nr_roboty": "GK.6640.1.2026",
    "pole__nr_operatu": "",
    "pole__data_zakonczenia": "2026-07-31",
    "pole__uwagi": "",
    "tab__punkty__0__numer": "101",
    "tab__punkty__0__x": "5712345.12",
    "tab__punkty__1__numer": "",
    "tab__punkty__1__x": "",
}


def _prawdziwy_pdf(sciezka):
    """Jednostronicowy PDF, który przejdzie przez pypdf.

    Zaślepka `b"%PDF-1.4"` wygląda na PDF, ale sklejanie na niej pada — i wtedy test
    sprawdza obsługę błędu zamiast tego, o co go pytamy.
    """
    from pypdf import PdfWriter
    zapis = PdfWriter()
    zapis.add_blank_page(width=595, height=842)
    with open(sciezka, "wb") as wyjscie:
        zapis.write(wyjscie)
    return sciezka


def _dodaj_operat(klient):
    klient.srodowisko.dodaj_szablon(
        "spis_tresci_wzor",
        ["Robota: {{ nr_roboty }}", "Operat: {{ nr_operatu }}", "Data: {{ data_zakonczenia }}"],
        opis=OPIS_OPERATU, tabela=True)


# --- strony otwierają się ----------------------------------------------------

def test_strony_odpowiadaja(klient):
    _dodaj_operat(klient)
    for adres in ("/", "/nowy/spis_tresci_wzor", "/ustawienia", "/pomoc", "/pomoc/historia"):
        odpowiedz = klient.get(adres)
        assert odpowiedz.status_code == 200, f"{adres} -> {odpowiedz.status_code}"


def test_strona_glowna_pokazuje_tylko_szablony_glowne(klient):
    """Sprawozdanie samo, bez operatu, nie istnieje — dokłada się je w formularzu."""
    _dodaj_operat(klient)
    klient.srodowisko.dodaj_szablon("sprawozdanie_wzor", ["{{ nr_roboty }}"],
                                    opis={"nazwa": "Sprawozdanie techniczne", "pola": []})
    tresc = klient.get("/").text

    assert 'href="/nowy/spis_tresci_wzor"' in tresc
    assert 'href="/nowy/sprawozdanie_wzor"' not in tresc
    assert "Sprawozdanie techniczne" not in tresc


def test_wpisane_dane_to_karty_jak_w_formularzu(klient):
    """Strona operatu i formularz pokazują ten sam podział na grupy — więc mają go
    pokazywać tak samo. Jedna długa tabela z szarymi paskami wyglądała jak co innego
    niż strona, na której te dane się wpisuje.

    Nazwy pól to etykiety z opisu szablonu, nie klucze techniczne; klucz zostaje
    w `title`, bo po nim rozpoznaje się pole przy szukaniu usterki.
    """
    _dodaj_operat(klient)
    klient.post("/generuj/spis_tresci_wzor", data=FORMULARZ, follow_redirects=False)

    strona = klient.get(f"/dokument/{db.dokumenty()[0]['id']}").text

    assert '<fieldset class="karta-danych">' in strona
    assert "<legend>Dane</legend>" in strona, "grupa bez własnej karty"
    assert 'class="grupa"' not in strona, "został stary pasek grupy"
    assert '<th class="waski" title="nr_roboty">Nr roboty</th>' in strona
    assert 'title="nr_operatu">nr_operatu<' not in strona, "klucz zamiast etykiety"


def test_nowa_robota_to_przycisk_przy_naglowku_listy(klient):
    """Zaczęcie roboty to jedno kliknięcie. Karta z opisem szablonu i liczbą pól
    zajmowała ćwierć ekranu nad listą operatów, czyli nad tym, po co brat tu wchodzi.

    Przycisk stoi **w nagłówku listy**, dosunięty do jej prawej krawędzi — sam wygląd
    obroni dopiero oko, ale tę strukturę już test: bez wspólnego kontenera przycisk
    wraca nad nagłówek i wyrównanie do tabeli przestaje istnieć.
    """
    import re

    _dodaj_operat(klient)

    tresc = klient.get("/").text

    assert '<a class="glowny" href="/nowy/spis_tresci_wzor">Nowy operat</a>' in tresc
    assert 'class="karta"' not in tresc, "karta szablonu została na stronie głównej"
    naglowek = re.search(r'<div class="naglowek-listy">(.*?)</div>\s*</div>',
                         tresc, re.DOTALL)
    assert naglowek, "przycisk nie stoi w nagłówku listy"
    assert "<h1>Operaty</h1>" in naglowek.group(1)
    assert 'href="/nowy/spis_tresci_wzor"' in naglowek.group(1)


def test_nieznany_adres_daje_polska_strone_bledu(klient):
    odpowiedz = klient.get("/nie-ma-takiej-strony")
    assert odpowiedz.status_code == 404
    assert "Nie ma takiej strony" in odpowiedz.text
    assert "Not Found" not in odpowiedz.text


def test_bledny_identyfikator_nie_pokazuje_angielskiego_json(klient):
    """/dokument/abc zamiast /dokument/12 — brat ma zobaczyć polską stronę.

    Szukamy klucza `detail` z JSON-a FastAPI, a nie napisu „detail” gdziekolwiek:
    strona ma w menu `<details>` i luźne dopasowanie czerwieniało od własnego HTML-a.
    """
    odpowiedz = klient.get("/dokument/abc")
    assert odpowiedz.status_code == 404
    assert odpowiedz.headers["content-type"].startswith("text/html")
    assert '{"detail"' not in odpowiedz.text
    assert "Nie ma takiej strony" in odpowiedz.text


def test_strona_bledu_jest_cala_strona_a_nie_golym_html(klient):
    """Strona błędu ma nagłówek, menu i style — nie sam komunikat na białym tle.

    `strona_bledu` budowała własny, okrojony kontekst i brakowało w nim liczników
    ze stopki. Odczyt pola z nieistniejącej zmiennej to w Jinja **wyjątek**, więc
    render padał i szedł zapasowy goły HTML: po polsku, ale bez niczego wokół.
    Testy tego nie widziały, bo sprawdzały samą treść komunikatu.
    """
    import uruchom

    odpowiedz = klient.get("/nie-ma-takiej-strony")

    assert odpowiedz.status_code == 404
    tresc = odpowiedz.text
    assert tresc.lstrip().startswith("<!doctype"), "strona błędu poszła jako goły HTML"
    assert uruchom.ZNACZNIK in tresc, "brak nagłówka programu"
    assert "style.css" in tresc, "brak arkusza stylów"


def test_nieznany_szablon_nie_wywala_aplikacji(klient):
    odpowiedz = klient.get("/nowy/nie_ma_takiego", follow_redirects=False)
    assert odpowiedz.status_code in (303, 404)


# --- generowanie -------------------------------------------------------------

def test_generowanie_z_formularza(klient):
    _dodaj_operat(klient)
    odpowiedz = klient.post("/generuj/spis_tresci_wzor", data=FORMULARZ,
                            follow_redirects=False)
    assert odpowiedz.status_code == 303
    assert odpowiedz.headers["location"].startswith("/dokument/")

    wiersze = db.dokumenty()
    assert len(wiersze) == 1
    assert wiersze[0]["nr_operatu"].endswith(f"/{__import__('datetime').date.today().year}")

    katalog = klient.srodowisko.wyniki / wiersze[0]["katalog"]
    assert (katalog / "operat.json").exists()
    assert (katalog / "spis_tresci.docx").exists()
    zapisane = json.loads(wiersze[0]["dane_json"])
    assert zapisane["punkty"] == [{"numer": "101", "x": "5712345.12"}]   # pusty wiersz odpadł


def _szczyt(klient, wpis):
    """Górny blok strony operatu: numer, data i przyciski."""
    tresc = klient.get(f"/dokument/{wpis['id']}").text
    return tresc.split('<div class="szczyt">')[1].split("<fieldset")[0]


def test_szczyt_operatu_to_numer_data_i_przyciski(klient):
    """Numer operatu, pod nim data utworzenia, obok przyciski — jeden wiersz.

    Numer roboty stoi w karcie „Robota” niżej; w nagłówku był kolejnym członem
    do przeczytania, zanim wzrok trafi w treść. Data jest mniejsza i szara: służy
    do sprawdzenia „czy to ten operat”, a nie do czytania w pierwszej kolejności.
    """
    from app.config import WEB

    _dodaj_operat(klient)
    klient.post("/generuj/spis_tresci_wzor", data=FORMULARZ, follow_redirects=False)
    wpis = db.dokumenty()[0]

    szczyt = _szczyt(klient, wpis)

    assert f"<h1>Operat: {wpis['nr_operatu']}</h1>" in szczyt
    assert "GK.6640.1.2026" not in szczyt, "numer roboty wrócił na szczyt strony"
    assert szczyt.index("<h1>") < szczyt.index('class="lekki"') < szczyt.index("Otwórz katalog")

    style = (WEB / "static" / "style.css").read_text(encoding="utf-8")
    lekki = style.split(".szczyt .lekki {")[1].split("}")[0]
    assert "font-size" in lekki, "data w wielkości nagłówka ciągnie wzrok na siebie"
    blok = style.split(".szczyt {")[1].split("}")[0]
    assert "space-between" in blok, "przyciski nie odsuną się na prawo"


def test_szczyt_bez_licznika_mowi_to_samo_co_lista(klient):
    """Szablon bez licznika numeru nie nadaje — zostaje nazwa katalogu.

    Szczyt ma wtedy pokazywać dokładnie to, co lista operatów: inaczej ten sam operat
    nazywałby się na dwóch stronach dwiema różnymi rzeczami.
    """
    klient.srodowisko.dodaj_szablon(
        "spis_tresci_wzor", ["{{ nr_roboty }}"],
        opis={"nazwa": "Operat", "glowny": True,
              "pola": [{"klucz": "nr_roboty", "etykieta": "Nr roboty"}]})

    klient.post("/generuj/spis_tresci_wzor", data={"pole__nr_roboty": "GK.9.2026"},
                follow_redirects=False)
    wpis = db.dokumenty()[0]

    assert wpis["nr_operatu"] in _szczyt(klient, wpis)
    assert wpis["nr_operatu"] in klient.get("/").text


def test_szczyt_formularza_przy_poprawianiu_jak_strona_operatu(klient):
    """Po kliknięciu „Popraw” szczyt ma wyglądać tak samo jak ten, z którego się przyszło.

    Numer operatu w nagłówku, data pod nim, akcje po prawej — i żadnych zdań
    objaśniających: opis szablonu i notka o numeracji czytały się jak ostrzeżenia.
    Górny „Zapisz” stoi **poza** formularzem, więc musi wskazywać go przez `form=`;
    literówka w tym miejscu daje przycisk, który po cichu nic nie robi.
    """
    _dodaj_operat(klient)
    klient.post("/generuj/spis_tresci_wzor", data=FORMULARZ, follow_redirects=False)
    wpis = db.dokumenty()[0]

    strona = klient.get(f"/nowy/spis_tresci_wzor?edytuj={wpis['id']}").text
    szczyt = strona.split('<div class="szczyt">')[1].split("</div>\n</div>")[0]

    assert f"Operat: {wpis['nr_operatu']}" in szczyt
    assert "lekki" in szczyt, "zniknęła data utworzenia"
    assert "Numer i katalog zostają te same" not in strona
    assert "Strona tytułowa" not in strona, "opis szablonu wrócił na szczyt"

    assert 'form="operat"' in szczyt, "górny przycisk nie wskazuje formularza"
    assert 'id="operat"' in strona, "formularz nie ma identyfikatora, na który wskazuje"
    assert ">Zapisz<" in szczyt
    assert strona.count(">Zapisz<") == 2, "„Zapisz” ma być na górze i na dole formularza"


def test_szczyt_formularza_przy_nowym_operacie(klient):
    """Nowy operat — nagłówek to nazwa szablonu i nic poza nim.

    Numer, który zostanie nadany, widać w polu „Nr operatu” jako podpowiedź, więc
    zdanie o nim nad formularzem tylko mówiło to samo drugi raz.
    """
    _dodaj_operat(klient)

    strona = klient.get("/nowy/spis_tresci_wzor").text

    assert "<h1>Nowy operat</h1>" in strona
    assert "Numer nadany temu dokumentowi" not in strona
    assert strona.count(">Zapisz<") == 2, "„Zapisz” ma być na górze i na dole formularza"
    numer = f"001/{__import__('datetime').date.today().year}"
    assert f'placeholder="{numer}"' in strona, "zniknął podgląd numeru z pola"


def _szczyt_formularza(strona):
    return strona.split('<div class="szczyt">')[1].split("</div>\n</div>")[0]


def test_szczyt_po_bledzie_przy_poprawianiu_nadal_mowi_ktory_operat(klient):
    """Po „Uzupełnij wymagane pola” formularz ma wrócić jako ten sam operat.

    Powrót na formularz po błędzie budował kontekst osobno i bez numeru operatu —
    nagłówek przeskakiwał wtedy z „Operat: 001/2026” na „Nowy operat”, a data znikała.
    Dla brata wyglądało to tak, jakby poprawka przepadła i zakładał nowy operat.
    """
    _dodaj_operat(klient)
    klient.post("/generuj/spis_tresci_wzor", data=FORMULARZ, follow_redirects=False)
    wpis = db.dokumenty()[0]

    strona = klient.post(f"/generuj/spis_tresci_wzor?edytuj={wpis['id']}",
                         data={**FORMULARZ, "pole__nr_roboty": ""}).text

    assert "Uzupełnij wymagane pola" in strona
    szczyt = _szczyt_formularza(strona)
    assert f"Operat: {wpis['nr_operatu']}" in szczyt
    assert "Nowy operat" not in szczyt
    assert "lekki" in szczyt, "zniknęła data utworzenia"
    assert f'placeholder="{wpis["nr_operatu"]}"' in strona, "pole numeru straciło podpowiedź"
    assert len(db.dokumenty()) == 1, "nieudana poprawka założyła nowy operat"


def test_szczyt_przy_poprawianiu_operatu_bez_licznika(klient):
    """Szablon bez pola auto_numer: poprawianie też ma się nazywać operatem, nie „Nowy”.

    Numer brało się wyłącznie w pętli po polach `auto_numer`, więc bez takiego pola
    nagłówek mówił „Nowy operat” — choć strona operatu, z której się przyszło, mówiła
    „Operat: <nazwa katalogu>”.
    """
    klient.srodowisko.dodaj_szablon(
        "spis_tresci_wzor", ["{{ nr_roboty }}"],
        opis={"nazwa": "Operat", "glowny": True,
              "pola": [{"klucz": "nr_roboty", "etykieta": "Nr roboty"}]})
    klient.post("/generuj/spis_tresci_wzor", data={"pole__nr_roboty": "GK.9.2026"},
                follow_redirects=False)
    wpis = db.dokumenty()[0]

    szczyt = _szczyt_formularza(klient.get(f"/nowy/spis_tresci_wzor?edytuj={wpis['id']}").text)

    assert f"Operat: {wpis['nr_operatu']}" in szczyt
    assert "Nowy operat" not in szczyt
    assert "lekki" in szczyt


def test_poprawianie_skasowanego_operatu_nie_udaje_poprawiania(klient):
    """Stara zakładka z „Popraw” po skasowaniu operatu.

    Formularz brał wtedy kolejny numer z licznika i ogłaszał „Operat: 003/2026”, jakby
    poprawiał istniejący — a zapis zakładał nowy. Ma odesłać na listę z wyjaśnieniem.
    """
    _dodaj_operat(klient)
    klient.post("/generuj/spis_tresci_wzor", data=FORMULARZ, follow_redirects=False)
    wpis = db.dokumenty()[0]
    klient.post(f"/dokument/{wpis['id']}/usun", follow_redirects=False)

    odpowiedz = klient.get(f"/nowy/spis_tresci_wzor?edytuj={wpis['id']}", follow_redirects=False)

    assert odpowiedz.status_code == 303
    assert odpowiedz.headers["location"].startswith("/?blad=")
    assert "nie ma" in klient.get(odpowiedz.headers["location"]).text


def test_zapis_poprawki_skasowanego_operatu_zostawia_dane_i_nie_udaje_poprawki(klient):
    """„Zapisz” w starej zakładce, gdy operat już skasowano.

    Nie wolno po cichu założyć nowego operatu pod pozorem poprawki ani wyrzucić
    wpisanych danych: formularz wraca z komunikatem, już jako nowy operat.
    """
    _dodaj_operat(klient)
    klient.post("/generuj/spis_tresci_wzor", data=FORMULARZ, follow_redirects=False)
    wpis = db.dokumenty()[0]
    klient.post(f"/dokument/{wpis['id']}/usun", follow_redirects=False)

    strona = klient.post(f"/generuj/spis_tresci_wzor?edytuj={wpis['id']}",
                         data={**FORMULARZ, "pole__nr_roboty": "GK.7.2026"}).text

    assert db.dokumenty() == [], "zapis poprawki skasowanego operatu założył nowy"
    assert "nie ma" in strona and 'class="komunikat' in strona
    assert 'value="GK.7.2026"' in strona, "wpisane dane przepadły"
    assert "Nowy operat" in _szczyt_formularza(strona)
    assert 'action="/generuj/spis_tresci_wzor"' in strona, "formularz nadal udaje poprawianie"


def test_przyciski_bedace_linkami_tez_reaguja_na_najechanie():
    """„Popraw” i „Powiel” to linki, „Otwórz katalog” to przycisk formularza.

    Wyglądają tak samo, więc muszą tak samo reagować — link bez podświetlenia wygląda
    jak nieaktywny, choć robi to samo co sąsiad obok.
    """
    from app.config import WEB

    style = (WEB / "static" / "style.css").read_text(encoding="utf-8")

    assert ".wtorny:hover" in style


def test_karta_przegladarki_nazywa_sie_numerem_operatu(klient):
    """Przy kilku otwartych operatach karty rozróżnia się po tytule."""
    _dodaj_operat(klient)
    klient.post("/generuj/spis_tresci_wzor", data=FORMULARZ, follow_redirects=False)
    wpis = db.dokumenty()[0]

    strona = klient.get(f"/dokument/{wpis['id']}").text
    tytul = strona.split("<title>")[1].split("</title>")[0]

    assert tytul.strip() == f"Operat: {wpis['nr_operatu']}"


def test_strona_operatu_pokazuje_nadany_numer(klient):
    """Numer operatu nadaje program, więc w danych z formularza go nie ma.

    Na stronie operatu musi być mimo to widoczny — to po nim rozpoznaje się robotę
    w ośrodku, a pusta krata przy „nr_operatu” wygląda jak usterka programu.
    """
    import re

    _dodaj_operat(klient)
    klient.post("/generuj/spis_tresci_wzor", data=FORMULARZ, follow_redirects=False)
    wpis = db.dokumenty()[0]

    strona = klient.get(f"/dokument/{wpis['id']}").text

    assert wpis["nr_operatu"] in strona, "numeru operatu nie ma nigdzie na stronie"
    krata = re.search(r'<th class="waski" title="nr_operatu">.*?</th>\s*<td>(.*?)</td>',
                      strona, re.DOTALL)
    assert krata and wpis["nr_operatu"] in krata.group(1), \
        "przy nr_operatu została pusta krata"


def test_wpisane_dane_ida_grupami_z_szablonu(klient):
    """Kolejność i grupy biorą się z opisu szablonu, a nie z kolejności danych w bazie.

    W bazie dane leżą tak, jak przyszły z formularza, więc numer roboty sąsiadował
    z opisem przebiegu, a daty stały w trzech miejscach. Grupy są już opisane w `.json`
    obok szablonu — tym samym, po którym formularz układa karty — więc zmiana układu
    nie wymaga ruszania kodu.
    """
    import re

    klient.srodowisko.dodaj_szablon(
        "spis_tresci_wzor", ["{{ nr_roboty }} {{ nr_operatu }} {{ uwagi }} {{ data_zakonczenia }}"],
        opis={"nazwa": "Operat", "glowny": True, "licznik": "operat", "pola": [
            {"klucz": "nr_roboty", "grupa": "Robota", "wymagane": True},
            {"klucz": "nr_operatu", "typ": "auto_numer", "domyslnie": "{numer3}/{rok}",
             "grupa": "Robota"},
            {"klucz": "uwagi", "typ": "textarea", "grupa": "Opis"},
            # pole tej samej grupy dopisane na końcu ma trafić do niej, a nie założyć
            # drugiego bloku o tym samym nagłówku
            {"klucz": "data_zakonczenia", "typ": "date", "grupa": "Robota"},
        ]})

    klient.post("/generuj/spis_tresci_wzor",
                data={"pole__nr_roboty": "GK.1.2026", "pole__nr_operatu": "",
                      "pole__uwagi": "cokolwiek", "pole__data_zakonczenia": "2026-08-06"},
                follow_redirects=False)
    strona = klient.get(f"/dokument/{db.dokumenty()[0]['id']}").text

    uklad = re.findall(r'<fieldset class="karta-danych">\s*<legend>(.*?)</legend>'
                       r'|<th class="waski" title="(.*?)">', strona)
    assert [g or p for g, p in uklad] == [
        "Robota", "nr_roboty", "nr_operatu", "data_zakonczenia", "Opis", "uwagi"]


def test_lista_pozycji_stoi_w_pionie_z_numerami(klient):
    """Spis treści czyta się na stronie operatu tak jak w gotowym dokumencie.

    Sklejony średnikami zawijał się w akapit, w którym nie dało się ani policzyć
    pozycji, ani sprawdzić, czy ta jedna szukana w ogóle jest. Numery są te same,
    bo formatka numeruje `loop.index` po tej samej liście.
    """
    klient.srodowisko.dodaj_szablon(
        "spis_tresci_wzor",
        ["{{ nr_roboty }} {{ nr_operatu }}", "{{ spis_tresci }}"],
        opis={**OPIS_OPERATU, "pola": [
            {"klucz": "nr_roboty", "etykieta": "Nr roboty", "grupa": "Robota"},
            {"klucz": "nr_operatu", "typ": "auto_numer", "domyslnie": "{numer3}/{rok}",
             "etykieta": "Nr operatu", "grupa": "Robota"},
            {"klucz": "spis_tresci", "typ": "wybor_wielokrotny", "grupa": "Spis treści",
             "opcje": ["Spis treści", "Sprawozdanie techniczne", "Mapa z projektem"]},
        ]})

    klient.post("/generuj/spis_tresci_wzor",
                data={"pole__nr_roboty": "GK.1.2026", "pole__nr_operatu": "",
                      "pole__spis_tresci": ["Spis treści", "Mapa z projektem"]},
                follow_redirects=False)
    strona = klient.get(f"/dokument/{db.dokumenty()[0]['id']}").text

    assert "Spis treści; Mapa z projektem" not in strona, "pozycje nadal w jednej linijce"
    lista = strona.split('<ol class="pozycje">')[1].split("</ol>")[0]
    assert lista.count("<li>") == 2
    # kolejność zachowana — numer na stronie ma znaczyć to samo co w dokumencie
    assert lista.index("Spis treści") < lista.index("Mapa z projektem")


def test_strona_operatu_podpisuje_pola_etykietami(klient):
    """Podpisy pól są **jedynym** sposobem odróżnienia dwóch dat od siebie.

    Etykieta jest ta sama co w formularzu; pole, które jej nie ma, dostaje nazwę
    wyprowadzoną z klucza. Pusta kolumna podpisów nie wchodzi w grę — z „2026-07-30”
    i „2026-08-05” pod sobą nie da się wtedy poznać, która jest która.
    """
    import re

    klient.srodowisko.dodaj_szablon(
        "spis_tresci_wzor",
        ["{{ nr_roboty }} {{ nr_operatu }} {{ data_zgloszenia }} {{ data_zakonczenia }}"],
        opis={**OPIS_OPERATU, "pola": [
            {"klucz": "nr_roboty", "etykieta": "Nr roboty", "grupa": "Robota"},
            {"klucz": "nr_operatu", "typ": "auto_numer", "domyslnie": "{numer3}/{rok}",
             "etykieta": "Nr operatu", "grupa": "Robota"},
            {"klucz": "data_zgloszenia", "typ": "date",
             "etykieta": "Data zgłoszenia pracy geodezyjnej", "grupa": "Robota"},
            # bez `etykieta` w opisie — podpis ma się wziąć z klucza
            {"klucz": "data_zakonczenia", "typ": "date", "grupa": "Robota"},
        ]})

    klient.post("/generuj/spis_tresci_wzor",
                data={"pole__nr_roboty": "GK.1.2026", "pole__nr_operatu": "",
                      "pole__data_zgloszenia": "2026-07-30",
                      "pole__data_zakonczenia": "2026-08-05"},
                follow_redirects=False)
    strona = klient.get(f"/dokument/{db.dokumenty()[0]['id']}").text

    podpisy = dict(re.findall(r'<th class="waski" title="(.*?)">(.*?)</th>', strona))
    assert podpisy["data_zgloszenia"] == "Data zgłoszenia pracy geodezyjnej"
    assert podpisy["nr_roboty"] == "Nr roboty"
    assert podpisy["data_zakonczenia"], "pole bez etykiety zostało bez podpisu"
    assert not [k for k, v in podpisy.items() if not v.strip()]


def test_pole_zbiorcze_dokumentow_nie_pokazuje_sie_puste(klient):
    """Kafelek „Wygeneruj też” zbiera dokumenty, których nie wziął żaden inny.

    Gdy wszystkie są już rozdane po kafelkach nazwanych, nie ma z czego wybierać
    i formularz w ogóle go nie pokazuje. Na liście wpisanych danych zostawała po nim
    krata „0 wierszy” — informacja o niczym, wyglądająca jak zgubione dokumenty.
    """
    klient.srodowisko.dodaj_szablon(
        "spis_tresci_wzor", ["{{ nr_roboty }} {{ nr_operatu }}"],
        opis={**OPIS_OPERATU, "pola": OPIS_OPERATU["pola"] + [
            {"klucz": "dokumenty_sprawozdanie", "typ": "dokumenty",
             "tylko": ["sprawozdanie_wzor"]},
            {"klucz": "dokumenty", "typ": "dokumenty"},        # zbiorcze, bez `tylko`
        ]})
    klient.srodowisko.dodaj_szablon("sprawozdanie_wzor", ["{{ nr_operatu }}"],
                                    opis={"nazwa": "Sprawozdanie techniczne", "pola": []})

    klient.post("/generuj/spis_tresci_wzor",
                data={**FORMULARZ, "pole__dokumenty_sprawozdanie": "sprawozdanie_wzor"},
                follow_redirects=False)
    strona = klient.get(f"/dokument/{db.dokumenty()[0]['id']}").text

    assert "0 wierszy" not in strona
    assert ">dokumenty</th>" not in strona, "puste pole zbiorcze zostało na liście"
    # ...a wybrany dokument opisany jest nazwą, nie identyfikatorem pliku
    assert "Sprawozdanie techniczne" in strona
    assert "sprawozdanie_wzor" not in strona


def test_powielenie_zaczyna_z_pustym_numerem_operatu(klient):
    """I dlatego numeru **nie** zapisujemy do danych formularza.

    Te dane wracają do formularza przy „Powiel jako nowy”. Numer wpisany tam zostałby
    użyty drugi raz zamiast wziąć kolejny z licznika — dwa operaty o tym samym numerze
    to najgorsze, co może się tu stać.
    """
    import re

    _dodaj_operat(klient)
    klient.post("/generuj/spis_tresci_wzor", data=FORMULARZ, follow_redirects=False)
    wpis = db.dokumenty()[0]

    formularz = klient.get(f"/nowy/spis_tresci_wzor?kopiuj={wpis['id']}").text

    pole = re.search(r'id="p_nr_operatu"[^>]*value="([^"]*)"', formularz)
    assert pole and pole.group(1) == "", \
        "powielanie startuje z wpisanym numerem — kolejny operat dostanie ten sam"


def test_brak_wymaganego_pola_wraca_na_formularz_z_danymi(klient):
    _dodaj_operat(klient)
    dane = dict(FORMULARZ, pole__nr_roboty="")
    odpowiedz = klient.post("/generuj/spis_tresci_wzor", data=dane)
    assert odpowiedz.status_code == 200
    assert "Uzupełnij wymagane pola" in odpowiedz.text
    assert "5712345.12" in odpowiedz.text, "wykaz współrzędnych przepadł przy błędzie walidacji"
    assert db.dokumenty() == []


def test_poprawianie_nie_zaklada_drugiego_operatu(klient):
    """`?edytuj=` wraca do tego samego katalogu, wpisu i numeru."""
    _dodaj_operat(klient)
    klient.post("/generuj/spis_tresci_wzor", data=FORMULARZ, follow_redirects=False)
    pierwszy = db.dokumenty()[0]

    poprawka = dict(FORMULARZ, pole__uwagi="literówka poprawiona")
    odpowiedz = klient.post(f"/generuj/spis_tresci_wzor?edytuj={pierwszy['id']}",
                            data=poprawka, follow_redirects=False)
    assert odpowiedz.status_code == 303

    wiersze = db.dokumenty()
    assert len(wiersze) == 1, "poprawka założyła drugi wpis w historii"
    assert wiersze[0]["id"] == pierwszy["id"]
    assert wiersze[0]["nr_operatu"] == pierwszy["nr_operatu"]
    assert wiersze[0]["katalog"] == pierwszy["katalog"]
    assert len(operaty.lista()) == 1, "poprawka założyła drugi katalog operatu"


def test_powielenie_bierze_kolejny_numer(klient):
    _dodaj_operat(klient)
    klient.post("/generuj/spis_tresci_wzor", data=FORMULARZ, follow_redirects=False)
    klient.post("/generuj/spis_tresci_wzor", data=dict(FORMULARZ, pole__nr_roboty="GK.2.2026"),
                follow_redirects=False)
    numery = sorted(w["nr_operatu"] for w in db.dokumenty())
    assert len(set(numery)) == 2
    assert numery[0].startswith("001/") and numery[1].startswith("002/")


def test_dokument_dodatkowy_powstaje_w_tym_samym_katalogu(klient):
    """Pole typu `dokumenty` dokłada kolejne pliki Worda do katalogu operatu."""
    klient.srodowisko.dodaj_szablon(
        "spis_tresci_wzor", ["{{ nr_roboty }} {{ nr_operatu }}"],
        opis={**OPIS_OPERATU,
              "pola": OPIS_OPERATU["pola"] + [{"klucz": "dokumenty", "typ": "dokumenty"}]})
    klient.srodowisko.dodaj_szablon("sprawozdanie_wzor", ["Operat {{ nr_operatu }}"],
                                    opis={"nazwa": "Sprawozdanie", "pola": []})

    dane = dict(FORMULARZ, pole__dokumenty="sprawozdanie_wzor")
    klient.post("/generuj/spis_tresci_wzor", data=dane, follow_redirects=False)

    katalog = klient.srodowisko.wyniki / db.dokumenty()[0]["katalog"]
    assert (katalog / "spis_tresci.docx").exists()
    assert (katalog / "sprawozdanie.docx").exists()


# --- składanie PDF -----------------------------------------------------------

def test_skladanie_przekierowuje_zamiast_oddawac_plik(klient):
    """POST oddaje przekierowanie, a PDF otwiera się z linku — formularz z target=_blank
    bywa blokowany, a „nic się nie stało” to najgorszy objaw dla użytkownika."""
    _dodaj_operat(klient)
    klient.post("/generuj/spis_tresci_wzor", data=FORMULARZ, follow_redirects=False)
    katalog = db.dokumenty()[0]["katalog"]

    odpowiedz = klient.post(f"/scal/{katalog}", data={"plik": "spis_tresci.docx"},
                            follow_redirects=False)
    assert odpowiedz.status_code == 303
    assert "application/pdf" not in odpowiedz.headers.get("content-type", "")


def test_wynik_skladania_nazywa_sie_numerem_roboty(klient):
    _dodaj_operat(klient)
    klient.post("/generuj/spis_tresci_wzor", data=FORMULARZ, follow_redirects=False)
    katalog_nazwa = db.dokumenty()[0]["katalog"]
    klient.post(f"/scal/{katalog_nazwa}", data={"plik": "spis_tresci.docx"},
                follow_redirects=False)

    katalog = klient.srodowisko.wyniki / katalog_nazwa
    assert (katalog / "GK.6640.1.2026.pdf").exists(), sorted(p.name for p in katalog.iterdir())

    # …i tak samo nazywa się w czytniku: bez tytułu w metadanych karta przeglądarki
    # brałaby nazwę z adresu, czyli „wynik”
    from pypdf import PdfReader
    assert PdfReader(str(katalog / "GK.6640.1.2026.pdf")).metadata.title == "GK.6640.1.2026"


def test_sciezka_z_adresu_nie_wyprowadza_poza_wyniki(klient):
    """Nazwa katalogu z URL-a nie może sięgnąć wyżej niż `wyniki/`."""
    odpowiedz = klient.get("/scal/..%2F..%2Fetc", follow_redirects=False)
    assert odpowiedz.status_code in (303, 404)
    assert odpowiedz.status_code != 500


def test_lista_pokazuje_operat_spoza_historii(klient):
    """Katalog przywrócony z archiwum ma być do złożenia, choć nie ma go w bazie.

    To był jedyny powód istnienia osobnej strony `/scal`: czytała dysk, a strona
    główna bazę. Po scaleniu list ta ścieżka nie może zniknąć — inaczej operat
    przywrócony na świeżej instalacji zostałby poza zasięgiem.
    """
    katalog = klient.srodowisko.wyniki / "777.2026"
    katalog.mkdir(parents=True)
    (katalog / "operat.json").write_text(
        json.dumps({"nr_operatu": "777/2026", "nr_roboty": "G.99.2026",
                    "utworzono": "2026-07-20T08:00:00", "dane": {}}, ensure_ascii=False),
        encoding="utf-8")

    tresc = klient.get("/").text

    assert "777/2026" in tresc
    assert "spoza historii" in tresc
    assert 'href="/scal/777.2026"' in tresc


def test_lista_nie_ucina_sie_na_pietnastu_operatach(klient):
    """Wcześniej strona główna pokazywała 15 najnowszych — reszta była poza zasięgiem
    składania, bo druga lista (`/scal`) właśnie zniknęła."""
    _dodaj_operat(klient)
    for numer in range(18):
        klient.post("/generuj/spis_tresci_wzor",
                    data=dict(FORMULARZ, pole__nr_roboty=f"GK.{numer}.2026"),
                    follow_redirects=False)

    tresc = klient.get("/").text

    assert "GK.0.2026" in tresc, "najstarszy operat wypadł z listy"
    assert "GK.17.2026" in tresc


def test_stara_strona_listy_odsyla_na_dokumenty(klient):
    """Prowadzi tu kilkanaście przekierowań z obsługi błędów i zakładka brata."""
    odpowiedz = klient.get("/scal", follow_redirects=False)

    assert odpowiedz.status_code == 303
    assert odpowiedz.headers["location"] == "/"


def test_logo_jest_poprawnym_plikiem_svg():
    """SVG to XML — plik z błędem składni przeglądarka pokazuje jako pustą ramkę.

    Komunikat, który przy tym daje („nie da się zdekodować obrazu”), nie mówi nic
    o przyczynie. Najłatwiej o to w komentarzu: dwa myślniki pod rząd są w XML-u
    zabronione i wywracają cały plik. Parser wyłapie to w ułamku sekundy.
    """
    import xml.etree.ElementTree as ET

    from app.config import WEB
    drzewo = ET.parse(WEB / "static" / "logo.svg")
    assert drzewo.getroot().tag.endswith("svg")


def test_strona_ma_logo_i_ikone_karty(klient):
    odpowiedz = klient.get("/static/logo.svg")
    assert odpowiedz.status_code == 200
    assert "svg" in odpowiedz.headers["content-type"]

    strona = klient.get("/").text
    assert 'rel="icon"' in strona and "logo.svg" in strona
    assert '<img src="/static/logo.svg' in strona


def test_menu_nie_ma_juz_pozycji_zloz_pdf(klient):
    tresc = klient.get("/").text
    assert '<a href="/scal">' not in tresc


def test_kolumna_daty_mowi_ktora_to_data(klient):
    """W operacie są trzy daty: utworzenia, zgłoszenia i zakończenia pracy.

    Nagłówek „Data” kazał się domyślać, którą pokazuje lista — a pokazuje tę,
    której nigdzie indziej nie widać.
    """
    _dodaj_operat(klient)
    klient.post("/generuj/spis_tresci_wzor", data=FORMULARZ, follow_redirects=False)

    naglowki = klient.get("/").text.split("<thead>")[1].split("</thead>")[0]

    assert "<th>Utworzono</th>" in naglowki
    assert "<th>Data</th>" not in naglowki


def test_lista_ma_komplet_akcji_co_strona_operatu(klient):
    """Na liście ma być to samo, co po wejściu w operat — w tym „Popraw”.

    Bez tego poprawka literówki wymagała wejścia w dokument tylko po to, żeby
    kliknąć drugi raz. „Popraw” wraca do tego samego operatu (`?edytuj=`),
    a „Powiel” zakłada nowy z tymi samymi danymi (`?kopiuj=`) — to są dwie
    różne rzeczy i obie muszą być pod ręką.
    """
    _dodaj_operat(klient)
    klient.post("/generuj/spis_tresci_wzor", data=FORMULARZ, follow_redirects=False)
    wpis = db.dokumenty()[0]

    lista = klient.get("/").text
    strona_operatu = klient.get(f"/dokument/{wpis['id']}").text

    for adres in (f'href="/scal/{wpis["katalog"]}"',
                  f'href="/nowy/spis_tresci_wzor?edytuj={wpis["id"]}"',
                  f'href="/nowy/spis_tresci_wzor?kopiuj={wpis["id"]}"'):
        assert adres in lista, f"brakuje na liście: {adres}"
        assert adres in strona_operatu, f"brakuje na stronie operatu: {adres}"


def test_skladanie_zapamietuje_kolejnosc_i_obrot(klient):
    """Drugie wejście na stronę składania ma zaczynać tam, gdzie brat skończył."""
    _dodaj_operat(klient)
    klient.post("/generuj/spis_tresci_wzor", data=FORMULARZ, follow_redirects=False)
    katalog = next(k for k in klient.srodowisko.wyniki.iterdir() if k.is_dir())
    _prawdziwy_pdf(katalog / "mapa.pdf")

    klient.post(f"/scal/{katalog.name}",
                data={"plik": ["mapa.pdf", "spis_tresci.docx"], "obrot__mapa.pdf": "90"},
                follow_redirects=False)

    zapisany = operaty.uklad(katalog)
    assert zapisany["kolejnosc"] == ["mapa.pdf", "spis_tresci.docx"]
    assert zapisany["obroty"] == {"mapa.pdf": 90}

    tresc = klient.get(f"/scal/{katalog.name}").text
    assert tresc.index("mapa.pdf") < tresc.index("spis_tresci.docx")   # kolejność wróciła
    assert 'name="obrot__mapa.pdf" value="90"' in tresc                # i obrót też


def test_nieudane_skladanie_nie_nadpisuje_ukladu(klient):
    """Pomyłka („nie wybrano plików”) nie może skasować ustawionego wcześniej układu."""
    _dodaj_operat(klient)
    klient.post("/generuj/spis_tresci_wzor", data=FORMULARZ, follow_redirects=False)
    katalog = next(k for k in klient.srodowisko.wyniki.iterdir() if k.is_dir())
    _prawdziwy_pdf(katalog / "mapa.pdf")
    klient.post(f"/scal/{katalog.name}",
                data={"plik": ["mapa.pdf", "spis_tresci.docx"]}, follow_redirects=False)

    klient.post(f"/scal/{katalog.name}", data={}, follow_redirects=False)

    assert operaty.uklad(katalog)["kolejnosc"] == ["mapa.pdf", "spis_tresci.docx"]


# --- operat przeniesiony do archiwum ----------------------------------------

def test_operat_z_archiwum_zostaje_na_liscie_ale_bez_skladania(klient):
    """Brat przenosi gotowe operaty na dysk archiwalny — wpis w historii zostaje.

    To jest w porządku: widzi, że taki operat istniał. Ale nie ma czego składać,
    więc przycisk „Złóż PDF” nie może tam stać. Kliknięty odsyłał po cichu na listę,
    a „nic się nie stało” to najgorszy objaw dla użytkownika.
    """
    import shutil

    _dodaj_operat(klient)
    klient.post("/generuj/spis_tresci_wzor", data=FORMULARZ, follow_redirects=False)
    katalog = klient.srodowisko.wyniki / db.dokumenty()[0]["katalog"]
    shutil.rmtree(katalog)                       # „przeniósł do archiwum”

    tresc = klient.get("/").text

    assert db.dokumenty()[0]["nr_operatu"] in tresc, "operat zniknął z historii"
    assert "w archiwum" in tresc
    assert f'href="/scal/{katalog.name}"' not in tresc, \
        "przycisk składania stoi przy operacie, którego nie ma na dysku"


def test_wejscie_na_skladanie_archiwalnego_operatu_tlumaczy_dlaczego(klient):
    """Z zakładki albo starego adresu — ma być wyjaśnienie, nie ciche odesłanie."""
    odpowiedz = klient.get("/scal/999.2026", follow_redirects=False)

    assert odpowiedz.status_code == 303
    adres = odpowiedz.headers["location"]
    assert adres.startswith("/?blad="), f"odesłanie bez wyjaśnienia: {adres}"
    from urllib.parse import unquote
    assert "archiwum" in unquote(adres)


def test_otwarcie_katalogu_archiwalnego_operatu_tlumaczy_dlaczego(klient):
    import shutil
    from urllib.parse import unquote

    _dodaj_operat(klient)
    klient.post("/generuj/spis_tresci_wzor", data=FORMULARZ, follow_redirects=False)
    wpis = db.dokumenty()[0]
    shutil.rmtree(klient.srodowisko.wyniki / wpis["katalog"])

    odpowiedz = klient.post(f"/dokument/{wpis['id']}/otworz-katalog", follow_redirects=False)

    assert "blad=" in odpowiedz.headers["location"]
    assert "archiwum" in unquote(odpowiedz.headers["location"])


def test_otwarcie_katalogu_z_listy_zostawia_na_liscie(klient, monkeypatch):
    """„Otwórz katalog” kliknięte na liście ma wrócić na listę, nie na stronę operatu.

    Trasa wracała zawsze na stronę operatu, więc po kliknięciu z listy strona zmieniała
    się pod otwieranym Eksploratorem — brat prosił o katalog, a dostawał inną stronę.
    """
    from app import operaty

    _dodaj_operat(klient)
    klient.post("/generuj/spis_tresci_wzor", data=FORMULARZ, follow_redirects=False)
    wpis = db.dokumenty()[0]
    otwarte = []
    monkeypatch.setattr(operaty, "otworz_w_systemie", otwarte.append)

    assert f'action="/dokument/{wpis["id"]}/otworz-katalog?powrot=lista"' in klient.get("/").text
    z_listy = klient.post(f"/dokument/{wpis['id']}/otworz-katalog?powrot=lista",
                          follow_redirects=False)
    ze_strony = klient.post(f"/dokument/{wpis['id']}/otworz-katalog", follow_redirects=False)

    assert z_listy.headers["location"] == "/"
    assert ze_strony.headers["location"] == f"/dokument/{wpis['id']}"
    assert [k.name for k in otwarte] == [wpis["katalog"]] * 2
    # adres spoza listy nie wysyła nigdzie indziej
    obcy = klient.post(f"/dokument/{wpis['id']}/otworz-katalog?powrot=https://zly.example",
                       follow_redirects=False)
    assert obcy.headers["location"] == f"/dokument/{wpis['id']}"


def test_usuwanie_wpisu_bez_katalogu_nie_pyta_o_katalog_none(klient):
    """Wpis sprzed podziału na katalogi ma `katalog` NULL — pytanie mówiło „katalogiem None”."""
    _dodaj_operat(klient)
    klient.post("/generuj/spis_tresci_wzor", data=FORMULARZ, follow_redirects=False)
    wpis = db.dokumenty()[0]
    with db.polaczenie() as polaczenie:
        polaczenie.execute("UPDATE dokumenty SET katalog = NULL, nr_operatu = NULL WHERE id = ?",
                           (wpis["id"],))

    strona = klient.get(f"/dokument/{wpis['id']}").text

    assert "None" not in strona
    assert "z historii razem z jego dokumentami" in strona
    assert "Złóż PDF" not in strona.split('<div class="szczyt">')[1].split("<fieldset")[0]


def test_karta_formularza_nazywa_sie_jak_naglowek(klient):
    """Nazwa karty przeglądarki mówiła „Operat” przy nowym i przy poprawianiu — jak
    strona operatu; przy kilku kartach nie dało się ich rozróżnić."""
    _dodaj_operat(klient)
    klient.post("/generuj/spis_tresci_wzor", data=FORMULARZ, follow_redirects=False)
    wpis = db.dokumenty()[0]

    def tytul(strona):
        return strona.split("<title>")[1].split("</title>")[0].strip()

    assert tytul(klient.get("/nowy/spis_tresci_wzor").text).startswith("Nowy operat")
    poprawianie = tytul(klient.get(f"/nowy/spis_tresci_wzor?edytuj={wpis['id']}").text)
    assert poprawianie.startswith(f"Operat: {wpis['nr_operatu']}")
    assert poprawianie != tytul(klient.get(f"/dokument/{wpis['id']}").text), \
        "karta formularza i karta operatu nie do odróżnienia"


def test_poprawienie_operatu_z_archiwum_wraca_do_tego_samego_numeru(klient):
    """Zgłoszone z użytkowania: „poprawiam 055, a robi się 060”.

    Numer przy poprawianiu brał się z `operat.json` **leżącego w folderze**, a ten
    pojechał do archiwum razem z katalogiem. Program uznawał więc poprawkę za nowy
    operat: zakładał katalog obok i **zjadał kolejny numer z licznika** — czyli robił
    dziurę w numeracji, której już nikt nie odzyska. Numer cały czas jest w historii.
    """
    import shutil

    _dodaj_operat(klient)
    klient.post("/generuj/spis_tresci_wzor", data=FORMULARZ, follow_redirects=False)
    pierwszy = db.dokumenty()[0]
    numer, katalog = pierwszy["nr_operatu"], pierwszy["katalog"]
    shutil.rmtree(klient.srodowisko.wyniki / katalog)          # „przeniósł do archiwum”

    klient.post(f"/generuj/spis_tresci_wzor?edytuj={pierwszy['id']}",
                data=dict(FORMULARZ, pole__uwagi="poprawka"), follow_redirects=False)

    wiersze = db.dokumenty()
    assert len(wiersze) == 1, "poprawka założyła drugi wpis w historii"
    assert wiersze[0]["nr_operatu"] == numer, "poprawka zmieniła numer operatu"
    assert wiersze[0]["katalog"] == katalog
    assert (klient.srodowisko.wyniki / katalog).is_dir(), \
        "katalog nie został odtworzony pod starą nazwą"

    # ...a licznik stoi w miejscu: następny nowy operat bierze kolejny numer, nie dalszy
    klient.post("/generuj/spis_tresci_wzor", data=dict(FORMULARZ, pole__nr_roboty="GK.2.2026"),
                follow_redirects=False)
    nowy = [w for w in db.dokumenty() if w["nr_operatu"] != numer][0]
    assert nowy["nr_operatu"].startswith("002/"), \
        f"poprawka zjadła numer z licznika — nowy operat dostał {nowy['nr_operatu']}"


# --- pliki statyczne w przeglądarce -----------------------------------------

def test_adres_arkusza_zmienia_sie_po_zmianie_pliku(klient, tmp_path, monkeypatch):
    """Poprawka CSS bez wydania też musi dojechać do przeglądarki.

    Adres był wcześniej znakowany samym numerem wersji, a ten stoi w miejscu aż do
    wydania — przeglądarka trzymała więc stary arkusz i poprawka wyglądała na
    niedziałającą, choć serwer oddawał już nowy plik (zdarzyło się przy układzie
    listy operatów). Teraz w znaczniku jest też czas zmiany plików w `static/`.
    """
    from app import main

    statyczne = tmp_path / "static"
    statyczne.mkdir()
    (statyczne / "style.css").write_text("body { color: red }", encoding="utf-8")
    monkeypatch.setattr(main, "WEB", tmp_path)

    monkeypatch.setattr(main, "_ZNACZNIK_ZASOBOW", None)
    przed = main.wersja_zasobow()

    import os
    os.utime(statyczne / "style.css", (2_000_000_000, 2_000_000_000))
    monkeypatch.setattr(main, "_ZNACZNIK_ZASOBOW", None)      # nowe uruchomienie programu

    assert main.wersja_zasobow() != przed


def test_odstepy_nad_pierwsza_karta_sa_takie_jak_miedzy_kartami():
    """Pasek przycisków i karty trzymają **jeden** odstęp.

    Gdy któryś się rozjedzie, strona wygląda na poskładaną z dwóch kawałków: jedna
    przerwa ciasna, druga luźna.
    """
    import re

    from app.config import WEB

    style = (WEB / "static" / "style.css").read_text(encoding="utf-8")

    def margines(selektor: str) -> str:
        blok = style.split(selektor + " {")[1].split("}")[0]
        return re.search(r"margin:\s*([^;]+);", blok).group(1).strip()

    assert margines("fieldset").endswith("0 0 18px")
    assert margines(".szczyt").startswith("0 0 18px")
    # kreska oddzielająca szczyt strony od kart z danymi
    assert "border-bottom" in style.split(".szczyt {")[1].split("}")[0]


def test_nazwy_kart_maja_kolor_akcentu():
    """Formularz operatu ma kilkanaście kart i przy przewijaniu szuka się właśnie ich
    nazw — czarne na tle czarnego tekstu zlewały się w jedno.

    Podkarty („Wykaz 1”, „Działka 2”) zostają szare: różnica między kartą a jej
    wnętrzem ma być widoczna.
    """
    from app.config import WEB

    style = (WEB / "static" / "style.css").read_text(encoding="utf-8")

    legenda = style.split("legend {")[1].split("}")[0]
    assert "var(--akcent)" in legenda, "nazwy kart bez koloru akcentu"
    podkarta = style.split(".sekcja > legend {")[1].split("}")[0]
    assert "var(--szary)" in podkarta, "podkarty przestały być szare"


def test_znacznik_stylow_odswieza_sie_w_kopii_roboczej(klient, monkeypatch):
    """Serwer nie ma auto-reloadu, a znacznik był liczony raz na uruchomienie — po
    zmianie CSS-u adres zostawał ten sam i przeglądarka brała arkusz z cache. Poprawka
    wyglądała wtedy na niedziałającą, choć serwer oddawał już nowy plik.

    U brata (bez `.git`) zostaje jak było: katalog jest niezmienny przez całe
    uruchomienie, a aktualizacja i tak restartuje program.
    """
    from app import aktualizacja, main
    from app.config import WEB

    monkeypatch.setattr(aktualizacja, "kopia_robocza_gita", lambda: True)
    monkeypatch.setattr(main, "_ZNACZNIK_ZASOBOW", None)
    przed = main.wersja_zasobow()
    (WEB / "static" / "style.css").touch()
    assert main.wersja_zasobow() != przed, "znacznik nie nadąża za zmianą arkusza"

    monkeypatch.setattr(aktualizacja, "kopia_robocza_gita", lambda: False)
    stoi = main.wersja_zasobow()
    (WEB / "static" / "style.css").touch()
    assert main.wersja_zasobow() == stoi, "u brata znacznik ma być liczony raz"


def test_strona_znakuje_arkusz_stylow(klient):
    """Bez znacznika w adresie każda zmiana wyglądu wymagałaby od brata Ctrl+F5.

    Znacznik musi być **czymś więcej niż numerem wersji** — na tym poległa pierwsza
    wersja: numer stoi w miejscu aż do wydania, więc adres się nie zmieniał.
    """
    import re

    from app import aktualizacja
    _dodaj_operat(klient)

    tresc = klient.get("/").text

    znacznik = re.search(r"/static/style\.css\?v=([^\"']+)", tresc)
    assert znacznik, "arkusz stylów bez znacznika — przeglądarka zostanie przy starym"
    wersja = aktualizacja.wersja_lokalna()[0]
    assert znacznik.group(1) != wersja, "sam numer wersji nie zmienia się między wydaniami"
    assert wersja in znacznik.group(1), "numer wersji zostaje, bo po nim poznaje się wydanie"


def test_formularz_ostrzega_przed_zgubieniem_wpisanych_danych(klient):
    """Wstecz, odświeżenie albo zamknięcie karty kasowało wypełniony operat bez słowa.

    Testem sprawdzamy to, co da się sprawdzić bez przeglądarki: że strona formularza
    wiezie ten strażnik i że jest **wpięty w wysyłkę** — bez tego okienko wyskakiwałoby
    przy każdym wygenerowaniu dokumentu, czyli zawsze, czyli brat nauczyłby się je
    odklikiwać. Zachowanie w przeglądarce sprawdzone ręcznie: czysta strona nie pyta,
    po wpisaniu pyta, po wysłaniu znów nie.
    """
    _dodaj_operat(klient)

    strona = klient.get("/nowy/spis_tresci_wzor").text

    assert "beforeunload" in strona, "formularz bez ostrzeżenia o niezapisanych zmianach"
    straznik = strona[max(0, strona.index("beforeunload") - 2000):]
    assert "'submit'" in straznik or '"submit"' in straznik, \
        "wysyłka nie zeruje flagi — okienko wyskoczy przy generowaniu"


def test_podglad_wykazu_wyrownuje_komorki_do_gory():
    """To samo wyrównanie co w dokumencie: przy trzech linijkach po jednej stronie
    i dwóch po drugiej krótsza kolumna nie może pływać w pionie. Formatka ma to
    w komórkach tabeli, a podgląd operatu musi w CSS — przeglądarka domyślnie
    środkuje komórki tabeli w pionie."""
    from app.config import WEB

    style = (WEB / "static" / "style.css").read_text(encoding="utf-8")

    komorki = style.split('.sekcja-podglad table.wiersze')[1:]
    assert komorki, "podgląd wykazów zniknął z arkusza stylów"
    assert any("vertical-align: top" in blok.split("}")[0] for blok in komorki), \
        "komórki podglądu środkują w pionie — krótsza kolumna pływa jak kiedyś w PDF"


# --- pytania o usunięcie i stare karty po skasowaniu -------------------------

def test_pytanie_o_usuniecie_nie_rozrywa_sie_na_apostrofie(klient):
    """Apostrof w nazwie opisu wyłączał pytanie „Usunąć…?” — kasowało od razu.

    Jinja zamienia apostrof na `&#39;`, ale parser HTML odkodowuje go z powrotem, zanim
    przeglądarka skompiluje `onsubmit` — literał JS w apostrofach rozrywał się i `confirm`
    w ogóle nie był wołany. Treść pytania siedzi więc w atrybucie danych, który Jinja
    escapuje poprawnie, a JS czyta gotowy napis.
    """
    klient.post("/ustawienia/opisy", data={"nazwa": "Wg O'Briena", "opis": "<p>x</p>"},
                follow_redirects=False)
    _dodaj_operat(klient)
    klient.post("/generuj/spis_tresci_wzor", data={**FORMULARZ, "pole__nr_roboty": "GK.1'2026"},
                follow_redirects=False)
    wpis = db.dokumenty()[0]

    ustawienia = klient.get("/ustawienia").text
    lista = klient.get("/").text
    strona = klient.get(f"/dokument/{wpis['id']}").text

    assert 'data-pytanie="Usunąć opis „Wg O&#39;Briena”?' in ustawienia
    for tresc in (ustawienia, lista, strona):
        # statyczne pytania bez wstawianych danych („Wyczyścić zapamiętane obręby?”)
        # mogą zostać w literale — rozrywa go tylko tekst wpisany przez użytkownika
        assert "confirm('Usunąć" not in tresc, "treść pytania znów siedzi w literale JS"
        assert "confirm(this.dataset.pytanie)" in tresc


def test_pytanie_o_usuniecie_mowi_co_naprawde_zniknie(klient):
    """Operat w archiwum: kasuje się sam wpis, a pytanie straszyło katalogiem z mapami.

    Strona operatu w archiwum pokazywała też „Złóż PDF”, które lista już chowa —
    kliknięcie wyrzucało na listę z komunikatem. Oba ekrany mają mówić to samo.
    """
    import shutil

    _dodaj_operat(klient)
    klient.post("/generuj/spis_tresci_wzor", data=FORMULARZ, follow_redirects=False)
    wpis = db.dokumenty()[0]

    for tresc in (klient.get("/").text, klient.get(f"/dokument/{wpis['id']}").text):
        assert f"wraz z całym katalogiem {wpis['katalog']}" in tresc

    shutil.rmtree(klient.srodowisko.wyniki / wpis["katalog"])      # „przeniósł do archiwum”
    lista = klient.get("/").text
    strona = klient.get(f"/dokument/{wpis['id']}").text

    for tresc in (lista, strona):
        assert "z historii? Jego katalogu nie ma już w wyniki" in tresc
        assert "także z plikami" not in tresc, "pytanie straszy plikami, których nie skasuje"
    szczyt = strona.split('<div class="szczyt">')[1].split("<fieldset")[0]
    assert "Złóż PDF" not in szczyt, "strona operatu w archiwum oferuje składanie"
    assert "w archiwum" in szczyt


def test_powielenie_skasowanego_operatu_tlumaczy_dlaczego(klient):
    """„Powiel” ze starej karty po skasowaniu operatu otwierało pusty formularz bez słowa."""
    from urllib.parse import unquote

    _dodaj_operat(klient)
    klient.post("/generuj/spis_tresci_wzor", data=FORMULARZ, follow_redirects=False)
    wpis = db.dokumenty()[0]
    klient.post(f"/dokument/{wpis['id']}/usun", follow_redirects=False)

    odpowiedz = klient.get(f"/nowy/spis_tresci_wzor?kopiuj={wpis['id']}", follow_redirects=False)

    assert odpowiedz.status_code == 303
    assert "powielić" in unquote(odpowiedz.headers["location"])


def test_otwarcie_katalogu_skasowanego_wpisu_z_listy(klient, monkeypatch):
    """Komunikat o archiwum mówił „wpis w historii zostaje” nad listą, na której go nie ma."""
    from urllib.parse import unquote

    from app import operaty

    monkeypatch.setattr(operaty, "otworz_w_systemie", lambda _: None)
    _dodaj_operat(klient)
    klient.post("/generuj/spis_tresci_wzor", data=FORMULARZ, follow_redirects=False)
    wpis = db.dokumenty()[0]
    klient.post(f"/dokument/{wpis['id']}/usun", follow_redirects=False)

    odpowiedz = klient.post(f"/dokument/{wpis['id']}/otworz-katalog?powrot=lista",
                            follow_redirects=False)

    assert odpowiedz.headers["location"].startswith("/?blad=")
    assert "nie ma już w historii" in unquote(odpowiedz.headers["location"])
    assert "zostaje" not in unquote(odpowiedz.headers["location"])


def test_wiersz_spoza_historii_ma_otworz_katalog(klient, monkeypatch):
    """Pomoc obiecuje „Otwórz katalog” na liście — także przy operacie przywróconym z archiwum.

    Taki operat nie ma wpisu w bazie, więc przycisk idzie trasą po nazwie katalogu
    i, jak reszta listy, wraca na listę.
    """
    from app import operaty

    otwarte = []
    monkeypatch.setattr(operaty, "otworz_w_systemie", otwarte.append)
    katalog = klient.srodowisko.wyniki / "777.2026"
    katalog.mkdir(parents=True)
    (katalog / "operat.json").write_text(
        json.dumps({"nr_operatu": "777/2026", "nr_roboty": "G.99.2026",
                    "utworzono": "2026-07-20T08:00:00", "dane": {}}, ensure_ascii=False),
        encoding="utf-8")

    lista = klient.get("/").text
    assert 'action="/scal/777.2026/otworz-katalog?powrot=lista"' in lista

    odpowiedz = klient.post("/scal/777.2026/otworz-katalog?powrot=lista", follow_redirects=False)
    assert odpowiedz.headers["location"] == "/"
    assert [k.name for k in otwarte] == ["777.2026"]
    # ze strony składania — jak dotąd, z powrotem na nią
    assert klient.post("/scal/777.2026/otworz-katalog",
                       follow_redirects=False).headers["location"] == "/scal/777.2026"


def test_pomoc_opisuje_ekran_ktory_jest(klient):
    """Pomoc mówiła o „Pobierz PDF” (przycisk zniknął 31.07), „Wpisanych danych”,
    „danych stałych” i „pobieraniu pliku Worda” — rzeczach, których na ekranie nie ma."""
    pomoc = klient.get("/pomoc").text

    for nieaktualne in ("Pobierz PDF", "Wpisanymi danymi", "Popraw ten", "dane stałe",
                        "da się pobrać", "dwa różne przyciski"):
        assert nieaktualne not in pomoc, f"Pomoc opisuje ekran, którego nie ma: {nieaktualne!r}"
    assert "<strong>Usuń</strong>" in pomoc, "Pomoc milczy o czerwonym „Usuń”"
    assert "prawy dolny róg" in pomoc, "Pomoc nie mówi, że edytor da się powiększyć"
def test_numer_operatu_ma_kolor_akcentu_takze_po_kliknieciu(klient):
    """Numer operatu to link, więc przeglądarka malowała go domyślnym niebieskim,
    a po wejściu w operat przestawiała na fioletowy (`:visited`). Lista miała wtedy
    numery w dwóch kolorach naraz, a fiolet nie niósł żadnej informacji poza tym,
    że ktoś tam kiedyś zajrzał.

    Kolor wolno nałożyć **tylko na numer**. W tym samym wierszu stoją `a.glowny`
    („Złóż PDF”) i `a.wtorny` („Popraw”, „Powiel”) — to przyciski, nie odnośniki.
    Selektor obejmujący wszystkie linki wiersza przebija im kolor tekstu
    specyficznością i „Złóż PDF” wychodzi niebieskim napisem na niebieskim tle
    (zdarzyło się przy pisaniu tej zmiany).
    """
    korzen = Path(__file__).resolve().parent.parent

    _dodaj_operat(klient)
    klient.post("/generuj/spis_tresci_wzor", data=FORMULARZ, follow_redirects=False)

    tresc = klient.get("/").text
    css = (korzen / "app" / "web" / "static" / "style.css").read_text(encoding="utf-8")

    assert 'class="nr-operatu"' in tresc, "numer operatu stracił swoją klasę"
    assert ".nr-operatu, .nr-operatu:visited { color: var(--akcent); }" in css,         "numer musi trzymać kolor akcentu także jako odwiedzony link"
    assert "tbody.operat a" not in css,         "kolor nałożony na wszystkie linki wiersza zabiera przyciskom ich własny"

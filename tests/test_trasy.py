"""Strony i formularze — smoke testy przez TestClient.

Konwersja PDF jest tu podmieniona na atrapę: testy mają chodzić w sekundy, bez Worda
i bez LibreOffice'a. Sprawdzamy zachowanie aplikacji, nie jakość PDF-a.
"""
from __future__ import annotations

import json

from app import db, operaty

OPIS_OPERATU = {
    "nazwa": "Operat", "glowny": True, "licznik": "operat",
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
    _dodaj_operat(klient)
    klient.srodowisko.dodaj_szablon("sprawozdanie_wzor", ["{{ nr_roboty }}"],
                                    opis={"nazwa": "Sprawozdanie techniczne", "pola": []})
    tresc = klient.get("/").text
    assert "Operat" in tresc
    assert "Sprawozdanie techniczne" not in tresc


def test_nieznany_adres_daje_polska_strone_bledu(klient):
    odpowiedz = klient.get("/nie-ma-takiej-strony")
    assert odpowiedz.status_code == 404
    assert "Nie ma takiej strony" in odpowiedz.text
    assert "Not Found" not in odpowiedz.text


def test_bledny_identyfikator_nie_pokazuje_angielskiego_json(klient):
    """/dokument/abc zamiast /dokument/12 — brat ma zobaczyć polską stronę."""
    odpowiedz = klient.get("/dokument/abc")
    assert odpowiedz.status_code == 404
    assert "detail" not in odpowiedz.text
    assert "Nie ma takiej strony" in odpowiedz.text


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


def test_menu_nie_ma_juz_pozycji_zloz_pdf(klient):
    tresc = klient.get("/").text
    assert '<a href="/scal">' not in tresc


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

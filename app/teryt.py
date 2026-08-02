"""Jednostki podziału terytorialnego (TERYT) i obręby ewidencyjne.

Skąd biorą się dane:

* **województwa, powiaty, gminy** — plik `TERC_Urzedowy` z GUS. Jeden POST i mamy
  komplet dla całego kraju (16 / 380 / ~3960 pozycji, ok. 130 kB). Oficjalna usługa
  sieciowa GUS-u (TERYT ws1) wymagałaby rejestracji i hasła przysyłanego przez Urząd
  Statystyczny — dla użytkownika tego programu to dyskwalifikacja, więc pobieramy
  ten sam plik, który człowiek pobiera ze strony klikając „Pobierz”.
* **obręby ewidencyjne** — ULDK (GUGiK). Zapytanie `GetRegionById` z identyfikatorem
  *jednostki ewidencyjnej* zwraca od razu całą listę jej obrębów, więc to jedno
  zapytanie na gminę. Pobieramy je dopiero wtedy, gdy użytkownik wybierze gminę,
  i zapamiętujemy na zawsze — pobranie obrębów dla całej Polski z góry to prawie
  cztery tysiące zapytań i kilkanaście minut czekania przy pierwszym uruchomieniu.

Wszystko ląduje w SQLite, więc **po pierwszym pobraniu program działa bez internetu** —
to warunek konieczny, bo w terenie sieci nie ma.
"""
from __future__ import annotations

import csv
import html
import io
import re
import threading
import urllib.parse
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from . import db

# Strona GUS-u z „plikami pełnymi”. Nie ma tu zwykłego linku do pliku — pobieranie jest
# przyciskiem ASP.NET, więc trzeba wczytać stronę, wyjąć __VIEWSTATE i odesłać POST-em.
URL_TERC = ("https://eteryt.stat.gov.pl/eTeryt/rejestr_teryt/udostepnianie_danych/"
            "baza_teryt/uzytkownicy_indywidualni/pobieranie/pliki_pelne.aspx?contrast=default")
PRZYCISK_TERC = "ctl00$body$BTERCUrzedowyPobierz"

URL_ULDK = "https://uldk.gugik.gov.pl/"
LIMIT_CZASU = 60

# RODZ = 3 to gmina miejsko-wiejska: w ewidencji gruntów nie jest jednostką ewidencyjną,
# bo dzieli się na miasto (4) i obszar wiejski (5). Pokazywanie jej myliłoby użytkownika
# i dawało niepełną listę obrębów (ULDK zwraca dla niej tylko część obszaru wiejskiego).
RODZAJ_POMIJANY = "3"


class BladPobierania(RuntimeError):
    """Nie udało się pobrać danych — brak internetu albo źródło zmieniło stronę."""


# --- pobieranie --------------------------------------------------------------

def _pobierz_terc() -> bytes:
    """Zwraca zawartość pliku TERC_Urzedowy.zip prosto z GUS-u."""
    otwieracz = urllib.request.build_opener(urllib.request.HTTPCookieProcessor())
    try:
        strona = otwieracz.open(URL_TERC, timeout=LIMIT_CZASU).read().decode("utf-8", "replace")
    except Exception as blad:
        raise BladPobierania(
            "Nie udało się połączyć ze stroną GUS-u. Sprawdź, czy komputer ma internet."
        ) from blad

    def ukryte(nazwa: str) -> str:
        trafienie = re.search(rf'id="{nazwa}"[^>]*value="([^"]*)"', strona)
        return html.unescape(trafienie.group(1)) if trafienie else ""

    formularz = urllib.parse.urlencode({
        "__EVENTTARGET": PRZYCISK_TERC,
        "__EVENTARGUMENT": "",
        "__VIEWSTATE": ukryte("__VIEWSTATE"),
        "__VIEWSTATEGENERATOR": ukryte("__VIEWSTATEGENERATOR"),
        "__EVENTVALIDATION": ukryte("__EVENTVALIDATION"),
    }).encode()
    zadanie = urllib.request.Request(
        URL_TERC, data=formularz,
        headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with otwieracz.open(zadanie, timeout=LIMIT_CZASU) as odpowiedz:
            tresc = odpowiedz.read()
    except Exception as blad:
        raise BladPobierania("GUS nie oddał pliku z jednostkami TERYT.") from blad

    if tresc[:2] != b"PK":
        raise BladPobierania(
            "Zamiast pliku przyszła strona internetowa — GUS zmienił sposób pobierania. "
            "Program działa dalej na tym, co już ma; zgłoś to bratu."
        )
    return tresc


def _czytaj_terc(paczka: bytes) -> tuple[list[tuple], str]:
    """Rozpakowuje TERC i zwraca (wiersze do bazy, data stanu rejestru)."""
    with zipfile.ZipFile(io.BytesIO(paczka)) as archiwum:
        nazwy = [n for n in archiwum.namelist() if n.lower().endswith(".csv")]
        if not nazwy:
            raise BladPobierania("W paczce z GUS-u nie ma pliku CSV.")
        tekst = archiwum.read(nazwy[0]).decode("utf-8-sig")

    wiersze: list[tuple] = []
    stan_na = ""
    for pozycja in csv.DictReader(io.StringIO(tekst), delimiter=";"):
        woj, pow_, gmi = pozycja["WOJ"], pozycja["POW"], pozycja["GMI"]
        rodz, nazwa = pozycja["RODZ"], pozycja["NAZWA"].strip()
        stan_na = stan_na or pozycja.get("STAN_NA", "")

        if not pow_:
            # GUS zapisuje województwa wersalikami, a poprawnie pisze się je małą literą
            wiersze.append((woj, "wojewodztwo", None, nazwa.lower(), ""))
        elif not gmi:
            wiersze.append((woj + pow_, "powiat", woj, nazwa, pozycja["NAZWA_DOD"].strip()))
        elif rodz != RODZAJ_POMIJANY:
            wiersze.append((f"{woj}{pow_}{gmi}_{rodz}", "gmina", woj + pow_,
                            nazwa, pozycja["NAZWA_DOD"].strip()))
    if not wiersze:
        raise BladPobierania("Plik z GUS-u był pusty.")
    return wiersze, stan_na


# Stany sprawdzenia działki. „nieznane” to **nie** to samo co „brak”: usługa mogła nie
# odpowiedzieć, a wtedy nie wolno sugerować, że numer jest zły.
DZIALKA_JEST = "jest"
DZIALKA_BRAK = "brak"
DZIALKA_NIEZNANE = "nieznane"


def sprawdz_dzialke(obreb: str, numer: str, limit_czasu: int = 8) -> str:
    """Czy ULDK zna działkę `numer` w obrębie `obreb`.

    Identyfikator działki to `<obręb>.<numer>`, np. `120102_2.0001.123/4`.
    Odpowiedź ULDK zaczyna się od kodu w pierwszej linii: `0` = znaleziona,
    `-1` = brak wyników. Przy braku ULDK dokłada jeszcze swój wewnętrzny komunikat
    o „błędnym formacie odpowiedzi XML” — to jego bałagan, a nie nasz błąd, więc
    patrzymy wyłącznie na kod.

    Krótszy limit czasu niż przy pobieraniu TERC: to jest podpowiedź w formularzu,
    a nie operacja, na którą ktoś świadomie czeka.
    """
    obreb, numer = obreb.strip(), numer.strip()
    if not obreb or not numer:
        return DZIALKA_NIEZNANE
    adres = URL_ULDK + "?" + urllib.parse.urlencode(
        {"request": "GetParcelById", "id": f"{obreb}.{numer}", "result": "teryt"})
    try:
        with urllib.request.urlopen(adres, timeout=limit_czasu) as odpowiedz:
            tresc = odpowiedz.read().decode("utf-8", "replace")
    except Exception:
        return DZIALKA_NIEZNANE          # brak sieci, ULDK nie odpowiada — nie zgadujemy

    pierwsza = (tresc.splitlines() or [""])[0].strip()
    if pierwsza.startswith("0"):
        return DZIALKA_JEST
    if pierwsza.startswith("-1"):
        return DZIALKA_BRAK
    return DZIALKA_NIEZNANE


def _pobierz_obreby(gmina: str) -> list[tuple[str, str]]:
    """Lista (identyfikator, nazwa) obrębów jednej jednostki ewidencyjnej."""
    adres = URL_ULDK + "?" + urllib.parse.urlencode(
        {"request": "GetRegionById", "id": gmina, "result": "teryt,nazwa"})
    try:
        with urllib.request.urlopen(adres, timeout=LIMIT_CZASU) as odpowiedz:
            tresc = odpowiedz.read().decode("utf-8", "replace")
    except Exception as blad:
        raise BladPobierania(
            "Nie udało się pobrać obrębów z serwisu GUGiK. Sprawdź, czy jest internet."
        ) from blad

    linie = [w.strip() for w in tresc.splitlines() if w.strip()]
    if not linie or not linie[0].startswith("0"):
        return []                       # „-1 brak wyników” — gmina bez obrębów w ULDK
    obreby = []
    for linia in linie[1:]:
        if "|" in linia:
            identyfikator, _, nazwa = linia.partition("|")
            obreby.append((identyfikator.strip(), nazwa.strip()))
    return obreby


# --- zapis i odczyt ----------------------------------------------------------

def aktualizuj_jednostki() -> tuple[int, str]:
    """Pobiera TERC z GUS-u i podmienia tabelę jednostek. Zwraca (ile, stan_na)."""
    wiersze, stan_na = _czytaj_terc(_pobierz_terc())
    with db.polacz() as con:
        con.execute("DELETE FROM teryt_jednostki")
        con.executemany(
            "INSERT INTO teryt_jednostki (id, poziom, rodzic, nazwa, rodzaj)"
            " VALUES (?, ?, ?, ?, ?)", wiersze)
        con.execute(
            "INSERT INTO teryt_stan (klucz, wartosc) VALUES ('jednostki_pobrano', ?)"
            " ON CONFLICT(klucz) DO UPDATE SET wartosc = excluded.wartosc",
            (datetime.now().isoformat(timespec="seconds"),))
        con.execute(
            "INSERT INTO teryt_stan (klucz, wartosc) VALUES ('jednostki_stan_na', ?)"
            " ON CONFLICT(klucz) DO UPDATE SET wartosc = excluded.wartosc", (stan_na,))
    return len(wiersze), stan_na


def obreby(gmina: str, wymus: bool = False) -> list[dict[str, str]]:
    """Obręby jednostki ewidencyjnej — z bazy, a gdy ich tam nie ma, z GUGiK-u."""
    if not wymus:
        with db.polacz() as con:
            zapisane = con.execute(
                "SELECT id, nazwa FROM teryt_obreby WHERE gmina = ? ORDER BY nazwa",
                (gmina,)).fetchall()
        if zapisane:
            return [{"id": w["id"], "nazwa": w["nazwa"]} for w in zapisane]

    pobrane = _pobierz_obreby(gmina)
    if pobrane:
        with db.polacz() as con:
            con.execute("DELETE FROM teryt_obreby WHERE gmina = ?", (gmina,))
            con.executemany(
                "INSERT OR REPLACE INTO teryt_obreby (id, gmina, nazwa) VALUES (?, ?, ?)",
                [(identyfikator, gmina, nazwa) for identyfikator, nazwa in pobrane])
    return [{"id": i, "nazwa": n} for i, n in sorted(pobrane, key=lambda p: p[1])]


def potomkowie(rodzic: str | None, poziom: str) -> list[dict[str, str]]:
    """Województwa (rodzic=None), powiaty danego województwa albo gminy powiatu."""
    with db.polacz() as con:
        if rodzic is None:
            wiersze = con.execute(
                "SELECT id, nazwa, rodzaj FROM teryt_jednostki WHERE poziom = ?"
                " ORDER BY nazwa", (poziom,)).fetchall()
        else:
            wiersze = con.execute(
                "SELECT id, nazwa, rodzaj FROM teryt_jednostki"
                " WHERE poziom = ? AND rodzic = ? ORDER BY nazwa", (poziom, rodzic)).fetchall()
    return [{"id": w["id"], "nazwa": w["nazwa"], "rodzaj": w["rodzaj"] or ""} for w in wiersze]


def jednostka(identyfikator: str) -> dict[str, str] | None:
    if not identyfikator:
        return None
    with db.polacz() as con:
        wiersz = con.execute(
            "SELECT id, poziom, rodzic, nazwa, rodzaj FROM teryt_jednostki WHERE id = ?",
            (identyfikator,)).fetchone()
    return dict(wiersz) if wiersz else None


def obreb(identyfikator: str) -> dict[str, str] | None:
    if not identyfikator:
        return None
    with db.polacz() as con:
        wiersz = con.execute(
            "SELECT id, gmina, nazwa FROM teryt_obreby WHERE id = ?",
            (identyfikator,)).fetchone()
    return dict(wiersz) if wiersz else None


def stan() -> dict[str, str | int]:
    """Co program ma u siebie — do pokazania w Ustawieniach."""
    with db.polacz() as con:
        policz = lambda zapytanie: int(con.execute(zapytanie).fetchone()[0])  # noqa: E731
        opis = {w["klucz"]: w["wartosc"] for w in con.execute("SELECT * FROM teryt_stan")}
        return {
            "wojewodztw": policz("SELECT COUNT(*) FROM teryt_jednostki"
                                 " WHERE poziom = 'wojewodztwo'"),
            "powiatow": policz("SELECT COUNT(*) FROM teryt_jednostki WHERE poziom = 'powiat'"),
            "gmin": policz("SELECT COUNT(*) FROM teryt_jednostki WHERE poziom = 'gmina'"),
            "obrebow": policz("SELECT COUNT(*) FROM teryt_obreby"),
            "gmin_z_obrebami": policz("SELECT COUNT(DISTINCT gmina) FROM teryt_obreby"),
            "pobrano": opis.get("jednostki_pobrano", ""),
            "stan_na": opis.get("jednostki_stan_na", ""),
        }


def pusto() -> bool:
    return int(stan()["wojewodztw"]) == 0


# --- pobieranie obrębów dla całej Polski -------------------------------------
#
# Ponad trzy tysiące zapytań, więc leci to w tle, z paskiem postępu i możliwością
# przerwania. Zapisuje wątek główny tej roboty, a nie wątki pobierające — SQLite
# nie lubi kilku piszących naraz, a i tak wąskim gardłem jest sieć.

ROWNOLEGLE = 4                 # tyle zapytań naraz; więcej nie przyspiesza, a obciąża GUGiK

_postep = {"trwa": False, "zrobione": 0, "wszystkich": 0, "pobranych": 0,
           "gmina": "", "blad": "", "przerwane": False, "koniec": ""}
_zamek = threading.Lock()
_stop = threading.Event()


def postep() -> dict:
    with _zamek:
        return dict(_postep)


def przerwij_pobieranie() -> None:
    _stop.set()


def _gminy_do_pobrania(od_nowa: bool) -> list[str]:
    with db.polacz() as con:
        if od_nowa:
            wiersze = con.execute(
                "SELECT id FROM teryt_jednostki WHERE poziom = 'gmina' ORDER BY id").fetchall()
        else:
            # pomijamy te, które już mamy — dzięki temu przerwane pobieranie da się wznowić
            wiersze = con.execute(
                "SELECT id FROM teryt_jednostki WHERE poziom = 'gmina'"
                " AND id NOT IN (SELECT DISTINCT gmina FROM teryt_obreby) ORDER BY id").fetchall()
    return [w["id"] for w in wiersze]


def pobierz_wszystkie_obreby(od_nowa: bool = False) -> None:
    """Chodzi w osobnym wątku; stan czyta przeglądarka przez `postep()`."""
    _stop.clear()
    gminy = _gminy_do_pobrania(od_nowa)
    with _zamek:
        _postep.update({"trwa": True, "wszystkich": len(gminy)})

    def zadanie(gmina: str):
        if _stop.is_set():
            return gmina, None
        try:
            return gmina, _pobierz_obreby(gmina)
        except BladPobierania:
            return gmina, None

    przerwane = False
    try:
        with ThreadPoolExecutor(max_workers=ROWNOLEGLE) as pula:
            for gmina, obreby in pula.map(zadanie, gminy):
                # Po przerwaniu wychodzimy z pętli, zamiast doliczać pominięte gminy —
                # inaczej pasek dobiegłby do końca i wyglądało to jak udane pobranie.
                if _stop.is_set():
                    przerwane = True
                    break
                if obreby:
                    with db.polacz() as con:
                        con.execute("DELETE FROM teryt_obreby WHERE gmina = ?", (gmina,))
                        con.executemany(
                            "INSERT OR REPLACE INTO teryt_obreby (id, gmina, nazwa)"
                            " VALUES (?, ?, ?)",
                            [(i, gmina, n) for i, n in obreby])
                with _zamek:
                    _postep["zrobione"] += 1
                    _postep["gmina"] = gmina
                    if obreby:
                        _postep["pobranych"] += len(obreby)
    except Exception as blad:                     # sieć potrafi paść w połowie
        with _zamek:
            _postep["blad"] = f"Pobieranie przerwał błąd: {blad}"
    finally:
        with _zamek:
            _postep["trwa"] = False
            _postep["przerwane"] = przerwane
            _postep["koniec"] = datetime.now().isoformat(timespec="seconds")
        _stop.clear()


def uruchom_pobieranie_obrebow(od_nowa: bool = False) -> bool:
    """False = już trwa, drugiego nie startujemy.

    Znacznik „trwa” stawiamy **tutaj**, pod zamkiem, a nie w wątku roboczym: między
    sprawdzeniem a startem wątku mieści się drugie kliknięcie i poleciałyby dwa
    pobierania naraz, dopisując się do tego samego licznika postępu.
    """
    with _zamek:
        if _postep["trwa"]:
            return False
        _postep.update({"trwa": True, "zrobione": 0, "wszystkich": 0, "pobranych": 0,
                        "gmina": "", "blad": "", "przerwane": False, "koniec": ""})
    threading.Thread(target=pobierz_wszystkie_obreby, args=(od_nowa,), daemon=True).start()
    return True

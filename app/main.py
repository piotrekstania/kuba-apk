"""Aplikacja webowa: formularz -> gotowy .docx / .pdf.

Chodzi lokalnie na komputerze użytkownika (127.0.0.1), więc nie ma logowania
ani multitenancy — to celowe uproszczenie.
"""
from __future__ import annotations

import json
import shutil
import threading
import traceback
from collections import defaultdict
from contextlib import asynccontextmanager
from datetime import date, datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import (FileResponse, HTMLResponse, JSONResponse,
                               RedirectResponse, Response)
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as BladHTTP

from . import aktualizacja, db, generator, miniatury, operaty, pdf, szablony, teryt
from .config import DANE, WEB, WYNIKI


def _pierwsze_pobranie_teryt() -> None:
    """Przy pierwszym uruchomieniu dociąga listę gmin — w tle i po cichu.

    W osobnym wątku, bo start programu nie może czekać na GUS, a brak internetu
    (np. w terenie) nie może go zatrzymać. Gdy się nie uda, w Ustawieniach jest
    przycisk do pobrania ręcznie.
    """
    try:
        if teryt.pusto():
            teryt.aktualizuj_jednostki()
    except Exception:
        pass


@asynccontextmanager
async def cykl_zycia(_: FastAPI):
    db.init()
    threading.Thread(target=_pierwsze_pobranie_teryt, daemon=True).start()
    yield


app = FastAPI(title="Generator operatów", lifespan=cykl_zycia)
app.mount("/static", StaticFiles(directory=WEB / "static"), name="static")
widoki = Jinja2Templates(directory=str(WEB / "templates"))

DZIENNIK_BLEDOW = DANE / "bledy.log"


def _widok(request: Request, nazwa: str, **kontekst: Any) -> HTMLResponse:
    kontekst.setdefault("konwerter", pdf.dostepny_konwerter())
    kontekst.setdefault("wersja", aktualizacja.wersja_lokalna()[0])
    return widoki.TemplateResponse(request, nazwa, kontekst)


# --- błędy: użytkownik nie jest programistą i nie może zobaczyć angielskiego 500 ----

def zapisz_blad(request: Request, wyjatek: BaseException) -> str:
    """Dopisuje ślad wyjątku do dane/bledy.log i zwraca go do pokazania na stronie.

    Bez tego jedynym śladem po awarii u brata jest okno konsoli, które zamyka razem
    z programem — a wtedy zostaje tylko „nie działa”.
    """
    slad = "".join(traceback.format_exception(wyjatek))
    try:
        with open(DZIENNIK_BLEDOW, "a", encoding="utf-8") as dziennik:
            dziennik.write(f"\n=== {datetime.now():%Y-%m-%d %H:%M:%S} "
                           f"{request.method} {request.url.path} ===\n{slad}")
    except OSError:
        pass                                   # brak miejsca na dysku nie może zjeść komunikatu
    return slad


def strona_bledu(request: Request, naglowek: str, wyjasnienie: str,
                 szczegoly: str = "", status: int = 500) -> HTMLResponse:
    try:
        return widoki.TemplateResponse(
            request, "blad.html",
            {"naglowek": naglowek, "wyjasnienie": wyjasnienie, "szczegoly": szczegoly,
             "konwerter": pdf.dostepny_konwerter(),
             "wersja": aktualizacja.wersja_lokalna()[0]},
            status_code=status,
        )
    except Exception:
        # Sama strona błędu też potrafi paść (np. po nieudanej aktualizacji brakuje
        # pliku szablonu) — wtedy zostaje goły HTML, ale nadal po polsku.
        return HTMLResponse(f"<h1>{naglowek}</h1><p>{wyjasnienie}</p>", status_code=status)


@app.exception_handler(Exception)
def blad_nieprzewidziany(request: Request, wyjatek: Exception) -> HTMLResponse:
    return strona_bledu(
        request,
        "Coś poszło nie tak",
        "Program nie dokończył tej czynności. Twoje dokumenty, szablony i numeracja "
        "są nietknięte — nic nie zostało skasowane. Spróbuj jeszcze raz; jeśli błąd wraca, "
        "rozwiń szczegóły poniżej i pokaż je bratu.",
        zapisz_blad(request, wyjatek),
    )


@app.exception_handler(BladHTTP)
def blad_adresu(request: Request, wyjatek: BladHTTP) -> HTMLResponse:
    if wyjatek.status_code == 404:
        return strona_bledu(
            request, "Nie ma takiej strony",
            "Ten adres nie istnieje. Mógł się zmienić po aktualizacji programu — "
            "wróć na stronę główną i zacznij stamtąd.",
            status=404,
        )
    return strona_bledu(
        request, "Nie udało się otworzyć tej strony",
        f"Program odpowiedział kodem {wyjatek.status_code}. Wróć na stronę główną "
        "i spróbuj jeszcze raz.",
        status=wyjatek.status_code,
    )


@app.exception_handler(RequestValidationError)
def blad_adresu_z_danymi(request: Request, wyjatek: RequestValidationError) -> HTMLResponse:
    """Np. /dokument/abc zamiast /dokument/12 — inaczej poleciałby angielski JSON."""
    return strona_bledu(
        request, "Nie ma takiej strony",
        "Adres jest niepoprawny — wróć na stronę główną i wybierz dokument z listy.",
        status=404,
    )


# --- parsowanie formularza ---------------------------------------------------

def odczytaj_dane(formularz, szablon: szablony.Szablon) -> dict[str, Any]:
    """Zamienia płaski formularz HTML na słownik z listami dla tabel.

    pole__nr_roboty            -> {"nr_roboty": "..."}
    tab__wykaz__0__nr_punktu   -> {"wykaz": [{"nr_punktu": "..."}, ...]}
    """
    proste: dict[str, Any] = {}
    tabele: dict[str, dict[int, dict[str, str]]] = defaultdict(lambda: defaultdict(dict))

    for klucz, wartosc in formularz.multi_items():
        if klucz.startswith("pole__"):
            proste[klucz[len("pole__"):]] = wartosc.strip() if isinstance(wartosc, str) else wartosc
        elif klucz.startswith("tab__"):
            czesci = klucz.split("__")
            if len(czesci) == 4:
                _, nazwa, indeks, kolumna = czesci
                if indeks.isdigit():
                    tabele[nazwa][int(indeks)][kolumna] = (wartosc or "").strip()

    for nazwa, wiersze in tabele.items():
        uporzadkowane = [wiersze[i] for i in sorted(wiersze)]
        # wiersze całkiem puste (użytkownik dodał i nie wypełnił) pomijamy
        proste[nazwa] = [w for w in uporzadkowane if any(v for v in w.values())]

    for pole in szablon.pola:
        if pole.typ == "checkbox":
            proste[pole.klucz] = pole.klucz in {k[len("pole__"):] for k in formularz
                                                if k.startswith("pole__")}
        elif pole.typ == "tabela":
            proste.setdefault(pole.klucz, [])
        elif pole.typ == "teryt":
            # cztery listy rozwijane przychodzą jako pole__polozenie__gmina itd.;
            # scalamy je w jeden słownik identyfikatorów, żeby walidacja „wymagane”
            # i zapis do historii widziały to jako jedno pole
            czesci = {poziom: proste.pop(f"{pole.klucz}__{poziom}", "")
                      for poziom in ("wojewodztwo", "powiat", "gmina", "obreb")}
            proste[pole.klucz] = czesci if any(czesci.values()) else {}
    return proste


# --- strony ------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def strona_glowna(request: Request):
    return _widok(request, "index.html",
                  szablony=szablony.lista_szablonow(),
                  dokumenty=db.dokumenty(limit=15),
                  co_nowego=aktualizacja.co_nowego())   # pokazuje się raz, po aktualizacji


def _szablon_albo_blad(request: Request, identyfikator: str):
    """Zwraca (szablon, None) albo (None, gotowa odpowiedź).

    Szablony edytuje sam użytkownik w Wordzie, więc uszkodzony albo źle otagowany
    plik jest normalną sytuacją — ma dać zrozumiały komunikat, a nie 500.
    """
    try:
        szablon = szablony.szablon_po_id(identyfikator)
    except Exception as blad:
        return None, strona_bledu(
            request, "Nie udało się otworzyć szablonu",
            f"Pliku „{identyfikator}.docx” z katalogu szablony nie da się przeczytać. "
            "Najczęściej znaczy to, że jest otwarty w Wordzie z niezapisanymi zmianami "
            "albo ma literówkę w znaczniku {{ }} lub {% ... %}. Zamknij go w Wordzie "
            "i odśwież tę stronę.",
            zapisz_blad(request, blad),
        )
    if szablon is None:
        return None, RedirectResponse("/", status_code=303)
    return szablon, None


@app.get("/nowy/{identyfikator}", response_class=HTMLResponse)
def formularz(request: Request, identyfikator: str, kopiuj: int | None = None):
    szablon, odpowiedz = _szablon_albo_blad(request, identyfikator)
    if odpowiedz is not None:
        return odpowiedz

    # wartości startowe; przy typie auto_numer "domyslnie" to wzorzec numeru, nie wartość
    wartosci: dict[str, Any] = {}
    for pole in szablon.pola:
        if not pole.domyslnie or pole.typ == "auto_numer":
            continue
        wartosci[pole.klucz] = (date.today().isoformat()
                                if pole.typ == "date" and pole.domyslnie == "dzisiaj"
                                else pole.domyslnie)
    if kopiuj:                                   # „zrób podobny jak poprzedni”
        poprzedni = db.dokument(kopiuj)
        if poprzedni:
            wartosci.update(json.loads(poprzedni["dane_json"]))

    podglad = None
    for pole in szablon.pola:
        if pole.typ == "auto_numer":
            numer = db.podglad_numeru(szablon.licznik or szablon.id, date.today().year)
            wzor = pole.domyslnie or "{numer}/{rok}"
            podglad = wzor.format(numer=numer, numer3=f"{numer:03d}", rok=date.today().year)

    return _widok(request, "formularz.html", szablon=szablon, wartosci=wartosci,
                  podglad_numeru=podglad, dzisiaj=date.today().isoformat())


@app.post("/generuj/{identyfikator}")
async def generuj(request: Request, identyfikator: str):
    szablon, odpowiedz = _szablon_albo_blad(request, identyfikator)
    if odpowiedz is not None:
        return odpowiedz

    formularz_danych = await request.form()
    dane = odczytaj_dane(formularz_danych, szablon)

    brakujace = [p.etykieta for p in szablon.pola
                 if p.wymagane and p.zrodlo != "ustawienia" and not dane.get(p.klucz)]
    if brakujace:
        return _widok(request, "formularz.html", szablon=szablon, wartosci=dane,
                      blad="Uzupełnij wymagane pola: " + ", ".join(brakujace),
                      dzisiaj=date.today().isoformat())

    try:
        plik, kontekst, ostrzezenia = generator.generuj(szablon, dane, db.wczytaj_ustawienia())
    except Exception as blad:
        # Wracamy na formularz z kompletem wpisanych danych — utrata wykazu współrzędnych
        # przez literówkę w szablonie byłaby gorsza niż sam błąd.
        zapisz_blad(request, blad)
        return _widok(request, "formularz.html", szablon=szablon, wartosci=dane,
                      blad=f"Nie udało się wypełnić szablonu „{szablon.nazwa}”. Zwykle "
                           "znaczy to, że w pliku .docx jest literówka w znaczniku "
                           "{{ }} albo {% ... %}. Twoje dane zostały tutaj — popraw "
                           f"szablon w Wordzie i kliknij ponownie. Szczegóły: {blad}",
                      dzisiaj=date.today().isoformat())

    katalog = plik.parent
    tytul = kontekst.get("nr_roboty") or katalog.name
    dokument_id = db.zapisz_dokument(
        szablon.id, str(tytul), f"{katalog.name}/{plik.name}", dane, katalog.name)
    adres = f"/dokument/{dokument_id}"
    if ostrzezenia:
        adres += "?blad=" + quote(" ".join(ostrzezenia))
    return RedirectResponse(adres, status_code=303)


@app.get("/dokument/{dokument_id}", response_class=HTMLResponse)
def dokument(request: Request, dokument_id: int, blad: str | None = None):
    wiersz = db.dokument(dokument_id)
    if wiersz is None:
        return RedirectResponse("/", status_code=303)
    return _widok(request, "dokument.html", dokument=wiersz,
                  dane=json.loads(wiersz["dane_json"]), blad=blad)


@app.get("/pobierz/{dokument_id}/docx")
def pobierz_docx(dokument_id: int):
    wiersz = db.dokument(dokument_id)
    if wiersz is None or not (WYNIKI / wiersz["plik_docx"]).exists():
        return RedirectResponse("/", status_code=303)
    plik = WYNIKI / wiersz["plik_docx"]
    return FileResponse(plik, filename=plik.name,
                        media_type="application/vnd.openxmlformats-officedocument"
                                   ".wordprocessingml.document")


@app.get("/pobierz/{dokument_id}/pdf")
def pobierz_pdf(request: Request, dokument_id: int):
    wiersz = db.dokument(dokument_id)
    if wiersz is None or not (WYNIKI / wiersz["plik_docx"]).exists():
        return RedirectResponse("/", status_code=303)
    zrodlo = WYNIKI / wiersz["plik_docx"]
    try:
        # Konwersja ląduje poza katalogiem operatu (dane/podglad/), a nie obok .docx —
        # inaczej spis treści pojawiłby się w sklejaniu drugi raz, jako osobny PDF.
        cel = operaty.jako_pdf(zrodlo)
    except pdf.BrakKonwertera as blad:
        return RedirectResponse(f"/dokument/{dokument_id}?blad={quote(str(blad))}",
                                status_code=303)
    except Exception as blad:
        # Word potrafi wywalić się na sto sposobów (aktywacja, uszkodzony profil,
        # otwarte okno dialogowe) — dokument .docx nadal da się pobrać.
        zapisz_blad(request, blad)
        komunikat = ("Nie udało się zrobić PDF-a z tego dokumentu. Plik Worda (.docx) "
                     "jest gotowy i możesz go pobrać poniżej. Szczegóły zapisały się "
                     "w dane\\bledy.log.")
        return RedirectResponse(f"/dokument/{dokument_id}?blad={quote(komunikat)}",
                                status_code=303)
    return FileResponse(cel, filename=cel.name, media_type="application/pdf")


@app.post("/dokument/{dokument_id}/usun")
def usun(dokument_id: int):
    """Kasuje operat razem z katalogiem — czyli także z plikami dołożonymi ręcznie.

    Strona pyta o potwierdzenie, podając nazwę katalogu i liczbę plików w środku,
    żeby nikt nie skasował map i skanów w ciemno.
    """
    wiersz = db.dokument(dokument_id)
    if wiersz:
        katalog = operaty.katalog_po_nazwie(wiersz["katalog"] or "")
        if katalog is not None:
            operaty.usun_podglady(katalog)
            shutil.rmtree(katalog, ignore_errors=True)
        else:
            for nazwa in (wiersz["plik_docx"], wiersz["plik_pdf"]):
                if nazwa:
                    (WYNIKI / nazwa).unlink(missing_ok=True)
        db.usun_dokument(dokument_id)
    return RedirectResponse("/", status_code=303)


# --- łączenie PDF ------------------------------------------------------------
#
# Sklejamy zawartość **katalogu operatu**, a nie pliki wybierane z dysku: brat wkłada
# tam swoje mapy i szkice zwykłym Eksploratorem, więc program ma tylko pokazać, co
# w folderze leży, pozwolić ustawić kolejność myszą i obrócić to, co przyszło bokiem.

@app.get("/scal", response_class=HTMLResponse)
def scal_lista(request: Request, komunikat: str | None = None, blad: str | None = None):
    return _widok(request, "scal.html", operaty=operaty.lista(),
                  komunikat=komunikat, blad=blad)


@app.get("/scal/{nazwa}", response_class=HTMLResponse)
def scal_katalog(request: Request, nazwa: str, blad: str | None = None):
    katalog = operaty.katalog_po_nazwie(nazwa)
    if katalog is None:
        return RedirectResponse("/scal", status_code=303)
    # liczby stron nie liczymy: dla plików Worda wymagałaby konwersji całej listy,
    # a miniatury i tak dociągają się leniwie, dopiero gdy przeglądarka o nie poprosi
    pozycje = [{"nazwa": p.name, "word": p.suffix.lower() != ".pdf"}
               for p in operaty.pliki(katalog)]
    return _widok(request, "scal_katalog.html", katalog=katalog.name,
                  opis=operaty.opis(katalog), pozycje=pozycje,
                  wynik=operaty.nazwa_wyniku(katalog), blad=blad)


@app.get("/miniatura/{nazwa}/{plik}")
def miniatura(request: Request, nazwa: str, plik: str, obrot: int = 0):
    """PNG pierwszej strony — dokumenty Worda są po drodze zamieniane na PDF."""
    katalog = operaty.katalog_po_nazwie(nazwa)
    if katalog is None:
        return RedirectResponse("/scal", status_code=303)
    zrodlo = katalog / Path(plik).name            # sama nazwa, żeby nie wyjść z katalogu
    if not zrodlo.is_file():
        return RedirectResponse("/scal", status_code=303)
    try:
        obrazek = miniatury.miniatura(operaty.jako_pdf(zrodlo), obrot)
    except pdf.BrakKonwertera:
        return Response(status_code=204)          # brak konwertera: strona pokaże zastępnik
    except Exception as blad:
        zapisz_blad(request, blad)
        return Response(status_code=204)
    return Response(obrazek, media_type="image/png",
                    headers={"Cache-Control": "no-store"})


@app.post("/scal/{nazwa}")
async def scal_wykonaj(request: Request, nazwa: str):
    katalog = operaty.katalog_po_nazwie(nazwa)
    if katalog is None:
        return RedirectResponse("/scal", status_code=303)

    formularz_danych = await request.form()
    kolejnosc = formularz_danych.getlist("plik")          # nazwy w kolejności ustawionej myszą
    dostepne = {p.name: p for p in operaty.pliki(katalog)}

    def niepowodzenie(tresc: str):
        return RedirectResponse(f"/scal/{quote(nazwa)}?blad={quote(tresc)}", status_code=303)

    wybrane: list[Path] = []
    obroty: dict[Path, int] = {}
    etykiety: dict[Path, str] = {}
    for pozycja in kolejnosc:
        zrodlo = dostepne.get(pozycja)
        if zrodlo is None:
            continue
        try:
            gotowy = operaty.jako_pdf(zrodlo)
        except pdf.BrakKonwertera as blad:
            return niepowodzenie(str(blad))
        except Exception as blad:
            zapisz_blad(request, blad)
            return niepowodzenie(
                f"Nie udało się zamienić pliku „{zrodlo.name}” na PDF. "
                "Otwórz go i sprawdź, czy wyświetla się normalnie.")
        wybrane.append(gotowy)
        etykiety[gotowy] = zrodlo.name
        try:
            obroty[gotowy] = int(formularz_danych.get(f"obrot__{pozycja}") or 0)
        except ValueError:
            obroty[gotowy] = 0

    if not wybrane:
        return niepowodzenie("Nie wybrano żadnych plików do połączenia.")

    wynik = katalog / operaty.nazwa_wyniku(katalog)
    try:
        pdf.polacz_pdf(wybrane, wynik, etykiety, obroty)
    except pdf.BladPliku as blad:
        return niepowodzenie(str(blad))
    return FileResponse(wynik, filename=wynik.name, media_type="application/pdf")


# --- ustawienia --------------------------------------------------------------
#
# Dane stałe geodety (nazwisko, uprawnienia, firma) miały tu swój formularz, ale brat
# woli mieć je wpisane na sztywno w swoich szablonach Worda — i ma rację, bo to i tak
# jego pieczątka, a nie coś, co zmienia się między robotami. Ustawienia zostają dla
# rzeczy, które program musi trzymać u siebie: danych TERYT.

@app.get("/ustawienia", response_class=HTMLResponse)
def ustawienia_formularz(request: Request, komunikat: str | None = None,
                         blad: str | None = None):
    return _widok(request, "ustawienia.html", komunikat=komunikat, blad=blad,
                  teryt_stan=teryt.stan())


# --- TERYT: listy do pól kaskadowych i pobieranie danych ---------------------

@app.get("/teryt/lista")
def teryt_lista(poziom: str, rodzic: str | None = None):
    """Zasila listy rozwijane w formularzu. Zwraca JSON, bo woła to JavaScript."""
    if poziom not in ("wojewodztwo", "powiat", "gmina"):
        return JSONResponse({"pozycje": [], "blad": "Nieznany poziom podziału."},
                            status_code=400)
    return JSONResponse({"pozycje": teryt.potomkowie(rodzic or None, poziom)})


@app.get("/teryt/obreby")
def teryt_obreby(gmina: str):
    """Obręby jednostki ewidencyjnej — z bazy albo, przy pierwszym razie, z GUGiK-u."""
    try:
        return JSONResponse({"pozycje": teryt.obreby(gmina)})
    except teryt.BladPobierania as blad:
        return JSONResponse({"pozycje": [], "blad": str(blad)})


@app.post("/teryt/aktualizuj")
def teryt_aktualizuj(request: Request):
    try:
        ile, stan_na = teryt.aktualizuj_jednostki()
        komunikat = (f"Pobrano listę jednostek TERYT: {ile} pozycji "
                     f"(rejestr GUS na dzień {stan_na}).")
    except teryt.BladPobierania as blad:
        return RedirectResponse(f"/ustawienia?blad={quote(str(blad))}", status_code=303)
    except Exception as blad:
        zapisz_blad(request, blad)
        return RedirectResponse(
            "/ustawienia?blad=" + quote("Nie udało się pobrać listy TERYT. "
                                        "Szczegóły zapisały się w dane\\bledy.log."),
            status_code=303)
    return RedirectResponse(f"/ustawienia?komunikat={quote(komunikat)}", status_code=303)


@app.post("/teryt/obreby-wszystkie")
def teryt_obreby_wszystkie(od_nowa: bool = False):
    """Startuje pobieranie obrębów dla całej Polski — trwa kilka minut, więc w tle."""
    return JSONResponse({"ruszylo": teryt.uruchom_pobieranie_obrebow(od_nowa),
                         "postep": teryt.postep()})


@app.get("/teryt/postep")
def teryt_postep():
    return JSONResponse(teryt.postep())


@app.post("/teryt/przerwij")
def teryt_przerwij():
    teryt.przerwij_pobieranie()
    return JSONResponse({"postep": teryt.postep()})


@app.post("/teryt/zapomnij-obreby")
def teryt_zapomnij_obreby():
    """Kasuje zapamiętane obręby — pobiorą się na nowo przy następnym wyborze gminy."""
    with db.polacz() as con:
        con.execute("DELETE FROM teryt_obreby")
    return RedirectResponse(
        "/ustawienia?komunikat=" + quote("Zapamiętane obręby wyczyszczone — pobiorą się "
                                         "na nowo, gdy wybierzesz gminę."),
        status_code=303)


@app.get("/pomoc", response_class=HTMLResponse)
def pomoc(request: Request):
    return _widok(request, "pomoc.html")

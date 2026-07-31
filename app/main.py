"""Aplikacja webowa: formularz -> gotowy .docx / .pdf.

Chodzi lokalnie na komputerze użytkownika (127.0.0.1), więc nie ma logowania
ani multitenancy — to celowe uproszczenie.
"""
from __future__ import annotations

import json
import re
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
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
# UWAGA: UploadFile bierzemy ze Starlette, nie z FastAPI. `fastapi.UploadFile` jest
# *podklasą* tej klasy, a `request.form()` tworzy obiekty klasy nadrzędnej — przez
# `isinstance(..., fastapi.UploadFile)` każdy wgrany plik po cichu wypadał ze scalania.
from starlette.datastructures import UploadFile
from starlette.exceptions import HTTPException as BladHTTP

from . import aktualizacja, db, generator, pdf, szablony, teryt
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
    aktualizacja.uzupelnij_szablony()   # dokłada brakujące wzorce, istniejących nie rusza
    threading.Thread(target=_pierwsze_pobranie_teryt, daemon=True).start()
    yield


app = FastAPI(title="Generator operatów", lifespan=cykl_zycia)
app.mount("/static", StaticFiles(directory=WEB / "static"), name="static")
widoki = Jinja2Templates(directory=str(WEB / "templates"))

PRZESLANE = DANE / "przeslane"
PRZESLANE.mkdir(parents=True, exist_ok=True)

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
        "Program nie dokończył tej czynności. Twoje dokumenty, dane stałe i numeracja "
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
        plik, kontekst = generator.generuj(szablon, dane, db.wczytaj_ustawienia())
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

    tytul = plik.stem.rsplit("__", 1)[0].replace("_", " ")
    dokument_id = db.zapisz_dokument(szablon.id, tytul, plik.name, dane)
    return RedirectResponse(f"/dokument/{dokument_id}", status_code=303)


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
    cel = zrodlo.with_suffix(".pdf")
    if not cel.exists():
        try:
            pdf.docx_na_pdf(zrodlo, cel)
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
    db.ustaw_pdf(dokument_id, cel.name)
    return FileResponse(cel, filename=cel.name, media_type="application/pdf")


@app.post("/dokument/{dokument_id}/usun")
def usun(dokument_id: int):
    wiersz = db.dokument(dokument_id)
    if wiersz:
        for nazwa in (wiersz["plik_docx"], wiersz["plik_pdf"]):
            if nazwa:
                (WYNIKI / nazwa).unlink(missing_ok=True)
        db.usun_dokument(dokument_id)
    return RedirectResponse("/", status_code=303)


# --- łączenie PDF ------------------------------------------------------------

@app.get("/scal", response_class=HTMLResponse)
def scal_formularz(request: Request, dokument: int | None = None, komunikat: str | None = None):
    return _widok(request, "scal.html", dokumenty=db.dokumenty(limit=50),
                  wybrany=dokument, komunikat=komunikat)


def _kolejnosc(wartosc: Any, domyslna: float) -> float:
    """Pole „kolejność” bywa puste albo wpisane z przecinkiem — nie może wywalić scalania."""
    try:
        return float(str(wartosc).replace(",", "."))
    except (TypeError, ValueError):
        return domyslna


# Do scalenia przyjmujemy tylko to, co naprawdę umiemy zamienić na strony PDF-a.
# Wszystko inne (skan .jpg, arkusz .xlsx) odrzucamy z wyjaśnieniem — bez tego
# pypdf wywalał się dopiero przy sklejaniu, czyli po konwersji całej reszty.
ROZSZERZENIA_PDF = {".pdf"}
ROZSZERZENIA_WORD = {".docx", ".doc", ".rtf", ".odt"}


@app.post("/scal")
async def scal(request: Request):
    formularz_danych = await request.form()
    elementy: list[tuple[float, Path]] = []
    tymczasowe: list[Path] = []
    etykiety: dict[Path, str] = {}      # ścieżka robocza -> nazwa, którą zna użytkownik

    def sprzataj() -> None:
        for plik in tymczasowe:
            plik.unlink(missing_ok=True)

    def niepowodzenie(tresc: str) -> HTMLResponse:
        """Wraca na formularz z komunikatem zamiast wywalać serwer."""
        sprzataj()
        return _widok(request, "scal.html", dokumenty=db.dokumenty(limit=50),
                      wybrany=None, blad=tresc)

    # 1. dokumenty z historii (zaznaczone checkboxem, kolejność z pola liczbowego)
    for klucz in formularz_danych:
        if not klucz.startswith("dok__") or not klucz[len("dok__"):].isdigit():
            continue
        dokument_id = int(klucz[len("dok__"):])
        wiersz = db.dokument(dokument_id)
        if not wiersz:
            continue
        zrodlo = WYNIKI / wiersz["plik_docx"]
        cel = zrodlo.with_suffix(".pdf")
        if not cel.exists():
            try:
                pdf.docx_na_pdf(zrodlo, cel)
            except pdf.BrakKonwertera as blad:
                return niepowodzenie(str(blad))
            except Exception as blad:
                zapisz_blad(request, blad)
                return niepowodzenie(
                    f"Nie udało się zrobić PDF-a z dokumentu „{wiersz['tytul']}”. "
                    "Sprawdź, czy Word nie czeka gdzieś z otwartym oknem, i spróbuj ponownie."
                )
        db.ustaw_pdf(dokument_id, cel.name)
        etykiety[cel] = wiersz["tytul"]
        elementy.append((_kolejnosc(formularz_danych.get(f"kol__{dokument_id}"), 50), cel))

    # 2. pliki wgrane przez przeglądarkę
    kolejnosci = formularz_danych.getlist("kol_plik")
    for indeks, przeslany in enumerate(formularz_danych.getlist("pliki")):
        if not isinstance(przeslany, UploadFile) or not przeslany.filename:
            continue
        # Nazwa pliku przychodzi z przeglądarki, więc nie wolno jej wkleić prosto
        # w ścieżkę — „..\..\coś” zapisałoby się poza katalogiem dane\przeslane.
        nazwa = Path(przeslany.filename).name
        rozszerzenie = Path(nazwa).suffix.lower()
        if rozszerzenie not in ROZSZERZENIA_PDF | ROZSZERZENIA_WORD:
            return niepowodzenie(
                f"Pliku „{nazwa}” nie da się dołączyć — to nie jest PDF ani dokument Worda. "
                "Skany, mapy i zdjęcia zapisz najpierw jako PDF (w programie skanera albo "
                "otwierając plik i wybierając Drukuj → Microsoft Print to PDF)."
            )

        # Rozszerzenie doklejamy z listy dozwolonych, a nie z oczyszczonej nazwy:
        # przy nazwie bez znaków ASCII (np. cyrylicą) zostałaby sama końcówka i Word
        # nie wiedziałby, w jakim formacie jest plik.
        docelowy = (PRZESLANE / f"{datetime.now():%Y%m%d-%H%M%S}-{indeks}"
                                f"-{generator.bezpieczna_nazwa(Path(nazwa).stem)}{rozszerzenie}")
        with open(docelowy, "wb") as zapis:
            shutil.copyfileobj(przeslany.file, zapis)
        tymczasowe.append(docelowy)

        if rozszerzenie in ROZSZERZENIA_WORD:
            try:
                docelowy = pdf.docx_na_pdf(docelowy)
            except pdf.BrakKonwertera as blad:
                return niepowodzenie(str(blad))
            except Exception as blad:
                zapisz_blad(request, blad)
                return niepowodzenie(
                    f"Nie udało się zamienić pliku „{nazwa}” na PDF. Otwórz go w Wordzie "
                    "i sprawdź, czy da się go normalnie wyświetlić."
                )
            tymczasowe.append(docelowy)

        etykiety[docelowy] = nazwa
        elementy.append((_kolejnosc(kolejnosci[indeks] if indeks < len(kolejnosci) else None,
                                    60), docelowy))

    if not elementy:
        return niepowodzenie("Nie wybrano żadnych plików do połączenia.")

    elementy.sort(key=lambda para: para[0])
    nazwa_wyniku = formularz_danych.get("nazwa_wynikowa") or "Operat_scalony"
    wynik = (WYNIKI / f"{generator.bezpieczna_nazwa(nazwa_wyniku)}"
                      f"__{datetime.now():%Y%m%d-%H%M%S}.pdf")
    try:
        pdf.polacz_pdf([sciezka for _, sciezka in elementy], wynik, etykiety)
    except pdf.BladPliku as blad:
        return niepowodzenie(str(blad))

    sprzataj()
    return FileResponse(wynik, filename=wynik.name, media_type="application/pdf")


# --- ustawienia (dane stałe) -------------------------------------------------

@app.get("/ustawienia", response_class=HTMLResponse)
def ustawienia_formularz(request: Request, zapisano: bool = False,
                         komunikat: str | None = None, blad: str | None = None):
    return _widok(request, "ustawienia.html", ustawienia=db.wczytaj_ustawienia(),
                  zapisano=zapisano, komunikat=komunikat, blad=blad,
                  teryt_stan=teryt.stan())


@app.post("/ustawienia")
async def ustawienia_zapis(request: Request):
    formularz_danych = await request.form()
    nowe: dict[str, str] = {}
    klucze = formularz_danych.getlist("klucz")
    wartosci = formularz_danych.getlist("wartosc")
    for klucz, wartosc in zip(klucze, wartosci):
        klucz = re.sub(r"[^a-z0-9_]", "", klucz.strip().lower().replace(" ", "_"))
        if klucz:
            nowe[klucz] = wartosc.strip()
    db.zastap_ustawienia(nowe)
    return RedirectResponse("/ustawienia?zapisano=1", status_code=303)


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

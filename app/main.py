"""Aplikacja webowa: formularz -> gotowy .docx / .pdf.

Chodzi lokalnie na komputerze użytkownika (127.0.0.1), więc nie ma logowania
ani multitenancy — to celowe uproszczenie.
"""
from __future__ import annotations

import json
import re
import shutil
from collections import defaultdict
from contextlib import asynccontextmanager
from datetime import date, datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from . import db, generator, pdf, szablony
from .config import DANE, WEB, WYNIKI

@asynccontextmanager
async def cykl_zycia(_: FastAPI):
    db.init()
    yield


app = FastAPI(title="Generator operatów", lifespan=cykl_zycia)
app.mount("/static", StaticFiles(directory=WEB / "static"), name="static")
widoki = Jinja2Templates(directory=str(WEB / "templates"))

PRZESLANE = DANE / "przeslane"
PRZESLANE.mkdir(parents=True, exist_ok=True)


def _widok(request: Request, nazwa: str, **kontekst: Any) -> HTMLResponse:
    kontekst.setdefault("konwerter", pdf.dostepny_konwerter())
    return widoki.TemplateResponse(request, nazwa, kontekst)


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
    return proste


# --- strony ------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def strona_glowna(request: Request):
    return _widok(request, "index.html",
                  szablony=szablony.lista_szablonow(),
                  dokumenty=db.dokumenty(limit=15))


@app.get("/nowy/{identyfikator}", response_class=HTMLResponse)
def formularz(request: Request, identyfikator: str, kopiuj: int | None = None):
    szablon = szablony.szablon_po_id(identyfikator)
    if szablon is None:
        return RedirectResponse("/", status_code=303)

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
    szablon = szablony.szablon_po_id(identyfikator)
    if szablon is None:
        return RedirectResponse("/", status_code=303)

    formularz_danych = await request.form()
    dane = odczytaj_dane(formularz_danych, szablon)

    brakujace = [p.etykieta for p in szablon.pola
                 if p.wymagane and p.zrodlo != "ustawienia" and not dane.get(p.klucz)]
    if brakujace:
        return _widok(request, "formularz.html", szablon=szablon, wartosci=dane,
                      blad="Uzupełnij wymagane pola: " + ", ".join(brakujace),
                      dzisiaj=date.today().isoformat())

    plik, kontekst = generator.generuj(szablon, dane, db.wczytaj_ustawienia())
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
def pobierz_pdf(dokument_id: int):
    wiersz = db.dokument(dokument_id)
    if wiersz is None or not (WYNIKI / wiersz["plik_docx"]).exists():
        return RedirectResponse("/", status_code=303)
    zrodlo = WYNIKI / wiersz["plik_docx"]
    cel = zrodlo.with_suffix(".pdf")
    if not cel.exists():
        try:
            pdf.docx_na_pdf(zrodlo, cel)
        except pdf.BrakKonwertera as blad:
            return RedirectResponse(f"/dokument/{dokument_id}?blad={blad}", status_code=303)
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


@app.post("/scal")
async def scal(request: Request):
    formularz_danych = await request.form()
    elementy: list[tuple[float, Path]] = []
    tymczasowe: list[Path] = []

    # 1. dokumenty z historii (zaznaczone checkboxem, kolejność z pola liczbowego)
    for klucz in formularz_danych:
        if not klucz.startswith("dok__"):
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
                return RedirectResponse(f"/scal?komunikat={blad}", status_code=303)
        db.ustaw_pdf(dokument_id, cel.name)
        kolejnosc = formularz_danych.get(f"kol__{dokument_id}") or "50"
        elementy.append((float(kolejnosc), cel))

    # 2. pliki wgrane przez przeglądarkę
    for indeks, przeslany in enumerate(formularz_danych.getlist("pliki")):
        if not isinstance(przeslany, UploadFile) or not przeslany.filename:
            continue
        docelowy = PRZESLANE / f"{datetime.now():%Y%m%d-%H%M%S}-{indeks}-{przeslany.filename}"
        with open(docelowy, "wb") as zapis:
            shutil.copyfileobj(przeslany.file, zapis)
        tymczasowe.append(docelowy)
        if docelowy.suffix.lower() == ".docx":
            docelowy = pdf.docx_na_pdf(docelowy)
            tymczasowe.append(docelowy)
        kolejnosc = formularz_danych.getlist("kol_plik")[indeks] if indeks < len(
            formularz_danych.getlist("kol_plik")) else "60"
        elementy.append((float(kolejnosc or 60), docelowy))

    if not elementy:
        return RedirectResponse("/scal?komunikat=Nie wybrano żadnych plików.", status_code=303)

    elementy.sort(key=lambda para: para[0])
    nazwa = formularz_danych.get("nazwa_wynikowa") or "Operat_scalony"
    wynik = WYNIKI / f"{generator.bezpieczna_nazwa(nazwa)}__{datetime.now():%Y%m%d-%H%M%S}.pdf"
    pdf.polacz_pdf([sciezka for _, sciezka in elementy], wynik)

    for plik in tymczasowe:
        plik.unlink(missing_ok=True)
    return FileResponse(wynik, filename=wynik.name, media_type="application/pdf")


# --- ustawienia (dane stałe) -------------------------------------------------

@app.get("/ustawienia", response_class=HTMLResponse)
def ustawienia_formularz(request: Request, zapisano: bool = False):
    return _widok(request, "ustawienia.html", ustawienia=db.wczytaj_ustawienia(),
                  zapisano=zapisano)


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


@app.get("/pomoc", response_class=HTMLResponse)
def pomoc(request: Request):
    return _widok(request, "pomoc.html")

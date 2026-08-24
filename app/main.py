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
from starlette.datastructures import UploadFile
from starlette.exceptions import HTTPException as BladHTTP

from . import (aktualizacja, db, generator, miniatury, operaty, opisy, pdf, raport,
               statystyki, szablony, tekst, teryt, warianty, zmiany)
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


def _porzadki() -> None:
    """Sprzątanie po sobie przy starcie: stare kopie zapasowe i osierocone podglądy.

    Wszystko tutaj jest samonaprawcze i nic nie blokuje startu — to porządki, a nie
    funkcja programu. Wisi na starcie, a nie na aktualizacji, bo działać ma także
    u kogoś, kto akurat niczego nie aktualizuje (patrz pułapka 7b).
    """
    try:
        aktualizacja.sprzataj_kopie()
        db.sprzataj_kopie_bazy()
        operaty.sprzataj_podglady()
    except Exception:
        pass


def _wyslij_statystyki() -> None:
    """Trzy liczby do arkusza autora — raz na uruchomienie, w tle i po cichu.

    W osobnym wątku z tego samego powodu co pobieranie TERYT-u: start programu nie
    ma prawa czekać na cudzy serwer. Wyjątek połykamy tutaj, a nie tylko w `raport`,
    żeby żaden ślad stosu nie wyszedł bratu do konsoli.
    """
    try:
        raport.wyslij(aktualizacja.wersja_lokalna()[0], statystyki.podsumowanie())
    except Exception:
        pass


@asynccontextmanager
async def cykl_zycia(_: FastAPI):
    db.init()
    # Liczniki startują od tego, co brat już zrobił — inaczej po aktualizacji
    # zobaczyłby „0 operatów”, mając ich pięćdziesiąt. Robi się to raz.
    statystyki.zasiej_z_historii()
    # Opisy dostarczone z programem — też raz na pozycję, żeby skasowana przez brata
    # nie wracała przy każdym uruchomieniu (patrz `app/opisy.py`).
    try:
        opisy.zasiej()
    except Exception:
        pass                    # wygoda, a nie funkcja — nie ma prawa zatrzymać startu
    # Porządki w `dane/kopie/` przy każdym starcie, a nie tylko przy aktualizacji:
    # aktualizację wykonuje kod, który użytkownik już ma, więc sprzątanie wpięte
    # w nią zaczynałoby działać dopiero przy następnej (patrz pułapka 7b).
    _porzadki()
    threading.Thread(target=_pierwsze_pobranie_teryt, daemon=True).start()
    threading.Thread(target=_wyslij_statystyki, daemon=True).start()
    yield


app = FastAPI(title="Generator operatów", lifespan=cykl_zycia)
app.mount("/static", StaticFiles(directory=WEB / "static"), name="static")
widoki = Jinja2Templates(directory=str(WEB / "templates"))
# Formularz sam oznacza pola z numerem działki — skrypt po stronie przeglądarki
# podpowiada przy nich, czy ULDK zna taką działkę.
widoki.env.globals["POLA_DZIALKI"] = szablony.POLA_DZIALKI

DZIENNIK_BLEDOW = DANE / "bledy.log"


def wersja_zasobow() -> str:
    """Znacznik do adresów `/static/...`, po którym przeglądarka pozna nowy arkusz.

    Sam numer wersji programu tu nie wystarcza. Przy zwykłej pracy `WERSJA` stoi
    w miejscu (podbija ją dopiero wydanie), więc adres `style.css?v=…` się nie zmienia
    i przeglądarka trzyma stary plik — poprawka wygląda wtedy na niedziałającą, choć
    serwer oddaje już nowy CSS. Kosztowało to jedną rundę poprawek: układ listy operatów
    wyglądał na niezmieniony, bo do przeglądarki nie dojechały nowe reguły.

    Dokładamy więc czas zmiany plików statycznych. Nie zastępujemy nim numeru wersji —
    numer zostaje, bo jest czytelny, gdy trzeba dopasować zgłoszenie brata do wydania.
    Odczyt jest tani (trzy pliki), ale u brata i tak trzymamy wynik: katalog jest tam
    niezmienny przez całe uruchomienie, a aktualizacja restartuje program.

    **W kopii roboczej gita liczymy go za każdym razem.** Przy pracy nad wyglądem plik
    zmienia się co chwilę, a serwer nie ma auto-reloadu — zapamiętany znacznik dawał
    stary adres, przeglądarka brała arkusz z cache i poprawka wyglądała na niedziałającą.
    Kosztowało to dwie rundy „przecież nie wygląda tak samo”, przy czym za pierwszym
    razem podejrzenie padło na CSS, a nie na cache.
    """
    global _ZNACZNIK_ZASOBOW
    if _ZNACZNIK_ZASOBOW is None or aktualizacja.kopia_robocza_gita():
        try:
            najnowszy = max(p.stat().st_mtime for p in (WEB / "static").iterdir()
                            if p.is_file())
            _ZNACZNIK_ZASOBOW = str(int(najnowszy))
        except (OSError, ValueError):      # brak katalogu — trudno, zostaje sam numer
            _ZNACZNIK_ZASOBOW = ""
    return _ZNACZNIK_ZASOBOW


_ZNACZNIK_ZASOBOW: str | None = None


def _co_nowego() -> dict[str, Any] | None:
    """Komunikat po aktualizacji, rozebrany tak samo jak wpis w historii wersji.

    Pierwsza linijka pliku to numer wersji, reszta — opis dla użytkownika (wstęp
    i listy punktów). Czyta to `app/zmiany.py`, żeby obie strony pokazywały to samo
    tym samym kształtem.
    """
    tresc = aktualizacja.co_nowego()
    if not tresc:
        return None
    wersja, _, opis = tresc.partition("\n")
    return {"wersja": wersja.strip(), **zmiany.rozbierz_opis(opis)}


def _widok(request: Request, nazwa: str, status: int = 200,
           **kontekst: Any) -> HTMLResponse:
    kontekst.setdefault("konwerter", pdf.dostepny_konwerter())
    kontekst.setdefault("wersja", aktualizacja.wersja_lokalna()[0])
    kontekst.setdefault("zasoby", f"{aktualizacja.wersja_lokalna()[0]}-{wersja_zasobow()}")
    kontekst.setdefault("statystyki", statystyki.podsumowanie())
    return widoki.TemplateResponse(request, nazwa, kontekst, status_code=status)


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
        # Ten sam kontekst co każda inna strona (`_widok`), a nie własny, okrojony:
        # brakowało w nim liczników ze stopki, a odczyt pola z nieistniejącej zmiennej
        # to w Jinja **wyjątek**, nie pustka. Strona błędu leciała więc do zapasowego
        # gołego HTML-a — po polsku, ale bez stylów, nagłówka i menu. Widać to było
        # tylko na prawdziwym błędzie, bo testy sprawdzały samą treść komunikatu.
        return _widok(request, "blad.html", status=status, naglowek=naglowek,
                      wyjasnienie=wyjasnienie, szczegoly=szczegoly)
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

def _przytnij_wielolinijkowe(tekst: str) -> str:
    """Jak `strip()`, ale **puste linijki na początku zostają**.

    W wykazach OFU/OZU/OZK stoją w dwóch kolumnach obok siebie i brat wyrównuje
    wartość pustymi enterami do właściwej linijki sąsiedniej kolumny — wpis w stanie
    nowym potrafi dotyczyć dopiero drugiego użytku. `strip()` zjadał te linijki
    po cichu. Koniec ucinamy jak dotąd (ogonowe entery tylko nadmuchują komórkę),
    a `\\r\\n` z przeglądarki sprowadzamy do `\\n` — na tym łamie docxtpl.
    """
    tekst = (tekst or "").replace("\r\n", "\n").replace("\r", "\n")
    return tekst.rstrip().lstrip(" \t")


def odczytaj_dane(formularz, szablon: szablony.Szablon) -> dict[str, Any]:
    """Zamienia płaski formularz HTML na słownik z listami dla tabel.

    pole__nr_roboty            -> {"nr_roboty": "..."}
    tab__wykaz__0__nr_punktu   -> {"wykaz": [{"nr_punktu": "..."}, ...]}
    """
    proste: dict[str, Any] = {}
    tabele: dict[str, dict[int, dict[str, str]]] = defaultdict(lambda: defaultdict(dict))
    # `sekcje` to powtarzany **komplet pól** (np. jeden wykaz zmian danych budynku),
    # a nie wiersz tabeli. Dane wychodzą w tym samym kształcie co z tabeli — lista
    # słowników — więc formatka obsługuje jedno i drugie tą samą pętlą `{%p for %}`.
    sekcje: dict[str, dict[int, dict[str, str]]] = defaultdict(lambda: defaultdict(dict))

    for klucz, wartosc in formularz.multi_items():
        if klucz.startswith("pole__"):
            proste[klucz[len("pole__"):]] = wartosc.strip() if isinstance(wartosc, str) else wartosc
        elif klucz.startswith("tab__") or klucz.startswith("sek__"):
            czesci = klucz.split("__")
            if len(czesci) == 4:
                przedrostek, nazwa, indeks, podklucz = czesci
                if indeks.isdigit():
                    gdzie = tabele if przedrostek == "tab" else sekcje
                    gdzie[nazwa][int(indeks)][podklucz] = _przytnij_wielolinijkowe(wartosc)

    for zbior in (tabele, sekcje):
        for nazwa, wiersze in zbior.items():
            uporzadkowane = [wiersze[i] for i in sorted(wiersze)]
            # całkiem puste pomijamy — dołożony i niewypełniony wykaz nie ma po co
            # jechać do dokumentu jako pusta strona
            proste[nazwa] = [w for w in uporzadkowane if any(v for v in w.values())]

    for pole in szablon.pola:
        if pole.typ == "checkbox":
            proste[pole.klucz] = pole.klucz in {k[len("pole__"):] for k in formularz
                                                if k.startswith("pole__")}
        elif pole.typ in ("tabela", "sekcje"):
            proste.setdefault(pole.klucz, [])
        elif pole.typ == "dokumenty":
            proste[pole.klucz] = formularz.getlist(f"pole__{pole.klucz}")
        elif pole.typ == "wybor_wielokrotny":
            # Kolejność bierzemy z listy opcji, nie z formularza, a pozycje „zawsze”
            # dokładamy niezależnie od tego, co przyszło — w formularzu są wyłączone,
            # więc przeglądarka i tak ich nie wysyła.
            zaznaczone = set(formularz.getlist(f"pole__{pole.klucz}"))
            proste[pole.klucz] = [o for o in pole.opcje
                                  if o in zaznaczone or o in pole.zawsze]
        elif pole.typ == "teryt":  # noqa: SIM114 (kolejność gałęzi jest tu czytelniejsza)
            # cztery listy rozwijane przychodzą jako pole__polozenie__gmina itd.;
            # scalamy je w jeden słownik identyfikatorów, żeby walidacja „wymagane”
            # i zapis do historii widziały to jako jedno pole
            czesci = {poziom: proste.pop(f"{pole.klucz}__{poziom}", "")
                      for poziom in ("wojewodztwo", "powiat", "gmina", "obreb")}
            proste[pole.klucz] = czesci if any(czesci.values()) else {}

    # Pola przyjmujące formatowanie przychodzą jako fragment HTML z edytora w przeglądarce.
    # Zdejmujemy z nich wszystko poza pogrubieniem, kursywą, podkreśleniem i złamaniem
    # wiersza: to jedyne, co umiemy wstawić do Worda, a reszta (kolory, czcionki ze
    # skopiowanego Worda, skrypty) rozjechałaby wygląd operatu albo samą stronę.
    for pole in szablon.pola:
        if pole.formatowanie and isinstance(proste.get(pole.klucz), str):
            proste[pole.klucz] = tekst.oczysc(proste[pole.klucz])

    # Wybór formatek z tabelki na dole. Zapisujemy **wszystkie** pozycje, także te
    # ustawione z powrotem na standardową (pusta wartość): brak klucza znaczyłby
    # „weź domyślną z ustawień”, czyli świadomy powrót do standardu nie przeżyłby
    # poprawiania operatu.
    wybor = {klucz[len(warianty.KLUCZ):]: wartosc.strip()
             for klucz, wartosc in formularz.multi_items()
             if klucz.startswith(warianty.KLUCZ) and isinstance(wartosc, str)}
    if wybor:
        proste["warianty"] = wybor
    return proste


# --- strony ------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def strona_glowna(request: Request, blad: str | None = None):
    # Kafelki tylko dla szablonów oznaczonych jako główne: reszta (sprawozdanie,
    # protokoły) sama bez operatu nie istnieje, dokłada się ją checkboxem w formularzu.
    # Gdy nikt nie jest oznaczony, pokazujemy wszystkie — inaczej po dodaniu pierwszego
    # szablonu bez „glowny” strona byłaby pusta i nie wiadomo dlaczego.
    wszystkie = szablony.lista_szablonow()
    glowne = [s for s in wszystkie if s.glowny] or wszystkie
    return _widok(request, "index.html",
                  szablony=glowne,
                  operaty=_lista_operatow(),
                  blad=blad,
                  co_nowego=_co_nowego())   # pokazuje się raz, po aktualizacji


LIMIT_LISTY = 500          # zapas na lata pracy; przy 50 operatach rocznie to długo


def _lista_operatow() -> list[dict[str, Any]]:
    """Jedna lista operatów: historia z bazy **plus** katalogi znalezione w `wyniki/`.

    Sama historia nie wystarcza: operat przywrócony z archiwum na świeżej instalacji
    (albo po utracie `dane/`) leży na dysku, a wpisu w bazie nie ma — bez tego byłby
    poza zasięgiem, bo składanie idzie tylko z listy. Sam dysk też nie wystarcza:
    wpis w historii trzyma dane formularza potrzebne do „Powiel”.

    Wcześniej te dwa źródła miały osobne strony (`/` i `/scal`) i wyglądały jak ta sama
    lista pokazana dwa razy — a różniły się właśnie tym, czego nie było widać.
    """
    wiersze: list[dict[str, Any]] = []
    znane: set[str] = set()

    for wpis in db.dokumenty(limit=LIMIT_LISTY):
        katalog = wpis["katalog"] or ""
        if katalog:
            znane.add(katalog)
        wiersze.append({
            "id": wpis["id"],
            "nr_operatu": wpis["nr_operatu"] or katalog,
            "nr_roboty": wpis["tytul"],
            "katalog": katalog,
            "utworzono": wpis["utworzono"] or "",
            "szablon": wpis["szablon"],
            "notatka": wpis["notatka"] or "",
            "w_historii": True,
            # Operat przeniesiony do archiwum zostaje w historii, ale jego katalogu
            # już nie ma — nie ma więc czego składać. Lista musi to pokazać, zamiast
            # oferować przycisk, który po cichu odsyła z powrotem na listę.
            "na_dysku": bool(katalog) and (WYNIKI / katalog).is_dir(),
        })

    for operat in operaty.lista():
        if operat["katalog"] in znane:
            continue
        wiersze.append({
            "id": None,
            "nr_operatu": operat["nr_operatu"],
            "nr_roboty": operat["nr_roboty"],
            "katalog": operat["katalog"],
            "utworzono": operat["utworzono"],
            "szablon": "",
            # operat spoza historii ma notatkę tylko w swoim `operat.json` — dlatego
            # zapisujemy ją w obu miejscach
            "notatka": operat["notatka"],
            "w_historii": False,
            "na_dysku": True,          # ta lista bierze się właśnie ze skanu `wyniki/`
        })

    return sorted(wiersze, key=lambda w: w["utworzono"], reverse=True)


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


def _przygotuj_podglady_po_cichu(katalog: Path) -> None:
    """Konwersja z wyprzedzeniem — awaria tutaj nie może niczego popsuć.

    Gdy się nie uda, miniatury zrobią się później, na żądanie, tak jak wcześniej.
    """
    try:
        operaty.przygotuj_podglady(katalog)
    except Exception:
        pass


def _listy_dokumentow(szablon: szablony.Szablon) -> dict[str, list[dict[str, str]]]:
    """Dla każdego pola typu `dokumenty` — które szablony ma pokazać.

    Pole z `tylko` bierze wymienione pozycje, więc każdy dokument może mieć własną
    kartę i swoje opcje pod spodem. Pole bez `tylko` zbiera całą resztę — dzięki temu
    nowy szablon wrzucony do `szablony/` nadal pokazuje się sam, choćby w karcie
    „Inne dokumenty”, zamiast zniknąć bez śladu.

    **Uwaga: ta funkcja zmienia przekazany szablon.** Pola, dla których nie zostało nic
    do pokazania, wyrzuca z `szablon.pola` — inaczej w formularzu zostałaby pusta karta
    z samym nagłówkiem. Kto potrzebuje kompletu pól (np. strona operatu, żeby wiedzieć,
    czego *nie* było w formularzu), musi zrobić kopię **przed** tym wywołaniem.
    """
    wszystkie = [s for s in szablony.lista_skrocona() if s["id"] != szablon.id]
    # „Zajęty” to szablon, który ma już swój włącznik gdzie indziej: albo własną kartę
    # (`tylko`), albo pozycję w spisie treści. Bez tego drugiego sprawozdanie i wykazy
    # wróciłyby do karty „Inne dokumenty” i dało się je włączyć w dwóch miejscach naraz.
    zajete = {i for p in szablon.pola if p.typ == "dokumenty" for i in p.tylko}
    zajete |= {i for p in szablon.pola for i in p.dokumenty.values()}

    listy: dict[str, list[dict[str, str]]] = {}
    for pole in szablon.pola:
        if pole.typ != "dokumenty":
            continue
        listy[pole.klucz] = ([s for s in wszystkie if s["id"] in pole.tylko] if pole.tylko
                             else [s for s in wszystkie if s["id"] not in zajete])

    szablon.pola = [p for p in szablon.pola
                    if p.typ != "dokumenty" or listy.get(p.klucz)]
    return listy


def _warianty_pozycji(szablon: szablony.Szablon) -> list[dict[str, Any]]:
    """Pozycje do tabelki „Formatki” na dole formularza — tylko te z wyborem.

    Kategoria bez ani jednej własnej formatki nie ma czego wybierać, więc się nie
    pokazuje; gdy nie ma ich nigdzie, tabelka znika w całości. Formularz ma być
    do wypełniania, a nie do oglądania list z jedną pozycją.
    """
    kolejnosc = [{"id": szablon.id, "nazwa_dokumentu": szablon.nazwa_dokumentu}]
    kolejnosc += [dokument for lista in _listy_dokumentow(szablon).values()
                  for dokument in lista]

    pozycje, widziane = [], set()
    for pozycja in kolejnosc:
        if pozycja["id"] in widziane:
            continue
        widziane.add(pozycja["id"])
        wlasne = warianty.lista(pozycja["id"])
        if wlasne:
            pozycje.append({**pozycja, "warianty": wlasne})
    return pozycje


def _szczyt_formularza(szablon: szablony.Szablon, poprawiany: Any) -> dict[str, Any]:
    """Numer i data do szczytu formularza — jedno miejsce dla obu wyświetleń.

    Przy poprawianiu numer się nie zmienia i pochodzi z historii (dla szablonu bez
    licznika numerem jest nazwa katalogu — to samo, co pokazuje lista i strona operatu);
    data utworzenia stoi pod nim, żeby szczyt wyglądał jak ten, z którego się przyszło.
    Przy nowym operacie podglądamy numer, który zostanie nadany — to podpowiedź w polu
    „Nr operatu”.

    Liczone osobno od reszty kontekstu, bo powrót na formularz po błędzie („Uzupełnij
    wymagane pola”, literówka w formatce) budował go własnym słownikiem i gubił numer:
    nagłówek przeskakiwał wtedy z „Operat: 001/2026” na „Nowy operat”, a brat miał
    prawo sądzić, że poprawka przepadła i zakłada nowy operat.
    """
    if poprawiany:
        return {"podglad_numeru": (poprawiany["nr_operatu"] or poprawiany["katalog"]
                                   or poprawiany["tytul"]),
                "utworzono": poprawiany["utworzono"] or ""}
    podglad = None
    for pole in szablon.pola:
        if pole.typ == "auto_numer":
            numer = db.podglad_numeru(szablon.licznik or szablon.id, date.today().year)
            wzor = pole.domyslnie or "{numer}/{rok}"
            podglad = wzor.format(numer=numer, numer3=f"{numer:03d}", rok=date.today().year)
    return {"podglad_numeru": podglad, "utworzono": ""}


@app.get("/nowy/{identyfikator}", response_class=HTMLResponse)
def formularz(request: Request, identyfikator: str, kopiuj: int | None = None,
              edytuj: int | None = None):
    szablon, odpowiedz = _szablon_albo_blad(request, identyfikator)
    if odpowiedz is not None:
        return odpowiedz

    # wartości startowe; przy typie auto_numer "domyslnie" to wzorzec numeru, nie wartość
    wartosci: dict[str, Any] = {}
    for pole in szablon.pola:
        if pole.domyslne:                    # lista wielokrotnego wyboru z zaznaczeniami na start
            wartosci[pole.klucz] = list(pole.domyslne)
        if not pole.domyslnie or pole.typ == "auto_numer":
            continue
        wartosci[pole.klucz] = (date.today().isoformat()
                                if pole.typ == "date" and pole.domyslnie == "dzisiaj"
                                else pole.domyslnie)
    # „Powiel” robi nowy operat z tymi samymi danymi, „Popraw” wraca do tego samego
    zrodlo = db.dokument(edytuj or kopiuj) if (edytuj or kopiuj) else None
    if (edytuj or kopiuj) and zrodlo is None:
        # Stara zakładka z „Popraw” albo „Powiel” po skasowaniu operatu. Formularz brał
        # wtedy kolejny numer z licznika i ogłaszał „Operat: 003/2026”, jakby poprawiał
        # istniejący — a zapis zakładał nowy; „Powiel” otwierał po cichu pusty formularz,
        # jakby nie miał czego skopiować. Nie ma czego, więc wracamy na listę i mówimy to.
        czynnosc = "poprawić" if edytuj else "powielić"
        return RedirectResponse("/?blad=" + quote(
            f"Operatu, który chcesz {czynnosc}, nie ma już w historii — pewnie został "
            "usunięty. Jeśli to nowa robota, zacznij od „Nowy operat”."), status_code=303)
    if zrodlo:
        wartosci.update(json.loads(zrodlo["dane_json"]))

    # Wybór formatek: przy poprawianiu i powielaniu bierzemy ten zapisany przy operacie
    # (siedzi w `dane_json`), a przy nowym — ostatnio używany z ustawień.
    wybor_wariantow = dict(warianty.domyslne(db.wczytaj_ustawienia()))
    wybor_wariantow.update(wartosci.get("warianty") or {})

    # Notatka („Opis”) idzie osobno od `wartosci`, bo nie jest daną dokumentu — nie ma
    # jej w szablonie i nigdy nie trafia do treści. Przy „Powiel” bierzemy ją razem
    # z resztą: nowa robota zwykle zaczyna się od tych samych uwag, a skasować łatwiej
    # niż przepisać.
    return _widok(request, "formularz.html", szablon=szablon, wartosci=wartosci,
                  **_szczyt_formularza(szablon, zrodlo if edytuj else None),
                  dzisiaj=date.today().isoformat(),
                  edytuj=edytuj, listy_dokumentow=_listy_dokumentow(szablon),
                  warianty_pozycji=_warianty_pozycji(szablon),
                  wybor_wariantow=wybor_wariantow,
                  opisy_biblioteki=db.opisy_sprawozdania(),
                  notatka=(zrodlo["notatka"] or "") if zrodlo else "")


@app.post("/generuj/{identyfikator}")
async def generuj(request: Request, identyfikator: str, edytuj: int | None = None):
    szablon, odpowiedz = _szablon_albo_blad(request, identyfikator)
    if odpowiedz is not None:
        return odpowiedz

    formularz_danych = await request.form()
    dane = odczytaj_dane(formularz_danych, szablon)
    wybor_wariantow = dane.get("warianty") or {}
    # Notatka stoi poza `pole__`, więc nie miesza się z danymi szablonu i nie może
    # przypadkiem zderzyć się ze znacznikiem o tej samej nazwie w formatce Worda.
    notatka = str(formularz_danych.get("notatka") or "").strip()

    poprawiany = db.dokument(edytuj) if edytuj else None
    komunikat = None
    if edytuj and poprawiany is None:
        # „Zapisz” w starej zakładce, gdy operat już skasowano. Dotąd szło to dalej jako
        # nowy operat — pod pozorem poprawki, z kolejnym numerem z licznika. Danych
        # nie wyrzucamy (brat właśnie je wpisał), ale formularz wraca już jako nowy
        # i mówi dlaczego; dopiero następne „Zapisz” założy operat.
        edytuj = None
        komunikat = ("Operatu, który poprawiałeś, nie ma już w historii — pewnie został "
                     "usunięty. Wpisane dane zostały tutaj; „Zapisz” założy go teraz "
                     "jako nowy operat, z kolejnym numerem.")

    # wspólne dla obu powrotów na formularz — po błędzie ma wrócić komplet, razem
    # z numerem operatu, wybranymi formatkami i notatką, żeby nic nie trzeba było
    # ustawiać drugi raz ani zgadywać, czy to nadal ta sama robota
    powrot = dict(szablon=szablon, wartosci=dane, edytuj=edytuj,
                  **_szczyt_formularza(szablon, poprawiany),
                  dzisiaj=date.today().isoformat(),
                  listy_dokumentow=_listy_dokumentow(szablon),
                  warianty_pozycji=_warianty_pozycji(szablon),
                  wybor_wariantow=wybor_wariantow, notatka=notatka,
                  opisy_biblioteki=db.opisy_sprawozdania())
    if komunikat:
        return _widok(request, "formularz.html", **powrot, blad=komunikat)

    # `auto_numer` pomijamy: pole zostaje puste celowo, bo numer nadaje program przy
    # generowaniu. Oznaczenie go jako wymaganego ma sens tylko po to, żeby w formularzu
    # stała gwiazdka — inaczej każda próba kończyłaby się „uzupełnij wymagane pola”.
    brakujace = [p.etykieta for p in szablon.pola
                 if p.wymagane and p.zrodlo != "ustawienia" and p.typ != "auto_numer"
                 and not dane.get(p.klucz)]
    if brakujace:
        return _widok(request, "formularz.html", **powrot,
                      blad="Uzupełnij wymagane pola: " + ", ".join(brakujace))

    poprzedni_opis = None
    if poprawiany:
        katalog_poprzedni = operaty.katalog_po_nazwie(poprawiany["katalog"] or "")
        poprzedni_opis = operaty.opis(katalog_poprzedni) if katalog_poprzedni else None
        if not (poprzedni_opis or {}).get("nr_operatu"):
            # Operat przeniesiony do archiwum: `operat.json` pojechał razem z folderem,
            # ale numer i tak znamy — siedzi w historii. Bez tego poprawka brała kolejny
            # numer z licznika i zakładała nowy katalog obok: „poprawiam 055, a robi się
            # 060”. Zjadała przy tym numer, którego już nikt nie odzyska.
            poprzedni_opis = {"nr_operatu": poprawiany["nr_operatu"] or "",
                              "nr_roboty": poprawiany["tytul"] or ""}
        # Nazwa katalogu z historii — dla szablonów bez licznika to jedyny ślad, po którym
        # poprawka trafi tam, gdzie leżą poprzednie dokumenty (`operat.json` jej nie ma).
        poprzedni_opis = {**poprzedni_opis, "katalog": poprawiany["katalog"] or ""}

    try:
        plik, kontekst, ostrzezenia = generator.generuj(
            warianty.z_wariantem(szablon, wybor_wariantow.get(szablon.id, "")),
            dane, db.wczytaj_ustawienia(), poprzedni_opis)
    except Exception as blad:
        # Wracamy na formularz z kompletem wpisanych danych — utrata wykazu współrzędnych
        # przez literówkę w szablonie byłaby gorsza niż sam błąd.
        zapisz_blad(request, blad)
        return _widok(request, "formularz.html", **powrot,
                      blad=f"Nie udało się wypełnić szablonu „{szablon.nazwa}”. Zwykle "
                           "znaczy to, że w pliku .docx jest literówka w znaczniku "
                           "{{ }} albo {% ... %}. Twoje dane zostały tutaj — popraw "
                           f"szablon w Wordzie i kliknij ponownie. Szczegóły: {blad}")

    # Dodatkowe dokumenty do tego samego katalogu, wypełnione tym samym kontekstem.
    # Awaria któregoś nie może przekreślić dokumentu głównego, który już jest na dysku —
    # zgłaszamy ją jako ostrzeżenie na stronie operatu.
    katalog = plik.parent
    # zaznaczenia zbieramy ze wszystkich pól typu „dokumenty” — każdy dokument
    # ma swoją kartę, więc pól jest kilka
    # Co wygenerować: pozycje zaznaczone w spisie treści (mapowanie `dokumenty` w .json)
    # plus pola typu `dokumenty`, które zostały dla szablonów bez własnej pozycji w spisie.
    wybrane_szablony = [identyfikator
                        for pole in szablon.pola if pole.typ == "dokumenty"
                        for identyfikator in (dane.get(pole.klucz) or [])]
    for pole in szablon.pola:
        if not pole.dokumenty:
            continue
        zaznaczone = dane.get(pole.klucz) or []
        wybrane_szablony += [pole.dokumenty[o] for o in zaznaczone if o in pole.dokumenty]
    wypelnionych = 1                      # dokument główny już powstał
    aktualne = {plik.name}                # dokumenty tej rundy — reszta programowych to starocie
    for identyfikator_dodatkowego in wybrane_szablony:
        dodatkowy = szablony.szablon_po_id(str(identyfikator_dodatkowego))
        if dodatkowy is None or dodatkowy.id == szablon.id:
            continue
        # Dokument, który jest samą pętlą po pustej liście, wyszedłby jako plik bez
        # jednej litery — w składaniu operatu widać go wtedy jako pusty kafelek i nie
        # wiadomo, czy to usterka, czy zapomniane dane. Mówimy o tym wprost.
        if dodatkowy.wymaga and not dane.get(dodatkowy.wymaga):
            ostrzezenia.append(
                f"„{dodatkowy.nazwa}” nie powstał, bo nie wypełniłeś ani jednej pozycji. "
                "Uzupełnij dane i popraw operat, a dokument się dołoży.")
            continue
        try:
            generator.dopisz_dokument(
                warianty.z_wariantem(dodatkowy, wybor_wariantow.get(dodatkowy.id, "")),
                kontekst, katalog)
            wypelnionych += 1
            aktualne.add(operaty.nazwa_dokumentu(dodatkowy.id))
        except Exception as blad:
            zapisz_blad(request, blad)
            ostrzezenia.append(
                f"Nie udało się wygenerować dokumentu „{dodatkowy.nazwa}” — sprawdź "
                f"znaczniki w pliku {dodatkowy.plik.name}. Reszta operatu jest gotowa.")
            # awaria to nie odznaczenie — stary plik zostaje, bo jest lepszy niż dziura
            aktualne.add(operaty.nazwa_dokumentu(dodatkowy.id))

    # Poprawianie nadpisuje pliki nazwa po nazwie, więc dokument odznaczony w tej
    # rundzie (albo pominięty przez `wymaga`) zostawał w katalogu z danymi
    # z poprzedniej — szedł potem do scalonego PDF-a, choć spis treści o nim milczał,
    # a przy pustym wykazie program ogłaszał „nie powstał”, mając jego starą wersję
    # na dysku. Sprzątamy wyłącznie nazwy nadawane przez program: mapy i skany
    # dołożone Eksploratorem zostają.
    if poprawiany:
        programowe = {operaty.nazwa_dokumentu(s["id"]) for s in szablony.lista_skrocona()}
        for nazwa in operaty.usun_dokumenty_programu(katalog, programowe - aktualne):
            ostrzezenia.append(
                f"Nie udało się usunąć nieaktualnego pliku „{nazwa}” — pewnie jest "
                "otwarty w Wordzie. Zamknij go i usuń z katalogu operatu ręcznie, "
                "inaczej wejdzie do złożonego PDF-a.")

    # Wybrane formatki zostają domyślne na **następny** operat. Wybór dla tego operatu
    # siedzi w jego `operat.json` (razem z danymi formularza), więc „Popraw” wróci
    # do formatek, którymi ten operat naprawdę powstał.
    warianty.zapamietaj(wybor_wariantow)

    # Podglądy robimy w tle, zaraz po wygenerowaniu. Zanim brat przejdzie na stronę
    # składania, PDF-y zwykle są już gotowe i miniatury pokazują się od razu.
    threading.Thread(target=_przygotuj_podglady_po_cichu, args=(katalog,),
                     daemon=True).start()

    # Poprawianie operatu **nie jest** nowym operatem — tak samo jak nie zużywa numeru.
    # Dokumenty liczymy za każdym razem, bo za każdym razem program je naprawdę wypełnia.
    statystyki.zlicz(statystyki.DOKUMENT, wypelnionych)
    if not poprawiany:
        statystyki.zlicz(statystyki.OPERAT)

    # Notatka do `operat.json` — po `zaloz()`, które przepisuje ten plik od nowa.
    operaty.zapisz_notatke(katalog, notatka)

    tytul = kontekst.get("nr_roboty") or katalog.name
    if poprawiany:
        db.zaktualizuj_dokument(poprawiany["id"], str(tytul), dane,
                                f"{katalog.name}/{plik.name}", katalog.name, notatka)
        dokument_id = poprawiany["id"]
    else:
        dokument_id = db.zapisz_dokument(
            szablon.id, str(tytul), f"{katalog.name}/{plik.name}", dane, katalog.name,
            str(kontekst.get("nr_operatu") or katalog.name), notatka)
    adres = f"/dokument/{dokument_id}"
    if ostrzezenia:
        adres += "?blad=" + quote(" ".join(ostrzezenia))
    return RedirectResponse(adres, status_code=303)


@app.get("/dokument/{dokument_id}", response_class=HTMLResponse)
def dokument(request: Request, dokument_id: int, blad: str | None = None):
    wiersz = db.dokument(dokument_id)
    if wiersz is None:
        return RedirectResponse("/", status_code=303)
    dane = json.loads(wiersz["dane_json"])
    # Pole TERYT jest w bazie słownikiem identyfikatorów — na stronie ma się pokazać
    # to, co człowiek rozpozna, a nie „4 wiersze”.
    czytelne = {
        klucz: (generator.pola_teryt(klucz, wartosc)[klucz]
                if isinstance(wartosc, dict) and "obreb" in wartosc else wartosc)
        for klucz, wartosc in dane.items()
    }

    # Surowy zapis wyboru formatek wygląda na liście danych jak „1 wierszy” — zdejmujemy
    # go stąd, ale niżej pokazujemy w osobnej grupie, po ludzku.
    czytelne.pop("warianty", None)

    szablon = szablony.szablon_po_id(wiersz["szablon"] or "")
    # Uwaga: `_listy_dokumentow` **przycina `szablon.pola`** — wyrzuca pola typu
    # `dokumenty`, dla których nie ma czego pokazać. Robi to dla formularza (żeby nie
    # została pusta karta z samym nagłówkiem), ale tutaj potrzebujemy pełnej listy pól,
    # bo właśnie tym przyciętym trzeba się zająć. Stąd kopia zrobiona **przed** wywołaniem.
    pola = list(szablon.pola) if szablon else []
    listy = _listy_dokumentow(szablon) if szablon else {}
    nazwy_dokumentow = {d["id"]: d["nazwa_dokumentu"] for d in szablony.lista_skrocona()}

    for pole in pola:
        # Numer operatu nadaje program przy generowaniu, więc w danych z formularza jest
        # **pusty** — i musi taki zostać, bo te dane wracają do formularza przy „Powiel
        # jako nowy”; wpisany tam numer zostałby użyty drugi raz zamiast wziąć kolejny
        # z licznika. Ale na tej stronie pusta krata przy numerze operatu wygląda jak
        # usterka, więc pokazujemy numer, który operat naprawdę dostał — z bazy.
        if pole.typ == "auto_numer" and not czytelne.get(pole.klucz):
            czytelne[pole.klucz] = wiersz["nr_operatu"] or ""

        elif pole.typ == "dokumenty":
            # Pole bez `tylko` zbiera dokumenty, których nie wziął żaden inny kafelek.
            # Gdy wszystkie są już rozdane, nie ma z czego wybierać i **formularz w ogóle
            # go nie pokazuje** — więc na liście wpisanych danych też nie ma czego pokazać.
            # Zostawała po nim krata „0 wierszy”, czyli informacja o niczym.
            if not listy.get(pole.klucz):
                czytelne.pop(pole.klucz, None)
                continue
            # a wybrane dokumenty piszemy tak, jak nazywa je reszta programu,
            # zamiast identyfikatorami plików („sprawozdanie_techniczne_wzor”)
            czytelne[pole.klucz] = "; ".join(
                nazwy_dokumentow.get(str(i), str(i)) for i in (czytelne.get(pole.klucz) or []))

    grupy = _dane_w_grupach(pola, czytelne)
    uzyte = _uzyte_formatki(dane.get("warianty") or {}, nazwy_dokumentow)
    if uzyte:
        grupy.append({"nazwa": "Użyte formatki", "pola": uzyte})

    # Czy katalog jest na dysku — liczone tak samo jak na liście: operat przeniesiony
    # do archiwum zostaje w historii, ale nie ma czego składać ani kasować z dysku.
    return _widok(request, "dokument.html", dokument=wiersz, blad=blad, grupy=grupy,
                  na_dysku=bool(wiersz["katalog"]) and (WYNIKI / wiersz["katalog"]).is_dir())


def _uzyte_formatki(wybor: dict[str, str],
                    nazwy_dokumentow: dict[str, str]) -> list[dict[str, Any]]:
    """Które dokumenty powstały z **własnej** formatki, a nie ze standardowej.

    Standardowych nie wymieniamy: to domyślny stan i wypisywanie go przy każdym operacie
    byłoby szumem. Ale gdy operat wyszedł z własnej formatki, po samym dokumencie nie
    widać tego z niczego — a to jest właśnie ta informacja, której szuka się po miesiącu,
    gdy operat wygląda inaczej niż pozostałe.

    Formatkę można w międzyczasie usunąć. Piszemy o tym wprost, bo poprawianie takiego
    operatu wróci już do standardowej i dokument wyjdzie inny niż leżący na dysku.
    """
    pozycje: list[dict[str, Any]] = []
    for kategoria, identyfikator in sorted(wybor.items()):
        if not identyfikator:
            continue                      # standardowa formatka — nie ma o czym pisać
        nazwa = identyfikator.partition(warianty.ROZDZIELNIK)[2] or identyfikator
        if warianty.plik(identyfikator) is None:
            nazwa += " (formatka już usunięta)"
        pozycje.append({"klucz": nazwy_dokumentow.get(kategoria, kategoria),
                        "wartosc": nazwa})
    return pozycje


def _wypelnione_sekcje(pole: szablony.Pole, wartosc: Any) -> list[dict[str, Any]]:
    """Powtarzalne sekcje rozpisane na to, co naprawdę wpisano.

    Bez tego strona operatu pokazywała przy wykazach samo „2 wierszy” — liczbę, po której
    nie da się sprawdzić ani numeru działki, ani co się w niej zmieniło. A po to właśnie
    wchodzi się w gotowy operat: żeby zobaczyć, z czym się go oddało.

    Puste atrybuty pomijamy. Wykaz budynku ma ich piętnaście, a wypełnione bywają dwa —
    reszta byłaby ścianą kresek zasłaniającą to, co istotne.
    """
    if pole.typ != "sekcje" or not isinstance(wartosc, list):
        return []
    kolumny = [k.get("klucz", "") for k in pole.kolumny]
    nazwa = pole.etykieta_pozycji or "Pozycja"

    sekcje: list[dict[str, Any]] = []
    for numer, wpis in enumerate(wartosc, start=1):
        if not isinstance(wpis, dict):
            continue
        # pola dotyczące całej pozycji (numer działki) — nad tabelą stanów, tak jak
        # w formularzu i jak w nagłówku strony w gotowym dokumencie
        # Etykieta zostaje w danych — widok decyduje, czy ją pokazać: przy sekcji
        # z tabelą wartość dopisuje się do nagłówka („Działka 1: 119/80”, bo etykieta
        # powtarzałaby wyraz z nagłówka), a w sekcji płaskiej, gdzie tabeli nie ma,
        # pary „etykieta: wartość” są jedyną treścią.
        wspolne = [{"etykieta": pod.get("etykieta_krotka") or pod.get("etykieta", pod["klucz"]),
                    "wartosc": str(wpis.get(pod["klucz"], "") or "")}
                   for pod in pole.podpola_wspolne if wpis.get(pod["klucz"])]
        # Wiersz z podziałem (OFU, OZU, OZK, PPU) daje po jednej komórce na podkolumnę
        # w każdym stanie — tak samo jak w dokumencie i w formularzu.
        podkolumny = [k.get("klucz", "") for k in pole.podkolumny]
        wiersze = []
        for wiersz in pole.wiersze_sekcji:
            if wiersz["podzial"]:
                komorki = [str(wpis.get(
                    wiersz["podzial"].get(kolumna, {}).get(podkolumna, {}).get("klucz", ""),
                    "") or "") for kolumna in kolumny for podkolumna in podkolumny]
            else:
                komorki = [str(wpis.get(wiersz["pola"][k]["klucz"], "") or "")
                           if k in wiersz["pola"] else "" for k in kolumny]
            if any(komorki):
                wiersze.append({"etykieta": wiersz["etykieta"], "komorki": komorki,
                                "podzielony": bool(wiersz["podzial"])})
        if not kolumny:          # sekcja bez układu tabelarycznego — płaska lista pól
            # tylko podpola z `wiersz`: te bez niego są już wyżej w `wspolne`
            # i wypisane drugi raz robiłyby z podglądu echo
            wiersze = [{"etykieta": pod.get("etykieta", pod["klucz"]),
                        "komorki": [str(wpis.get(pod["klucz"], "") or "")]}
                       for pod in pole.podpola
                       if pod.get("wiersz") and wpis.get(pod["klucz"])]
        if wiersze or wspolne:
            sekcje.append({"naglowek": f"{nazwa} {numer}", "wspolne": wspolne,
                           "wiersze": wiersze})
    return sekcje


def _dane_w_grupach(pola: list[szablony.Pole],
                    wartosci: dict[str, Any]) -> list[dict[str, Any]]:
    """Wpisane dane w kolejności i grupach **z opisu szablonu**, a nie z bazy.

    Dane w bazie leżą w kolejności, w jakiej przyszły z formularza, więc na stronie
    operatu numer roboty sąsiadował z opisem przebiegu, a daty stały w trzech miejscach.
    Kolejność i grupy są już opisane w pliku `.json` obok szablonu — to samo, po czym
    formularz układa karty — więc bierzemy je stamtąd. Zmiana układu nie wymaga wtedy
    ruszania kodu, dokładnie tak jak przy formularzu.

    Pola, których nie ma w szablonie (dane po skasowanym polu, ślad po starszej wersji
    formatki), lądują na końcu — lepiej pokazać je bez grupy niż zgubić.
    """
    # Grupy scalamy po nazwie, tak samo jak `Szablon.grupy` przy budowaniu formularza:
    # pole tej samej grupy dopisane na końcu szablonu ma trafić do niej, a nie założyć
    # drugiego bloku o tym samym nagłówku. Kolejność bloków wyznacza pierwsze wystąpienie.
    grupy: dict[str, list[dict[str, Any]]] = {}
    uzyte: set[str] = set()

    # `html` mówi widokowi, że wartość wolno pokazać jako HTML. Zaznaczamy tak **wyłącznie**
    # pola opisane w szablonie jako przyjmujące formatowanie — ich treść przeszła przez
    # `tekst.oczysc`. Reszta zostaje eskejpowana, bo bierze się wprost z tego, co ktoś
    # wpisał, i nawias trójkątny w uwagach nie ma prawa stać się znacznikiem.
    def dopisz(nazwa: str, klucz: str, html: bool = False, sekcje: list | None = None,
               kolumny: list | None = None, podkolumny: list | None = None,
               etykieta: str = "") -> None:
        grupy.setdefault(nazwa, []).append(
            {"klucz": klucz, "etykieta": etykieta or klucz,
             "wartosc": wartosci[klucz], "html": html,
             "sekcje": sekcje or [], "kolumny": kolumny or [],
             "podkolumny": podkolumny or []})
        uzyte.add(klucz)

    for pole in pola:
        if pole.klucz in wartosci and pole.klucz not in uzyte:
            # Etykieta z opisu szablonu — ta sama, którą brat widzi w formularzu.
            # Klucz techniczny („wykazy_dzialek”) nic mu nie mówi; zostaje przy polach
            # spoza szablonu, bo tam nie ma czego wziąć.
            dopisz(pole.grupa, pole.klucz, html=pole.formatowanie,
                   etykieta=pole.etykieta,
                   sekcje=_wypelnione_sekcje(pole, wartosci[pole.klucz]),
                   kolumny=[k.get("etykieta", "") for k in pole.kolumny],
                   podkolumny=[k.get("etykieta", "") for k in pole.podkolumny])
    for klucz in wartosci:
        if klucz not in uzyte:
            dopisz("Pozostałe dane", klucz)
    return [{"nazwa": nazwa, "pola": lista} for nazwa, lista in grupy.items()]


@app.post("/dokument/{dokument_id}/otworz-katalog")
def otworz_katalog_dokumentu(request: Request, dokument_id: int, powrot: str | None = None):
    # Skąd przyszło kliknięcie, tam wracamy: z listy operatów na listę, ze strony
    # operatu na stronę operatu. Brat kliknął „Otwórz katalog”, a nie „pokaż operat” —
    # strona zmieniająca się pod Eksploratorem wyglądała jak pomyłka. Cel jest wybierany
    # z dwóch wpisanych tu adresów, a nie brany z formularza, żeby nie dało się nim
    # odesłać nigdzie indziej.
    cel = "/" if powrot == "lista" else f"/dokument/{dokument_id}"
    wiersz = db.dokument(dokument_id)
    if wiersz is None:
        # Stara karta po skasowaniu operatu — komunikat o archiwum mówiłby „wpis
        # w historii zostaje” nad listą, na której tego wpisu już nie ma.
        return RedirectResponse("/?blad=" + quote(
            "Tego operatu nie ma już w historii — pewnie został usunięty."), status_code=303)
    katalog = operaty.katalog_po_nazwie(wiersz["katalog"] or "")
    if katalog is None:
        return RedirectResponse(cel + "?blad=" + quote(
            "Katalogu tego operatu nie ma już w wyniki — pewnie przeniesiony "
            "do archiwum. Wpis w historii zostaje, ale nie ma czego otworzyć."),
            status_code=303)
    return _otworz(request, katalog, cel)


@app.post("/scal/{nazwa}/otworz-katalog")
def otworz_katalog_operatu(request: Request, nazwa: str, powrot: str | None = None):
    # `powrot=lista` — z wiersza „spoza historii” na liście (operat bez wpisu w bazie,
    # więc trasa po identyfikatorze nie ma jak go znaleźć); wraca na listę jak reszta.
    katalog = operaty.katalog_po_nazwie(nazwa)
    if katalog is None:
        return RedirectResponse("/?blad=" + quote(
            f"Katalogu operatu „{nazwa}” nie ma już w wyniki — pewnie przeniesiony "
            "do archiwum."), status_code=303)
    return _otworz(request, katalog, "/" if powrot == "lista" else f"/scal/{quote(nazwa)}")


def _otworz(request: Request, katalog: Path, powrot: str) -> RedirectResponse:
    """Otwiera katalog w Eksploratorze. Program chodzi u brata, więc okno wyskoczy u niego."""
    try:
        operaty.otworz_w_systemie(katalog)
    except Exception as blad:
        zapisz_blad(request, blad)
        return RedirectResponse(
            powrot + "?blad=" + quote(
                "Nie udało się otworzyć katalogu. Znajdziesz go ręcznie: "
                f"wyniki\\{katalog.name}"),
            status_code=303)
    return RedirectResponse(powrot, status_code=303)


@app.post("/dokument/{dokument_id}/usun")
def usun(dokument_id: int):
    """Kasuje operat razem z katalogiem — czyli także z plikami dołożonymi ręcznie.

    Strona pyta o potwierdzenie, podając nazwę katalogu i liczbę plików w środku,
    żeby nikt nie skasował map i skanów w ciemno.
    """
    wiersz = db.dokument(dokument_id)
    if wiersz:
        katalog = operaty.katalog_po_nazwie(wiersz["katalog"] or "")
        # Podglądy kasujemy po nazwie, nie po katalogu: operat bywa usuwany z historii
        # wtedy, gdy jego folder brat już przeniósł do archiwum — a wtedy `katalog`
        # jest `None` i podglądy zostawałyby na zawsze.
        operaty.usun_podglady(wiersz["katalog"] or "")
        if katalog is not None:
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

@app.get("/scal")
def scal_lista(blad: str | None = None):
    """Została po osobnej stronie z listą operatów — dziś lista jest jedna, na `/`.

    Trasy nie kasujemy: prowadzi tu kilkanaście przekierowań z obsługi błędów, zakładka
    w przeglądarce brata i „Wróć do listy” ze starych stron. Ma po prostu odesłać tam,
    gdzie ta lista jest teraz, razem z komunikatem, jeśli jakiś był.
    """
    return RedirectResponse("/?blad=" + quote(blad) if blad else "/", status_code=303)


@app.get("/scal/{nazwa}", response_class=HTMLResponse)
def scal_katalog(request: Request, nazwa: str, blad: str | None = None,
                 zlozono: bool = False):
    katalog = operaty.katalog_po_nazwie(nazwa)
    if katalog is None:
        # Zwykle: operat przeniesiony do archiwum, a brat wszedł tu z zakładki albo
        # ze starego adresu. Odesłanie bez słowa wygląda jak zepsuty program.
        return RedirectResponse("/?blad=" + quote(
            f"Operatu „{nazwa}” nie ma już w katalogu wyniki — pewnie przeniesiony "
            "do archiwum. Żeby złożyć z niego PDF, skopiuj folder z powrotem."),
            status_code=303)
    # liczby stron nie liczymy: dla plików Worda wymagałaby konwersji całej listy,
    # a miniatury i tak dociągają się leniwie, dopiero gdy przeglądarka o nie poprosi
    # Kolejność i obroty zapamiętane przy poprzednim składaniu; nowe pliki na końcu.
    pozycje = [{"nazwa": p.name, "word": p.suffix.lower() != ".pdf", "obrot": kat}
               for p, kat in operaty.pliki_ulozone(katalog)]
    nazwa_pliku = operaty.nazwa_wyniku(katalog)
    return _widok(request, "scal_katalog.html", katalog=katalog.name,
                  opis=operaty.opis(katalog), pozycje=pozycje,
                  wynik=nazwa_pliku, wynik_gotowy=(katalog / nazwa_pliku).exists(),
                  zlozono=zlozono, blad=blad)


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


@app.get("/scal/{nazwa}/wynik")
def scal_wynik(nazwa: str):
    """Złożony PDF pod stałym adresem — stąd otwiera go nowa karta."""
    katalog = operaty.katalog_po_nazwie(nazwa)
    if katalog is None:
        return RedirectResponse("/scal", status_code=303)
    plik = katalog / operaty.nazwa_wyniku(katalog)
    if not plik.exists():
        return RedirectResponse(f"/scal/{quote(nazwa)}", status_code=303)
    return FileResponse(plik, filename=plik.name, media_type="application/pdf",
                        content_disposition_type="inline")


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
    uklad_kolejnosc: list[str] = []          # do zapamiętania w operat.json
    uklad_obroty: dict[str, int] = {}
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
        uklad_kolejnosc.append(zrodlo.name)
        uklad_obroty[zrodlo.name] = obroty[gotowy]

    if not wybrane:
        return niepowodzenie("Nie wybrano żadnych plików do połączenia.")

    wynik = katalog / operaty.nazwa_wyniku(katalog)
    try:
        pdf.polacz_pdf(wybrane, wynik, etykiety, obroty)
    except pdf.BladPliku as blad:
        return niepowodzenie(str(blad))
    statystyki.zlicz(statystyki.PDF)      # dopiero tutaj: PDF naprawdę leży na dysku
    # Układ zapamiętujemy po udanym złożeniu — nieudana próba nie ma prawa nadpisać
    # tego, co brat ustawił poprzednio.
    operaty.zapisz_uklad(katalog, uklad_kolejnosc, uklad_obroty)
    # Nie odsyłamy pliku prosto w odpowiedzi na POST: formularz z target="_blank" bywa
    # blokowany i wtedy kliknięcie „Złóż PDF” nie robi *nic*, co dla brata wygląda jak
    # zepsuty program. Wracamy więc na stronę układania z potwierdzeniem, a gotowy PDF
    # otwiera się w nowej karcie zwykłym linkiem — tego żadna przeglądarka nie blokuje.
    return RedirectResponse(f"/scal/{quote(nazwa)}?zlozono=1", status_code=303)


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
                  teryt_stan=teryt.stan(), rodzaje=szablony.lista_skrocona(),
                  wlasne_formatki=warianty.wszystkie(),
                  opisy_sprawozdania=db.opisy_sprawozdania())


# --- opisy sprawozdania ------------------------------------------------------

@app.post("/ustawienia/opisy")
async def dodaj_opis(request: Request):
    """Dokłada gotowy opis do biblioteki. Oba pola muszą być wypełnione.

    Nazwa jest do rozpoznania opisu na liście, więc pusta nie ma sensu; pusty opis
    to pozycja, która niczego nie wstawi. Zamiast zapisywać takie wpisy i zostawiać
    brata z zagadką, mówimy o tym wprost.
    """
    formularz_danych = await request.form()
    nazwa = str(formularz_danych.get("nazwa") or "").strip()
    # Opis przychodzi z edytora, czyli jako fragment HTML — przepuszczamy go przez
    # `tekst.oczysc`, bo wraca potem na stronę jako HTML i jedzie do dokumentu.
    opis = tekst.oczysc(str(formularz_danych.get("opis") or ""))

    if not nazwa or not tekst.na_zwykly_tekst(opis):
        brakuje = "nazwę" if not nazwa else "treść opisu"
        return RedirectResponse(
            "/ustawienia?blad=" + quote(f"Uzupełnij {brakuje} — bez tego opisu nie zapiszę."),
            status_code=303)

    db.dodaj_opis_sprawozdania(nazwa, opis)
    return RedirectResponse(
        "/ustawienia?komunikat=" + quote(f"Opis „{nazwa}” zapisany.") + "#opisy",
        status_code=303)


@app.post("/ustawienia/opisy/usun")
async def usun_opis(request: Request):
    formularz_danych = await request.form()
    try:
        opis_id = int(str(formularz_danych.get("opis") or ""))
    except ValueError:
        return RedirectResponse("/ustawienia#opisy", status_code=303)

    db.usun_opis_sprawozdania(opis_id)
    return RedirectResponse(
        "/ustawienia?komunikat=" + quote("Opis usunięty.") + "#opisy", status_code=303)


# --- własne formatki ---------------------------------------------------------

@app.post("/ustawienia/formatki")
async def dodaj_formatke(request: Request):
    """Przyjmuje wgrany plik .docx jako kolejny wariant wybranego rodzaju dokumentu."""
    formularz_danych = await request.form()
    kategoria = str(formularz_danych.get("kategoria") or "")
    przeslany = formularz_danych.get("plik")

    # UploadFile bierzemy ze Starlette, nie z FastAPI: `request.form()` tworzy obiekty
    # klasy nadrzędnej, więc `isinstance(..., fastapi.UploadFile)` jest zawsze fałszem
    # i wgrany plik znika bez śladu (kosztowało to już raz działające scalanie).
    if not isinstance(przeslany, UploadFile) or not przeslany.filename:
        return RedirectResponse(
            "/ustawienia?blad=" + quote("Nie wybrano pliku."), status_code=303)

    try:
        wariant, ostrzezenia = warianty.dodaj(kategoria, przeslany.filename, przeslany.file)
    except warianty.BladWariantu as blad:
        return RedirectResponse("/ustawienia?blad=" + quote(str(blad)), status_code=303)
    except Exception as blad:
        zapisz_blad(request, blad)
        return RedirectResponse(
            "/ustawienia?blad=" + quote("Nie udało się wgrać tego pliku."), status_code=303)

    komunikat = f"Dodano formatkę „{wariant['nazwa']}”. Wybierzesz ją na dole formularza."
    if ostrzezenia:
        return RedirectResponse("/ustawienia?blad=" + quote(" ".join(ostrzezenia)),
                                status_code=303)
    return RedirectResponse("/ustawienia?komunikat=" + quote(komunikat), status_code=303)


@app.post("/ustawienia/formatki/usun")
async def usun_formatke(request: Request):
    """Kasuje plik formatki. Operaty nią zrobione zostają nietknięte."""
    formularz_danych = await request.form()
    identyfikator = str(formularz_danych.get("wariant") or "")
    if warianty.usun(identyfikator):
        return RedirectResponse(
            "/ustawienia?komunikat=" + quote(
                "Formatka usunięta. Gotowe operaty zostają bez zmian — kasujemy tylko "
                "wzór na przyszłość."), status_code=303)
    return RedirectResponse("/ustawienia?blad=" + quote("Nie ma już takiej formatki."),
                            status_code=303)


@app.post("/tekst/oczysc")
async def tekst_oczysc(request: Request):
    """Czyści wklejony fragment HTML — woła to edytor w przeglądarce przy każdym wklejeniu.

    Edytor mógłby czyścić sam, ale wtedy lista dozwolonych znaczników istniałaby dwa razy
    (raz w JS, raz tutaj) i po pierwszej zmianie zaczęłaby się rozjeżdżać. Tak zostaje
    jedna, ta sprawdzona testami; program chodzi na `127.0.0.1`, więc to jest kilka
    milisekund. Gdy zapytanie padnie, edytor wkleja czysty tekst — patrz `formularz.html`.
    """
    dane = await request.json()
    return JSONResponse({"html": tekst.oczysc(str(dane.get("html") or ""))})


# --- TERYT: listy do pól kaskadowych i pobieranie danych ---------------------

@app.get("/teryt/lista")
def teryt_lista(poziom: str, rodzic: str | None = None):
    """Zasila listy rozwijane w formularzu. Zwraca JSON, bo woła to JavaScript."""
    if poziom not in ("wojewodztwo", "powiat", "gmina"):
        return JSONResponse({"pozycje": [], "blad": "Nieznany poziom podziału."},
                            status_code=400)
    return JSONResponse({"pozycje": teryt.potomkowie(rodzic or None, poziom)})


@app.get("/teryt/dzialka")
def teryt_dzialka(obreb: str, numery: str):
    """Czy ULDK zna te działki. `numery` bywa listą: „123/4, 123/5”.

    Podpowiedź, nigdy blokada — dlatego stan „nieznane” (ULDK milczy) jest osobny
    od „brak” i nie może wyglądać jak błąd numeru.
    """
    wyniki = []
    for numer in [n.strip() for n in numery.replace(";", ",").split(",") if n.strip()][:10]:
        wyniki.append({"numer": numer, **teryt.sprawdz_dzialke(obreb, numer)})
    return JSONResponse({"wyniki": wyniki})


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


@app.get("/pomoc/historia", response_class=HTMLResponse)
def historia_wersji(request: Request):
    return _widok(request, "historia.html", wpisy=zmiany.wpisy())

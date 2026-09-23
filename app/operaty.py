"""Katalog operatu: jeden folder na jedną robotę.

Każde wygenerowanie dokumentu zakłada w `wyniki/` katalog nazwany **numerem operatu**
i wkłada do niego `spis_tresci.docx`. Brat dorzuca tam potem swoje pliki — mapy, szkice,
skany, wykaz współrzędnych z C-Geo — a na końcu wszystko skleja się w jeden PDF.

**Nazwa scalonego PDF-a musi być dokładnie taka jak numer roboty (KERG)** — tego wymagają
przepisy, więc nie przepuszczamy jej przez `bezpieczna_nazwa`, która gubi polskie znaki.
Podmieniamy wyłącznie znaki, których Windows w nazwie pliku nie przyjmie, i mówimy
o tym głośno, gdy do tego dojdzie.

W katalogu leżą dwa pliki opisujące robotę:

* `operat.json` — źródło prawdy dla programu (numer roboty, numer operatu, data, dane
  z formularza). Dzięki niemu katalog jest samowystarczalny: przeżyje skopiowanie na inny
  dysk i utratę bazy przy reinstalacji,
* pusty plik o nazwie numeru roboty — wyłącznie po to, żeby brat widział numer w Eksploratorze
  bez otwierania czegokolwiek. Nie ma rozszerzenia, więc nigdy nie wejdzie do sklejania.
"""
from __future__ import annotations

import errno
import json
import os
import shutil
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

from . import pdf
from .config import DANE, WYNIKI

PLIK_OPISU = "operat.json"
SPIS_TRESCI = "spis_tresci.docx"      # ten plik zawsze idzie pierwszy przy sklejaniu
SUFIKS_WZORU = "_wzor"

ROZSZERZENIA_PDF = {".pdf"}
ROZSZERZENIA_WORD = {".docx", ".doc", ".rtf", ".odt"}
ROZSZERZENIA_DO_SCALENIA = ROZSZERZENIA_PDF | ROZSZERZENIA_WORD

# Windows nie przyjmie tych znaków w nazwie pliku ani katalogu.
ZNAKI_ZAKAZANE = r'<>:"/\|?*'

# Pliki Worda z katalogu operatu zamieniamy na PDF poza katalogiem — inaczej powstały
# PDF zostałby przy następnym sklejaniu policzony drugi raz, obok swojego .docx.
PODGLADY = DANE / "podglad"

# Pilnuje, żeby ten sam plik nie był konwertowany kilka razy naraz.
_BLOKADA_PODGLADU = threading.Lock()

# Tyle zapis dokumentu czeka na podgląd, który trzyma jego plik (`zapisz_dokument`).
# Zwykły podgląd kompletu to kilka–kilkanaście sekund; dłużej trzyma tylko Word
# zawieszony na oknie — a na niego czekać do limitu strażnika (minuty) nie ma sensu.
CZEKAJ_NA_PODGLAD = 60


class PlikWPodgladzie(PermissionError):
    """Dokumentu nie da się zapisać, bo trzyma go podgląd robiony w tle — nie Word brata."""


def nazwa_bezpieczna(tekst: str, zapas: str = "operat") -> tuple[str, bool]:
    """Zwraca (nazwa, czy_podmieniono). Zostawia polskie znaki — zmienia tylko zakazane."""
    oczyszczona = "".join("-" if z in ZNAKI_ZAKAZANE or ord(z) < 32 else z for z in tekst)
    oczyszczona = oczyszczona.strip().rstrip(". ")      # Windows nie lubi kropki na końcu
    return (oczyszczona or zapas), oczyszczona != tekst.strip()


class KatalogZajety(Exception):
    """Nowy operat miałby wejść do katalogu, w którym leży już inny operat."""

    def __init__(self, katalog: Path):
        super().__init__(f"Katalog {katalog.name} należy już do innego operatu")
        self.katalog = katalog


# --- zakładanie i opis -------------------------------------------------------

def nazwa_katalogu(nr_operatu: str) -> str:
    """'001/2026' -> '001.2026'.

    Numer operatu zostaje z ukośnikiem — tak wygląda w dokumencie i tak go czyta ośrodek.
    Katalog dostaje w tym miejscu kropkę, bo Windows ukośnika w nazwie folderu nie przyjmie,
    a myślnik czytało się gorzej niż kropka.
    """
    return nazwa_bezpieczna(nr_operatu.replace("/", "."))[0]


def katalog_operatu(nr_operatu: str) -> Path:
    return WYNIKI / nazwa_katalogu(nr_operatu)


def zaloz(nr_operatu: str, nr_roboty: str, szablon: str, dane: dict[str, Any],
          poprzedni_numer_roboty: str = "", nowy: bool = False,
          wpis: int | None = None) -> tuple[Path, list[str]]:
    """Tworzy albo odświeża katalog operatu z opisem.

    Zwraca (katalog, ostrzeżenia dla użytkownika). Wołane też przy poprawianiu operatu —
    wtedy katalog już istnieje i tylko nadpisujemy `operat.json`.

    `nowy=True` (nowy operat, nie poprawka) to ostatnia zapora: katalog, w którym leży
    już `operat.json`, należy do innego operatu, więc zamiast wejść do niego i nadpisać
    mu opis i dokumenty, rzucamy `KatalogZajety`. Licznik takich numerów nie wydaje
    (`generator.najwyzszy_znany_numer`), a numer wpisany z ręki sprawdza strażnik
    w `main.generuj` — zapora jest na to, czego żadne z nich nie przewidziało.
    Katalog bez `operat.json` (założony przez brata z góry, z mapami na nową robotę)
    operatem nie jest i nowy operat do niego wchodzi, jak dotąd.

    `wpis` = numer wpisu w historii, do którego należy katalog (przy poprawianiu) — patrz
    `oznacz_wpis`. Zapisujemy go już tutaj, przed dokumentem: własność sprawdza się przed
    poprawką, więc nieudany zapis nie może jej przerzucić na inny wpis.
    """
    # Ukośnik w nazwie katalogu zamieniamy na kropkę po cichu — to norma, a nie usterka
    # warta straszenia użytkownika.
    ostrzezenia: list[str] = []
    nazwa = nazwa_katalogu(nr_operatu)
    katalog = WYNIKI / nazwa
    if nowy and (katalog / PLIK_OPISU).exists():
        raise KatalogZajety(katalog)
    katalog.mkdir(parents=True, exist_ok=True)

    poprzedni = opis(katalog)          # przy poprawianiu operatu plik już tu jest
    nowy_opis = {
        "nr_operatu": nr_operatu,
        "nr_roboty": nr_roboty,
        "szablon": szablon,
        "utworzono": datetime.now().isoformat(timespec="seconds"),
        "dane": dane,
    }
    # Układ kafelków zostaje: poprawianie operatu przepisuje ten plik od nowa, a brat
    # ustawiał kolejność i obroty myszą — skasowanie tego przy literówce w formularzu
    # byłoby dla niego niezrozumiałe.
    if poprzedni.get("uklad"):
        nowy_opis["uklad"] = poprzedni["uklad"]
    # Notatka („Opis” w interfejsie) z tego samego powodu. Wpisuje ją `zapisz_notatke`
    # zaraz po wygenerowaniu, więc świadomą zmianę i tak zobaczymy — przenosimy ją tutaj
    # po to, żeby żadne inne wywołanie `zaloz` nie skasowało jej po cichu.
    if poprzedni.get("notatka"):
        nowy_opis["notatka"] = poprzedni["notatka"]
    if wpis is not None or poprzedni.get("wpis") is not None:
        nowy_opis["wpis"] = wpis if wpis is not None else poprzedni["wpis"]
    # Nazwy złożonych PDF-ów też: po nich `pliki()` poznaje, że to wynik składania,
    # a nie plik brata — zgubione, zrobiłyby ze starego operatu kafelek.
    zlozone = _zlozone(poprzedni)
    # Przy poprawianiu numer roboty mógł się zmienić, a razem z nim nazwa złożonego
    # PDF-a. Stary plik zostawał wtedy w katalogu jako zwykły kafelek, włączony jak każdy
    # — i cały operat wchodził do nowego PDF-a. Tutaj tylko go zapisujemy w `zlozone`
    # (to już wystarcza, żeby nie był kafelkiem); usuwa go `usun_stary_wynik` dopiero
    # **po udanym** zapisie dokumentu — kasowany tu znikał także wtedy, gdy poprawka
    # padła (spis treści otwarty w Wordzie), a wiadomość o tym przepadała razem z nią.
    # `zlozone` tylko **ukrywa** kafelki; nic z tej listy nie jest kasowane.
    stary_wynik = (_nazwa_wyniku(str(poprzedni.get("nr_roboty") or ""), katalog)
                   if poprzedni else "")
    if (stary_wynik and stary_wynik.lower() != _nazwa_wyniku(nr_roboty, katalog).lower()
            and (katalog / stary_wynik).is_file() and stary_wynik not in zlozone):
        zlozone.append(stary_wynik)
    if zlozone:
        nowy_opis["zlozone"] = zlozone
    (katalog / PLIK_OPISU).write_text(json.dumps(nowy_opis, ensure_ascii=False, indent=2),
                                      encoding="utf-8")

    # Przy poprawianiu operatu numer roboty mógł się zmienić — stary pusty znacznik
    # trzeba sprzątnąć, żeby w katalogu nie leżały dwa numery naraz.
    if poprzedni_numer_roboty and poprzedni_numer_roboty != nr_roboty:
        stary = katalog / nazwa_bezpieczna(poprzedni_numer_roboty, zapas="")[0]
        # Kasujemy tylko wtedy, gdy plik jest pusty — czyli jest naszym znacznikiem.
        # Sprawdzanie rozszerzenia nic tu nie daje: numer roboty ma kropki, więc
        # „GK.6640.123.2026” wygląda dla Pythona jak plik z rozszerzeniem „.2026”.
        if stary.name and stary.is_file() and stary.stat().st_size == 0:
            stary.unlink(missing_ok=True)

    if nr_roboty:
        znacznik, podmieniono = nazwa_bezpieczna(nr_roboty, zapas="")
        if podmieniono:
            ostrzezenia.append(
                f"Numer roboty „{nr_roboty}” zawiera znaki zabronione w nazwach plików. "
                f"Scalony PDF będzie się nazywał „{znacznik}.pdf”, a nie dokładnie tak jak "
                "numer roboty — sprawdź, czy ośrodek to przyjmie.")
        if znacznik:
            (katalog / znacznik).touch()          # pusty plik, żeby numer było widać w folderze
    return katalog, ostrzezenia


def wycofaj_nowy(katalog: Path, usun_katalog: bool) -> None:
    """Sprząta po nowym operacie, którego dokument nie powstał.

    Zdejmujemy wyłącznie to, co założył `zaloz`: `operat.json` i pusty znacznik
    z numerem roboty, a sam katalog tylko wtedy, gdy to my go założyliśmy i został
    pusty — pliki brata (np. w katalogu założonym przez niego z góry) zostają.
    Niemo: wołane w trakcie obsługi błędu, więc nie może przykryć go własnym.
    """
    try:
        nr_roboty = str(opis(katalog).get("nr_roboty") or "")
        (katalog / PLIK_OPISU).unlink(missing_ok=True)
        znacznik = katalog / nazwa_bezpieczna(nr_roboty, zapas="")[0] if nr_roboty else None
        if znacznik and znacznik.is_file() and znacznik.stat().st_size == 0:
            znacznik.unlink()
        if usun_katalog and not any(katalog.iterdir()):
            katalog.rmdir()
    except OSError:
        pass


def nazwa_dokumentu(id_szablonu: str) -> str:
    """'spis_tresci_wzor' -> 'spis_tresci.docx'.

    Każdy szablon robi w katalogu operatu swój plik, nazwany tak jak szablon.
    Końcówkę „_wzor” obcinamy: to znak, że formatka jest do podmiany na własną,
    a nie część nazwy dokumentu.
    """
    rdzen = (id_szablonu[:-len(SUFIKS_WZORU)] if id_szablonu.endswith(SUFIKS_WZORU)
             else id_szablonu)
    return nazwa_bezpieczna(rdzen or id_szablonu, zapas="dokument")[0] + ".docx"


def opis(katalog: Path) -> dict[str, Any]:
    """Zawartość `operat.json`; pusty słownik, gdy pliku nie ma albo jest zepsuty.

    Także gdy w środku jest poprawny JSON, ale nie słownik (`[]`, `null` — ręczna edycja,
    przerwany zapis): każde wywołanie woła potem `.get`, a lista operatów, formularz
    i licznik czytają opisy wszystkich katalogów naraz, więc jeden taki plik
    wywracał całą stronę.
    """
    try:
        dane = json.loads((katalog / PLIK_OPISU).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return dane if isinstance(dane, dict) else {}


def usun_stary_wynik(katalog: Path, dawny_nr_roboty: str) -> list[str]:
    """Usuwa złożony PDF z dawnym numerem roboty **poprawianego wpisu**. Zwraca zdania
    dla brata.

    Wołane **po udanym** zapisie dokumentu przy poprawianiu, z numerem roboty, jaki ten
    wpis miał w historii przed poprawką. Stary złożony PDF jest nieaktualny (dawny numer
    w nazwie i w środku) — zostawiony, wyglądałby na gotowy operat. Liczymy go z historii,
    a nie z `operat.json`: tamten plik bywa cudzy (dwa wpisy z jednym katalogiem po
    dawnych błędach), a wtedy kasowalibyśmy PDF innego operatu. Kasujemy raz — przy tej
    poprawce, która zmienia numer roboty — więc plik, który brat odłoży potem pod tą
    nazwą (wersja wysłana do ośrodka), zostaje. Obecnego wyniku nie ruszamy: nadpisze
    go następne „Złóż PDF”. Plik, którego nie da się usunąć (otwarty w czytniku),
    zostaje, ale trafia do `zlozone`, więc nie wejdzie do nowego PDF-a.
    """
    obecny = nazwa_wyniku(katalog)
    dawny = _nazwa_wyniku(dawny_nr_roboty, katalog) if dawny_nr_roboty else ""
    plik = katalog / dawny
    if not dawny or dawny.lower() == obecny.lower() or not plik.is_file():
        return []
    try:
        plik.unlink()
    except OSError:
        dane = opis(katalog)
        if dane and dawny not in _zlozone(dane):
            dane["zlozone"] = _zlozone(dane) + [dawny]
            (katalog / PLIK_OPISU).write_text(json.dumps(dane, ensure_ascii=False, indent=2),
                                              encoding="utf-8")
        return [f"Numer roboty się zmienił, ale stary złożony PDF „{dawny}” jest otwarty "
                "w innym programie (pewnie w czytniku PDF) i został w katalogu. Zamknij go "
                "i usuń ręcznie — do nowego PDF-a i tak nie wejdzie."]
    return [f"Numer roboty się zmienił, więc usunąłem stary złożony PDF „{dawny}” — miał "
            f"w sobie dawny numer. Złóż operat jeszcze raz, żeby powstał „{obecny}”."]


def oznacz_wpis(katalog: Path, dokument_id: int) -> None:
    """Zapisuje w `operat.json`, do którego wpisu w historii należy katalog.

    Dwa wpisy z jednym katalogiem zostawiały dawne błędy numeracji; do tej pory
    własność poznawaliśmy tylko po numerze roboty, a ten zmienia się przy poprawianiu
    — nieudana poprawka przerzucała ją na drugi wpis. Numer wpisu jest trwały
    (`main._wlasciciel_katalogu` sprawdza go najpierw). Na innym komputerze wskazuje
    obcą bazę, ale wtedy nie pasuje do żadnego z wpisów i po prostu się nie liczy.
    """
    dane = opis(katalog)
    if not dane or dane.get("wpis") == dokument_id:
        return
    dane["wpis"] = dokument_id
    (katalog / PLIK_OPISU).write_text(json.dumps(dane, ensure_ascii=False, indent=2),
                                      encoding="utf-8")


def ustaw_numer(katalog: Path, nr_operatu: str, klucz: str) -> None:
    """Wpisuje nowy numer do `operat.json` katalogu przeniesionego pod nowy numer.

    Zaraz po przeniesieniu, jeszcze przed wypełnianiem dokumentów: gdyby wypełnianie
    padło, następne zwykłe „Popraw” wzięłoby stary numer z `operat.json` i założyło
    katalog obok. Numer wpisany kiedyś z ręki siedzi też w danych formularza (`klucz`).
    """
    dane = opis(katalog)
    if not dane:
        return
    dane["nr_operatu"] = nr_operatu
    if isinstance(dane.get("dane"), dict) and dane["dane"].get(klucz):
        dane["dane"][klucz] = nr_operatu
    (katalog / PLIK_OPISU).write_text(json.dumps(dane, ensure_ascii=False, indent=2),
                                      encoding="utf-8")


def usun_dokumenty_programu(katalog: Path, nazwy: set[str]) -> list[str]:
    """Kasuje wskazane dokumenty programu razem z ich podglądami. Zwraca to,
    czego usunąć **nie zdołała** — np. plik otwarty przez brata w Wordzie.

    Do sprzątania po poprawianiu operatu: pliki nadpisują się nazwa po nazwie, więc
    dokument odznaczony w tej rundzie (albo pominięty przez `wymaga`) zostawał
    w katalogu z danymi z poprzedniej — szedł potem do scalonego PDF-a, choć spis
    treści o nim milczał. Wołający podaje wyłącznie nazwy nadawane przez program
    (`nazwa_dokumentu`), więc mapy i skany dołożone ręcznie są poza zasięgiem.

    Pod `_BLOKADA_PODGLADU`, bo konwersja podglądów chodzi w tle: bez blokady
    kasowalibyśmy plik, który Word ma właśnie otwarty (na Windowsie `PermissionError`
    w środku trasy), a wątek podglądów odtwarzałby PDF skasowanego dokumentu.
    Blokadę bierzemy **tylko wtedy, gdy jest co kasować**: nazwy to wszystkie formatki
    spoza tej rundy, zwykle nieistniejące, a każde „Zapisz” przy poprawianiu stało
    dotąd za całą konwersją podglądów z poprzedniego zapisu — przy zawieszonym Wordzie
    do limitu strażnika. Pod blokadą sprawdzamy jeszcze raz, jak `przygotuj_podglady`.
    """
    istniejace = [nazwa for nazwa in sorted(nazwy) if (katalog / nazwa).is_file()]
    if not istniejace:
        return []
    # Podgląd na zawieszonym Wordzie trzyma blokadę minutami, a my siedzimy pod blokadą
    # zapisów — bez limitu stało każde następne „Zapisz”. Po limicie pliki zostają,
    # a wołający mówi o nich tak samo jak o pliku otwartym w Wordzie.
    if not _BLOKADA_PODGLADU.acquire(timeout=CZEKAJ_NA_PODGLAD):
        return istniejace
    zostawione: list[str] = []
    try:
        for nazwa in istniejace:
            plik = katalog / nazwa
            if not plik.is_file():
                continue
            try:
                plik.unlink()
            except OSError:
                zostawione.append(nazwa)          # zostaje jak przed poprawką — bez awarii
                continue
            (PODGLADY / katalog.name / (plik.stem + ".pdf")).unlink(missing_ok=True)
    finally:
        _BLOKADA_PODGLADU.release()
    return zostawione


def zapisz_dokument(dokument: Any, plik: Path) -> None:
    """Zapisuje wypełniony dokument Worda (`dokument.save`) w katalogu operatu.

    Plik bywa trzymany przez **nasz własny** podgląd: wątek w tle konwertuje dokumenty
    zaraz po „Zapisz”, a Word otwiera je „tylko do odczytu”, ale bez prawa zapisu dla
    innych (sprawdzone na prawdziwym Wordzie). Szybkie „Popraw” → „Zapisz” trafiało
    wtedy na `PermissionError`, a brat czytał „zamknij Worda”, choć żadnego nie miał
    otwartego. Przy odmowie czekamy więc na koniec podglądu i próbujemy jeszcze raz,
    już pod blokadą, żeby następny podgląd nie wszedł w pół zapisu. Druga odmowa to
    naprawdę Word brata — idzie dalej zwykłym `PermissionError`. Gdy podgląd nie kończy
    się w `CZEKAJ_NA_PODGLAD` (Word stanął na oknie), `PlikWPodgladzie` — z własnym
    komunikatem, bo „zamknij Worda” byłoby tu nieprawdą.

    Bez blokady przy zwykłym zapisie: brana zawsze, kazałaby każdemu „Zapisz” czekać
    na cały komplet podglądów, także gdy żaden nie dotyczy tego pliku.
    """
    try:
        dokument.save(plik)
        return
    except PermissionError:
        if not _BLOKADA_PODGLADU.acquire(timeout=CZEKAJ_NA_PODGLAD):
            raise PlikWPodgladzie(
                errno.EACCES, "Dokument trzyma podgląd robiony w tle", str(plik)) from None
    try:
        dokument.save(plik)
    finally:
        _BLOKADA_PODGLADU.release()


def zapisz_notatke(katalog: Path, tekst: str) -> None:
    """Notatka brata do operatu — w interfejsie „Opis”.

    Do dokumentu nie wchodzi: to jego własne uwagi do roboty (co jeszcze zostało,
    na co czeka), a nie dane do wypełnienia formatki. Trzymamy ją **i** w bazie,
    **i** tutaj, z tego samego powodu co numer operatu: `operat.json` jedzie razem
    z katalogiem, więc notatka przeżyje skopiowanie na inny dysk i utratę bazy,
    a wpis w historii przeżyje przeniesienie katalogu do archiwum.

    Osobno od `zaloz`, bo notatka nie ma nic wspólnego z wypełnianiem dokumentów
    i nie ma po co przechodzić przez generator.
    """
    dane = opis(katalog)
    if not dane:                     # katalogu nie ma albo plik jest połamany
        return
    dane["notatka"] = tekst
    (katalog / PLIK_OPISU).write_text(json.dumps(dane, ensure_ascii=False, indent=2),
                                      encoding="utf-8")


def lista() -> list[dict[str, Any]]:
    """Katalogi operatów, od najnowszego. Rozpoznajemy je po pliku operat.json."""
    wynik = []
    for sciezka in WYNIKI.iterdir() if WYNIKI.is_dir() else []:
        if not sciezka.is_dir() or not (sciezka / PLIK_OPISU).exists():
            continue
        dane = opis(sciezka)
        wynik.append({
            "katalog": sciezka.name,
            "nr_operatu": dane.get("nr_operatu", sciezka.name),
            "nr_roboty": dane.get("nr_roboty", ""),
            "utworzono": dane.get("utworzono", ""),
            "notatka": dane.get("notatka", ""),
            "plikow": len(pliki(sciezka)),
        })
    return sorted(wynik, key=lambda o: o["utworzono"], reverse=True)


def numery_katalogow() -> list[str]:
    """Nazwy katalogów operatów w `wyniki/` — z nich licznik czyta zajęte numery.

    Operaty skopiowane z innego komputera albo przywrócone po utracie bazy są tylko
    tutaj, a ich numery też są zajęte. Katalog bez `operat.json` nie jest operatem
    (brat zakłada czasem folder na nową robotę z góry) i się nie liczy. Same nazwy
    (katalog nazywa się numerem), bez czytania opisów: wołane przy każdym otwarciu
    formularza, a przy kilkuset operatach czytanie każdego `operat.json` było widać.
    """
    return [sciezka.name for sciezka in (WYNIKI.iterdir() if WYNIKI.is_dir() else [])
            if sciezka.is_dir() and (sciezka / PLIK_OPISU).is_file()]


def przenies(katalog: Path, nowa_nazwa: str) -> Path:
    """Przenosi katalog operatu pod nową nazwę (nowy numer operatu) i zwraca nowy.

    Jedzie wszystko: pliki brata, `operat.json` (układ kafelków, opis) i podglądy —
    dotąd zmiana numeru przy poprawianiu zakładała katalog obok i rozbijała operat na dwa.
    `FileExistsError`, gdy katalog o tej nazwie już jest (dwóch katalogów nie łączymy).
    Inny `OSError`, gdy Windows nie pozwala, bo w środku jest plik otwarty w Wordzie albo
    w czytniku — wtedy nic się nie zmienia. Pod `_BLOKADA_PODGLADU`, bo wątek podglądów
    może akurat konwertować coś z tego katalogu.
    """
    cel = WYNIKI / nowa_nazwa
    # bez limitu podgląd na zawieszonym Wordzie trzymałby tu zapis minutami (albo bez
    # końca); `PlikWPodgladzie` to `OSError`, więc wołający mówi „plik otwarty, nic nie
    # zostało zmienione” — i tak właśnie jest
    if not _BLOKADA_PODGLADU.acquire(timeout=CZEKAJ_NA_PODGLAD):
        raise PlikWPodgladzie(errno.EACCES, "Katalog trzyma podgląd robiony w tle", str(katalog))
    try:
        if cel.exists():               # Linux przemianowałby na pusty katalog bez słowa
            raise FileExistsError(errno.EEXIST, "Katalog już istnieje", str(cel))
        katalog.rename(cel)
        stare = PODGLADY / katalog.name
        if stare.is_dir():
            # resztki po operacie, który kiedyś miał ten numer, nie mogą udawać podglądów
            shutil.rmtree(PODGLADY / nowa_nazwa, ignore_errors=True)
            try:
                stare.rename(PODGLADY / nowa_nazwa)
            except OSError:
                shutil.rmtree(stare, ignore_errors=True)       # odtworzą się same
    finally:
        _BLOKADA_PODGLADU.release()
    return cel


def katalog_po_nazwie(nazwa: str) -> Path | None:
    """Zamienia nazwę z adresu na katalog — z blokadą wyjścia poza `wyniki/`."""
    kandydat = (WYNIKI / nazwa).resolve()
    if WYNIKI.resolve() not in kandydat.parents or not (kandydat / PLIK_OPISU).exists():
        return None
    return kandydat


# --- pliki w katalogu --------------------------------------------------------

def _nazwa_wyniku(nr_roboty: str, katalog: Path) -> str:
    return nazwa_bezpieczna(nr_roboty or katalog.name, zapas=katalog.name)[0] + ".pdf"


def nazwa_wyniku(katalog: Path) -> str:
    """Nazwa scalonego PDF-a: dokładnie numer roboty (przepisy), z .pdf na końcu."""
    return _nazwa_wyniku(str(opis(katalog).get("nr_roboty") or ""), katalog)


def _zlozone(dane: dict[str, Any]) -> list[str]:
    """Nazwy PDF-ów złożonych przez program w tym katalogu (`operat.json` → `zlozone`)."""
    zapisane = dane.get("zlozone")
    return [n for n in zapisane if isinstance(n, str)] if isinstance(zapisane, list) else []


def pliki(katalog: Path) -> list[Path]:
    """Co idzie do sklejenia: PDF-y i dokumenty Worda, spis treści zawsze pierwszy.

    Pomijamy opis operatu, pusty znacznik z numerem roboty (nie ma rozszerzenia)
    i wyniki sklejania — obecny i każdy wcześniejszy, który złożył program (`zlozone`),
    żeby stary operat nie wpadł do nowego.
    """
    if not katalog.is_dir():
        return []
    dane = opis(katalog)
    wyniki_scalania = {_nazwa_wyniku(str(dane.get("nr_roboty") or ""), katalog).lower()}
    wyniki_scalania |= {nazwa.lower() for nazwa in _zlozone(dane)}
    znalezione = [
        p for p in katalog.iterdir()
        if p.is_file()
        and p.suffix.lower() in ROZSZERZENIA_DO_SCALENIA
        and p.name != PLIK_OPISU
        and p.name.lower() not in wyniki_scalania
        and not p.name.startswith("~$")
    ]
    return sorted(znalezione, key=lambda p: (p.name != SPIS_TRESCI, p.name.lower()))


def uklad(katalog: Path) -> dict[str, Any]:
    """Zapamiętany układ kafelków: `{"kolejnosc": [...], "obroty": {nazwa: kąt}}`."""
    zapisany = opis(katalog).get("uklad")
    return zapisany if isinstance(zapisany, dict) else {}


def zapisz_uklad(katalog: Path, kolejnosc: list[str], obroty: dict[str, int]) -> None:
    """Zapamiętuje ustawienie kafelków po udanym złożeniu PDF-a.

    Brat układa kolejność myszą i obraca skany, które przyszły bokiem — przy drugim
    składaniu tego samego operatu (a poprawia je regularnie) nie ma powodu, żeby
    robił to od nowa.

    Świadomie **nie** zapamiętujemy plików pominiętych krzyżykiem: plik ukryty na stałe,
    o którym program milczy, byłby trudniejszy do odnalezienia niż jedno kliknięcie.
    Pominięty pokaże się więc znowu, na końcu listy — jak każdy nowy.
    """
    dane = opis(katalog)
    if not dane:                       # katalog bez operat.json to nie jest nasz operat
        return
    dane["uklad"] = {
        "kolejnosc": list(kolejnosc),
        "obroty": {nazwa: int(kat) % 360 for nazwa, kat in obroty.items()
                   if int(kat) % 360},
        "zapisano": datetime.now().isoformat(timespec="seconds"),
    }
    (katalog / PLIK_OPISU).write_text(json.dumps(dane, ensure_ascii=False, indent=2),
                                      encoding="utf-8")


def pliki_ulozone(katalog: Path) -> list[tuple[Path, int]]:
    """Pliki w zapamiętanej kolejności, każdy ze swoim obrotem; nowe na końcu.

    `sort` jest stabilny, więc pliki, których nie było przy poprzednim składaniu,
    zachowują między sobą kolejność z `pliki()` (spis treści pierwszy, potem alfabet)
    i lądują za tymi, które brat już ustawił.
    """
    zapamietany = uklad(katalog)
    miejsca = {nazwa: numer for numer, nazwa in enumerate(zapamietany.get("kolejnosc") or [])}
    obroty = zapamietany.get("obroty") or {}

    pozycje = pliki(katalog)
    pozycje.sort(key=lambda p: miejsca.get(p.name, len(miejsca)))
    return [(p, int(obroty.get(p.name, 0)) % 360) for p in pozycje]


def _aktualny(cel: Path, zrodlo: Path) -> bool:
    return cel.exists() and cel.stat().st_mtime >= zrodlo.stat().st_mtime


def jako_pdf(plik: Path, w_tle: bool = False) -> Path:
    """PDF danego pliku — sam siebie dla .pdf, a dla Worda konwersja z pamięcią podręczną.

    Wynik konwersji leży poza katalogiem operatu, żeby brat nie musiał patrzeć
    na duplikaty i żeby sklejanie nie policzyło tego samego dokumentu dwa razy.
    `w_tle` — miniatura, a nie składanie (patrz `pdf.PRZERWA_PO_ZAWIESZENIU`).
    """
    if plik.suffix.lower() in ROZSZERZENIA_PDF:
        return plik

    cel = PODGLADY / plik.parent.name / (plik.stem + ".pdf")
    if _aktualny(cel, plik):
        return cel

    with _BLOKADA_PODGLADU:
        # Sprawdzamy drugi raz, już pod blokadą. Strona składania pobiera miniatury
        # równolegle, więc bez tego kilka wątków widziało „brak w pamięci podręcznej”
        # naraz i każdy uruchamiał własną konwersję tego samego pliku — czyli Worda
        # tyle razy, ile było żądań.
        if _aktualny(cel, plik):
            return cel
        cel.parent.mkdir(parents=True, exist_ok=True)
        return pdf.docx_na_pdf(plik, cel, w_tle=w_tle)


def przygotuj_podglady(katalog: Path) -> int:
    """Robi z góry PDF-y wszystkich dokumentów Worda w katalogu operatu.

    Wołane w tle zaraz po wygenerowaniu dokumentów. Bez tego pierwsze wejście na stronę
    składania czekało na konwersję każdego pliku po kolei — a to właśnie tam widać
    miniatury. Teraz konwersja dzieje się, gdy brat i tak jeszcze klika po formularzu.
    """
    do_zrobienia = [(p, PODGLADY / katalog.name / (p.stem + ".pdf"))
                    for p in pliki(katalog)
                    if p.suffix.lower() in ROZSZERZENIA_WORD]
    do_zrobienia = [(z, c) for z, c in do_zrobienia if not _aktualny(c, z)]
    if not do_zrobienia:
        return 0
    with _BLOKADA_PODGLADU:
        # Listę filtrujemy drugi raz, już pod blokadą: między spisaniem plików a wzięciem
        # zamka poprawianie operatu mogło sprzątnąć odznaczony dokument — konwersja
        # skasowanego pliku by padła, a jego podgląd wróciłby zza grobu.
        do_zrobienia = [(z, c) for z, c in do_zrobienia if z.is_file()]
        return len(pdf.docx_na_pdf_wsad(do_zrobienia))


def usun_podglady(katalog: Path | str) -> None:
    """Kasuje podglądy jednego operatu. Przyjmuje katalog albo samą jego nazwę.

    Nazwa jest tu potrzebna, bo operat bywa kasowany z historii wtedy, gdy jego
    katalogu już nie ma — a podglądy zostają i nikt po nich nie sprząta.
    """
    import shutil
    nazwa = katalog.name if isinstance(katalog, Path) else str(katalog)
    if nazwa:
        shutil.rmtree(PODGLADY / nazwa, ignore_errors=True)


def sprzataj_podglady() -> int:
    """Kasuje podglądy operatów, których już nie ma w `wyniki/`. Zwraca ile usunięto.

    Program sprząta podglądy, gdy operat kasuje się przyciskiem — ale brat **przenosi
    gotowe operaty na dysk archiwalny Eksploratorem**, a o tym program się nie dowiaduje.
    PDF-y podglądów zostawały wtedy na zawsze: katalog `dane/podglad/` rósł mimo
    znikających operatów.

    Wołane przy każdym starcie programu, z tego samego powodu co sprzątanie kopii:
    ma działać u kogoś, kto niczego nie kasuje w programie, tylko robi porządki
    w Eksploratorze.

    Podgląd odtwarza się sam przy następnym wejściu na stronę składania, więc jedyne
    ryzyko pomyłki to jedna konwersja więcej — nie utrata danych.
    """
    import shutil
    usuniete = 0
    for katalog in PODGLADY.iterdir() if PODGLADY.is_dir() else []:
        if katalog.is_dir() and not (WYNIKI / katalog.name).is_dir():
            shutil.rmtree(katalog, ignore_errors=True)
            usuniete += 1
    return usuniete


def _okno_katalogu(nazwa: str):
    """Uchwyt okna Eksploratora pokazującego dany katalog (albo None).

    Okna folderów mają klasę `CabinetWClass`, a nazwa katalogu jest w tytule. Numery
    operatów („001.2026”) są na tyle charakterystyczne, że nie trafimy w cudze okno.
    """
    import win32gui

    znalezione = []

    def sprawdz(uchwyt, _):
        if (win32gui.GetClassName(uchwyt) == "CabinetWClass"
                and win32gui.IsWindowVisible(uchwyt)
                and nazwa in win32gui.GetWindowText(uchwyt).lower()):
            znalezione.append(uchwyt)

    win32gui.EnumWindows(sprawdz, None)
    return znalezione[0] if znalezione else None


def _konsole_na_spod(win32gui, win32con) -> None:
    """Odsuwa czarne okno serwera na sam spód kolejki okien.

    O wysunięcie Eksploratora prosi **nasz** proces, więc Windows wciąga jego konsolę
    do kolejki aktywacji: po zamknięciu katalogu na wierzch potrafi wyjść czarne okno
    zamiast przeglądarki, w której brat pracował. Konsola nie jest mu do niczego
    potrzebna poza zamknięciem programu, więc jej miejsce jest na spodzie.

    `SWP_NOACTIVATE` jest tu istotne: przesuwamy okno w kolejce, ale go nie aktywujemy.
    """
    try:
        import win32console
        konsola = win32console.GetConsoleWindow()
    except Exception:
        return
    if not konsola:                       # uruchomienie bez konsoli (pythonw, usługa)
        return
    try:
        win32gui.SetWindowPos(
            konsola, win32con.HWND_BOTTOM, 0, 0, 0, 0,
            win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE)
    except Exception:
        pass


def _na_pierwszy_plan(katalog: Path) -> None:
    """Wyciąga okno otwartego katalogu przed pozostałe okna.

    Windows **nie pozwala** procesowi w tle zabrać pierwszego planu, a nasz serwer
    właśnie takim procesem jest: aktywna jest przeglądarka, nie uvicorn. Bez tego
    Eksplorator otwiera się za oknem przeglądarki i miga tylko na pasku zadań —
    z punktu widzenia brata „przycisk nic nie zrobił”. (Sprawdzone: przez trasę HTTP
    okno nigdy nie wychodziło na wierzch, choć ten sam `os.startfile` wywołany
    z świeżo uruchomionego skryptu wychodził — bo tamten proces miał prawo do planu).

    Obejście: podpinamy swoją kolejkę wejścia pod wątek okna, które plan ma teraz,
    i dopiero wtedy prosimy o wysunięcie. Chodzi w osobnym wątku, bo okno Eksploratora
    pojawia się z opóźnieniem, a odpowiedź HTTP nie ma na co czekać.
    """
    import time

    try:
        import win32con
        import win32gui
        import win32process
    except ImportError:
        return                                 # bez pywin32 zostaje zachowanie jak dotąd

    nazwa = katalog.name.lower()
    koniec = time.monotonic() + 3.0            # tyle wystarcza na start Eksploratora
    while time.monotonic() < koniec:
        try:
            uchwyt = _okno_katalogu(nazwa)
        except Exception:
            return
        if uchwyt:
            podpiete = False
            watek_aktywnego = watek_celu = 0
            try:
                aktywne = win32gui.GetForegroundWindow()
                watek_aktywnego = win32process.GetWindowThreadProcessId(aktywne)[0]
                watek_celu = win32process.GetWindowThreadProcessId(uchwyt)[0]
                if watek_aktywnego and watek_aktywnego != watek_celu:
                    podpiete = bool(win32process.AttachThreadInput(
                        watek_aktywnego, watek_celu, True))
                win32gui.ShowWindow(uchwyt, win32con.SW_RESTORE)   # gdy był zminimalizowany
                win32gui.BringWindowToTop(uchwyt)
                win32gui.SetForegroundWindow(uchwyt)
                _konsole_na_spod(win32gui, win32con)
            except Exception:
                # SetForegroundWindow potrafi odmówić i to nie jest awaria programu —
                # katalog jest otwarty, tyle że w tle.
                pass
            finally:
                if podpiete:
                    try:
                        win32process.AttachThreadInput(watek_aktywnego, watek_celu, False)
                    except Exception:
                        pass
            return
        time.sleep(0.15)


def _wysun_po_cichu(katalog: Path) -> None:
    """Opakowanie wątku: wysuwanie okna to kosmetyka i nie ma prawa nic wypisać.

    Wyjątek w wątku roboczym nie przewróciłby programu, ale wysypałby bratu do konsoli
    angielski ślad stosu — a to jest dokładnie to, czego w tym programie nie robimy.
    """
    try:
        _na_pierwszy_plan(katalog)
    except Exception:
        pass


def otworz_w_systemie(sciezka: Path) -> None:
    """Otwiera katalog w Eksploratorze (albo odpowiedniku na Linuksie/macOS).

    Program chodzi na komputerze użytkownika, więc „serwer” i „biurko” to ta sama
    maszyna — okno otworzy się tam, gdzie siedzi brat. Nie czekamy na zamknięcie
    okna, więc `Popen` bez `wait()`.
    """
    import subprocess
    import sys

    if sys.platform == "win32":
        os.startfile(sciezka)                                    # noqa: S606 (tylko Windows)
        # Wysunięcie okna nie może przewrócić otwierania katalogu: gdy zawiedzie
        # (brak pywin32, inna wersja Windowsa), katalog i tak jest otwarty — po prostu
        # w tle, czyli tak jak było wcześniej.
        try:
            threading.Thread(target=_wysun_po_cichu, args=(sciezka,), daemon=True).start()
        except Exception:
            pass
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(sciezka)])
    else:
        subprocess.Popen(["xdg-open", str(sciezka)])

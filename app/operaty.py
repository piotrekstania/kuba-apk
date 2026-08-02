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

import json
import os
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


def nazwa_bezpieczna(tekst: str, zapas: str = "operat") -> tuple[str, bool]:
    """Zwraca (nazwa, czy_podmieniono). Zostawia polskie znaki — zmienia tylko zakazane."""
    oczyszczona = "".join("-" if z in ZNAKI_ZAKAZANE or ord(z) < 32 else z for z in tekst)
    oczyszczona = oczyszczona.strip().rstrip(". ")      # Windows nie lubi kropki na końcu
    return (oczyszczona or zapas), oczyszczona != tekst.strip()


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
          poprzedni_numer_roboty: str = "") -> tuple[Path, list[str]]:
    """Tworzy albo odświeża katalog operatu z opisem.

    Zwraca (katalog, ostrzeżenia dla użytkownika). Wołane też przy poprawianiu operatu —
    wtedy katalog już istnieje i tylko nadpisujemy `operat.json`.
    """
    # Ukośnik w nazwie katalogu zamieniamy na kropkę po cichu — to norma, a nie usterka
    # warta straszenia użytkownika.
    ostrzezenia: list[str] = []
    nazwa = nazwa_katalogu(nr_operatu)
    katalog = WYNIKI / nazwa
    katalog.mkdir(parents=True, exist_ok=True)

    (katalog / PLIK_OPISU).write_text(json.dumps({
        "nr_operatu": nr_operatu,
        "nr_roboty": nr_roboty,
        "szablon": szablon,
        "utworzono": datetime.now().isoformat(timespec="seconds"),
        "dane": dane,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

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
    try:
        return json.loads((katalog / PLIK_OPISU).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


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
            "plikow": len(pliki(sciezka)),
        })
    return sorted(wynik, key=lambda o: o["utworzono"], reverse=True)


def katalog_po_nazwie(nazwa: str) -> Path | None:
    """Zamienia nazwę z adresu na katalog — z blokadą wyjścia poza `wyniki/`."""
    kandydat = (WYNIKI / nazwa).resolve()
    if WYNIKI.resolve() not in kandydat.parents or not (kandydat / PLIK_OPISU).exists():
        return None
    return kandydat


# --- pliki w katalogu --------------------------------------------------------

def nazwa_wyniku(katalog: Path) -> str:
    """Nazwa scalonego PDF-a: dokładnie numer roboty (przepisy), z .pdf na końcu."""
    numer = opis(katalog).get("nr_roboty") or katalog.name
    return nazwa_bezpieczna(numer, zapas=katalog.name)[0] + ".pdf"


def pliki(katalog: Path) -> list[Path]:
    """Co idzie do sklejenia: PDF-y i dokumenty Worda, spis treści zawsze pierwszy.

    Pomijamy opis operatu, pusty znacznik z numerem roboty (nie ma rozszerzenia)
    i poprzedni wynik sklejania, żeby nie wpadł sam w siebie.
    """
    if not katalog.is_dir():
        return []
    wynik_scalania = nazwa_wyniku(katalog).lower()
    znalezione = [
        p for p in katalog.iterdir()
        if p.is_file()
        and p.suffix.lower() in ROZSZERZENIA_DO_SCALENIA
        and p.name != PLIK_OPISU
        and p.name.lower() != wynik_scalania
        and not p.name.startswith("~$")
    ]
    return sorted(znalezione, key=lambda p: (p.name != SPIS_TRESCI, p.name.lower()))


def _aktualny(cel: Path, zrodlo: Path) -> bool:
    return cel.exists() and cel.stat().st_mtime >= zrodlo.stat().st_mtime


def jako_pdf(plik: Path) -> Path:
    """PDF danego pliku — sam siebie dla .pdf, a dla Worda konwersja z pamięcią podręczną.

    Wynik konwersji leży poza katalogiem operatu, żeby brat nie musiał patrzeć
    na duplikaty i żeby sklejanie nie policzyło tego samego dokumentu dwa razy.
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
        return pdf.docx_na_pdf(plik, cel)


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
        return len(pdf.docx_na_pdf_wsad(do_zrobienia))


def usun_podglady(katalog: Path) -> None:
    import shutil
    shutil.rmtree(PODGLADY / katalog.name, ignore_errors=True)


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

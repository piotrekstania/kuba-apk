"""Start aplikacji: podnosi serwer lokalny i otwiera przeglądarkę.

Dla użytkownika końcowego to „program” — klika ikonę, otwiera się strona.
Nic nie wychodzi poza ten komputer: nasłuch tylko na 127.0.0.1.
"""
import importlib
import sys
import threading
import time
import urllib.request
import webbrowser

try:
    import uvicorn
except ModuleNotFoundError:     # powie o tym po polsku `_brakuje_bibliotek`
    uvicorn = None

from app.config import HOST, PORT


ZNACZNIK = "Generator operatów"      # jest w <title> każdej strony programu


def serwer_odpowiada(sekundy: float = 15.0) -> bool:
    """Czeka, aż odpowie **nasz** program. False = nie wystartował.

    Nie wystarczy sprawdzić, czy port jest zajęty: gdy siedzi na nim coś innego
    (zapomniana druga kopia programu, inny serwer deweloperski), otwarty port
    wygląda jak udany start, choć nasz serwer właśnie się nie podniósł.
    Sprawdzone na blokadzie portu — samo `connect` dawało fałszywe „działa”.
    """
    koniec = time.monotonic() + sekundy
    while time.monotonic() < koniec:
        try:
            with urllib.request.urlopen(f"http://{HOST}:{PORT}/", timeout=2) as odpowiedz:
                if ZNACZNIK in odpowiedz.read(4096).decode("utf-8", "ignore"):
                    return True
        except Exception:
            pass
        time.sleep(0.3)
    return False


def zminimalizuj_konsole() -> None:
    """Chowa czarne okno serwera do paska zadań.

    Konsola nie jest użytkownikowi do niczego potrzebna poza zamknięciem programu,
    a stojąc na wierzchu wchodzi w kolejkę okien: po zamknięciu katalogu otwartego
    przyciskiem „Otwórz katalog” potrafiła wyskoczyć przed przeglądarkę, w której
    brat pracował. Zminimalizowana w tej kolejce nie uczestniczy w ogóle
    (potwierdzone na komputerze brata).

    Program zamyka się nadal tym oknem — jest o jedno kliknięcie w pasku zadań.
    """
    if sys.platform != "win32":
        return
    try:
        import win32con
        import win32console
        import win32gui

        okno = win32console.GetConsoleWindow()
        if okno:
            win32gui.ShowWindow(okno, win32con.SW_MINIMIZE)
    except Exception:
        pass                    # bez pywin32 albo bez konsoli po prostu zostaje jak było


def po_starcie() -> None:
    """Otwiera przeglądarkę i chowa konsolę — **dopiero gdy serwer naprawdę wstał**.

    Gdy start się nie uda (zajęty port, błąd w kodzie), okno zostaje na wierzchu
    z komunikatem. Schowanie go w takiej sytuacji byłoby najgorsze z możliwych:
    brat widziałby pustą przeglądarkę i nic poza tym.
    """
    if not serwer_odpowiada():
        print("Serwer nie wystartował — okno zostaje otwarte, żeby było widać dlaczego.")
        return
    webbrowser.open(f"http://{HOST}:{PORT}/")
    time.sleep(1.5)             # niech przeglądarka zdąży się pokazać i wziąć pierwszy plan
    zminimalizuj_konsole()


def _brakuje_bibliotek() -> str | None:
    """Nazwa biblioteki, której brakuje do startu — albo None, gdy są wszystkie.

    `start.bat` nie zatrzymuje się już na nieudanej instalacji bibliotek (w terenie
    nie ma internetu, a stare zwykle wystarczają). Gdy jednak nowa wersja programu
    potrzebuje czegoś, czego jeszcze nie ma, import kończył się angielskim śladem
    stosu. Import `app.main` przed startem serwera sprawdza cały program naraz.
    """
    if uvicorn is None:
        return "uvicorn"
    try:
        importlib.import_module("app.main")
    except ModuleNotFoundError as blad:
        return blad.name or str(blad)
    return None


def glowna() -> None:
    """Start programu — albo przejście do tego, który już działa.

    Brat zostawia program w schowanym oknie i następnego dnia klika skrót jeszcze raz.
    Drugi serwer i tak by nie wstał (port zajęty), a do tej pory kończyło się to
    angielskim błędem w konsoli. Gorzej: `start.bat` robi przed nami aktualizację, więc
    działający stary proces dostaje nowe szablony i nowe style, a nowego kodu nie —
    stąd prośba o zamknięcie tamtego okna. Sprawdzamy krótko: gdy nikt nie nasłuchuje,
    odmowa połączenia przychodzi od razu.
    """
    if serwer_odpowiada(sekundy=0.5):
        print("Generator operatów już działa w innym oknie (na pasku zadań) — otwieram go")
        print("w przeglądarce. Jeśli przed chwilą przyszła aktualizacja, zamknij tamto okno")
        print("i uruchom program jeszcze raz, żeby wczytać nową wersję.")
        webbrowser.open(f"http://{HOST}:{PORT}/")
        return
    brakuje = _brakuje_bibliotek()
    if brakuje:
        print(f"Brakuje biblioteki {brakuje}, której potrzebuje nowa wersja programu —")
        print("nie udało się jej doinstalować, pewnie nie było internetu.")
        print("Podłącz komputer do internetu i uruchom program jeszcze raz: biblioteka")
        print("doinstaluje się sama. Twoje operaty i dane są całe.")
        return
    threading.Thread(target=po_starcie, daemon=True).start()
    print(f"Generator operatów działa: http://{HOST}:{PORT}/   (zamknij okno, aby zakończyć)")
    uvicorn.run("app.main:app", host=HOST, port=PORT, log_level="warning")


if __name__ == "__main__":
    glowna()

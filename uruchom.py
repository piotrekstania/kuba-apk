"""Start aplikacji: podnosi serwer lokalny i otwiera przeglądarkę.

Dla użytkownika końcowego to „program” — klika ikonę, otwiera się strona.
Nic nie wychodzi poza ten komputer: nasłuch tylko na 127.0.0.1.
"""
import threading
import webbrowser

import uvicorn

from app.config import HOST, PORT


def otworz_przegladarke() -> None:
    webbrowser.open(f"http://{HOST}:{PORT}/")


if __name__ == "__main__":
    threading.Timer(1.5, otworz_przegladarke).start()
    print(f"Generator operatów działa: http://{HOST}:{PORT}/   (zamknij okno, aby zakończyć)")
    uvicorn.run("app.main:app", host=HOST, port=PORT, log_level="warning")

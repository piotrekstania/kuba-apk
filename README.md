# Generator operatów

Lokalna aplikacja dla geodety: wypełniasz formularz w przeglądarce → dostajesz gotowy
dokument Word, w razie potrzeby PDF, a PDF-y można ze sobą połączyć (mapy, skany, załączniki).

Wszystko działa na jednym komputerze — serwer nasłuchuje tylko na `127.0.0.1`, nic nie
wychodzi do internetu, dane właścicieli i numery KW nie lądują na żadnym hostingu.

## Uruchomienie

Windows — dwuklik na `start.bat` (za pierwszym razem sam zakłada środowisko i doinstaluje
biblioteki; wymaga zainstalowanego [Pythona](https://www.python.org/downloads/) 3.11+
z zaznaczoną opcją „Add python.exe to PATH”).

Linux / macOS:

```bash
./start.sh
```

Przeglądarka otworzy się sama na `http://127.0.0.1:8000`.

## Do zrobienia PDF-ów

Potrzebny jest jeden z dwóch programów — aplikacja wykrywa je sama i pokazuje w prawym
górnym rogu, którego używa:

1. **Microsoft Word** (Windows) — wygląd PDF-a 1:1 z dokumentem. Wymaga doinstalowania
   `docx2pdf` (odkomentowana linia w `requirements.txt`).
2. **[LibreOffice](https://pl.libreoffice.org/)** — darmowy, działa na każdym systemie.

Bez żadnego z nich generowanie .docx nadal działa, tylko przycisk „Pobierz PDF” zgłosi brak
konwertera.

## Jak to jest poskładane

| Katalog / plik | Do czego |
| --- | --- |
| `szablony/` | pliki `.docx` z tagami `{{ }}` — **to tu brat edytuje wygląd dokumentów** |
| `szablony/*.json` | nieobowiązkowy opis pól: etykiety, typy, kolejność, grupy |
| `wyniki/` | wygenerowane dokumenty i PDF-y |
| `dane/operaty.sqlite3` | historia, dane stałe, liczniki numeracji |
| `app/szablony.py` | czyta szablon i buduje z niego formularz |
| `app/generator.py` | wypełnia szablon danymi |
| `app/pdf.py` | konwersja DOCX→PDF i łączenie PDF-ów |
| `app/main.py` | strony i obsługa formularzy |
| `narzedzia/utworz_wzor_szablonu.py` | generuje przykładowy szablon do testów |

Kluczowa zasada: **źródłem prawdy jest plik .docx**. Dodanie `{{ nowe_pole }}` w Wordzie
automatycznie dokłada pole w formularzu — bez zmian w kodzie. Instrukcja pisania szablonów
jest w samej aplikacji, w zakładce „Jak edytować szablon”.

## Typy pól (plik `.json` obok szablonu)

`text`, `textarea`, `date`, `number`, `select`, `checkbox`, `tabela`, `auto_numer`.
Dodatkowo `"zrodlo": "ustawienia"` chowa pole z formularza i bierze wartość z zakładki
„Dane stałe” (nazwisko, uprawnienia, dane firmy — wpisywane raz).

## Zrobienie pliku .exe (opcjonalnie)

Żeby brat nie musiał instalować Pythona:

```bash
.venv/bin/pip install pyinstaller
.venv/bin/pyinstaller --name GeneratorOperatow --onefile --add-data "app/web:app/web" uruchom.py
```

Katalogi `szablony/`, `wyniki/` i `dane/` zostają obok `.exe` — szablony mają być edytowalne,
więc celowo nie są pakowane do środka.

## Kopia zapasowa

Wystarczy skopiować `szablony/` i `dane/`. Reszta odtwarza się sama.

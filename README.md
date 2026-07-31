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

1. **Microsoft Word** (Windows) — ścieżka domyślna, wygląd PDF-a 1:1 z dokumentem.
   Nic nie trzeba dokładać: `start.bat` instaluje `pywin32` i program steruje Wordem sam.
   Word otwiera się niewidocznie, w osobnej instancji, i zamyka po konwersji — nie przeszkadza
   w pracy w normalnie otwartym Wordzie.
2. **[LibreOffice](https://pl.libreoffice.org/)** — darmowy zapas na komputery bez Worda
   (a także na Linuksa/macOS); wykrywany też jako wersja przenośna w katalogu `libreoffice/`.

Bez żadnego z nich generowanie .docx nadal działa, tylko przycisk „Pobierz PDF” zgłosi brak
konwertera.

## Aktualizacje

Program przy każdym uruchomieniu porównuje swój plik `WERSJA` z tym na GitHubie
(`piotrekstania/kuba-apk`, gałąź `main`). Jeśli tam jest nowszy, pobiera paczkę `.zip`
i podmienia **wyłącznie kod**. Brak internetu = start po staremu, bez błędu.

Nietykalne przy aktualizacji: `dane/` (historia, liczniki numeracji, pobrane dane TERYT)
i `wyniki/` (gotowe dokumenty). Przed każdą podmianą leci kopia bazy i poprzedniej
zawartości do `dane/kopie/`.

**Szablony jadą razem z kodem.** Jest jeden katalog `szablony/`, wersjonowany w repozytorium
i nadpisywany przy każdej aktualizacji — formatki Worda utrzymuje autor, nie użytkownik,
więc poprawka w szablonie dociera do brata tak samo zwyczajnie jak poprawka w programie.
Wcześniej był podział na `szablony_wzorcowe/` (wysyłane) i `szablony/` (jego, nietykalne);
przy takim podziale zmieniony wzorzec nie docierał do użytkownika, dopóki nie skasował
pliku ręcznie.

**Wydanie nowej wersji = podbicie pliku `WERSJA` i `git push`.** Pierwsza linia to numer
(porównywany), reszta to opis pokazywany użytkownikowi jednorazowo po aktualizacji.
Commit bez zmiany `WERSJA` nikomu się nie zainstaluje — i o to chodzi, bo to Ty decydujesz,
kiedy brat dostaje nową wersję.

W **kopii roboczej gita aktualizator się nie uruchamia** (wykrywa katalog `.git`) — inaczej
`./start.sh` nadpisałby niezacommitowane zmiany plikami z GitHuba. Tam obowiązuje `git pull`.
Żeby zobaczyć to, co zobaczy użytkownik, zrób instalację testową bez `.git`:

```bash
python narzedzia/instalacja_testowa.py /sciezka/do/testu --stara-wersja
```

Numer wersji program czyta z **API GitHuba**, bo `raw.githubusercontent.com` serwuje pliki
z cache i po `push` przez kilka minut podaje jeszcze stary numer (zmierzone: 3,5 min, przy
paczce `.zip`, która nowy kod miała od razu). Gdy API odmówi — limit to 60 zapytań na godzinę
z jednego adresu IP, a program pyta raz na uruchomienie — zostaje ścieżka przez `raw`
i wtedy znów trzeba chwilę odczekać.
Numer wersji jest zwykłym tekstem, porównywanym na równość, więc format jest dowolny
(`2026.07.31`, `2026.07.31.1`, `1.4` — co wygodniejsze).

Zmiany w bazie danych obsługuje `PRAGMA user_version` i lista `MIGRACJE` w
[app/db.py](app/db.py): dopisujesz krok, podbijasz `WERSJA_SCHEMATU`, a stara baza
sama się doprowadzi do porządku (po uprzednim zrobieniu kopii).

## Jak to jest poskładane

| Katalog / plik | Do czego |
| --- | --- |
| `szablony/` | pliki `.docx` z tagami `{{ }}` — wygląd dokumentów; **wersjonowane w repo**, aktualizacja je podmienia |
| `szablony/*.json` | nieobowiązkowy opis pól: etykiety, typy, kolejność, grupy |
| `wyniki/` | wygenerowane dokumenty i PDF-y |
| `dane/operaty.sqlite3` | historia, liczniki numeracji, jednostki TERYT i obręby |
| `app/szablony.py` | czyta szablon i buduje z niego formularz |
| `app/generator.py` | wypełnia szablon danymi |
| `app/pdf.py` | konwersja DOCX→PDF i łączenie PDF-ów |
| `app/aktualizacja.py` | pobieranie nowej wersji z GitHuba, kopie zapasowe |
| `WERSJA` | numer wersji + opis zmian; podbijasz go, wydając nową wersję |
| `app/main.py` | strony i obsługa formularzy |
| `narzedzia/utworz_wzor_szablonu.py` | generuje przykładowy szablon do testów |

Kluczowa zasada: **źródłem prawdy jest plik .docx**. Dodanie `{{ nowe_pole }}` w Wordzie
automatycznie dokłada pole w formularzu — bez zmian w kodzie. Instrukcja pisania szablonów
jest w samej aplikacji, w zakładce „Jak edytować szablon”.

## Typy pól (plik `.json` obok szablonu)

`text`, `textarea`, `date`, `number`, `select`, `checkbox`, `tabela`, `auto_numer`,
`auto_numer` (wzorzec `{numer3}.{rok}` daje `001.2026` — kropka, nie ukośnik, bo tak samo nazywa się katalog operatu),
`teryt` (kaskada województwo → powiat → jednostka ewidencyjna → obręb; do dokumentu
wchodzą nazwy i identyfikatory TERYT osobnymi znacznikami).

Dane, które nie zmieniają się między robotami — nazwisko geodety, numer uprawnień,
pieczątka firmy — wpisuje się na stałe w szablon Worda, a nie w program.

## Zrobienie pliku .exe (opcjonalnie)

Żeby brat nie musiał instalować Pythona:

```bash
.venv/bin/pip install pyinstaller
.venv/bin/pyinstaller --name GeneratorOperatow --onefile --add-data "app/web:app/web" uruchom.py
```

Katalogi `szablony/`, `wyniki/` i `dane/` zostają obok `.exe` — szablony mają być edytowalne,
więc celowo nie są pakowane do środka.

## Kopia zapasowa

Wystarczy skopiować `dane/` — siedzi tam historia, numeracja i pobrane dane TERYT.
Szablony i kod odtwarzają się z repozytorium.

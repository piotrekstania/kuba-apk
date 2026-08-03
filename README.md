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

Bez żadnego z nich generowanie .docx nadal działa; nie da się tylko złożyć operatu
w jeden PDF ani zobaczyć miniatur plików Worda.

Formatki są złożone **Calibri** — jest na każdym Windowsie z pakietem Office. Na Linuksie
warto dołożyć metrycznie zgodny zamiennik, inaczej podglądy PDF będą się łamać inaczej
niż dokumenty u odbiorcy:

```bash
sudo apt install fonts-crosextra-carlito
```

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

Numer ma postać `rok.miesiąc.dzień.licznik`, z datą **dnia wydania** i licznikiem
liczącym wydania tego dnia od 1. Zaraz po podbiciu uruchom:

```bash
python narzedzia/zbuduj_zmiany.py --zapisz
```

— to zbiera historię wydań do `ZMIANY.md`, którą brat ogląda w menu „Pomoc". Bez tego
kroku dostanie komunikat o nowej wersji i pustą stronę historii; pilnuje tego
`test_wydana_wersja_ma_wpis_w_historii`.

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
| `wyniki/` | operaty — po jednym katalogu na robotę, razem z plikami dokładanymi ręcznie |
| `dane/operaty.sqlite3` | historia, liczniki numeracji, jednostki TERYT i obręby |
| `app/config.py` | ścieżki; działa też, gdy program siedzi w spakowanym `.exe` |
| `app/szablony.py` | czyta szablon i buduje z niego formularz |
| `app/generator.py` | wypełnia szablon danymi |
| `app/operaty.py` | katalog operatu: zakładanie, `operat.json`, lista plików do sklejenia |
| `app/pdf.py` | konwersja DOCX→PDF (Word przez COM albo LibreOffice) i łączenie PDF-ów |
| `app/miniatury.py` | podglądy stron do układania kolejności przed sklejeniem |
| `app/teryt.py` | jednostki TERYT z GUS-u, obręby i sprawdzanie działek w ULDK |
| `app/statystyki.py` | liczniki w stopce: operaty, dokumenty, złożone PDF-y |
| `app/zmiany.py` | historia wersji pokazywana w programie (czyta `ZMIANY.md`) |
| `app/aktualizacja.py` | pobieranie nowej wersji z GitHuba, kopie zapasowe |
| `WERSJA` | numer wersji + opis zmian; podbijasz go, wydając nową wersję |
| `ZMIANY.md` | historia wydań dla użytkownika — **generowana**, nie pisana ręcznie |
| `app/main.py` | strony i obsługa formularzy |
| `narzedzia/utworz_wzor_szablonu.py` | generuje przykładowy szablon do testów |
| `narzedzia/zbuduj_zmiany.py` | składa `ZMIANY.md` z opisów w historii pliku `WERSJA` |
| `narzedzia/ujednolic_wyglad.py` | nakłada wspólny wygląd na wszystkie formatki — krój, logo, stopka, hierarchia nagłówków, wyrównanie kolumn; **nie rusza treści, pogrubień ani czerwieni**. Puszczaj po każdej podmianie `.docx` |
| `narzedzia/popraw_szablon.py` | drobiazgi, których nie da się wyklikać na stałe: tabulator i wcięcie wiszące w spisie treści, podpis przypięty do dołu strony |
| `narzedzia/instalacja_testowa.py` | odtwarza instalację brata — zip z GitHuba, bez `.git` |

Kluczowa zasada: **źródłem prawdy jest plik .docx**. Dodanie `{{ nowe_pole }}` w Wordzie
automatycznie dokłada pole w formularzu — bez zmian w kodzie. Instrukcja pisania szablonów
jest w samej aplikacji, w zakładce „Jak edytować szablon”.

## Typy pól (plik `.json` obok szablonu)

`text`, `textarea`, `date`, `number`, `select`, `checkbox`, `tabela`,
`auto_numer` (wzorzec `{numer3}/{rok}` daje `001/2026`; katalog operatu nazywa się
wtedy `001.2026`, bo ukośnika w nazwie folderu być nie może),
`teryt` (kaskada województwo → powiat → jednostka ewidencyjna → obręb; do dokumentu
wchodzą nazwy i identyfikatory TERYT osobnymi znacznikami),
`wybor_wielokrotny` (lista z checkboxami; `zawsze` to pozycje obowiązkowe, a `wzor_wartosci`
przepuszcza zaznaczenia przez wzorzec — tak powstaje lista plików GML dla ośrodka),
`dokumenty` (które dodatkowe pliki Worda wygenerować razem z operatem; lista bierze się
z zawartości `szablony/`, a `tylko` decyduje, które pozycje trafiają do którego pola).

Dane, które nie zmieniają się między robotami — nazwisko geodety, numer uprawnień,
pieczątka firmy — wpisuje się na stałe w szablon Worda, a nie w program.

## Testy

```bash
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/pytest
```

Chodzą kilkanaście sekund, bez sieci i bez Worda. Testy ścieżki wordowej stoją za markerem
`word` i uruchamia się je ręcznie na Windowsie z Office (`pytest -m word`) — na runnerze
GitHuba nie ma czym ich wykonać. Reszta jedzie automatycznie przy każdym pushu.

Zasada: **żadna zmiana kodu bez zielonego `pytest`**, nowa funkcja przychodzi z testem
w tym samym commicie. Szczegóły i przepis na testy Worda są w [CLAUDE.md](CLAUDE.md).

## Pakowanie do .exe — odpuszczone

Rozważane i **porzucone 02.08.2026**: instalacja przez `start.bat` działa i sama się
aktualizuje, więc `.exe` rozwiązywałoby problem, którego nie ma, a dokładało ostrzeżenia
SmartScreen i osobną ścieżkę budowania. **Python zostaje wymaganiem wstępnym.**

Obsługa `sys.frozen` w `app/config.py` zostaje jako punkt zaczepienia, gdyby temat wrócił —
wtedy pamiętaj o `--hidden-import win32com.client` i `--hidden-import pythoncom` (bez nich
konwersja przez Worda nie ruszy) oraz o tym, że `pypdfium2` wnosi własną bibliotekę binarną.

## Kopia zapasowa

Kopiuj **`wyniki/` i `dane/`** — oba są nie do odtworzenia.

**`wyniki/` to same operaty i to jest najważniejszy katalog w całym programie.**
Leżą w nim nie tylko pliki wygenerowane z formularza: do katalogu operatu dokłada się
mapy, szkice, skany, wypisy i wykaz współrzędnych z C-Geo. Tych plików program nigdy
nie widział i nie ma ich skąd wziąć. W środku siedzi też `operat.json` — dane roboty
i zapamiętany układ kafelków przy składaniu PDF-a.

**`dane/`** to historia, licznik numeracji i pobrane dane TERYT. Bez niego program
działa dalej, ale numeracja operatów zaczyna się od nowa, a listy TERYT trzeba
ściągnąć jeszcze raz.

Odtwarzalne z repozytorium są **tylko kod i szablony**. Nie licz na odtworzenie
dokumentów z historii w bazie: baza pamięta, co było wpisane w formularzu, ale formatki
Worda są nadpisywane przy każdej aktualizacji, więc dokument wygenerowany ponownie za rok
może wyglądać inaczej niż ten, który poszedł do ośrodka. Operat ma zostać taki, jaki
został złożony.

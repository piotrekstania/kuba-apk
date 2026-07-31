# Kontekst projektu — dla Claude Code

Ten plik jest wczytywany automatycznie na starcie sesji. Opisuje **po co** powstaje ten
program i **dlaczego** jest zrobiony właśnie tak — reszta (co robi kod) jest w kodzie
i w [README.md](README.md).

## Dla kogo i po co

Odbiorcą jest **brat użytkownika — geodeta**. Nie jest programistą. Ma dostać narzędzie,
które zastępuje ręczne przeklejanie danych do formatek w Wordzie:

1. wypełnia formularz w przeglądarce (dane roboty, działki, wykaz współrzędnych),
2. dostaje **gotowy plik Worda** — to jest główny produkt, nie PDF,
3. czasem robi z niego PDF i **skleja z innymi PDF-ami** (mapy, skany, załączniki do operatu).

Program ma działać **lokalnie na jego komputerze z Windowsem**. Docelowo jeden plik do
zainstalowania/uruchomienia, bez instalowania Pythona.

## Decyzje już podjęte (nie podważaj ich bez powodu)

| Decyzja | Dlaczego |
| --- | --- |
| Python + serwer lokalny na `127.0.0.1`, interfejs w przeglądarce | wygląda dla użytkownika jak zwykły program, a formularze robi się szybciej w HTML niż w Tkinter/Qt |
| **Nie** PHP na hostingu WordPressa (brat go ma) | na shared hostingu nie ma jak zrobić DOCX→PDF (brak Worda/LibreOffice, `exec()` zwykle zablokowany), dane właścicieli działek i numery KW nie mają wyjeżdżać na współdzielony serwer, a w terenie nie ma internetu |
| **Nie** klasyczna aplikacja desktopowa (Tkinter/Qt) | nic się nie zyskuje, traci się czas na budowanie formularzy |
| docxtpl — szablonem jest **zwykły plik .docx** | brat sam edytuje wygląd dokumentu w Wordzie; gdyby układ dokumentu siedział w kodzie, każda zmiana pieczątki wracałaby do programisty |
| DOCX→PDF przez Worda (COM) albo LibreOffice `--headless` | ta sama ścieżka co szablon, więc PDF wygląda identycznie jak dokument |
| Wordem sterujemy sami przez `pywin32`, **nie** przez `docx2pdf` | `docx2pdf` woła `Dispatch` bez `CoInitialize()`, a trasy FastAPI chodzą w wątkach roboczych — tam to pada; własny kod daje też `ExportAsFixedFormat` (jakość, zakładki) i pewne zamknięcie Worda |
| **Nie** drugi, niezależny generator PDF (ReportLab/WeasyPrint) | oznaczałby dwa szablony do utrzymania, które po pół roku wyglądają inaczej |
| **Nie** konwersja przez API w chmurze | dane osobowe + wymaga internetu |
| SQLite | historia, numeracja, dane stałe — zero konfiguracji |
| Aktualizacje: program sam pobiera `.zip` z GitHuba przy starcie | brat nie jest programistą; nie ma mowy o `git pull` ani o ręcznym rozpakowywaniu paczek na wierzch, bo prędzej czy później nadpisałby sobie szablony |
| Wzorce szablonów w `szablony_wzorcowe/`, a nie w `szablony/` | `szablony/` to **jego** dane — jedyny katalog, który był i wysyłany, i edytowany przez użytkownika; wzorce kopiują się tam tylko gdy brakuje pliku |
| Wersja schematu bazy w `PRAGMA user_version` + lista `MIGRACJE` | baza u brata to jedyny egzemplarz historii i numeracji; nowy kod na starej bazie musi umieć ją dociągnąć, a nie wywalić się na brakującej kolumnie |
| **Żaden błąd nie wychodzi do przeglądarki po angielsku** — globalne uchwyty w `app/main.py` + `blad.html`, ślad do `dane/bledy.log` | brat nie odróżni `AttributeError` od awarii dysku; ma zobaczyć, co się stało, że jego dane są całe i co ma zrobić. Log to jedyny ślad po awarii, bo okno konsoli zamyka razem z programem |
| TERYT: plik `TERC_Urzedowy` z GUS + obręby z ULDK, **wszystko cache'owane w SQLite** | oficjalna usługa GUS (TERYT ws1) wymaga rejestracji i hasła wysyłanego pocztą przez Urząd Statystyczny — u brata to dyskwalifikacja. Cache jest obowiązkowy, bo w terenie nie ma internetu |
| Obręby dociągane **dla wybranej gminy**, nie dla całej Polski z góry | ULDK oddaje obręby jednej jednostki ewidencyjnej w jednym zapytaniu (~0,1 s), ale gmin jest 3240 — pobieranie wszystkiego z góry to kilkanaście minut przy pierwszym starcie za dane, z których brat użyje kilku |

## Zasada centralna

**Źródłem prawdy jest plik `.docx` w `szablony/`.** Aplikacja czyta z niego tagi Jinja
i **z nich buduje formularz**. Dopisanie `{{ nowe_pole }}` w Wordzie = nowe pole na stronie,
bez zmian w kodzie. Opcjonalny plik `.json` obok szablonu dokłada tylko etykiety, typy,
kolejność i grupy pól.

Jeśli masz pomysł, który wymaga wpisania listy pól konkretnego operatu do kodu Pythona —
to znak, że idziesz pod prąd tej architektury.

## Stos

Python 3.11+ (u autora testowane na 3.14), FastAPI + uvicorn, Jinja2, docxtpl (python-docx),
pypdf, SQLite, na Windowsie dodatkowo `pywin32` (Word przez COM). Wersje przypięte
w [requirements.txt](requirements.txt). Bez frontendowego frameworka — czysty HTML
+ trochę waniliowego JS w szablonach.

**Środowisko docelowe (komputer brata) = Windows + Microsoft Office, bez LibreOffice.**
Ścieżka przez LibreOffice zostaje w kodzie jako zapas i dla Linuksa.

Podział maszyn u autora:

| Maszyna | Rola |
| --- | --- |
| Linux | pisanie kodu, `git`, praca z Claude Code; po `apt install python3-venv` przechodzi tu cała ścieżka poza Wordem (PDF-y robi LibreOffice) |
| Windows (`E:\git\kuba-apk`) | kopia robocza gita — sprawdzanie Worda i COM-u |
| Windows, katalog poza gitem | instalacja testowa „jak u brata”: rozpakowany `.zip`, bez `.git`, z aktualizacją z GitHuba; robi ją `narzedzia/instalacja_testowa.py` |

**Aktualizator sam się wyłącza w kopii roboczej gita** (`.git` obok = pomijam) — inaczej
`./start.sh` na Linuksie nadpisałby niezacommitowane zmiany plikami z GitHuba. Wymuszenie:
`GENERATOR_WYMUS_AKTUALIZACJE=1`.

## Uruchomienie

Windows:

```bat
start.bat
```

(zakłada `.venv`, instaluje zależności, startuje serwer i otwiera przeglądarkę na
`http://127.0.0.1:8000`)

Linux/macOS: `./start.sh`

W Claude Code do podglądu w przeglądarce służy `preview_start`; w `.claude/launch.json` są
dwie konfiguracje — **na Windowsie użyj `generator-operatow-windows`** (ścieżka
`.venv\Scripts\python.exe`), na Linuksie `generator-operatow`.

Serwer **nie ma auto-reloadu**. Po zmianie kodu trzeba go zrestartować, inaczej testujesz
starą wersję (autor się na to nadział).

## Mapa kodu

| Plik | Rola |
| --- | --- |
| `app/config.py` | ścieżki; obsługuje też uruchomienie ze spakowanego `.exe` (dane obok exe, interfejs w paczce) |
| `app/szablony.py` | czyta `.docx` + opcjonalny `.json` → obiekt `Szablon` z listą `Pole`; to tu powstaje formularz |
| `app/generator.py` | wypełnia szablon, numeracja automatyczna, formaty dat, bezpieczne nazwy plików |
| `app/pdf.py` | wykrywanie konwertera, DOCX→PDF, łączenie PDF-ów |
| `app/aktualizacja.py` | pobieranie nowej wersji z GitHuba; **tylko biblioteka standardowa**, bo działa zanim `pip install` dołoży nowe zależności |
| `WERSJA` | 1. linia = numer porównywany z GitHubem, reszta = opis pokazywany bratu raz po aktualizacji |
| `app/db.py` | SQLite: `dokumenty`, `ustawienia`, `liczniki`, `teryt_*` |
| `app/teryt.py` | jednostki TERYT z GUS + obręby z ULDK; **tylko biblioteka standardowa** |
| `app/main.py` | trasy FastAPI, parsowanie formularza (w tym tabel) |
| `app/web/templates/` | widoki; `blad.html` to strona każdego niezłapanego wyjątku, a `pomoc.html` instrukcja dla brata — aktualizuj ją razem z funkcjami |
| `narzedzia/utworz_wzor_szablonu.py` | generuje przykładowy szablon operatu do testów |
| `narzedzia/instalacja_testowa.py` | odtwarza instalację brata (zip z GitHuba, bez `.git`), opcja `--stara-wersja` wymusza aktualizację przy starcie |
| `szablony/`, `wyniki/`, `dane/` | dane użytkownika — dwa ostatnie są w `.gitignore` |

Nazwy zmiennych, funkcji i komentarze są **po polsku** — trzymaj tę konwencję, kod czyta
też brat. Interfejs w całości po polsku.

## Pułapki wykryte przy budowie (oszczędzą ci godziny)

1. **docxtpl kasuje cały wiersz/akapit ze znacznikiem.** `{%tr for ... %}` usuwa *cały wiersz
   tabeli*, w którym stoi, a `{%p if ... %}` *cały akapit*. Dlatego pętla po wierszach wymaga
   **czterech** wierszy tabeli: nagłówek, sterujący (`{%tr for %}`), z danymi, zamykający
   (`{%tr endfor %}`). Wstawienie `{%tr for %}` w tej samej komórce co dane kasuje dane.
2. **`DocxTemplate.get_xml()` wymaga wcześniejszego `init_docx(reload=False)`**, inaczej leci
   `AttributeError: 'NoneType' object has no attribute '_element'`.
3. **LibreOffice ze Snapa/Flatpaka ma własny, odizolowany `/tmp`** — plik wyjściowy w
   `tempfile.TemporaryDirectory()` jest dla nas niewidoczny i konwersja „cicho" nie działa.
   Dlatego katalog roboczy konwersji leży w `dane/konwersja/`.
4. **LibreOffice odpala się z osobnym profilem** (`-env:UserInstallation=...`), żeby konwersja
   działała także wtedy, gdy użytkownik ma otwarty zwykły LibreOffice.
5. `domyslnie` przy polu typu `auto_numer` to **wzorzec numeru** (`{numer3}/{rok}`), a nie
   wartość startowa — nie wolno go wstawiać do formularza jako `value`.
6. **COM trzeba zainicjować w każdym wątku.** Trasy FastAPI zapisane jako `def` (a takie są
   `/pobierz/*/pdf` i `/scal`) wykonują się w puli wątków, nie w głównym — bez
   `pythoncom.CoInitialize()` leci `CoInitialize has not been called`. Stąd `_com()`
   w `app/pdf.py`.
7. **Wydanie = podbicie `WERSJA` + push.** Sam commit nic bratu nie wyśle — porównywany
   jest wyłącznie pierwszy wiersz pliku `WERSJA`. To celowe: decydujesz, kiedy dostaje
   nową wersję. Odwrotna pułapka: podbicie `WERSJA` bez wypchnięcia reszty kodu wyśle
   mu paczkę z gałęzi `main` w stanie, w jakim akurat jest. Numer czytamy z API GitHuba,
   bo `raw.githubusercontent` podawał go z cache jeszcze 3,5 minuty po pushu — paczka
   `.zip` miała już wtedy nowy kod, więc program ogłaszał „wersja aktualna”, mając
   nieaktualną. `raw` został jako zapas na wyczerpany limit API.
8. **Aktualizator nie może importować niczego spoza stdlib.** Chodzi z `.venv`, w którym
   nowych zależności jeszcze nie ma — `start.bat` woła go *przed* `pip install`, właśnie
   po to, żeby nowa wersja mogła dokładać biblioteki.
9. **Aktualizacja nadpisuje `app/` plik po pliku, nie kasując katalogu** — w trakcie
   działa z niego proces, który tę aktualizację przeprowadza.
10. **Word to jedna aplikacja na komputerze.** Konwersje idą pod `threading.Lock`, przez
   `DispatchEx` (własna instancja, nie przejmujemy okna użytkownika), z `Visible = False`
   i `DisplayAlerts = 0`, a `Documents.Open(..., ReadOnly=True)`. Bez `Quit()` w `finally`
   zostaje wiszący proces `WINWORD.EXE`.
11. **`UploadFile` bierz ze Starlette, nie z FastAPI.** `fastapi.UploadFile` jest *podklasą*
   `starlette.datastructures.UploadFile`, a `request.form()` tworzy obiekty klasy nadrzędnej —
   więc `isinstance(plik, fastapi.UploadFile)` jest zawsze fałszem i wgrane pliki znikają
   bez śladu. Kosztowało to działające scalanie załączników (wykryte dopiero testem z curl-em,
   bo formularz nie zgłaszał żadnego błędu).
12. **W zagnieżdżonej pętli Jinja `loop` to ta wewnętrzna.** W `formularz.html` numer wiersza
   tabeli trzeba zapamiętać w `{% set %}` przed pętlą po kolumnach — inaczej wszystkie wiersze
   dostają te same nazwy pól (`tab__punkty__0__…`, `__1__…` liczone po kolumnach) i wykaz
   współrzędnych rozsypuje się przy każdym ponownym wyświetleniu formularza: po błędzie
   walidacji i przy „Popraw i wygeneruj ponownie”.
13. **GUS nie ma linku do pliku TERC — jest przycisk ASP.NET.** Trzeba wczytać stronę
   „pliki pełne”, wyciągnąć `__VIEWSTATE` i odesłać POST z `__EVENTTARGET`
   (`ctl00$body$BTERCUrzedowyPobierz`). Działa i nie wymaga konta, ale jest kruche:
   gdy GUS przebuduje stronę, przyjdzie HTML zamiast ZIP-a. Dlatego `app/teryt.py`
   sprawdza nagłówek `PK` i mówi o tym po polsku, zamiast wywalać program —
   a stare dane zostają w bazie nietknięte.
14. **Gmina miejsko-wiejska (RODZ=3) nie jest jednostką ewidencyjną.** W EGiB dzieli się
   na miasto (4) i obszar wiejski (5), i tylko te mają obręby. ULDK odpytane o `_3`
   zwraca po cichu wyłącznie obręby obszaru wiejskiego — czyli listę niepełną. Dlatego
   `_3` w ogóle nie trafia do bazy.
15. **Pole typu `teryt` przychodzi z formularza jako cztery osobne pola**
   (`pole__polozenie__wojewodztwo` … `__obreb`). `odczytaj_dane` scala je w jeden słownik
   pod kluczem pola — inaczej walidacja „wymagane” nigdy by go nie zobaczyła, a historia
   zapisywałaby cztery luźne wartości zamiast jednego wyboru.

## Stan na teraz — przetestowane end-to-end

Formularz → `.docx` → PDF → sklejenie kilku PDF-ów w jeden. Działa: powtarzalne wiersze tabeli
(z wklejaniem z Excela), sekcje warunkowe, automatyczna numeracja (`001/2026`), daty w formacie
`31.07.2026` i `31 lipca 2026 r.`, dane stałe podstawiane do każdego dokumentu, powielanie
poprzedniego dokumentu, historia, ustawienia.

Wykrywanie konwertera PDF: Word (COM) → LibreOffice zainstalowany → LibreOffice przenośny
w katalogu `libreoffice/` obok programu. Stan widać w prawym górnym rogu aplikacji.

Ścieżka wordowa sprawdzona na Windows 11 + Office 16.0 (Python 3.14): formularz → `.docx` →
PDF przez trasę `/pobierz/{id}/pdf` (ok. 1,5 s) → `/scal`. Po konwersji nie zostaje proces
`WINWORD.EXE`. Gdy Word wywali się w trakcie, kod próbuje jeszcze LibreOffice’em (jeśli jest),
a jak go nie ma — pokazuje po polsku, że Word czeka pewnie z otwartym oknem dialogowym.

Aktualizacja sprawdzona na symulacji (skrypt jednorazowy, podstawione `file://` zamiast
GitHuba, instalacja z bazą + własnym szablonem brata): przeżywają baza, historia, licznik
numeracji, dane stałe, `wyniki/` i oba jego szablony; przychodzi nowy kod, nowe
`requirements.txt` i brakujące wzorce; powstaje kopia w `dane/kopie/`. Sprawdzone też
ścieżki „brak internetu" i „wersja aktualna" — obie kończą się startem programu.
Świeża instalacja i aktualizacja `.venv` przez `start.bat`: też przetestowane.

Pole typu `teryt` sprawdzone od końca do końca: pierwsze uruchomienie ściąga z GUS-u 3636
jednostek (16 województw / 380 powiatów / 3240 jednostek ewidencyjnych, rejestr na 2026-01-01)
w tle, bez blokowania startu; kaskada w przeglądarce zawęża listy, obręby dociągają się
z ULDK przy pierwszym wybraniu gminy (0,12 s) i potem lecą z bazy (0,03 s). Wybór przeżywa
błąd walidacji i „Popraw i wygeneruj ponownie”. Do dokumentu wchodzą nazwy i identyfikatory
osobnymi znacznikami (`{{ polozenie_obreb }}` = Baczków, `{{ polozenie_obreb_teryt }}` =
120102_2.0001).

Numer operatu jest **rezerwowany przed wypełnieniem szablonu** (musi wejść do treści
dokumentu), a po nieudanym generowaniu oddawany przez `db.zwolnij_numer` — warunkowym
`UPDATE ... WHERE stan = ?`, żeby nie cofnąć licznika, który w międzyczasie ruszył dalej.
Sprawdzone: trzy nieudane próby między dwoma dobrymi dokumentami dają `001` i `002`,
bez dziury.

**Nie ma jeszcze testów automatycznych.** Weryfikacja szła ręcznie przez przeglądarkę
i skrypty jednorazowe.

## Co dalej — kolejka

1. **Prawdziwe szablony brata.** `szablony/operat_wzor.docx` to atrapa wygenerowana skryptem.
   Gdy przyjdą jego formatki Worda — wstawić w nie tagi i dopisać pliki `.json`.
2. **Wczytywanie wykazu współrzędnych z pliku** zamiast wklepywania/wklejania — brat pewnie
   eksportuje dane z programu geodezyjnego (C-Geo, WinKalk, Geonet). Trzeba zapytać o format
   i dopisać parser.
2a. Sprawdzanie numeru działki przez ULDK (`GetParcelById`) — dane już są pod ręką, a to
   wyłapałoby literówkę w numerze, zanim operat pójdzie do ośrodka.
3. **Paczka dla Windowsa.** PyInstaller (`--onedir`) + instalator Inno Setup. Budowanie musi
   iść na Windowsie (brak cross-kompilacji) — albo lokalnie, albo GitHub Actions
   `windows-latest`. `app/config.py` jest już przygotowany na `sys.frozen`.
   Przy `--onefile` liczyć się z ostrzeżeniem SmartScreen i wolniejszym startem.
   Uwaga przy pakowaniu: `pywin32` wymaga w PyInstallerze `--hidden-import win32com.client`
   i `--hidden-import pythoncom`, inaczej konwersja PDF w `.exe` nie ruszy.
4. Kolejne typy dokumentów (protokół, szkic, sprawozdanie) — każdy to nowy plik w `szablony/`.
5. Testy (pytest) na `odczytaj_dane`, `przygotuj_kontekst` i wykrywanie pól z szablonu.
6. `bezpieczna_nazwa` gubi polskie znaki bez odpowiednika ASCII — „Sułkowice” w nazwie pliku
   robi się „Sukowice”. Kosmetyka, ale warto podmienić na transliterację (ł→l, ą→a…).

## Pytania otwarte do brata

- Które dokumenty poza operatem technicznym są mu potrzebne?
- Skąd bierze wykaz współrzędnych — z jakiego programu i w jakim formacie pliku?
- Ma na komputerze Microsoft Worda (wersję instalowaną, nie przeglądarkową)?
- Czy numeracja operatów ma być ciągła w roku, czy per rodzaj roboty?

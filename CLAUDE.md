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
| **Nie** drugi, niezależny generator PDF (ReportLab/WeasyPrint) | oznaczałby dwa szablony do utrzymania, które po pół roku wyglądają inaczej |
| **Nie** konwersja przez API w chmurze | dane osobowe + wymaga internetu |
| SQLite | historia, numeracja, dane stałe — zero konfiguracji |

## Zasada centralna

**Źródłem prawdy jest plik `.docx` w `szablony/`.** Aplikacja czyta z niego tagi Jinja
i **z nich buduje formularz**. Dopisanie `{{ nowe_pole }}` w Wordzie = nowe pole na stronie,
bez zmian w kodzie. Opcjonalny plik `.json` obok szablonu dokłada tylko etykiety, typy,
kolejność i grupy pól.

Jeśli masz pomysł, który wymaga wpisania listy pól konkretnego operatu do kodu Pythona —
to znak, że idziesz pod prąd tej architektury.

## Stos

Python 3.11+ (u autora testowane na 3.14), FastAPI + uvicorn, Jinja2, docxtpl (python-docx),
pypdf, SQLite. Wersje przypięte w [requirements.txt](requirements.txt). Bez frontendowego
frameworka — czysty HTML + trochę waniliowego JS w szablonach.

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
| `app/db.py` | SQLite: `dokumenty`, `ustawienia`, `liczniki` |
| `app/main.py` | trasy FastAPI, parsowanie formularza (w tym tabel) |
| `app/web/templates/` | widoki; `pomoc.html` to instrukcja dla brata, aktualizuj ją razem z funkcjami |
| `narzedzia/utworz_wzor_szablonu.py` | generuje przykładowy szablon operatu do testów |
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

## Stan na teraz — przetestowane end-to-end

Formularz → `.docx` → PDF → sklejenie kilku PDF-ów w jeden. Działa: powtarzalne wiersze tabeli
(z wklejaniem z Excela), sekcje warunkowe, automatyczna numeracja (`001/2026`), daty w formacie
`31.07.2026` i `31 lipca 2026 r.`, dane stałe podstawiane do każdego dokumentu, powielanie
poprzedniego dokumentu, historia, ustawienia.

Wykrywanie konwertera PDF: Word (COM) → LibreOffice zainstalowany → LibreOffice przenośny
w katalogu `libreoffice/` obok programu. Stan widać w prawym górnym rogu aplikacji.

**Nie ma jeszcze testów automatycznych.** Weryfikacja szła ręcznie przez przeglądarkę
i skrypty jednorazowe.

## Co dalej — kolejka

1. **Prawdziwe szablony brata.** `szablony/operat_wzor.docx` to atrapa wygenerowana skryptem.
   Gdy przyjdą jego formatki Worda — wstawić w nie tagi i dopisać pliki `.json`.
2. **Wczytywanie wykazu współrzędnych z pliku** zamiast wklepywania/wklejania — brat pewnie
   eksportuje dane z programu geodezyjnego (C-Geo, WinKalk, Geonet). Trzeba zapytać o format
   i dopisać parser.
3. **Paczka dla Windowsa.** PyInstaller (`--onedir`) + instalator Inno Setup. Budowanie musi
   iść na Windowsie (brak cross-kompilacji) — albo lokalnie, albo GitHub Actions
   `windows-latest`. `app/config.py` jest już przygotowany na `sys.frozen`.
   Przy `--onefile` liczyć się z ostrzeżeniem SmartScreen i wolniejszym startem.
4. **Word jako konwerter na Windowsie**: odkomentować `docx2pdf` w `requirements.txt`
   (ciągnie `pywin32`) i sprawdzić realnie na maszynie brata — dotąd testowane tylko
   na LibreOffice pod Linuksem.
5. Kolejne typy dokumentów (protokół, szkic, sprawozdanie) — każdy to nowy plik w `szablony/`.
6. Testy (pytest) na `odczytaj_dane`, `przygotuj_kontekst` i wykrywanie pól z szablonu.

## Pytania otwarte do brata

- Które dokumenty poza operatem technicznym są mu potrzebne?
- Skąd bierze wykaz współrzędnych — z jakiego programu i w jakim formacie pliku?
- Ma na komputerze Microsoft Worda (wersję instalowaną, nie przeglądarkową)?
- Czy numeracja operatów ma być ciągła w roku, czy per rodzaj roboty?

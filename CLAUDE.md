# Kontekst projektu — dla Claude Code

Ten plik jest wczytywany automatycznie na starcie sesji. Opisuje **po co** powstaje ten
program i **dlaczego** jest zrobiony właśnie tak — reszta (co robi kod) jest w kodzie
i w [README.md](README.md).

## Dla kogo i po co

Odbiorcą jest **brat użytkownika — geodeta**. Nie jest programistą. Ma dostać narzędzie,
które zastępuje ręczne przeklejanie danych do formatek w Wordzie:

1. wypełnia formularz w przeglądarce (dane roboty, położenie działki),
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
| SQLite | historia, numeracja, dane TERYT — zero konfiguracji |
| Aktualizacje: program sam pobiera `.zip` z GitHuba przy starcie | brat nie jest programistą; nie ma mowy o `git pull` ani o ręcznym rozpakowywaniu paczek na wierzch, bo prędzej czy później nadpisałby sobie szablony |
| `szablony/` jest **lustrzane**: plik usunięty z repozytorium znika też u brata (`LUSTRZANE` w `aktualizacja.py`) | bez tego szablon po zmianie nazwy zostawał u niego na zawsze i straszył na liście jako pozycja, której nikt już nie utrzymuje — dokładnie to się stało przy `operat_wzor` → `spis_tresci_wzor`. `app/` celowo nie jest lustrzane: kasowanie plików działającego procesu to proszenie się o kłopoty |
| **Jeden katalog `szablony/`**, wersjonowany w repo i nadpisywany przy aktualizacji | decyzja z 31.07.2026, zmiana wcześniejszej: formatki Worda utrzymuje autor, nie brat, więc podział na „wzorcowe” i „jego” tylko przeszkadzał — poprawka szablonu nie docierała do brata, dopóki nie skasował pliku ręcznie. Stara zawartość i tak ląduje w `dane/kopie/` przed każdą aktualizacją |
| Wersja schematu bazy w `PRAGMA user_version` + lista `MIGRACJE` | baza u brata to jedyny egzemplarz historii i numeracji; nowy kod na starej bazie musi umieć ją dociągnąć, a nie wywalić się na brakującej kolumnie |
| **Żaden błąd nie wychodzi do przeglądarki po angielsku** — globalne uchwyty w `app/main.py` + `blad.html`, ślad do `dane/bledy.log` | brat nie odróżni `AttributeError` od awarii dysku; ma zobaczyć, co się stało, że jego dane są całe i co ma zrobić. Log to jedyny ślad po awarii, bo okno konsoli zamyka razem z programem |
| TERYT: plik `TERC_Urzedowy` z GUS + obręby z ULDK, **wszystko cache'owane w SQLite** | oficjalna usługa GUS (TERYT ws1) wymaga rejestracji i hasła wysyłanego pocztą przez Urząd Statystyczny — u brata to dyskwalifikacja. Cache jest obowiązkowy, bo w terenie nie ma internetu |
| Obręby dociągane **dla wybranej gminy**, a hurtowo tylko na wyraźne kliknięcie | ULDK oddaje obręby jednej jednostki w jednym zapytaniu (~0,1 s), więc na co dzień nie ma czego pobierać z góry. Przycisk „Pobierz obręby dla całej Polski” (z paskiem postępu) jest dla wyjazdu w teren bez zasięgu: 3240 zapytań, ok. 100 s, 54 tys. obrębów, baza rośnie do ~4,7 MB |
| **Poprawianie operatu nie zużywa numeru** — `?edytuj=<id>` wraca do tego samego katalogu i wpisu w historii | brat będzie poprawiał spis treści i literówki po wygenerowaniu; gdyby każda poprawka brała kolejny numer, numeracja operatów rozjechałaby się w tydzień. „Powiel jako nowy” zostaje osobno, dla kolejnego zlecenia |
| Na stronie głównej tylko szablony z `"glowny": true` | sprawozdanie i protokoły same bez operatu nie istnieją — dokłada się je checkboxem w formularzu. Gdy nikt nie jest oznaczony, pokazujemy wszystkie, żeby świeży zestaw szablonów nie zniknął bez śladu |
| Pole typu `dokumenty` z listą `tylko` — osobna karta na każdy dokument | opcje sprawozdania stały pod wspólną listą checkboxów i wyglądały, jakby dotyczyły ostatniej pozycji. Teraz każdy dokument ma kartę: checkbox „czy generować” i pod nim jego opcje. Pole bez `tylko` zbiera resztę, więc nowy szablon nadal pokazuje się sam — w karcie „Inne dokumenty” |
| Kilka dokumentów naraz: pole typu `dokumenty` w formularzu, lista brana z plików w `szablony/` | operat to kilka plików Worda z tymi samymi danymi. Dodatkowe szablony wypełnia `generator.dopisz_dokument` **tym samym kontekstem**, więc numer operatu jest ten sam, a `auto_numer` nie sięga po kolejny z licznika. Lista jest świadomie niezależna od spisu treści — spis mówi, co w operacie jest, także rzeczy spoza programu |
| **Jeden operat = jeden katalog w `wyniki/`**, nazwany numerem operatu — numer ma postać `001/2026` (tak czyta go ośrodek), a katalog `001.2026` — ukośnik zamieniamy na **kropkę**, bo Windows go w nazwie folderu nie przyjmie, a myślnik czytał się gorzej; robi to `operaty.nazwa_katalogu`; scalony PDF nazywa się dokładnie jak numer roboty | brat i tak dokłada do operatu mapy i szkice Eksploratorem, a przepisy wymagają, żeby gotowy plik nazywał się numerem KERG. Katalog opisuje `operat.json`, żeby przeżył skopiowanie na inny dysk i utratę bazy |
| **Wynik składania nie wraca w odpowiedzi na POST** — POST przekierowuje na stronę układania z komunikatem, a PDF otwiera się z linku `target="_blank"` | formularz z `target="_blank"` bywa blokowany (potwierdzone w przeglądarce podglądu Claude Code: kliknięcie „Złóż PDF” nie robiło nic). Dla brata „nic się nie stało” to najgorszy możliwy objaw; link kliknięty przez człowieka nie jest blokowany nigdy |
| Podglądy PDF robione **z wyprzedzeniem, w tle**, i **wsadowo** — jedno uruchomienie konwertera na komplet dokumentów | najdroższy jest start Worda, nie sam dokument: cztery pliki osobno to cztery starty. Zmierzone na LibreOfficie: 3,55 s → 1,17 s (67% mniej), na Windowsie zysk większy, bo Word startuje wolniej. Konwersja rusza zaraz po wygenerowaniu, więc do wejścia na stronę składania zwykle jest już po wszystkim |
| Miniatury stron przez `pypdfium2` + `Pillow`, renderowane na serwerze | brat układa kolejność myszą, więc musi widzieć, co przeciąga. Renderowanie w przeglądarce oznaczałoby kilkanaście ramek z czytnikiem PDF, które połykają zdarzenia myszy; `pypdfium2` to jedno koło z pip, bez niczego do instalowania w systemie |
| Wygląd formatek nakłada **skrypt** (`ujednolic_wyglad.py`), a nie ręka w Wordzie | dokumenty operatu mają wyglądać jak komplet, a formatki przychodzą pojedynczo i przez lata; ręczne pilnowanie kroju, logo i stopki w każdym pliku z osobna nie ma szans się utrzymać. Skrypt rozpoznaje role akapitów po tym, co w pliku zastaje, więc działa też na formatkach dołożonych później |
| **Skrypt ustala hierarchię, brat ustala akcenty.** `ujednolic_wyglad.py` narzuca już tylko krój, rozmiary tytułu/nagłówka/tekstu, logo i stopkę. Nie rusza: pogrubień (w treści, w etykietach, w tabelach), wyrównania akapitów, rozmiarów w tabelach ani tabulatorów poza wyrównywanym blokiem | ta lista rosła kosztem **czterech** wpadek — skrypt po kolei kasował bratu pogrubienia w treści, pogrubienia etykiet, wybrany rozmiar nagłówka („Spis treści” 11 → 12 pt) i wcięcie zrobione pięcioma tabulatorami. Za każdym razem jego świadomy wybór brałem za niespójność do naprawienia, a poprawianie tego w Wordzie nic nie dawało, bo skrypt cofał to przy następnym uruchomieniu. Zasada: **jak się wahasz, czy coś ujednolicić — nie ujednolicaj**. Jedyny wyjątek to czerwony numer roboty, zawsze pogrubiony |
| **Jedna stopka, przepisywana z `spis_tresci_wzor.docx`** do pozostałych formatek | każda formatka przychodzi z własną kopią firmówki i drobne różnice same się w nich zalęgają: raz kreska jest obramowaniem akapitu, raz wklejonym obrazkiem, raz nazwa ulicy jest z wielkiej litery, raz z małej. Przystanki kolumn liczą się z szerokości **danej** strony, bo wykaz działki jest poziomy |
| Kolumna wartości w blokach „Etykieta: wartość” liczona z **pomiaru najdłuższej etykiety** prawdziwym plikiem czcionki | przystanek wzięty „na oko” albo wpisany na sztywno prędzej czy później wypada przed końcem etykiety — wtedy tabulator ją przeskakuje i ląduje na przypadkowym przystanku domyślnym. Tak właśnie rozjeżdżał się nagłówek wykazów. Mierzy `PIL.ImageFont` po pliku Calibri/Carlito |
| **Calibri**, nie Bahnschrift | Bahnschrift jest tylko na Windowsie i nie ma odpowiednika na Linuksie, więc podglądy PDF u autora łamały się inaczej niż dokumenty u brata. Calibri ma metrycznie zgodne Carlito (`fonts-crosextra-carlito`) — ten sam plik łamie się tak samo po obu stronach |
| **Bez numeracji stron**, jedna stopka na wszystkich stronach i we wszystkich dokumentach | operat i tak jest sklejany z kilkunastu plików w jeden PDF, więc numer strony pojedynczego dokumentu nic nie znaczy, a wprowadza w błąd. Uwaga: pole z numerem siedziało też w **nieużywanej** stopce stron parzystych i wróciłoby przy pierwszej zmianie ustawień — dlatego skrypt nadpisuje wszystkie trzy stopki |
| W wykazie zmian działki identyfikator kończy się **kropką i niczym więcej** — `[{{ polozenie_obreb_teryt }}.]` | to **nie jest błąd ani niedokończona edycja**, tylko pomysł brata: program wstawia obręb, a numer działki brat dopisuje sam w Wordzie, bo w jednym wykazie bywa ich kilka i nie zawsze wszystkie z formularza. `{{ nr_dzialki }}` celowo nie występuje w tym pliku — nie „poprawiaj” tego |
| **Dane stałe usunięte z programu** — nazwisko, uprawnienia, pieczątka firmy | brat woli mieć je wpisane na sztywno w swoim szablonie Worda; to i tak nie zmienia się między robotami, a jeden ekran mniej to jeden ekran mniej do tłumaczenia. `db.wczytaj_ustawienia` i `zrodlo: "ustawienia"` zostają w kodzie, ale bez interfejsu |

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
| `app/db.py` | SQLite: `dokumenty`, `liczniki`, `teryt_*` (`ustawienia` bez interfejsu) |
| `app/teryt.py` | jednostki TERYT z GUS + obręby z ULDK; **tylko biblioteka standardowa** |
| `app/operaty.py` | katalog operatu: zakładanie, `operat.json`, lista plików do sklejenia; nazwa pliku wynika z nazwy szablonu (`spis_tresci_wzor` → `spis_tresci.docx`) |
| `app/miniatury.py` | podgląd pierwszej strony PDF-a (pypdfium2 + Pillow) |
| `app/main.py` | trasy FastAPI, parsowanie formularza (w tym tabel) |
| `app/web/templates/` | widoki; `blad.html` to strona każdego niezłapanego wyjątku, a `pomoc.html` instrukcja dla brata — aktualizuj ją razem z funkcjami |
| `narzedzia/utworz_wzor_szablonu.py` | generuje przykładowy szablon spisu treści do testów; nie nadpisze istniejącego bez `--nadpisz` |
| `narzedzia/utworz_wzor_sprawozdania.py` | szkielet sprawozdania technicznego; też nie nadpisuje istniejącego bez `--nadpisz` |
| `narzedzia/utworz_wzory_wykazow.py` | szkielety obu wykazów zmian danych ewidencyjnych |
| `narzedzia/ujednolic_wyglad.py` | **puść po każdej podmianie formatki**, przed `popraw_szablon.py` — jeden krój, jedno logo, jedna hierarchia we wszystkich dokumentach operatu; nie rusza treści ani czerwieni numeru roboty |
| `narzedzia/popraw_szablon.py` | **puść po każdej podmianie formatki od brata** — nakłada tabulator i wcięcie wiszące w spisie treści oraz przypina podpis do dołu strony |
| `narzedzia/instalacja_testowa.py` | odtwarza instalację brata (zip z GitHuba, bez `.git`), opcja `--stara-wersja` wymusza aktualizację przy starcie |
| `szablony/` | formatki Worda, wersjonowane w repo; aktualizacja je podmienia |
| `wyniki/`, `dane/` | dane użytkownika, w `.gitignore` |

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
7a. **Numer wersji to `rok.miesiąc.dzień.licznik` — data ma być z dnia wydania,
   a licznik liczy wydania tego dnia i zaczyna się od 1.** Łatwo o tym zapomnieć przy
   serii poprawek ciągnącej się po północy: numery doszły do `2026.07.31.40`, choć
   wydania szły już 1 sierpnia. Nic się przez to nie psuje — porównanie jest wyłącznie
   na równość (`numer == lokalna`), nigdy „na większy”, więc licznik może wrócić do 1
   przy nowej dacie — ale numer przestaje mówić, kiedy brat co dostał.
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
12a. **Formatowania akapitu nie da się wyklikać raz na zawsze w formatce brata.** Przy każdej
   nowej wersji `.docx` trzeba puścić `narzedzia/popraw_szablon.py`: pozycja spisu treści
   potrzebuje tabulatora zamiast spacji po numerze (inaczej „1.” i „13.” mają różną
   szerokość i tekst startuje w różnych miejscach) oraz wcięcia wiszącego (inaczej
   zawinięta pozycja chowa się pod numerem), a podpis — ramki `w:framePr` z
   `vAnchor="margin" yAlign="bottom"`, żeby stał na dole strony niezależnie od długości
   spisu. Skrypt jest odporny na powtórzenie.
12d. **Kolejność elementów w OOXML jest częścią schematu, a Word tego pilnuje —
   LibreOffice nie.** Dołożenie `<wp:wrapSquare>` na końcu `<wp:anchor>` (zamiast zaraz
   po `effectExtent`) i `<w:spacing>` na końcu `<w:rPr>` (zamiast przed `<w:sz>`) dało
   pliki, które na Linuksie składały się do PDF-a bez jednego ostrzeżenia, a **w Wordzie
   w ogóle się nie otwierały** — u brata objawiło się to tym, że przestały powstawać
   miniatury, bo konwersja nie miała czego otworzyć. Kosztowało to całe wydanie.
   Wniosek: elementy dokładaj **przed** pierwszym, który wg schematu ma iść po nich
   (`_wstaw_przed` w `ujednolic_wyglad.py`), a poprawność sprawdzaj w kodzie
   (`_sprawdz_kolejnosc` odmawia zapisania pliku, który Word odrzuci). **Zielony PDF
   z LibreOffice'a nie jest dowodem, że plik jest poprawny.**
12e. **`<a:ext>` to dwa różne elementy o tej samej nazwie.** W `<a:xfrm>` niesie rozmiar
   obrazka (`cx`/`cy`), ale `<a:ext uri="…">` to pozycja listy rozszerzeń — dopisanie jej
   `cx`/`cy` daje plik nie do otwarcia w Wordzie. `findall(".//a:ext")` łapie oba; trzeba
   schodzić przez `a:xfrm`. Tak samo `<wp:wrapSquare>` **wymaga** atrybutu `wrapText` —
   podmiana oblewania na „gołe” `OxmlElement("wp:wrapSquare")` gubi go po cichu.
   Oba błędy trafiły tylko w spis treści (sprawozdanie ma `wrapTopAndBottom`, który
   niczego nie wymaga), więc objaw wyglądał na „jeden plik zepsuty, drugi działa”.
12f. **`dokument.paragraphs` nie widzi tabel.** Wyznaczając bloki akapitów sąsiadujących
   ze sobą, trzeba iść po `dokument.element.body`, bo tabela stojąca między blokiem
   nagłówkowym a podpisem jest dla pętli po akapitach niewidzialna — oba bloki
   skleiły się wtedy w jeden i podpis wykazu zjechał na lewą stronę kartki.
12g. **Przy dopasowywaniu bloku do szerokości strony zostaw zapas.** Pomiar szerokości
   napisu z pliku czcionki jest dokładny, ale Word łamie wiersz odrobinę wcześniej,
   niż wynika z sumy szerokości znaków. Bez zapasu podpis łamał się o włos i wypychał
   wykaz działki na drugą stronę.
12b. **Word trzyma każdy tabulator w osobnym biegu tekstu.** `"\t\t" in akapit.text` bywa
   prawdą, choć żaden pojedynczy bieg nie zawiera dwóch tabulatorów — `bieg.text.replace`
   nic wtedy nie robi i „poprawka” cicho nie działa (a przy powtórzeniu dokłada kolejny
   przystanek). Nadmiarowe tabulatory trzeba usuwać, idąc przez cały akapit i pamiętając
   ostatni znak z poprzedniego biegu; tak robi `narzedzia/ujednolic_wyglad.py`.
   **Ale zwijaj je wyłącznie w bloku, któremu sam ustawiasz przystanek.** Poza nim
   ciąg tabulatorów to świadome wcięcie: brat wsuwa pięcioma tabulatorami wiersz
   z tolerancjami (`[dl – 0.02 m] / [dh – 0.03 m]`) pod kolumnę wartości, a zwinięcie
   ich do jednego przesuwało mu ten wiersz w lewo przy każdym uruchomieniu skryptu.
12c. **Pusty akapit nie zawsze jest odstępem.** Ten z ramką `w:framePr` to podkładka
   podnosząca przypięty podpis (patrz `popraw_szablon.py`); zmiana jego rozmiaru przesuwa
   podpis na stronie. Przy hurtowym formatowaniu akapity w ramce trzeba pomijać.
13a. **Puste pole z formularza to nie brak pola.** Przeglądarka wysyła każdy `<input>`,
   także pusty, więc `dane.setdefault(klucz, ...)` nic nie zrobi — klucz *jest*, tylko
   z pustym napisem. Kosztowało to numerację: poprawianie operatu brało kolejny numer
   z licznika mimo podstawiania starego. Testując trasy curl-em wysyłaj **komplet pól
   formularza**, łącznie z pustymi, bo inaczej sprawdzasz coś innego niż przeglądarka.
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
16. **Znaczniki wyliczane muszą być wpisane na listę w `szablony.py`.** Wszystko, czego nie
   ma w `.json`, a jest w `.docx`, ląduje w formularzu jako puste pole tekstowe — więc
   `{{ polozenie_gmina }}` czy `{{ data_dokumentu_slownie }}` robiły grupę „Pozostałe pola
   z szablonu” pełną pól, których nikt nie ma wypełniać. Stąd `SUFIKSY_TERYT`, `SUFIKSY_DATY`
   i `POLA_WYLICZANE`; dokładając nowy wyliczany znacznik w `generator.py`, dopisz go tam.
17. **`hidden` w HTML-u nie działa, gdy CSS ustawia `display`.** Reguła
   `button, .glowny, .wtorny { display: inline-block }` przebijała domyślne `[hidden]`
   przeglądarki i przycisk „Przerwij” był widoczny zawsze. Stąd `[hidden] { display: none
   !important }` na górze `style.css`.
18. **Przerwanie puli wątków musi wychodzić z pętli po wynikach.** `ThreadPoolExecutor.map`
   ma już w kolejce wszystkie zadania; gdy zadanie po ustawieniu flagi stopu tylko szybko
   zwraca pustkę, licznik postępu i tak dobija do końca i wygląda to jak udane pobranie.
   Tak samo znacznik „trwa” trzeba postawić **w funkcji startującej, pod zamkiem**, a nie
   w wątku roboczym — inaczej dwa szybkie kliknięcia uruchamiają dwa pobierania naraz.

## Stan na teraz — przetestowane end-to-end

Formularz → `.docx` → PDF → sklejenie kilku PDF-ów w jeden. Działa: powtarzalne wiersze tabeli
(z wklejaniem z Excela), sekcje warunkowe, automatyczna numeracja (`001/2026`), daty w formacie
`31.07.2026` i `31 lipca 2026 r.`, powielanie poprzedniego dokumentu, historia.

**Wszystkie cztery formatki to prawdziwe dokumenty brata**, po przejściu
`ujednolic_wyglad.py` i `popraw_szablon.py`: spis treści, sprawozdanie techniczne
oraz wykazy zmian danych ewidencyjnych dotyczące budynku (pionowy) i działki
(**poziomy**, 13 kolumn). Wygląd sprawdzony na Wordzie u brata — po serii poprawek,
w których to on decydował o pogrubieniach, a skrypt o reszcie.

Spis treści mieści się na jednej stronie A4 z kompletem 13 pozycji, a podpis zostaje
przypięty do dołu strony niezależnie od jego długości. Sprawozdanie zajmuje dwie strony
i świadomie **nie walczymy o jedną** — przy dłuższym opisie przebiegu i tak by się nie
zmieściło (decyzja brata). Oba wykazy mieszczą się na jednej.

Formatki przeszły kilka rund poprawek brata. Przy każdej podmianie sprawdzaj nie tylko
to, czy skrypt się wykonał, ale **czy nie cofnął jego zmian** — najprościej porównaniem
biegów tekstu przed i po (pogrubienia, wyrównanie, liczba tabulatorów, liczba akapitów).
Cztery razy okazało się, że cofnął.

Wykrywanie konwertera PDF: Word (COM) → LibreOffice zainstalowany → LibreOffice przenośny
w katalogu `libreoffice/` obok programu. Stan widać w prawym górnym rogu aplikacji.

Ścieżka wordowa sprawdzona na Windows 11 + Office 16.0 (Python 3.14): formularz → `.docx` →
PDF przez trasę `/pobierz/{id}/pdf` (ok. 1,5 s) → `/scal`. Po konwersji nie zostaje proces
`WINWORD.EXE`. Gdy Word wywali się w trakcie, kod próbuje jeszcze LibreOffice’em (jeśli jest),
a jak go nie ma — pokazuje po polsku, że Word czeka pewnie z otwartym oknem dialogowym.

Aktualizacja sprawdzona na symulacji (skrypt jednorazowy, podstawione `file://` zamiast
GitHuba, instalacja z bazą + własnym szablonem brata): przeżywają baza, historia, licznik
numeracji, `wyniki/` i oba jego szablony; przychodzi nowy kod, nowe
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

Pobieranie obrębów dla całej Polski przetestowane w przeglądarce: 3240 jednostek w ok. 100 s
(4 zapytania naraz), 54 251 obrębów w 3227 jednostkach — 13 jednostek ULDK nie zna i to
normalne. Pasek postępu, przerwanie w połowie i „Pobierz brakujące” (wznawia tylko to,
czego nie ma) działają; drugie kliknięcie w trakcie nie startuje drugiego pobierania.

Numer operatu jest **rezerwowany przed wypełnieniem szablonu** (musi wejść do treści
dokumentu), a po nieudanym generowaniu oddawany przez `db.zwolnij_numer` — warunkowym
`UPDATE ... WHERE stan = ?`, żeby nie cofnąć licznika, który w międzyczasie ruszył dalej.
Sprawdzone: trzy nieudane próby między dwoma dobrymi dokumentami dają `001` i `002`,
bez dziury.

**Nie ma jeszcze testów automatycznych.** Weryfikacja szła ręcznie przez przeglądarkę
i skrypty jednorazowe.

## Co dalej — kolejka

1. **Dokładanie kolejnej formatki** (przepis, bo to się będzie powtarzać): wrzuć `.docx`
   do `szablony/` pod nazwą `<coś>_wzor.docx`, sprawdź, czy brat wstawił tagi `{{ }}`,
   i puść `ujednolic_wyglad.py`, a potem `popraw_szablon.py`. Checkbox w formularzu
   pojawi się sam. Obowiązkowo **obejrzyj złożony PDF**, a nie same liczby — wszystkie
   usterki tej serii (podpis zjeżdżający w lewo, dokument puchnący na drugą stronę,
   stopka kończąca się w dwóch trzecich szerokości) widać było dopiero na obrazku.
   Orientacja pozioma nie wymaga niczego dodatkowego: szerokości liczą się z rozmiaru
   strony danego pliku. `utworz_wzory_wykazow.py` zostaje jako generator szkieletu.
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

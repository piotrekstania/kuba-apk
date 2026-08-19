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
| Historia zmian jako **plik w repozytorium**, generowany z historii `WERSJA` w gicie | u brata nie ma `.git`, więc commity nie są dla niego żadnym źródłem. Opis dla użytkownika i tak powstaje przy każdym wydaniu w pliku `WERSJA` — `zbuduj_zmiany.py` tylko go zbiera, żeby nikt nie przepisywał tego ręcznie i nie pomylił numeru |
| Menu „Pomoc” na `<details>`, **bez JS-a** | natywny element obsługuje klawiaturę, działa bez skryptów i zamyka się sam przy przejściu na inną stronę. Uwaga: `display: flex` na liście nie psuje ukrywania — przeglądarka i tak nie maluje ani nie klika zawartości zamkniętego `<details>` (sprawdzone `elementFromPoint`) |
| Przy trafionej działce pokazujemy też **powierzchnię, liczoną z obrysu** | ULDK nie oddaje powierzchni osobnym polem (sprawdzone: `area`, `powierzchnia`, `parcel_area` zwracają pustkę), ale oddaje geometrię w `SRID=2180`, czyli w metrycznym PL-1992 — pole liczy się wprost ze współrzędnych (`powierzchnia_z_wkt`), bez przeliczania układów i bez wychodzenia poza bibliotekę standardową. To druga para oczu: numer `123/5` zamiast `123/4` **też istnieje**, więc samo „jest taka działka” tego nie wyłapie, a inna wielkość owszem (zmierzone na sąsiednich działkach: 4159 m² i 5016 m²). Piszemy „ok.”, bo to pole z obrysu, a nie powierzchnia ewidencyjna z rejestru |
| Sprawdzanie numeru działki w ULDK jest **podpowiedzią, nigdy blokadą** | ULDK nie zna wszystkich działek — przy hurtowym pobieraniu obrębów 13 jednostek w ogóle nie odpowiedziało. Komunikat „zły numer” o poprawnej działce nauczyłby brata ignorowania komunikatów, czyli zepsułby też te prawdziwe. Dlatego stan `nieznane` (usługa milczy, brak sieci) jest osobny od `brak` i **nic nie pokazuje**, a `brak` mówi „ewidencja nie zna — sprawdź numer”, na pomarańczowo, nie na czerwono. Formularz zawsze da się wysłać |
| **Układ kafelków zapamiętany w `operat.json`** (`uklad`: kolejność + obroty) | brat składa ten sam operat po kilka razy — po dołożeniu skanu, po poprawce spisu treści — a kolejność i obroty ustawia myszą. Powtarzanie tego za każdym razem to była praca do wyrzucenia. Nowe pliki dokładają się **na końcu** listy, bo `sort` jest stabilny. Świadomie **nie** zapamiętujemy plików pominiętych krzyżykiem: plik ukryty na stałe, o którym program milczy, byłby trudniejszy do odnalezienia niż jedno kliknięcie. Zapis idzie dopiero **po udanym** złożeniu, więc nieudana próba nie kasuje poprzedniego ustawienia. Uwaga: `zaloz()` przepisuje `operat.json` od nowa przy każdym poprawianiu operatu i musi ten klucz przenieść — inaczej literówka w formularzu kasowałaby układ |
| **Jedna lista operatów na stronie głównej**, bez osobnej strony „Złóż PDF” | dwie listy tych samych operatów wyglądały jak pomyłka, a różniły się dokładnie tym, czego nie było widać: strona główna czytała **bazę** i pokazywała **15 najnowszych**, a `/scal` skanował **dysk** i pokazywał **wszystkie**. Scalone: lista bierze historię z bazy i dokłada katalogi z `wyniki/`, których w historii nie ma (znacznik „spoza historii”) — tak wygląda operat przywrócony z archiwum albo skopiowany z innego komputera. Trasa `/scal` została jako przekierowanie na `/`, bo prowadzi do niej kilkanaście przekierowań z obsługi błędów i zakładka w przeglądarce |
| Numer przy poprawianiu bierzemy z `operat.json`, a **gdy folder jest w archiwum — z historii w bazie** | `operat.json` jedzie razem z katalogiem, więc po archiwizacji znikał jedyny znany programowi ślad numeru. Poprawka stawała się wtedy po cichu nowym operatem: brała kolejny numer z licznika i zakładała katalog obok („poprawiam 055, a robi się 060”), a w historii numer zostawał stary — wpis mówił jedno, folder drugie. Numer i numer roboty są w tabeli `dokumenty`, więc jest z czego odtworzyć; generatorowi wystarczają dwa klucze |
| Operat przeniesiony do archiwum **zostaje w historii**, ale oznaczony „w archiwum” i bez przycisku „Złóż PDF” | przeniesienie folderu Eksploratorem nie rusza bazy, więc wpis zostaje — i dobrze, bo brat widzi, że taka robota była. Ale składać nie ma czego: przycisk prowadził do trasy, która po cichu odsyłała na listę, czyli klasyczne „nic się nie stało”. Teraz wiersz ma znacznik, przycisku nie ma, a wejście z zakładki na `/scal/<nazwa>` tłumaczy po polsku, że folder trzeba skopiować z powrotem. To samo przy „Otwórz katalog” |
| Podglądy operatów, których nie ma już w `wyniki/`, kasują się **przy starcie** (`operaty.sprzataj_podglady`) | kasowanie operatu przyciskiem sprzątało po sobie od początku, ale brat **archiwizuje operaty Eksploratorem** i program się o tym nie dowiaduje — PDF-y podglądów zostawały wtedy na zawsze. Podgląd odtwarza się sam przy następnym wejściu na stronę składania, więc pomyłka kosztuje jedną konwersję, a nie utratę danych. Przy okazji: usuwanie operatu kasuje podglądy **po nazwie katalogu**, nie po obiekcie `Path` — operat bywa usuwany z historii wtedy, gdy jego folder już zniknął z dysku |
| W `dane/kopie/` zostaje **pięć ostatnich** kopii, a sprząta się to **przy każdym starcie programu** (`cykl_zycia`) | kopia powstaje przed **każdą** aktualizacją, a wydań bywa kilkanaście dziennie — przy ~1 MB na kopię (u brata z obrębami całej Polski ~5 MB, bo tyle waży wtedy baza) katalog rósłby bez końca; u brata uzbierało się 40 kopii, czyli ~34 MB. Ratunkowa jest zawsze ostatnia: gdy aktualizacja coś zepsuje, widać to od razu, a nie po dziesięciu wydaniach. Limit siedzi w `ILE_KOPII` (`aktualizacja.py`) i `ILE_KOPII_BAZY` (`db.py`) — kopie sprzed migracji schematu sprząta `db`, bo to pojedyncze pliki, a nie katalogi. **Pierwsza wersja sprzątała tylko w `_kopia_zapasowa`, czyli w trakcie aktualizacji — i nie zadziałała** (patrz pułapka 7b): aktualizację wykonuje stary kod, więc sprzątanie ruszyłoby dopiero przy następnej. Porządki na dysku nie mają nic wspólnego z aktualizacją i nie mogą od niej zależeć |
| Wersja schematu bazy w `PRAGMA user_version` + lista `MIGRACJE` | baza u brata to jedyny egzemplarz historii i numeracji; nowy kod na starej bazie musi umieć ją dociągnąć, a nie wywalić się na brakującej kolumnie |
| **Żaden błąd nie wychodzi do przeglądarki po angielsku** — globalne uchwyty w `app/main.py` + `blad.html`, ślad do `dane/bledy.log` | brat nie odróżni `AttributeError` od awarii dysku; ma zobaczyć, co się stało, że jego dane są całe i co ma zrobić. Log to jedyny ślad po awarii, bo okno konsoli zamyka razem z programem |
| TERYT: plik `TERC_Urzedowy` z GUS + obręby z ULDK, **wszystko cache'owane w SQLite** | oficjalna usługa GUS (TERYT ws1) wymaga rejestracji i hasła wysyłanego pocztą przez Urząd Statystyczny — u brata to dyskwalifikacja. Cache jest obowiązkowy, bo w terenie nie ma internetu |
| Obręby dociągane **dla wybranej gminy**, a hurtowo tylko na wyraźne kliknięcie | ULDK oddaje obręby jednej jednostki w jednym zapytaniu (~0,1 s), więc na co dzień nie ma czego pobierać z góry. Przycisk „Pobierz obręby dla całej Polski” (z paskiem postępu) jest dla wyjazdu w teren bez zasięgu: 3240 zapytań, ok. 100 s, 54 tys. obrębów, baza rośnie do ~4,7 MB |
| **Poprawianie operatu nie zużywa numeru** — `?edytuj=<id>` wraca do tego samego katalogu i wpisu w historii | brat będzie poprawiał spis treści i literówki po wygenerowaniu; gdyby każda poprawka brała kolejny numer, numeracja operatów rozjechałaby się w tydzień. „Powiel jako nowy” zostaje osobno, dla kolejnego zlecenia |
| Na stronie głównej tylko szablony z `"glowny": true` | sprawozdanie i protokoły same bez operatu nie istnieją — dokłada się je checkboxem w formularzu. Gdy nikt nie jest oznaczony, pokazujemy wszystkie, żeby świeży zestaw szablonów nie zniknął bez śladu |
| **Dokument, który jest samą pętlą, nie powstaje przy pustej liście** (`"wymaga"` w `.json` szablonu) | wykaz zmian danych budynku bez ani jednego wypełnionego wykazu wychodził jako plik **bez jednej litery**: szedł do konwersji i w składaniu operatu widać go było jako pusty kafelek, po którym nie wiadomo, czy to usterka, czy zapomniane dane. Warunek jest **wpisem w `.json`**, a nie regułą zgadującą po treści pliku — dokument bez `wymaga` zachowuje się dokładnie jak dotąd, a taki, który ma tylko logo i żadnego tekstu, nie zniknie przez pomyłkę. Pominięcie **nie jest ciche**: na stronie operatu staje zdanie, którego dokumentu zabrakło i dlaczego |
| **Ta sama sekcja w formularzu, dwa różne układy w dokumencie** — wykaz budynku `{%p for %}` (kolejne strony), wykaz działki `{%tr for %}` (kolejne wiersze jednej tabeli) | o formie w przeglądarce decyduje **typ pola**, a o dokumencie **znacznik w formatce** — i to są dwie niezależne decyzje. Oba pola są typu `sekcje` i dają ten sam kształt danych (lista słowników), więc jedna karta na budynek daje osobną stronę, a jedna karta na działkę — kolejny wiersz. Nie trzeba było do tego ani nowego typu pola, ani niczego w generatorze. L.p. w wykazie działki bierze się z `{{ loop.index }}`, więc nie ma po co pytać o nie w formularzu |
| **Powtarzalna sekcja pól (`typ: "sekcje"`) zamiast wiersza tabeli** — wykaz zmian danych budynku | w jednym operacie bywa kilka wykazów, a każdy to 15 atrybutów w dwóch stanach. Jako pole `tabela` miałby **30 kolumn** i nie dałoby się go wypełnić. Powtarzamy więc komplet pól: jedna karta w formularzu = jeden wykaz = jedna tabela w gotowym pliku. Dane wychodzą w tym samym kształcie co z tabeli (lista słowników), więc `{%p for %}` w Wordzie obsługuje jedno i drugie tak samo. Wykazy jadą **do jednego pliku**, kolejne od nowej strony — łamanie stoi w `{%p if not loop.last %}`, bo po ostatnim zostawiałoby w operacie pustą kartkę |
| **Spis treści jest jedynym włącznikiem dokumentu** (`"dokumenty"` w polu `wybor_wielokrotny`) | pozycja w spisie treści i checkbox „Wygeneruj” w karcie dokumentu pytały o to samo dwa razy i dało się je ustawić sprzecznie — dokument wymieniony w spisie, a pliku brak (albo odwrotnie). Teraz zaznaczenie pozycji **włącza pola tego dokumentu** (`aktywne_gdy: "spis_tresci:<pozycja>"`, obsługiwane przez istniejący mechanizm bez zmian w JS) **i** uruchamia jego wygenerowanie. Szablon wskazany w mapowaniu przestaje się pokazywać w karcie „Inne dokumenty”, żeby nie dało się go włączyć w dwóch miejscach. „Sprawozdanie techniczne” zniknęło z `zawsze` — na stałe zostaje sam spis treści |
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
| **Bez pliku czcionki skrypt odmawia pracy**, zamiast szacować z liczby znaków | oszacowanie wychodzi inne niż pomiar — zmierzone na obu wykazach: przystanek 3781 → 4371 twipów, czyli kolumna wartości przesunięta o ponad centymetr. Skrypt wypisywał przy tym zwykłe „kolumny: 4” i zapisywał plik, więc uruchomienie go na maszynie bez Calibri/Carlito po cichu przestawiało formatki, których nikt nie prosił o zmianę. Na Linuksie: `sudo apt install fonts-crosextra-carlito` |
| **Calibri**, nie Bahnschrift | Bahnschrift jest tylko na Windowsie i nie ma odpowiednika na Linuksie, więc podglądy PDF u autora łamały się inaczej niż dokumenty u brata. Calibri ma metrycznie zgodne Carlito (`fonts-crosextra-carlito`) — ten sam plik łamie się tak samo po obu stronach |
| **Bez numeracji stron**, jedna stopka na wszystkich stronach i we wszystkich dokumentach | operat i tak jest sklejany z kilkunastu plików w jeden PDF, więc numer strony pojedynczego dokumentu nic nie znaczy, a wprowadza w błąd. Uwaga: pole z numerem siedziało też w **nieużywanej** stopce stron parzystych i wróciłoby przy pierwszej zmianie ustawień — dlatego skrypt nadpisuje wszystkie trzy stopki |
| W wykazie zmian działki identyfikator kończy się **kropką i niczym więcej** — `[{{ polozenie_obreb_teryt }}.]` | to **nie jest błąd ani niedokończona edycja**, tylko pomysł brata: program wstawia obręb, a numer działki brat dopisuje sam w Wordzie, bo w jednym wykazie bywa ich kilka i nie zawsze wszystkie z formularza. `{{ nr_dzialki }}` celowo nie występuje w tym pliku — nie „poprawiaj” tego |
| **Liczniki pracy liczą zdarzenia w bazie, a nie pliki na dysku** (`app/statystyki.py`, tabela `zdarzenia`) | pierwsza wersja liczyła zawartość `wyniki/` i myliła się w obie strony: brat przenosi gotowe operaty na dysk archiwalny, więc licznik cofałby się do zera mimo setki zrobionych robót, a pliki, które sam dokłada do katalogu (mapy, skany, wypisy), wpadały jako „wygenerowane przez program”. Baza jest właściwym miejscem, bo `dane/` przeżywa aktualizacje, trafia do `dane/kopie/`, a `SET ile = ile + 1` jest niepodzielne — plik JSON gubiłby zliczenia przy dwóch kartach naraz |
| Statystyki jadą do **arkusza Google** (Apps Script), a nie do Google Analytics ani własnego serwera | do trzech liczb GA4 to armata na muchę: raporty opóźnione o dobę, a odczytanie „ile łącznie” upierdliwe. Arkusz **jest** panelem — autor otwiera go na telefonie i ma tabelę oraz wykres bez pisania frontendu. Endpoint to ~15 linii Apps Scriptu, hostingu zero |
| Wysyłamy **sumy od początku, nie przyrosty** (`app/raport.py`) | zgubiony pakiet nic nie kosztuje, bo następny niesie pełną prawdę — nie ma po co budować kolejki, ponawiania ani potwierdzeń. Przy przyrostach każde nieudane wysłanie gubiłoby dane bezpowrotnie. Raz na uruchomienie, w wątku, z krótkim limitem czasu; wyłącznik `GENERATOR_BEZ_STATYSTYK=1` gasi to bez wydawania nowej wersji |
| Adres i token wysyłki są **jawne w repozytorium** | repo jest publiczne, więc i tak by wyciekły — token jest sitem na przypadkowe boty, a nie zabezpieczeniem. Chroni to, że **sam arkusz zostaje prywatny**. Przy dwóch instalacjach śmieciowy wiersz kasuje się ręcznie |
| Etykieta instalacji: plik → **nazwa komputera** → dopisek „kopia robocza” | bez nazwy komputera wszystkie nieopisane instalacje wyglądają w arkuszu tak samo i trzeba je rozróżniać po losowym identyfikatorze. Nazwa idzie w polu `etykieta`, więc arkusz ani skrypt nie wymagają zmian. `platform.node()`, a **nie** `socket.getfqdn()` — ten drugi odpytuje DNS i przy kiepskiej sieci potrafi zawisnąć. Kopia robocza gita dokłada sobie dopisek, więc maszyna deweloperska nadal oznacza się sama. Uwaga: nazwa komputera zwykle zawiera imię właściciela (`Kuba-PC`), czyli **jest daną osobową** — dlatego mówi o niej wprost pomoc i opis wydania, a `dane/etykieta.txt` pozwala ją nadpisać |
| Historia liczników odtwarzana **raz** przy pierwszym starcie nowej wersji (`zasiej_z_historii`) | brat ma już kilkadziesiąt operatów; licznik od zera wyglądałby na zepsuty. Operaty odtwarzamy z tabeli `dokumenty` (pamięta też te zarchiwizowane), dokumenty i PDF-y z katalogów jeszcze obecnych w `wyniki/` — i **tylko pliki o nazwach nadawanych przez program**, żeby jego własne nie wpadły nawet ten jeden raz |
| **Własne formatki użytkownika leżą w `dane/szablony/<kategoria>/`, nigdy w `szablony/`** (`app/warianty.py`) | `szablony/` jest lustrzane — plik, którego nie ma w repozytorium, znika u brata przy najbliższej aktualizacji. Jego własna formatka wyparowałaby bez śladu, a on dowiedziałby się o tym dopiero po operacie zrobionym ze standardowego wzoru. `dane/` jest nietykalne i wchodzi do kopii zapasowej. **Kategoria** (rodzaj dokumentu) decyduje, jakie pola ma formularz, **wariant** podmienia tylko wypełniany plik — dzięki temu wybór może stać na dole formularza i niczego nie przeładowuje. Wariant z nieznanym znacznikiem dostaje ostrzeżenie przy wgrywaniu, nie blokadę: formatka różniąca się jednym polem to najczęstszy przypadek, a nie błąd |
| **Dane stałe usunięte z programu** — nazwisko, uprawnienia, pieczątka firmy | brat woli mieć je wpisane na sztywno w swoim szablonie Worda; to i tak nie zmienia się między robotami, a jeden ekran mniej to jeden ekran mniej do tłumaczenia. `db.wczytaj_ustawienia` i `zrodlo: "ustawienia"` zostają w kodzie, ale bez interfejsu |

## Zasada centralna

**Źródłem prawdy jest plik `.docx` w `szablony/`.** Aplikacja czyta z niego tagi Jinja
i **z nich buduje formularz**. Dopisanie `{{ nowe_pole }}` w Wordzie = nowe pole na stronie,
bez zmian w kodzie. Opcjonalny plik `.json` obok szablonu dokłada tylko etykiety, typy,
kolejność i grupy pól.

Jeśli masz pomysł, który wymaga wpisania listy pól konkretnego operatu do kodu Pythona —
to znak, że idziesz pod prąd tej architektury.

## Zasady pracy nad kodem (obowiązują od 01.08.2026)

1. **Żadna zmiana kodu nie idzie do commitu bez zielonego `pytest`.** Nie „uruchomię
   później”, nie „to drobiazg”. U brata aktualizacja instaluje się sama przy starcie,
   więc wypchnięty błąd jest u niego, zanim się o nim dowiesz.
2. **Nowa funkcja = nowy test, w tym samym commicie.** Nie w następnym, nie „jak
   będzie czas”. Test ma sprawdzać zachowanie, na którym zależy użytkownikowi,
   a nie to, że funkcja się wywołuje.
3. **Naprawiony błąd = test, który go łapie.** Najpierw czerwony, potem poprawka.
   Inaczej nie masz dowodu, że naprawiłeś to, co się psuło.
4. **Testu nie „naprawia się” przez rozluźnienie asercji.** Gdy test czerwienieje po
   zmianie, domyślnie to zmiana jest zła, a nie test. Jeśli jednak test opisywał złe
   oczekiwanie — zmień go świadomie i napisz w commicie dlaczego.
5. **Formatek w `szablony/` nie ruszasz bez wyraźnej prośby.** To dopracowane dokumenty
   brata; sprawdzaj `git diff -- szablony/` przed commitem — ma być puste. Skryptów
   `ujednolic_wyglad.py` i `popraw_szablon.py` nie uruchamiasz „przy okazji”.
6. **Zerknij na CI przed podbiciem `WERSJA`.** Zielony krzyżyk po wydaniu to już tylko
   raport ze szkody.

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
| `ZMIANY.md` | historia wydań pokazywana na `/pomoc/historia`; **generowana**, nie pisana ręcznie |
| `app/zmiany.py` | czyta `ZMIANY.md` (parser na trzech liniach, format do poprawienia w Notatniku) |
| `narzedzia/wydaj.py` | stempluje wydanie: numer z daty i kolejności, `WERSJA` + `ZMIANY.md` |
| `narzedzia/zbuduj_zmiany.py` | buduje `ZMIANY.md` z historii pliku `WERSJA` w gicie |
| `app/db.py` | SQLite: `dokumenty`, `liczniki`, `zdarzenia`, `teryt_*`, `opisy_sprawozdania` (`ustawienia` bez interfejsu) |
| `app/statystyki.py` | liczniki do stopki: operaty, dokumenty, złożone PDF-y; zliczane w chwili zdarzenia |
| `app/raport.py` | wysyłka tych trzech liczb do arkusza autora; **tylko biblioteka standardowa**, wszystko połykane po cichu |
| `app/teryt.py` | jednostki TERYT z GUS + obręby z ULDK; **tylko biblioteka standardowa** |
| `app/operaty.py` | katalog operatu: zakładanie, `operat.json` (w tym zapamiętany `uklad`), lista plików do sklejenia; nazwa pliku wynika z nazwy szablonu (`spis_tresci_wzor` → `spis_tresci.docx`) |
| `app/warianty.py` | własne formatki użytkownika: wgrywanie, lista, wybór zapamiętany w ustawieniach i przy operacie |
| `app/tekst.py` | pogrubienie/kursywa/podkreślenie: sanitizacja fragmentu HTML i zamiana na `RichText` |
| `app/opisy.py` | opisy sprawozdania dostarczane z programem (`szablony/opisy_sprawozdania.json`); zasiewane **raz na pozycję** |
| `app/miniatury.py` | podgląd pierwszej strony PDF-a (pypdfium2 + Pillow) |
| `app/main.py` | trasy FastAPI, parsowanie formularza (w tym tabel) |
| `app/web/templates/` | widoki; `blad.html` to strona każdego niezłapanego wyjątku, a `pomoc.html` instrukcja dla brata — aktualizuj ją razem z funkcjami |
| `narzedzia/utworz_wzor_szablonu.py` | generuje przykładowy szablon spisu treści do testów; nie nadpisze istniejącego bez `--nadpisz` |
| `narzedzia/utworz_wzor_sprawozdania.py` | szkielet sprawozdania technicznego; też nie nadpisuje istniejącego bez `--nadpisz` |
| `narzedzia/utworz_wzory_wykazow.py` | szkielety obu wykazów zmian danych ewidencyjnych |
| `narzedzia/ujednolic_wyglad.py` | **puść po każdej podmianie formatki**, przed `popraw_szablon.py` — jeden krój, jedno logo, jedna hierarchia we wszystkich dokumentach operatu; nie rusza treści ani czerwieni numeru roboty |
| `narzedzia/popraw_szablon.py` | **puść po każdej podmianie formatki od brata** — nakłada tabulator i wcięcie wiszące w spisie treści oraz przypina podpis do dołu strony |
| `narzedzia/utworz_ikone.py` | robi `app/web/static/logo.ico` z tej samej geometrii co `logo.svg`; Pillow nie czyta SVG, więc kształt jest opisany dwa razy i pilnuje tego test |
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
6. **COM trzeba zainicjować w każdym wątku.** Konwersja jedzie z trzech miejsc i żadne
   nie jest głównym wątkiem: trasa `/miniatura/...` (zapisana jako `def`, więc FastAPI
   puszcza ją w puli wątków), przygotowanie podglądów w tle (`threading.Thread`
   w `/generuj`) i `POST /scal/{nazwa}`. Bez `pythoncom.CoInitialize()` leci
   `CoInitialize has not been called` — stąd `_com()` w `app/pdf.py`.
7a. **Wydanie stempluje `narzedzia/wydaj.py "opis dla brata"` — nie rób tego ręcznie.**
   Skrypt ustala numer (`rok.miesiąc.dzień-kolejny`, np. `2026.08.06-82`: data z zegara,
   numer po kolei z historii `WERSJA` w gicie), zapisuje `WERSJA` i od razu przebudowuje
   `ZMIANY.md`. Powstał dlatego, że **oba człony wpisywane z ręki już się pomyliły**:
   raz weszła data z poprzedniej sesji (numery doszły do `2026.07.31.40`, choć wydania
   szły już 1 sierpnia), raz numer zajęty przez wydanie zrobione tego dnia na drugim
   komputerze — trzeba było poprawiać po fakcie. Historia wydań musi jechać do brata
   jako plik, bo on nie ma gita; pilnuje tego `test_wydana_wersja_ma_wpis_w_historii`:
   podbita wersja bez wpisu = czerwony test, zanim brat zobaczy „co nowego” i pustą stronę.
7c. **Format numeru wolno zmienić, bo porównanie jest na równość** (`numer == lokalna`),
   nigdy „na większy”. Dlatego przejście z `2026.08.06.3` na `2026.08.06-82` zadziałało
   u brata jak każda inna nowa wersja. Gdyby ktoś kiedyś przerobił to na porównanie
   porządkowe, **aktualizacje stanęłyby po cichu**: `2026.08.06-82` jest w porządku
   znakowym *mniejsze* niż `2026.08.06.3` (dywiz przed kropką), więc program uznałby,
   że ma nowszą wersję. Trzyma to `test_zmiana_formatu_numeru_wyzwala_aktualizacje` —
   sprawdzone, że przy `<=` zamiast `==` świeci na czerwono.
7. **Wydanie = podbicie `WERSJA` + push.** Sam commit nic bratu nie wyśle — porównywany
   jest wyłącznie pierwszy wiersz pliku `WERSJA`. To celowe: decydujesz, kiedy dostaje
   nową wersję. Odwrotna pułapka: podbicie `WERSJA` bez wypchnięcia reszty kodu wyśle
   mu paczkę z gałęzi `main` w stanie, w jakim akurat jest. Numer czytamy z API GitHuba,
   bo `raw.githubusercontent` podawał go z cache jeszcze 3,5 minuty po pushu — paczka
   `.zip` miała już wtedy nowy kod, więc program ogłaszał „wersja aktualna”, mając
   nieaktualną. `raw` został jako zapas na wyczerpany limit API.
7b. **Aktualizację wykonuje kod, który użytkownik ma u siebie — czyli stary.** Jego lista
   `AKTUALIZOWANE` nie zna plików dołożonych w nowym wydaniu, więc **nowy plik nie
   dojeżdża przy tej aktualizacji, która go wprowadza**, tylko przy następnej. Kosztowało
   to `ZMIANY.md`: brat dostał wersję `2026.08.02.8` z gotowym menu „Historia wersji”
   i komunikatem, że pliku z historią nie ma. Test sprawdzający „czy nazwa jest na
   liście” tego nie łapie — patrzy na **nowy** kod, a winny jest stary. Stąd
   `_lista_z_paczki`: listę czytamy z pobranego archiwum (`ast`, bez uruchamiania kodu
   z sieci), a nie z siebie. Kopię zapasową robimy nadal z własnej listy, bo
   zabezpieczamy to, co leży tutaj. Pilnuje tego
   `test_nowy_plik_dojezdza_juz_przy_tej_aktualizacji`.
   **Ta sama pułapka wraca przy każdej zmianie wpiętej w samą aktualizację.** Drugi raz
   kosztowała sprzątanie `dane/kopie/`: kod trafił do brata, ale ponieważ wołało go
   `_kopia_zapasowa`, u niego dalej leżało 40 kopii. Wniosek ogólny: **wszystko, co ma
   działać u użytkownika od razu, wieszaj na starcie programu, a nie na aktualizacji.**
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
19. **`with sqlite3.connect(...)` nie zamyka pliku** — zatwierdza transakcję i tyle.
   Na Linuksie otwarty uchwyt nie przeszkadza nawet skasować bazy, więc wyciek połączeń
   przeżył cały rozwój niezauważony; na Windowsie, czyli u brata, każda próba ruszenia
   pliku to `PermissionError`. Stąd `db.polaczenie()` — context manager, który commituje
   **i** zamyka. Pilnuje tego `test_polaczenie_zamyka_plik_bazy`, bo przy samej różnicy
   platform CI tego nie złapie. Wyszło dopiero, gdy testy bazy puszczono na Windowsie.
20. **Windows nie pozwala procesowi w tle wyciągnąć okna na pierwszy plan.** „Otwórz
   katalog” woła `os.startfile`, ale aktywna jest przeglądarka, nie uvicorn — Eksplorator
   otwierał się *za* oknem przeglądarki i tylko migał na pasku zadań, czyli dla brata
   „przycisk nic nie zrobił”. Mylące przy diagnozie: ten sam `os.startfile` uruchomiony
   ze świeżo odpalonego skryptu **wychodzi** na wierzch (proces startujący ma jeszcze
   prawo do planu), więc problem znika, gdy się go testuje poza serwerem. Sprawdzaj to
   przez trasę HTTP. Obejście w `operaty._na_pierwszy_plan`: znaleźć okno klasy
   `CabinetWClass` z nazwą katalogu w tytule, podpiąć się `AttachThreadInput` pod wątek
   okna aktywnego i dopiero wtedy `SetForegroundWindow`. Chodzi w osobnym wątku (okno
   pojawia się z opóźnieniem) i **musi być niemy** — wyjątek w wątku wysypałby bratu
   angielski ślad stosu do konsoli. Skutek uboczny, o którym trzeba pamiętać: skoro
   o wysunięcie prosi nasz proces, Windows wciąga do kolejki aktywacji **jego konsolę**
   i po zamknięciu katalogu na wierzch potrafi wyjść czarne okno serwera zamiast
   przeglądarki. Dlatego zaraz po wysunięciu odsuwamy własną konsolę na spód
   (`_konsole_na_spod`, `SWP_NOACTIVATE`). Uwaga przy diagnozie: objaw zależy od
   kolejności okien i od tego, że użytkownik zamyka katalog **myszą** — programowe
   `WM_CLOSE` w teście wraca do przeglądarki i niczego nie pokaże. Rozstrzygnął to brat:
   **przy zminimalizowanej konsoli problem znika**, bo okno w stanie zminimalizowanym
   nie uczestniczy w kolejce aktywacji. Dlatego `uruchom.py` chowa konsolę sam, po starcie.
21. **„Czy serwer wstał” nie znaczy „port jest zajęty”.** Konsolę wolno schować dopiero
   po udanym starcie — przy nieudanym to okno z komunikatem jest jedynym, co brat ma
   przed oczami. Pierwsza wersja sprawdzała `connect` na port i dała fałszywe „działa”,
   bo portu pilnowała **zapomniana druga kopia programu**; konsola schowała się mimo
   że serwer się nie podniósł. Teraz `uruchom.serwer_odpowiada` pobiera stronę i szuka
   w niej znacznika `Generator operatów`. Pilnuje tego `test_uruchom.py`.
22. **Test, który liczy pliki, liczy też to, co zostawiła po sobie fixture.**
   `test_migracja_zostawia_kopie_bazy` padał raz na kilkanaście przebiegów, i to nie
   na „zero kopii”, jak sugerował komunikat, tylko na **dwie** — `assert len(kopie) == 1`
   pokazuje własny opis w obie strony. Druga kopia była z `db.init()` w fixture
   `srodowisko`: `SCHEMAT` to schemat 1, kolumny `katalog` i `nr_operatu` dokładają
   migracje, więc **świeżo założona baza też przechodziła migrację** i też dostawała
   kopię. Zwykle obie kopie powstawały w tej samej sekundzie, a nazwa ma rozdzielczość
   sekundy — druga nadpisywała pierwszą i wychodziło „jedna”. Gdy trafiły w różne
   sekundy, test padał. Poprawka jest w `db.init()` (świeżej bazy nie ma po co
   kopiować — nie ma w niej czego ratować), a nie w asercji. Wniosek na przyszłość:
   **przy losowym padnięciu sprawdź, czy nie ma wyścigu z zegarem** — nazwa z datą
   co do sekundy zachowuje się inaczej w zależności od tego, kiedy zaczął się test.
   Odtworzenie: pętla po samym teście, ok. 3 padnięcia na 40 przebiegów.
23. **Wątki demoniczne z testu przeżywają test.** `cykl_zycia` startuje pobieranie
   TERYT-u, `/generuj` — przygotowanie podglądów; oba czytają `db.BAZA_DANYCH`
   i `operaty.WYNIKI` **w chwili wywołania**, więc taki wątek po sprzątnięciu
   monkeypatcha pisze do prawdziwych `dane/` i `wyniki/` autora, i to po cichu, bo oba
   łykają każdy wyjątek. Fixture `srodowisko` czeka teraz na nie w swoim sprzątaniu
   (`_zaczekaj_na_watki`), póki podmienione ścieżki jeszcze stoją. Czeka w `srodowisko`,
   a nie w `klient`, bo własny TestClient stawia też `test_word.py`.
24. **Znacznik bez domknięcia nie może odkładać ramki na stosie stylów.** W `app/tekst.py`
   `<br>` trafiał na stos razem ze zwykłymi znacznikami, a że nie ma `</br>`, kolejne
   `</p>` zdejmowało ramkę po nim zamiast po akapicie — styl akapitu zostawał włączony
   **do końca tekstu**. Objaw: wklejka z Worda `<p style="font-weight:700">pierwsza<br>
   druga</p><p>zwykła</p>` wychodziła pogrubiona w całości, a w edytorze wystarczyło
   pogrubić coś, nacisnąć Enter i pisać dalej. Dotyczy każdego pustego znacznika
   (`br`, `img`, `hr`), stąd lista `PUSTE`. Uwaga przy diagnozie: **przypadek bez
   złamania wiersza działa poprawnie**, więc łatwo uznać, że parser jest w porządku.

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
PDF (ok. 1,5 s na dokument) → złożenie operatu przez `POST /scal/{katalog}`. Po konwersji nie zostaje proces
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

Sprawdzanie numeru działki działa na żywym ULDK (02.08.2026): `120101_1.0006.6002` →
„✓ Jest taka działka w ewidencji”, numer zmyślony → pomarańczowe „ewidencja nie zna”,
kilka numerów w jednym polu (`6002, 999999`) → wskazany ten zły. Formularz przez cały
czas da się wysłać. Uwaga przy diagnozie: **`GetParcelById` dokłada do „-1 brak wyników”
własny komunikat o „błędnym formacie odpowiedzi XML”** — to bałagan po stronie GUGiK-u,
a nie objaw naszego błędu; patrzymy wyłącznie na kod w pierwszej linii. Przykład
z ich dokumentacji (`141201_1.0001.1/2`) też zwraca „brak wyników”, więc nie nadaje się
na test poprawności formatu — do sprawdzenia bierz identyfikator z `GetParcelByXY`.

Numer operatu jest **rezerwowany przed wypełnieniem szablonu** (musi wejść do treści
dokumentu), a po nieudanym generowaniu oddawany przez `db.zwolnij_numer` — warunkowym
`UPDATE ... WHERE stan = ?`, żeby nie cofnąć licznika, który w międzyczasie ruszył dalej.
Sprawdzone: trzy nieudane próby między dwoma dobrymi dokumentami dają `001` i `002`,
bez dziury.

## Testy

```bash
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/pytest
```

Chodzą w kilkanaście sekund, bez sieci i bez Worda (konwersja jest podmieniana na atrapę;
jeden test oznaczony markerem `konwerter` używa prawdziwego LibreOffice'a, gdy jest).
Żaden test nie dotyka prawdziwych `wyniki/` i `dane/` — `tests/conftest.py` podmienia
ścieżki **w każdym module z osobna**, bo `from .config import WYNIKI` przywiązuje je
do modułu w chwili importu.

Co pilnują, w kolejności od najbardziej bolesnych doświadczeń:

| Plik | Czego pilnuje |
| --- | --- |
| `test_ujednolic_wyglad.py` | że skrypt **nie cofa decyzji brata** (pogrubienia w treści i w etykietach, rozmiar nagłówka, ciąg tabulatorów), jest idempotentny, a wydane formatki przechodzą kontrolę kolejności OOXML — czyli otworzą się w Wordzie |
| `test_szablony.py` | że każda formatka daje się wczytać, nic nie wpada do „Pozostałych pól”, a **dokumenty dodatkowe nie używają znaczników, których formularz nie zbiera** (to najcichszy sposób zepsucia operatu: puste miejsce zamiast błędu) |
| `test_generator.py` | numeracja bez dziur, poprawianie nieznużywające numeru, formaty dat, brak `{{ }}` w gotowym pliku |
| `test_aktualizacja.py` | że `dane/` i `wyniki/` przeżywają, szablony są lustrzane, a nieudana aktualizacja zostawia działający program (GitHub podstawiony przez `file://`) |
| `test_db.py` | migracje starej bazy bez utraty historii i licznika; że kopia powstaje **przed** migracją i tylko wtedy, a nie przy zakładaniu bazy od zera; że połączenie **zamyka plik** (inaczej Windows blokuje bazę) |
| `test_word.py` | ścieżka przez Worda (COM) — tylko Windows z Office, nigdy w CI; opis niżej |
| `test_trasy.py` | formularz → operat przez HTTP, polskie strony błędów, brak wyjścia poza `wyniki/` |
| `test_operaty.py`, `test_pdf.py` | nazwy katalogów i plików, kolejność sklejania, komunikat przy uszkodzonym PDF |
| `test_statystyki.py` | że licznik **nie cofa się po archiwizacji** operatu i **nie rośnie** od plików dołożonych przez brata — na tym wyłożyła się pierwsza wersja |
| `test_uruchom.py` | że konsola chowa się **tylko po udanym starcie** i że obcy serwer na porcie nie uchodzi za nasz program |
| `test_zmiany.py` | że `ZMIANY.md` **jedzie do brata przy aktualizacji** i że wydana wersja ma swój wpis w historii |
| `test_warianty.py` | że własna formatka **przeżywa aktualizację** i że poprawianie operatu bierze tę formatkę, którą naprawdę powstał, a nie dzisiejszą domyślną |
| `test_uldk.py` | że milczenie ULDK **nie wygląda jak zły numer** — najważniejszy test w tym pliku |
| `test_teryt.py` | że zmiana strony GUS-u **nie czyści bazy** (przychodzi HTML zamiast ZIP-a), że gmina miejsko-wiejska nie wchodzi do listy, że obręby lecą z bazy zamiast z sieci i że przerwane pobieranie hurtowe **nie dobija paska do końca** |
| `test_opisy_wzorcowe.py` | że opis dostarczony z programem pojawia się sam po aktualizacji, ale **skasowany przez brata nie wraca** i nie nadpisuje jego własnej kopii |
| `test_sekcje.py` | że kilka wykazów w jednym operacie daje kilka tabel, każdą z własnymi danymi i nagłówkiem, a łamanie strony stoi **między** nimi, nie po ostatnim |
| `test_tekst.py` | że do dokumentu wchodzi **tylko** pogrubienie, kursywa i podkreślenie, a `{{r }}` w formatce jest konieczne — przy zwykłym `{{ }}` powstaje plik, którego Word nie otworzy; pilnuje też, żeby styl akapitu **nie rozlewał się** za złamanie wiersza (patrz pułapka 24) |
| `test_miniatury.py` | że pdfium nie jest wołany dwoma wątkami naraz (objawem jest zgaszony program, nie wyjątek) i że plik niebędący PDF-em nie wywraca strony składania |

Testy stabilności formatek **pomijają się bez czcionki Calibri/Carlito**
(`sudo apt install fonts-crosextra-carlito`), bo bez niej `ujednolic_wyglad.py` w ogóle
odmawia pracy. W CI czcionka jest instalowana, więc tam ten strażnik zawsze działa.

Testy chodzą w GitHub Actions przy każdym pushu na `main` — [.github/workflows/testy.yml](.github/workflows/testy.yml).
**Zerknij na wynik, zanim podbijesz `WERSJA`**: u brata aktualizacja instaluje się sama
przy starcie, więc czerwony test po wydaniu jest już tylko raportem ze szkody.

### Testy ścieżki wordowej — `tests/test_word.py`

Napisane i przechodzące na Windows 11 + Office 16.0 (Python 3.14, 01.08.2026).
**Nie da się ich sprawdzić na Linuksie ani w CI** — na runnerze nie ma Worda, więc
`.github/workflows/testy.yml` pomija je przez `-m "not konwerter and not word"`.
Uruchamiasz je ręcznie przed każdym wydaniem dotykającym `app/pdf.py`:

```bat
.venv\Scripts\pip install -r requirements-dev.txt
.venv\Scripts\pytest -m word -v
```

Przed pierwszym uruchomieniem **otwórz Worda ręcznie i zamknij** — świeża instalacja Office
potrafi pokazać okno aktywacji albo pytanie o domyślny format, a wtedy konwersja wisi,
zamiast paść. To samo dotyczy komputera brata.

| Test | Czego pilnuje |
| --- | --- |
| `test_konwersja_pojedyncza` | PDF ma treść dokumentu i **nie zostaje plik `*.czesciowy`** |
| `test_nie_zostaje_wiszacy_word` | liczba procesów `WINWORD.EXE` nie rośnie — bez `Quit()` w `finally` mnożą się w tle |
| `test_konwersja_z_watku_roboczego` | konwersja z puli wątków; to jest **powód, dla którego nie ma docx2pdf** |
| `test_dwie_konwersje_naraz` | `_BLOKADA_KONWERSJI`; żaden PDF nie jest urwany |
| `test_wsad_uruchamia_worda_tylko_raz` | że Word startuje **raz** na komplet dokumentów. Liczymy uruchomienia (`DispatchEx`), nie czas: pierwsza wersja porównywała czasy i raz na jakiś czas czerwieniała bez regresji — przy rozgrzanym Wordzie i obciążonej maszynie wyszło 13,95 s wobec 16,97 s, tuż przy progu. Zysk jest realny (zmierzone przy czterech dokumentach: **26,5 s → 4,2 s**, na LibreOfficie 3,55 s → 1,17 s), ale zegar zależy od tego, co akurat robi komputer, a liczba startów wyłącznie od naszego kodu. Sprawdzone, że licznik ma zęby: wsadem 1 start, po kolei 4 |
| `test_zakladki_z_naglowkow` | `CreateBookmarks` — brak zauważy dopiero ktoś otwierający operat w czytniku |
| `test_awaria_worda_*` | zejście na LibreOffice, a bez niego polski komunikat o oknie dialogowym |
| `test_trasa_scal_prawdziwym_wordem` | cała ścieżka przez HTTP: operat → `POST /scal` → PDF o nazwie numeru roboty |

Dwie rzeczy, które wyglądają na awarię, a nią nie są:

1. **`Windows fatal exception: code 0x800706be`** wypisywane przy każdej konwersji.
   To `RPC_S_CALL_FAILED` — pierwszorzutowy wyjątek SEH przy zwalnianiu wskaźnika COM
   po `Quit()`, czyli po zniknięciu procesu Worda (`app/pdf.py`, `word = None`).
   Przechwytuje go pywin32, PDF powstaje, proces kończy się zerem. Widać go tylko
   dlatego, że pytest włącza `faulthandler`; aplikacja go nie włącza, więc brat tego
   nie zobaczy. **Nie wyciszaj tego** — prawdziwa awaria to niezerowy kod wyjścia
   albo czerwona asercja, a `faulthandler` jest tu wart więcej niż cisza.
2. Testu nie puszczaj równolegle (`-n auto`) — Word to jedna aplikacja na komputerze,
   równoległość testowałaby wtedy samą siebie, a nie kod.

Gdy test padnie w połowie, **zajrzyj do Menedżera zadań** i ubij zostawionego
`WINWORD.EXE`, zanim uruchomisz kolejny — inaczej następne testy kłamią.
Diagnostyka: `narzedzia\diagnostyka.bat` ustawia `GENERATOR_DIAGNOSTYKA=1`, wtedy
`pdf.slad()` wypisuje każdy krok konwersji.

Czego test nie zastąpi, a trzeba zrobić okiem: **obejrzeć złożony PDF** po konwersji Wordem
i porównać z tym z LibreOffice'a. Wszystkie usterki formatek z lipca (podpis zjeżdżający
w lewo, dokument puchnący na drugą stronę, stopka kończąca się w dwóch trzecich szerokości)
widać było dopiero na obrazku, a nie w liczbach.

## Co dalej — kolejka

1. **Dokładanie kolejnej formatki** (przepis, bo to się będzie powtarzać): wrzuć `.docx`
   do `szablony/` pod nazwą `<coś>_wzor.docx`, sprawdź, czy brat wstawił tagi `{{ }}`,
   i puść `ujednolic_wyglad.py`, a potem `popraw_szablon.py`. Checkbox w formularzu
   pojawi się sam. Obowiązkowo **obejrzyj złożony PDF**, a nie same liczby — wszystkie
   usterki tej serii (podpis zjeżdżający w lewo, dokument puchnący na drugą stronę,
   stopka kończąca się w dwóch trzecich szerokości) widać było dopiero na obrazku.
   Orientacja pozioma nie wymaga niczego dodatkowego: szerokości liczą się z rozmiaru
   strony danego pliku. `utworz_wzory_wykazow.py` zostaje jako generator szkieletu.
2. ~~Wczytywanie wykazu współrzędnych z pliku~~ — **odpada** (ustalone z bratem 02.08.2026).
   Wykaz robi w C-Geo, generuje z niego PDF i dokłada go do operatu jak każdy inny
   załącznik. Program nie ma po co znać formatu C-Geo, a pole tabelaryczne w formularzu
   zostaje dla przypadków, w których wpisuje kilka punktów z ręki.
2a. ~~Sprawdzanie numeru działki przez ULDK~~ — **zrobione** 02.08.2026, opis niżej.
3. ~~Paczka `.exe` dla Windowsa~~ — **odpuszczone** (decyzja z 02.08.2026). Instalacja
   przez `start.bat` działa i sama się aktualizuje, więc pakowanie w `.exe` rozwiązywałoby
   problem, którego nie ma, a dokładało ostrzeżenia SmartScreen i osobną ścieżkę budowania.
   **Python zostaje wymaganiem wstępnym.** Obsługa `sys.frozen` w `app/config.py` zostaje —
   nie przeszkadza, a gdyby temat wrócił, to gotowy punkt zaczepienia (pamiętaj wtedy
   o `--hidden-import win32com.client` i `--hidden-import pythoncom`, bez nich konwersja
   PDF w `.exe` nie ruszy).
4. Kolejne typy dokumentów (protokół, szkic, sprawozdanie) — każdy to nowy plik w `szablony/`.
5. Pokrycie testami tego, czego dziś nie ruszają. ~~Sieć do GUS-u i ULDK~~ oraz
   ~~renderowanie miniatur~~ — **zrobione** 10.08.2026 (`test_teryt.py`,
   `test_miniatury.py`; odpowiedzi GUS-u i ULDK podstawiane, pdfium sprawdzany atrapą
   dokumentu). Zostaje: Word przez COM (ma testy, ale chodzą tylko na Windowsie
   — patrz `test_word.py`) i układanie kolejności myszą w przeglądarce, bo to jedyna
   rzecz w programie, której nie da się dotknąć inaczej niż przeglądarką.

## Pytania otwarte do brata

- Które dokumenty poza operatem technicznym są mu potrzebne?
- Czy numeracja operatów ma być ciągła w roku, czy per rodzaj roboty?

Odpowiedziane:

- ~~Skąd bierze wykaz współrzędnych?~~ — z C-Geo, ale **jako gotowy PDF**, który dokłada
  do operatu jak każdy załącznik (02.08.2026). Parsera formatów geodezyjnych nie robimy.
- ~~Ma Microsoft Worda?~~ — tak, Office 16.0; ścieżka przez COM jest sprawdzona.

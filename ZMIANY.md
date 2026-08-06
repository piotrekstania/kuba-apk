# Historia zmian

Co doszło w kolejnych wersjach programu. Ten sam opis pokazuje się raz, na stronie
głównej, zaraz po tym jak program sam się zaktualizuje.

## 2026.08.06-83 — 2026-08-06

Na stronie operatu widać teraz jego numer — w nagłówku („Operat 001/2026”) i w tabelce z danymi, gdzie wcześniej zostawała pusta krata. Numer nadaje program przy generowaniu, więc w danych z formularza go nie ma; program bierze go z historii. To była tylko kwestia wyświetlania — w dokumencie Worda, w nazwie katalogu i w historii numer był poprawny od zawsze.

## 2026.08.06-82 — 2026-08-06

Zmiana sposobu numerowania wersji: zamiast licznika wydań w danym dniu jest teraz numer po kolei od pierwszego wydania — „2026.08.06-82” to 82. wydanie programu. W historii wersji (Pomoc → Historia wersji) doszła kolumna z tym numerem, więc widać, które wydanie było które, także dla starszych. Dla Ciebie nic się nie zmienia: program dalej sam sprawdza i pobiera nowe wersje.

## 2026.08.06.3 — 2026-08-06

Naprawione: poprawianie operatu przeniesionego wcześniej do archiwum zakładało nowy katalog o kolejnym numerze — poprawiasz 055, a robi się 060. Teraz wraca do tego samego numeru i odtwarza katalog pod starą nazwą, a licznik nie przeskakuje. Uwaga: numery, które już przeskoczyły, zostają jak są.

## 2026.08.06.2 — 2026-08-06

Operat przeniesiony do archiwum jest teraz na liście oznaczony jako „w archiwum” i nie ma przy nim przycisku „Złóż PDF” — wcześniej przycisk był, ale po kliknięciu nic się nie działo. Zniknęły też podglądy PDF po operatach, których nie ma już w katalogu wyniki; wcześniej zostawały tam na zawsze po każdej archiwizacji.

## 2026.08.06.1 — 2026-08-06

Poprawka do poprzedniej wersji: sprzątanie starych kopii w katalogu dane\kopie faktycznie się teraz odbywa. Poprzednio kod trafiał do Ciebie, ale uruchamiał się dopiero przy kolejnej aktualizacji, więc katalog dalej rósł. Teraz porządki robią się przy każdym uruchomieniu programu — nadmiarowe kopie znikną same przy tym starcie.

## 2026.08.05.6 — 2026-08-05

Porządki na dysku: w katalogu dane\kopie zostaje teraz pięć ostatnich kopii bezpieczeństwa, a starsze kasują się same. Wcześniej przybywała jedna przy każdej aktualizacji i nic ich nie usuwało — po kilkudziesięciu wersjach uzbierałyby się setki megabajtów. Kopie robią się nadal tak samo, przed każdą aktualizacją i przed każdą zmianą układu bazy.

## 2026.08.05.5 — 2026-08-05

Program dostał ikonę także poza przeglądarką: przy pierwszym uruchomieniu obok „start.bat” powstaje skrót „Generator operatow” ze znakiem programu. Przeciągnij go na pulpit albo przypnij do paska zadań — uruchamiany z niego program pokazuje swój znak zamiast czarnej ikonki wiersza poleceń.

## 2026.08.05.4 — 2026-08-05

Program ma swój znak: trójkąt z kropką, czyli symbol punktu geodezyjnego. Widać go w lewym górnym rogu obok nazwy i na karcie przeglądarki — łatwiej trafić w okno programu, gdy masz otwarte kilkanaście zakładek.

## 2026.08.05.3 — 2026-08-05

Ustawienia podzielone na karty tematyczne, tak jak formularz operatu: „Własne formatki” i „TERYT”, a w tej drugiej jednostki ewidencyjne i pobieranie obrębów dla całej Polski. Nic nie zmieniło się w działaniu — chodzi tylko o to, żeby dało się to objąć wzrokiem.

## 2026.08.05.2 — 2026-08-05

Formatka spisu treści nazywa się teraz „Spis treści”, a nie „Operat” — na listach w Ustawieniach i w tabelce na dole formularza. Kafelek na stronie głównej zostaje „Operatem”, bo tam zaczyna się cała robota.

## 2026.08.05.1 — 2026-08-05

Nowość: własne formatki. W Ustawieniach możesz wgrać swoje pliki Worda — do każdego rodzaju dokumentu choćby kilka — a przy tworzeniu operatu, na samym dole formularza, wybrać z tabelki, z której skorzystać. Wybór zapamiętuje się do następnego razu, a przy poprawianiu operatu program bierze tę formatkę, którą on naprawdę powstał. Własne formatki leżą w katalogu „dane” i przeżywają aktualizacje.

## 2026.08.03.4 — 2026-08-03

Uzupełnienie poprzedniej wersji: razem z trzema liczbami program wysyła teraz także nazwę tego komputera — po niej brat odróżnia Twoje uruchomienia od swoich testowych. Jeśli wolisz, żeby wysyłał co innego, wpisz dowolny tekst do pliku dane\etykieta.txt. Z Twoich operatów nadal nie wychodzi nic.

## 2026.08.03.3 — 2026-08-03

Program wysyła teraz bratu trzy liczby ze stopki — ile operatów, dokumentów Worda i złożonych PDF-ów zrobiłeś — razem z numerem wersji. Dzięki temu wie, że wszystko u Ciebie działa, bez dopytywania. Nic z Twoich operatów nie wychodzi: ani numerów działek, ani nazwisk, ani numerów ksiąg wieczystych. Szczegóły są w Pomocy, w sekcji „Co program o sobie wysyła”.

## 2026.08.03.2 — 2026-08-03

Na liście operatów doszedł przycisk „Popraw” — obok „Złóż PDF” i „Powiel”. Wcześniej, żeby poprawić literówkę w gotowym operacie, trzeba było najpierw wejść w niego i dopiero tam kliknąć; teraz jest to jedno kliknięcie z listy. „Popraw” wraca do tego samego operatu i nie zużywa kolejnego numeru, a „Powiel” zakłada nowy z tymi samymi danymi.

## 2026.08.03.1 — 2026-08-03

Ta wersja nie zmienia niczego w samym programie. Jedna rzecz warta zapamiętania: robiąc kopię zapasową, kopiuj oba katalogi — „wyniki” i „dane”. W „wyniki” leżą całe operaty razem z mapami, szkicami i skanami, które sam do nich dokładasz, a tego nie da się odtworzyć z niczego innego.

## 2026.08.02.15 — 2026-08-02

Przy polu położenia zniknął rozwijany spis znaczników do Worda i podpowiedź nad listami — to samo jest w Pomocy, a formularz ma być do wypełniania, nie do czytania instrukcji.

## 2026.08.02.14 — 2026-08-02

Powierzchnia działki pokazuje się teraz zaokrąglona do dwóch miejsc — „ok. 0,42 ha” zamiast „ok. 0,4159 ha”. Dokładna liczba stoi obok w metrach kwadratowych i ta zostaje bez zmian. Cały komunikat z ewidencji jest grubszy, żeby dało się go złapać wzrokiem bez szukania.

## 2026.08.02.13 — 2026-08-02

Sprawdzanie działki pokazuje teraz także jej przybliżoną powierzchnię, np. „6002 — ok. 0,4159 ha (4159 m²)”. Warto na nią zerknąć: numer 123/5 wpisany zamiast 123/4 zwykle też istnieje, więc samo „jest taka działka” tego nie wyłapie, a inna wielkość od razu.

## 2026.08.02.12 — 2026-08-02

Nowość: po wpisaniu numeru działki program sprawdza w ewidencji (ULDK), czy taka działka istnieje w wybranym obrębie, i pisze o tym pod polem. To tylko podpowiedź na literówkę — nigdy nie blokuje wygenerowania dokumentu, a gdy usługa nie odpowiada, nie pisze nic.

## 2026.08.02.11 — 2026-08-02

Program pamięta teraz, jak poukładałeś operat: gdy złożysz PDF i wrócisz tu później, kolejność kafelków i obroty są takie, jak je zostawiłeś. Pliki dołożone w międzyczasie czekają na końcu listy, więc nic nie przestawia się samo. Ustawienie zapisuje się w katalogu operatu, więc jedzie razem z nim do archiwum.

## 2026.08.02.10 — 2026-08-02

Uproszczone menu: zniknęła osobna strona „Złóż PDF”, bo pokazywała drugi raz tę samą listę operatów. Składanie zaczynasz teraz przy konkretnym operacie — na liście albo na jego stronie. Lista pokazuje wszystkie operaty (wcześniej tylko 15 ostatnich), a także te przywrócone z archiwum, których nie ma już w historii.

## 2026.08.02.9 — 2026-08-02

Historia wersji w menu „Pomoc” pokazuje już pełną listę zmian — w poprzedniej wersji brakowało samego pliku z historią, więc strona świeciła pustką.

## 2026.08.02.8 — 2026-08-02

Nowość: w menu u góry jest teraz „Pomoc”, a w nim — obok instrukcji do szablonów — historia wersji. Zobaczysz w niej, co doszło w każdej kolejnej wersji programu, razem z tą, którą masz w tej chwili.

## 2026.08.02.7 — 2026-08-02

Drobne sprzątanie: przy pierwszym uruchomieniu programu nie powstaje już niepotrzebna kopia pustej bazy w katalogu dane\kopie. Kopie bezpieczeństwa robią się nadal — przed każdą zmianą układu bazy i przed każdą aktualizacją.

## 2026.08.02.6 — 2026-08-02

Drobne sprzątanie: przy pierwszym uruchomieniu programu nie powstaje już niepotrzebna kopia pustej bazy w katalogu dane\kopie. Kopie bezpieczeństwa robią się nadal — przed każdą zmianą układu bazy i przed każdą aktualizacją.

## 2026.08.02.5 — 2026-08-02

Czarne okno programu chowa się teraz samo do paska zadań zaraz po uruchomieniu — przestaje wyskakiwać przed przeglądarkę. Program zamykasz nim tak samo jak dotąd, wystarczy kliknąć je w pasku. Gdyby program się nie uruchomił, okno zostaje otwarte, żeby było widać dlaczego.

## 2026.08.02.4 — 2026-08-02

Po zamknięciu okna katalogu na wierzch wraca teraz przeglądarka, a nie czarne okno programu.

## 2026.08.02.3 — 2026-08-02

Po kliknięciu „Otwórz katalog” okno Eksploratora wychodzi teraz na wierzch, zamiast chować się za oknem przeglądarki i migać na pasku zadań.

## 2026.08.02.2 — 2026-08-02

Liczniki na dole strony liczą teraz poprawnie: przeniesienie gotowych operatów do archiwum ich nie kasuje, a pliki, które sam dołożysz do katalogu, nie są doliczane jako wygenerowane.

## 2026.08.02.1 — 2026-08-02

Na dole każdej strony widać teraz, ile masz operatów, ile dokumentów Worda i ile złożonych PDF-ów.

## 2026.08.01.12 — 2026-08-01

Zmiana pod spodem: program pewniej zwalnia plik bazy danych. Dla Ciebie nic się nie zmienia — historia, numeracja i formatki zostają takie same.

## 2026.08.01.11 — 2026-08-01

Poprawka: polskie „ł” nie znika już z nazw plików — „Sułkowice” zostaje „Sulkowice”, a nie „Sukowice”. Formatki są bez zmian, ta wersja ich nie rusza.

## 2026.08.01.10 — 2026-08-01

Naprawione: w sprawozdaniu wiersz z tolerancjami pod „Pomiar kontrolny…” przesuwał się w lewo — program zwijał wpisane w Wordzie tabulatory do jednego. Teraz zostają nietknięte.

## 2026.08.01.9 — 2026-08-01

Zmienione: poprawiony spis treści (większy nagłówek „Spis treści”) oraz sprawozdanie techniczne — doszło zdanie o dokładności punktów granicznych i możliwości projektowania bliżej niż 4 m od granicy.

## 2026.08.01.8 — 2026-08-01

Zmienione: formatki po poprawkach brata — dłuższe nazwy etykiet, REGON w danych wykonawcy, wiersz z pomiarem kontrolnym w sprawozdaniu oraz pogrubione wartości zamiast etykiet, jednakowo we wszystkich dokumentach.

## 2026.08.01.7 — 2026-08-01

Poprawione: usunięte justowanie w opisie przebiegu prac w sprawozdaniu technicznym.

## 2026.08.01.6 — 2026-08-01

Poprawione: w wykazie zmian działki (strona pozioma) dane w stopce rozkładają się teraz na całą szerokość kartki, a nie kończą w dwóch trzecich, jakby strona była pionowa.

## 2026.08.01.5 — 2026-08-01

Zmienione: ostatnie poprawki we wszystkich czterech formatkach — dodatkowe pogrubienia w wykazach, w sprawozdaniu i w spisie treści. Wygląd i układ bez zmian.

## 2026.08.01.4 — 2026-08-01

Nowość: prawdziwa formatka wykazu zmian dotyczącego działki ewidencyjnej (pozioma, z tabelą stanu dotychczasowego i nowego). Poprawione: w obu wykazach dane na górze i blok podpisu stoją teraz w równych kolumnach — wcześniej każdy wiersz lądował gdzie indziej. Pogrubienia dopisane w spisie treści zachowane.

## 2026.08.01.3 — 2026-08-01

Zmienione: poprawiona formatka wykazu zmian dotyczącego budynku. Pogrubienia, które wpiszesz w Wordzie, zostają teraz nietknięte — program ustala tylko krój, wielkości i układ, a o tym, co wyróżnić w treści, decyduje formatka.

## 2026.08.01.2 — 2026-08-01

Nowość: prawdziwa formatka wykazu zmian danych ewidencyjnych dotyczących budynku — z tabelą atrybutów wymaganą przez ośrodek, w tym samym wyglądzie co spis treści i sprawozdanie. Poprawione: wartości w nagłówku wykazu stoją w jednej kolumnie, a stopka jest teraz przepisywana z jednego wzorca, więc we wszystkich dokumentach jest identyczna.

## 2026.08.01.1 — 2026-08-01

Poprawiony sam numer wersji: data w numerze stanęła na 31 lipca, choć wydania szły już 1 sierpnia. Program działa dokładnie tak samo jak w poprzedniej wersji.

## 2026.07.31.40 — 2026-08-01

Poprawione: w stopce nazwa ulicy pisana jest wielką literą — „ul. Rybnicka 16A”.

## 2026.07.31.39 — 2026-07-31

Naprawione: spis treści dalej nie otwierał się w Wordzie — logo miało dopisany rozmiar w niewłaściwym miejscu pliku i zgubiony wymagany atrybut. Zmienione: czcionka na Calibri (jest na każdym Windowsie, a dokument tak samo łamie się na Linuksie), stopka bez wersalików, mniejsza i szara, ta sama na każdej stronie i w obu dokumentach. Numeracja stron usunięta.

## 2026.07.31.38 — 2026-07-31

Naprawione: szablony z poprzedniej wersji nie otwierały się w Wordzie, więc nie powstawały też miniatury i PDF-y. Przy ujednolicaniu wyglądu dwa elementy trafiły w niewłaściwe miejsce w pliku — Word takiego dokumentu nie przyjmuje. Formatki są poprawione, wygląd bez zmian.

## 2026.07.31.37 — 2026-07-31

Zmienione: spis treści i sprawozdanie techniczne wyglądają teraz jak jeden komplet — to samo logo w tym samym miejscu i rozmiarze, jeden krój pisma, ta sama hierarchia nagłówków, bez podkreśleń. Numer roboty zostaje czerwony. W sprawozdaniu poprawione wcięcia: druga linijka zdania nie wraca już na margines, a opis złożony z kilku urwanych linijek czyta się jak zwykły akapit.

## 2026.07.31.36 — 2026-07-31

Naprawione: wejście w „Złóż PDF” zaraz po zapisaniu operatu pokazywało puste kafelki, dopóki nie odświeżyło się strony. Word zapisywał PDF prosto do pliku docelowego, więc miniatura potrafiła trafić na dokument w połowie zapisany. Teraz plik pojawia się na miejscu dopiero gotowy, a gdyby miniatura mimo wszystko nie zdążyła, strona sama spróbuje ponownie.

## 2026.07.31.35 — 2026-07-31

Miniatury pokazują się teraz od razu. Program przerabia dokumenty na PDF zaraz po ich wygenerowaniu, w tle — więc zanim wejdziesz w „Złóż PDF”, wszystko jest już gotowe. Do tego cały komplet dokumentów idzie przez Worda za jednym uruchomieniem zamiast osobno dla każdego pliku, co skraca konwersję o dwie trzecie.

## 2026.07.31.34 — 2026-07-31

Przycisk „Usuń” został tylko na liście dokumentów — z zakładki „Złóż PDF” znika.

## 2026.07.31.33 — 2026-07-31

Doszły przyciski „Usuń” — na liście dokumentów i na liście w zakładce „Złóż PDF”. Każdy pyta o potwierdzenie i mówi wprost, że znika cały katalog operatu razem z plikami, które sam do niego włożyłeś.

## 2026.07.31.32 — 2026-07-31

Każdy dodatkowy dokument ma teraz własną kartę w formularzu. Sprawozdanie ze swoimi opcjami stoi osobno, wykazy zmian osobno — wcześniej wszystkie checkboxy były w jednej liście, a opcje sprawozdania wyglądały, jakby dotyczyły ostatniej pozycji.

## 2026.07.31.31 — 2026-07-31

Doszły dwa dokumenty do wyboru: wykaz zmian danych ewidencyjnych dotyczących budynku i dotyczących działki ewidencyjnej. Zaznaczasz je w karcie „Dokumenty do wygenerowania” tak samo jak sprawozdanie — nie trzeba nic dodatkowo wpisywać, biorą dane z operatu.

## 2026.07.31.30 — 2026-07-31

Dalsze poprawki pod awarię przy miniaturach: renderowanie idzie teraz pojedynczo (silnik PDF nie znosi pracy w kilku wątkach naraz), a ten sam plik nie jest już konwertowany kilka razy równolegle — przy operacie z dwoma dokumentami Word uruchamiał się cztery razy zamiast dwóch.

## 2026.07.31.29 — 2026-07-31

Poprawki pod awarię przy miniaturach na Windowsie: konwersje do PDF idą teraz pojedynczo (strona składania pobierała kilka miniatur naraz i uruchamiała tyleż konwersji), a Word jest zwalniany zanim wątek odłączy się od COM-u. Doszło też narzedzia\diagnostyka.bat — uruchamia program tak, że wszystko ląduje w dane\konsola.log.

## 2026.07.31.28 — 2026-07-31

Wszedł Twój szablon sprawozdania technicznego — z numeracją punktów, danymi firmy i pełnym opisem technologii. Bez zaznaczonego opisu przebiegu punkty 7 i 8 pokazują „brak”.

## 2026.07.31.27 — 2026-07-31

Zmiany w bazach danych wychodzą teraz w sprawozdaniu jako nazwy plików GML — np. GK.6640.123.2026-BDOT500.gml — po przecinku. Bez zaznaczonej żadnej bazy nadal „brak”.

## 2026.07.31.26 — 2026-07-31

Pola sprawozdania przeniosły się do karty „Dokumenty do wygenerowania” i budzą się dopiero po zaznaczeniu sprawozdania — wcześniej są wyszarzone, a nie schowane. Zmiany w bazach danych zależą teraz od „Opisu przebiegu”: bez niego też są wyszarzone. Aktualizacja kasuje wreszcie szablony, których nie ma już w programie.

## 2026.07.31.25 — 2026-07-31

Doszło sprawozdanie techniczne — zaznaczasz je w formularzu operatu i powstaje obok spisu treści, z tych samych danych. W karcie „Sprawozdanie techniczne” jest przełącznik „Opis przebiegu” (po zaznaczeniu pojawia się pole na opis) oraz trzy zaznaczone na start bazy: BDOT500, GESUT i EGiB. Bez opisu w sprawozdaniu wychodzi „brak”; odznaczenie wszystkich baz też daje „brak”.

## 2026.07.31.24 — 2026-07-31

Mniejszy odstęp między logo a danymi działki, a podpis podniesiony o dwa wiersze znad stopki.

## 2026.07.31.23 — 2026-07-31

Podpis stoi teraz zawsze na dole strony — niezależnie od tego, czy spis treści ma dwie pozycje, czy trzynaście.

## 2026.07.31.22 — 2026-07-31

Naprawione: poprawianie operatu zakładało za każdym razem nowy katalog z kolejnym numerem, mimo że numer w dokumencie zostawał stary. Teraz poprawka naprawdę wraca do tego samego operatu. Wszedł też Twój szablon z poprawioną odległością, żeby spis mieścił się na jednej stronie.

## 2026.07.31.21 — 2026-07-31

Wszedł Twój poprawiony szablon. Spis treści wygląda teraz jak lista: numery i tekst w równych kolumnach niezależnie od tego, czy numer ma jedną czy dwie cyfry, większe odstępy między pozycjami, a zawinięty wiersz trzyma się tekstu zamiast chować pod numer.

## 2026.07.31.20 — 2026-07-31

Wszedł Twój szablon operatu. Na stronie startowej jest teraz jeden kafelek — „Operat”; sprawozdanie i protokoły dokłada się do niego checkboxem w formularzu, bo same bez operatu nie istnieją. Najważniejsze: „Popraw ten operat” nie nadaje już kolejnego numeru — zostaje ten sam numer i ten sam katalog, a pliki się nadpisują. Do zakładania nowej roboty z tymi samymi danymi służy osobne „Powiel jako nowy”.

## 2026.07.31.19 — 2026-07-31

Pole I.Z.P.G zniknęło — okazało się tym samym co numer roboty. Numer roboty i numer operatu zajmują teraz po pół szerokości, tak jak daty poniżej.

## 2026.07.31.18 — 2026-07-31

W formularzu doszła karta „Dokumenty do wygenerowania”: zaznaczasz, które jeszcze pliki Worda mają powstać obok głównego. Wszystkie trafiają do tego samego katalogu operatu i dostają te same dane — numer roboty, numer operatu, daty i położenie. Lista pojawia się sama, gdy w katalogu szablonów jest więcej niż jeden plik, i nie ma nic wspólnego ze spisem treści.

## 2026.07.31.17 — 2026-07-31

Szablon nazywa się teraz spis_tresci_wzor.docx, bo wkrótce dojdą kolejne. Nazwa pliku w katalogu operatu wynika wprost z nazwy szablonu, więc każdy następny dokument trafi do własnego pliku, zamiast nadpisywać spis treści.

## 2026.07.31.16 — 2026-07-31

Poprawione brzmienie dwóch pozycji spisu treści („Protokół ustalenia”, „Protokół wznowienia”). Lista w formularzu jest teraz czystsza — bez numerków i dopisków; numeracja zostaje tam, gdzie ma sens, czyli w gotowym dokumencie.

## 2026.07.31.15 — 2026-07-31

Doszła karta „Spis treści”: odhaczasz, co wchodzi do operatu, a do dokumentu trafiają tylko zaznaczone pozycje, ponumerowane od nowa. Spis treści i sprawozdanie techniczne są zaznaczone na stałe — widać je, ale nie da się ich odznaczyć.

## 2026.07.31.14 — 2026-07-31

Numer operatu wrócił do postaci 001/2026, a katalog nazywa się 001.2026 — ukośnika w nazwie folderu być nie może. W karcie „Robota” doszło pole I.Z.P.G, a numery i daty ułożyły się po trzy i po dwa w rzędzie. Pod położeniem działki jest nowe wymagane pole „Nr działki”.

## 2026.07.31.13 — 2026-07-31

Karta „Robota” ma teraz właściwe pola: numer roboty i numer operatu (oba wymagane), datę zgłoszenia i datę zakończenia pracy geodezyjnej wybierane z kalendarza oraz listę rodzajów prac zgodną z formularzem zgłoszenia. Położenie działki przeniosło się do własnej karty.

## 2026.07.31.12 — 2026-07-31

Drobne porządki w interfejsie: zakładka „Łączenie PDF” nazywa się teraz „Złóż PDF”, a z listy dokumentów zniknęła kolumna z nazwą szablonu.

## 2026.07.31.11 — 2026-07-31

Numer operatu ma teraz kropkę zamiast ukośnika (001.2026), dzięki czemu katalog operatu nazywa się dokładnie tak jak numer — bez żadnych podmian.

## 2026.07.31.10 — 2026-07-31

Lista dokumentów zaczyna się teraz od numeru operatu, obok jest numer roboty. Pobierania Worda i PDF-a nie ma — wszystkie pliki leżą w katalogu operatu, a otwiera go przycisk „Otwórz katalog”. Po kliknięciu „Złóż PDF” gotowy plik zapisuje się sam w tym katalogu i można go od razu obejrzeć przyciskiem „Otwórz PDF”.

## 2026.07.31.9 — 2026-07-31

Każdy operat dostaje teraz własny katalog w „wyniki”, nazwany numerem operatu — w środku spis_tresci.docx, opis roboty i pusty plik z numerem KERG, żebyś widział go w Eksploratorze. Do tego katalogu wkładasz mapy, szkice i wykaz z C-Geo. Zakładka „Łączenie PDF” pokazuje teraz miniatury plików z wybranego operatu: kolejność ustawiasz przeciągając myszą, pliki bokiem obracasz strzałkami, a niepotrzebne wyłączasz krzyżykiem. Gotowy PDF nazywa się dokładnie tak jak numer roboty. Wgrywania plików z dysku już nie ma — wystarczy włożyć je do katalogu.

## 2026.07.31.8 — 2026-07-31

Szablony przyjeżdżają teraz razem z programem i przy aktualizacji podmieniają się na nowe — nie ma już osobnych „wzorcowych” i „twoich”. Jeśli coś w formatce ma wyglądać inaczej, powiedz bratu; poprawka przyjdzie z kolejną aktualizacją. Poprzednia wersja szablonów zostaje w dane\kopie.

## 2026.07.31.7 — 2026-07-31

Drobna poprawka wyglądu: przycisk „Przerwij” przy pobieraniu obrębów stoi teraz równo z sąsiednimi.

## 2026.07.31.6 — 2026-07-31

Formularz jest teraz przycięty do danych roboty i położenia działki — resztę sekcji dołożymy po kolei, tak jak ustalimy. Ekran „Dane stałe” zniknął: nazwisko, uprawnienia i pieczątkę wpisz na stałe w swoim szablonie Worda. W Ustawieniach doszedł przycisk „Pobierz obręby dla całej Polski” z paskiem postępu — ściąga obręby wszystkich gmin w kraju (kilka minut), żeby dało się pracować w terenie bez internetu; można go przerwać i dokończyć później.

## 2026.07.31.5 — 2026-07-31

Położenie działki wybierasz teraz z list: województwo, powiat, jednostka ewidencyjna, obręb. Dane pochodzą z rejestru TERYT (GUS) i z serwisu ULDK (GUGiK), pobierają się same przy pierwszym uruchomieniu i zostają na komputerze, więc program działa też bez internetu. Do dokumentu wchodzą i nazwy, i identyfikatory TERYT — spis znaczników do wstawienia w Wordzie masz w „Jak edytować szablon”, a ręczne odświeżanie list w „Dane stałe”.

## 2026.07.31.4 — 2026-07-31

Program tłumaczy teraz błędy po polsku i podpowiada, co z nimi zrobić. Przy łączeniu PDF-ów wgrane pliki wreszcie naprawdę się doklejają, a skan .jpg jest odrzucany od razu z wyjaśnieniem. Poprawione też: wykaz współrzędnych nie rozsypuje się przy „Popraw i wygeneruj ponownie”, a nieudane generowanie nie zjada numeru operatu.

## 2026.07.31.3 — 2026-07-31

PDF-y robi teraz Microsoft Word. Program sam sprawdza aktualizacje przy starcie.

## 2026.07.31.2 — 2026-07-31

PDF-y robi teraz Microsoft Word. Program sam sprawdza aktualizacje przy starcie.

## 2026.07.31.1 — 2026-07-31

PDF-y robi teraz Microsoft Word. Program sam sprawdza aktualizacje przy starcie.

## 2026.07.31 — 2026-07-31

PDF-y robi teraz Microsoft Word. Program sam sprawdza aktualizacje przy starcie.

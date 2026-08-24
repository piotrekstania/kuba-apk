# Historia zmian

Co doszło w kolejnych wersjach programu. Ten sam opis pokazuje się raz, na stronie
głównej, zaraz po tym jak program sam się zaktualizuje.

## 2026.08.24-110 — 2026-08-24

Zmiany:
- okno „co nowego” przewija samą listę wydań, a przycisk OK stoi na dole i widać go od razu — przy kilku wydaniach naraz okno otwierało się przewinięte na sam koniec, więc numer nowej wersji i najświeższe zmiany zostawały nad krawędzią ekranu
- nad przyciskiem OK jest kreska, żeby było widać, że treść nad nią się przewija

## 2026.08.24-109 — 2026-08-24

Zmiany:
- okno nowości pokazuje komplet przeskoczonych wydań także wtedy, gdy nigdy wcześniej nie kliknąłeś OK — wersję startową bierze wtedy z kopii sprzed aktualizacji; przy tym przeskoku z -106 na -108 zgubiło się -107 i to jest ta poprawka
- przy wielu wydaniach naraz okno przewija się w środku, zamiast wypychać przycisk OK poza ekran

## 2026.08.24-108 — 2026-08-24

Zmiany:
- wydanie porządkowe, bez zmian w programie — sprawdza, czy okno nowości poprawnie skleja kilka wydań przy przeskoku o więcej niż jedną wersję

## 2026.08.24-107 — 2026-08-24

Zmiany:
- okno nowości pokazuje wszystkie wydania od twojego ostatniego OK, każde ze swoim numerem — gdy nie uruchamiasz programu kilka dni i przeskoczysz parę wersji, przeczytasz wszystko za jednym razem, a nie tylko ostatnią zmianę

## 2026.08.24-106 — 2026-08-24

Zmiany:
- numer wersji w oknie nowości jest niebieski, taki sam jak przy nazwie programu w nagłówku

## 2026.08.24-105 — 2026-08-24

Zmiany:
- opis w oknie nowości ma znowu porządne listy punktów, tak jak w Historii wersji — wcześniej zlewał się w jeden akapit z myślnikami w środku

## 2026.08.24-104 — 2026-08-24

Zmiany:
- okno z nowościami po aktualizacji naprawdę się pokazuje — wcześniej gasło przy starcie programu, zanim przeglądarka zdążyła się otworzyć
- okno wraca przy każdym wejściu na stronę główną, dopóki nie klikniesz OK — zamknięcie przeglądarki bez klikania niczego nie gubi

## 2026.08.24-103 — 2026-08-24

Zmiany:
- opis nowego wydania pokazuje się w oknie na środku ekranu, w punktach — zamykasz przyciskiem OK i już nie wraca
- w stopce po lewej stoi firma z odnośnikiem do jej strony, po prawej liczniki

Nowości:
- numer działki wpisany w karcie wykazu działki jest sprawdzany w ewidencji, tak jak numer w Położeniu — przy trafieniu z powierzchnią z obrysu; podpowiada, nigdy nie blokuje
- każda karta działki sprawdza swój numer, a odpowiedź zawsze dotyczy tego, co wpisane teraz, także tuż po zmianie obrębu

## 2026.08.24-102 — 2026-08-24

W wykazie działki zmiana w użytku czerwieni cały wpis: gdy zmieni się choć jedna z czterech wartości (OFU, OZU, OZK, PPU), stan nowy całego użytku wychodzi czerwony i pogrubiony — tak jak dotąd nanosiłeś to ręcznie. Numer działki i pole powierzchni czerwienią się osobno, tylko gdy same się zmieniły. Pod tabelą użytków formularz liczy na bieżąco sumę PPU i porównuje ją z polem powierzchni — mówi, ile brakuje albo ile jest za dużo, przyjmuje kropkę i przecinek, a zapisu nigdy nie blokuje.

## 2026.08.22-101 — 2026-08-22

Runda ekranowa po setce. Strona operatu ma jeden wiersz na szczycie: numer operatu z datą utworzenia po lewej, a po prawej komplet przycisków — „Złóż PDF”, „Otwórz katalog”, „Popraw”, „Powiel” i „Usuń” (kasowanie przeszło z dołu strony na górę; nadal pyta o potwierdzenie i mówi teraz, co naprawdę zniknie — operat przeniesiony do archiwum znika tylko z listy). Formularz ma u góry to samo: przy poprawianiu numer operatu i datę, a „Zapisz” i „Anuluj” stoją na górze i na dole. Na liście operatów akcje są przyciskami, doszło „Otwórz katalog” (wraca na listę), a kolumna „Data” nazywa się „Utworzono”. Pole opisu — w Ustawieniach i w przebiegu prac — da się powiększyć, ciągnąc za prawy dolny róg. Krótsze podpisy dat: „Data zgłoszenia” i „Data zakończenia”. Po przeglądzie kodu: formularz po „Uzupełnij wymagane pola” nie udaje już nowego operatu, „Zapisz” ani „Powiel” w starej karcie skasowanego operatu nie zakładają po cichu nowego, pytanie „Usunąć…?” działa także przy apostrofie w nazwie, a Pomoc nie odsyła już do przycisku „Pobierz PDF”, którego nie ma.

## 2026.08.20-100 — 2026-08-20

Setne wydanie — porządki na ekranie. Strona operatu ma teraz karty z niebieskimi tytułami, jak formularz: opis i dane w jednej siatce, podpisy pól po ludzku (z opisu szablonu, nie klucze techniczne), spis treści w pionie z numerami jak w dokumencie, a w tabelach wykazów wyśrodkowane stany z kreską między dotychczasowym a nowym. Numer wersji przeniósł się ze stopki do nagłówka, pod nazwę programu; w stopce zostały liczniki. Strona błędu znów jest całą stroną z menu i stylami, a nie gołym napisem.

## 2026.08.20-99 — 2026-08-20

W wykazie działki oznaczenia OFU, OZU, OZK i PPU [ha] stoją teraz dopiero przy wierszu użytków — jako część punktu 3, tuż nad wartościami — a nie w nagłówku tabeli, gdzie wisiały też nad numerem działki i polem powierzchni. Nagłówek tabeli ma jedno piętro: tylko stan dotychczasowy i nowy.

## 2026.08.20-98 — 2026-08-20

Wykaz działki ma nowy układ użytków: OFU, OZU, OZK i PPU [ha] stoją obok siebie pod każdym stanem — jeden użytek to jedna linijka we wszystkich czterech kolumnach naraz, więc wszystko trzyma poziom. Numer działki i pole powierzchni idą na całą szerokość stanu, tabela jest domknięta z prawej i ma tę samą szerokość co tabela wykazu budynku. Formularz i strona operatu pokazują dokładnie ten sam układ, z oznaczeniami nad polami.

## 2026.08.20-97 — 2026-08-20

Wyrównanie komórek w wykazach jest teraz mądrzejsze: wiersz, w którym wpisałeś kilka linijek (OFU, OZU, OZK, pole użytków), jest wyrównany do góry — puste linijki nadal dosuwają wpis do właściwego użytku — a wiersz z pojedynczymi wartościami wraca na środek, równo z nazwą atrybutu obok. O układzie decyduje to, co naprawdę wpisałeś, osobno dla każdego wiersza.

## 2026.08.19-96 — 2026-08-19

Podgląd operatu (strona „Wpisane dane”) wyrównuje komórki wykazów do góry, tak samo jak gotowy dokument — przy różnej liczbie linijek w dwóch stanach linijki trzymają poziom także na ekranie, nie tylko w PDF.

## 2026.08.19-95 — 2026-08-19

W wykazie działki wartości wielolinijkowe (OFU, OZU, OZK, pole powierzchni użytków) zaczynają się od górnej krawędzi komórki, więc linijki stanu dotychczasowego i nowego trzymają poziom — wcześniej krótsza kolumna była środkowana w pionie i pływała. Razem z pustymi linijkami z poprzedniej wersji daje to równe wiersze w obu kolumnach.

## 2026.08.19-94 — 2026-08-19

W wielolinijkowych polach wykazu działki (OFU, OZU, OZK, pole powierzchni użytków) puste linijki zostają i wchodzą do dokumentu — możesz nimi zsunąć wpis stanu nowego do właściwego wiersza sąsiedniej kolumny, np. gdy zmiana dotyczy dopiero drugiego użytku. Puste linijki przeżywają też poprawianie operatu.

## 2026.08.19-93 — 2026-08-19

Wykazy zmian same wyróżniają to, co się zmieniło: stan nowy różny od dotychczasowego wychodzi w dokumencie na czerwono i pogrubiony — tak, jak dotąd zaznaczałeś to ręcznie w Wordzie. Wykaz działki wygląda teraz jak wykaz budynku: jedna działka to jedna strona, a jej numer wpisujesz w karcie działki — wchodzi do nagłówka swojej strony. OFU, OZU, OZK i pole powierzchni użytków przyjmują kilka wartości, każdą w osobnej linijce (Enter). Z wykazu budynku zniknęły odsyłacze do przypisów.

## 2026.08.19-92 — 2026-08-19

Wykaz zmian danych działki drukuje się teraz w pionie, jak reszta operatu: każda działka to dwa wiersze — stan dotychczasowy nad nowym — więc wartości przed i po zmianie porównujesz jedną pod drugą, a kolumny są szersze niż na poziomej kartce. Rodzaj budynku według KŚT wybierasz z listy w obu stanach, bez przepisywania z ręki — a wpis z ręki w starszym operacie zostaje. Cyfry L.p. w wykazie budynku stoją równo na środku komórek. Na stronie głównej zamiast karty szablonu jest przycisk „Nowy operat”, a nazwy kart formularza są niebieskie, żeby łatwiej je znaleźć przy przewijaniu.

## 2026.08.19-91 — 2026-08-19

Wykazy zmian danych ewidencyjnych wypełniasz teraz w programie — na to czekałeś: wykaz budynku po kilka na operat, każdy na osobnej stronie, a wykaz działki jako kolejne wiersze jednej tabeli, z identyfikatorem działki w nagłówku. Spis treści włącza dokumenty: zaznaczenie pozycji odblokowuje jej pola i generuje plik, a dokument odznaczony przy poprawianiu znika z katalogu operatu. Formularz ostrzega też przed wyjściem z niezapisanymi zmianami.

## 2026.08.14-90 — 2026-08-14

Poprawione formatowanie opisu przebiegu prac: pogrubienie ustawione na jednym akapicie nie rozlewa się już na tekst pod spodem. Dotyczyło to wklejki z Worda i pisania w edytorze po naciśnięciu Entera.

## 2026.08.13-89 — 2026-08-13

Opis przebiegu prac w sprawozdaniu przyjmuje teraz formatowanie: pogrubienie, kursywę i podkreślenie ustawiasz przyciskami nad polem albo skrótami Ctrl+B, Ctrl+I, Ctrl+U. Możesz też wkleić gotowy tekst z Worda — pogrubienia przyjadą razem z nim, a krój i rozmiar czcionki zostaną te z formatki, żeby dokument wyglądał jednolicie. W Ustawieniach doszła sekcja „Opis sprawozdania”: zapisujesz tam gotowe opisy, a przy każdej robocie wybierasz jeden z listy nad polem i klikasz „Załaduj”. Twój standardowy opis jest już wpisany — możesz go poprawić albo usunąć, program go nie przywróci. Zniknął checkbox „Opis przebiegu”, bo program sam widzi, czy coś wpisałeś. W formatce sprawozdania nie ma już drugiej kopii opisu wpisanej na sztywno — do dokumentu wchodzi to, co masz w polu.

## 2026.08.11-88 — 2026-08-11

Strona operatu poukładana. Opis stoi teraz własną sekcją tuż nad „Wpisanymi danymi” i wygląda tak samo jak one — nagłówek i biały panel — zamiast mieć własny styl obok reszty. Ścieżka do katalogu przestała być niebieskim pudełkiem: mówi to samo przy każdym operacie, więc nie ma po co krzyczeć głośniej niż twoje notatki; stoi teraz cicho tuż pod przyciskami, których dotyczy.

## 2026.08.10-87 — 2026-08-10

Nowe pole „Opis” przy zakładaniu i poprawianiu operatu — miejsce na twoje notatki do roboty: co zostało do zrobienia, na co czekasz, co ustaliłeś w ośrodku. Do żadnego dokumentu to nie wchodzi, jest tylko dla ciebie. Opis widać na liście operatów na stronie głównej, pod danymi operatu, i po wejściu w sam operat. Zmieniasz go przez „Popraw ten operat”, tak jak resztę danych. Zapisuje się razem z operatem, więc zostaje i po przeniesieniu katalogu do archiwum, i po skopiowaniu go na inny komputer.

## 2026.08.06-86 — 2026-08-06

Na stronie operatu widać teraz, z której formatki powstał. Gdy użyta była własna, na dole dochodzi blok „Użyte formatki” z nazwą pliku; przy standardowej nie ma tam nic, bo to stan domyślny. Jeśli formatka została w międzyczasie usunięta, program pisze o tym wprost — poprawianie takiego operatu wróci już do standardowej.

## 2026.08.06-85 — 2026-08-06

Lista wpisanych danych na stronie operatu jest teraz uporządkowana: pola idą w tej samej kolejności i w tych samych grupach co w formularzu — robota, położenie, spis treści, sprawozdanie, wykazy — rozdzielone nagłówkami. Wcześniej leżały w kolejności przypadkowej, więc numer roboty sąsiadował z opisem przebiegu, a daty stały w trzech miejscach.

## 2026.08.06-84 — 2026-08-06

Porządki na stronie operatu: zniknął wiersz „dokumenty — 0 wierszy”. To było pole zbiorcze „Wygeneruj też”, które zbiera dokumenty nieprzypisane do żadnej karty — a że wszystkie są już przypisane, nie ma z czego wybierać i formularz w ogóle go nie pokazuje. Wybrane dokumenty są teraz opisane nazwami („Sprawozdanie techniczne”) zamiast nazwami plików. Wygenerowane pliki były zawsze te, co trzeba.

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

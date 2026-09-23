# Przed wydaniem — co sprawdzić ręcznie

Testy jadą na Linuksie i w CI, ale **dwóch rzeczy nie sprawdzą**: prawdziwego Worda
(nie ma go na runnerze) i tego, jak dokument wygląda na kartce. U brata aktualizacja
instaluje się sama przy starcie, więc to jest ostatni moment, żeby coś złapać.

Ta lista ma dwie części: **stały rytuał** (część A) i **co doszło w tej rundzie**
(część B — dopisuj przy każdym wydaniu, kasuj po wydaniu). Część C to gotowy tekst
do zlecenia review.

---

## A. Stały rytuał na Windowsie (`E:\git\kuba-apk`)

**Zanim zaczniesz:** otwórz Worda ręcznie i zamknij. Świeża instalacja Office potrafi
pokazać okno aktywacji albo pytanie o domyślny format — wtedy konwersja **wisi**,
zamiast paść, i wygląda to na zawieszony program.

```bat
git pull
.venv\Scripts\pip install -r requirements-dev.txt
.venv\Scripts\pytest
```

Potem ścieżka wordowa — **nie równolegle** (`-n auto`), bo Word to jedna aplikacja
na komputerze:

```bat
.venv\Scripts\pytest -m word -v
```

Gdy test padnie w połowie, zajrzyj do Menedżera zadań i ubij zostawionego
`WINWORD.EXE`, zanim uruchomisz następny — inaczej kolejne testy kłamią.
`Windows fatal exception: code 0x800706be` przy każdej konwersji **nie jest awarią**
(opis w CLAUDE.md).

Dalej program:

```bat
start.bat
```

1. **Otwórz każdy wygenerowany `.docx` w prawdziwym Wordzie.** To jest jedyny test,
   który wykrywa złą kolejność elementów w OOXML — LibreOffice składa takie pliki
   do PDF-a bez jednego ostrzeżenia, a Word ich **w ogóle nie otwiera** (pułapka 12d).
   Objaw u brata: przestają powstawać miniatury.
2. **Obejrzyj złożony PDF** — nie liczby, tylko obrazek: podpisy, marginesy, stopka
   na całą szerokość, dokument niepuchnący na kolejną stronę.
3. Złóż operat (`Złóż PDF`) i sprawdź, że po konwersji **nie został**
   `WINWORD.EXE` w Menedżerze zadań.
4. Poprawianie operatu (`Popraw`): dane wracają do formularza, numer
   operatu **się nie zmienia**, katalog ten sam, układ kafelków zapamiętany.

---

## B. Co doszło w tej rundzie

Wszystko od ostatniego wydania — numer i skrót commita znajdziesz w `ZMIANY.md`
i `git log`. Dopisuj punkty przy każdej rundzie zmian, kasuj po wydaniu.

*(pusto — wydanie 2026.09.23-113 poszło 23.09. Sprawdzone na Linuksie w Chrome: sześć
kolorów, kafelki przy składaniu (obrót, pominięcie, przeciąganie, złożenie), lista operatów
przy 1280, 1060, 1000, 900, 820, 760 i 640 px, fokus z klawiatury, komunikaty obrębów
i pobierania dla całej Polski. Ten sam operat wygenerowany starym i nowym kodem: pliki
Worda identyczne bajt w bajt, złożony PDF i podglądy piksel w piksel)*

**Zostało do sprawdzenia na Windowsie** — tego na Linuksie nie widać:

1. **Krój z pliku, nie z internetu.** Odłącz sieć i otwórz program: nagłówki mają mieć
   zaokrąglone końcówki liter (Google Sans Flex), a nie kanciasty Segoe UI.
2. **Aktualizacja przywozi `app/web/static/czcionki/`** — na instalacji testowej
   (`narzedzia/instalacja_testowa.py --stara-wersja`). Bez tego katalogu program działa,
   tylko krojem zapasowym.
3. **Kolor programu przeżywa zamknięcie** programu i start przez `start.bat`.
4. **Lista operatów w oknie na pół ekranu** (Win+←) z paskiem przewijania Windowsa:
   bez poziomego przewijania strony, grupa przycisków schodzi niżej w całości.
5. **Pliki otwarte w innych programach** (na Linuksie udawane atrybutem „tylko do
   odczytu”): „Popraw” przy dokumencie otwartym w Wordzie, „Złóż PDF” przy wyniku
   otwartym w czytniku — komunikat mówi, co zamknąć. „Usuń” przy otwartym pliku:
   „Nic nie zostało skasowane”, katalog i wpis zostają **całe**. Jeśli Windows mimo
   to przemianuje katalog, poprawka nie działa i trzeba wrócić do tematu.
6. Rytuał A (Word) — ścieżka wordowa się nie zmieniła, ale to ona idzie do ośrodka.

**Numeracja i stary złożony PDF** (runda po wydaniu 113) — na Linuksie blokadę plików
udaje w testach atrybut „tylko do odczytu” i podmiana `rename`/`unlink`, więc prawdziwe
zachowanie Windowsa trzeba zobaczyć raz na żywo:

1. **„Popraw” z nowym numerem operatu** przy zamkniętych plikach: katalog w Eksploratorze
   zmienia nazwę na nowy numer, mapy i skany są w środku, na liście stoi nowy numer,
   a „Złóż PDF” pamięta ułożenie kafelków.
2. To samo przy **dokumencie otwartym w Wordzie**: komunikat „Nie mogę zmienić numeru…
   Nic nie zostało zmienione”, katalog i historia bez zmian. (Przy katalogu otwartym
   tylko w Eksploratorze zmiana nazwy zwykle przechodzi — to też jest w porządku.)
3. **„Popraw” z nowym numerem roboty** przy złożonym PDF-ie **zamkniętym**: stary PDF
   znika, na stronie operatu zdanie, żeby złożyć operat jeszcze raz. Przy PDF-ie
   **otwartym w czytniku**: komunikat, plik zostaje, ale na stronie składania go nie ma.
4. **Numer z ręki wyżej niż licznik** (np. 050): szary numer w pustym polu nowego
   operatu pokazuje 051, i taki operat dostaje.
5. **Numer z ręki dużo wyżej niż kolejny** (np. 0122 przy kolejnym 013): okienko
   z pytaniem w przeglądarce brata (Edge/Chrome); „Anuluj” zostawia formularz, a drugie
   „Zapisz” po poprawieniu numeru normalnie działa.

**Aktualizacja, `start.bat`, dane wyłączonych sekcji, zawieszony Word** (druga runda po
wydaniu 113). Na Linuksie sprawdzone testami i w Chrome (odznaczony wykaz budynku wraca
z danymi, wartość listy spoza opcji zostaje, składanie działa); ten sam operat co przy
wydaniu 113: pliki Worda identyczne bajt w bajt, PDF-y w tekście i obrazie. Zostaje
Windows — cmd i Worda tu nie ma:

1. **`start.bat` podmieniany w trakcie** — przejście ze starego `start.bat` na nowy,
   czyli dokładnie to, co zobaczy brat. Instalacja ze starego kodu (commit wydania 113),
   z cofniętym numerem:

   ```bat
   .venv\Scripts\python narzedzia\instalacja_testowa.py E:\test-brata --z-commita c3b1c98
   E:\test-brata\start.bat
   ```

   Stary `start.bat` i stary aktualizator ściągają nowy kod z `main`. Aktualizacja
   przechodzi, program startuje normalnie, w oknie **żadnego** „nie jest rozpoznawane
   jako polecenie wewnętrzne” ani drugiego startu. Po zamknięciu programu uruchom
   `start.bat` jeszcze raz — teraz już cały nowy — i też ma wystartować normalnie.
2. **Świeży `start.bat` od zera** (skasowany `.venv`): zakłada środowisko, instaluje
   biblioteki, zakłada skrót i startuje — blok w nawiasach nie może się rozsypać.
3. **Drugie uruchomienie w czasie pracy programu**, a potem zamknięcie pierwszego okna:
   pierwsze okno kończy się po „Naciśnij dowolny klawisz”, bez wykonywania czegokolwiek
   więcej.
4. **Aktualizacja przy szablonie otwartym w Wordzie** — działa dopiero od aktualizacji
   **po** tej, która przywiozła nowy aktualizator (pułapka 7b), więc na instalacji
   z punktu 1, już po przejściu: cofnij numer w pierwszej linii jej `WERSJA`, otwórz
   w Wordzie jej `szablony\spis_tresci_wzor.docx` i uruchom `start.bat`. Okno mówi, który
   plik zamknąć, program startuje w starej wersji, w `dane\kopie\` nie przybywa kopii.
   Po zamknięciu Worda i ponownym starcie — aktualizacja przechodzi.
5. **`pip` bez internetu**: dopisz coś do `requirements.txt` instalacji testowej, odłącz
   sieć, uruchom — komunikat „Nie udalo sie doinstalowac bibliotek” i program **startuje**.
   Z nieistniejącą biblioteką zaimportowaną w `app` — polski komunikat o brakującej
   bibliotece zamiast śladu stosu.
6. **Strażnik Worda**: `.venv\Scripts\pytest -m word -v` (w tym
   `test_limit_czasu_zamyka_tylko_naszego_worda`), a potem Menedżer zadań — żadnego
   zostawionego `WINWORD.EXE`. Z otwartym obok własnym dokumentem Worda: zostaje otwarty.
7. **Czas konwersji** po dołożeniu `tasklist`: podglądy po „Zapisz” mają się pojawiać
   tak samo szybko jak dotąd (dwa wywołania `tasklist` na start Worda to ułamek sekundy).

**Zostało do obejrzenia okiem** (z wydania 112) — tego testy ani przeglądarka nie sprawdzą:
otworzyć **złożony PDF w prawdziwym czytniku** i potwierdzić, że karta, panel stron
i pole „Tytuł” we właściwościach pokazują numer roboty, a plik otwiera się normalnie.
Metadane dopisujemy przy sklejaniu, więc gdyby coś poszło nie tak, ucierpiałby cały
operat, a `pypdf` w testach czyta tylko sam siebie.

---

## C. Zlecenie review (do wklejenia Fable)

> Zrób przegląd kodu zmian z zakresu `61f12ed..HEAD` w tym repozytorium
> (`git log --oneline 61f12ed..HEAD`, `git diff 61f12ed..HEAD`) — to wszystko, co
> przyszło po ostatnim wydaniu (`2026.09.23-113`). Kontekst projektu jest w `CLAUDE.md` —
> przeczytaj go najpierw, zwłaszcza listę pułapek i zasady pracy nad kodem.
> Odpowiadaj po polsku.
>
> Odbiorcą programu jest geodeta, nie programista, a aktualizacja instaluje się
> u niego sama przy starcie — więc szukam **błędów, które on zobaczy**, a nie
> uwag o stylu.
>
> Na czym się skup — **te punkty dopisujesz pod bieżącą rundę** (skasuj po wydaniu
> razem z częścią B). Poniżej zostaje to, o co warto pytać przy każdej rundzie:
> 1. `app/main.py` — dane operatu bywają starsze niż dzisiejszy szablon: pole
>    skasowane, zmieniony typ, wpis niebędący słownikiem. Czy któraś ścieżka wywala
>    stronę zamiast pominąć dane?
> 2. Szablony HTML — czy znaczniki domykają się przy **każdej** kombinacji danych,
>    a wzorzec do klonowania kart ma dokładnie to samo co karta pierwsza?
> 3. Kontekst stron budowany poza `_widok` — brak jednej zmiennej to w Jinja wyjątek,
>    nie pustka, i strona po cichu leci do zapasowego gołego HTML-a (pułapka 28).
> 4. Cokolwiek jednorazowego — czy gaśnie dopiero po **potwierdzeniu przez
>    użytkownika**, i czy działa **przy pierwszej** aktualizacji, która to wprowadza?
>    (pułapki 7b, 21 i 30 — ta seria kosztowała trzy wydania).
> 5. Cokolwiek, co mierzy okno albo stronę w JS — czy pomiar nie leci, zanim okno ma
>    docelowy rozmiar? Wyszło na przycisku „do góry”: `innerHeight` przy wykonaniu
>    skryptu bywa mniejszy niż po `load`.
> 6. Cokolwiek, co zapamiętuje węzły XML — nie po `id()` obiektu lxml (pułapka 29).
> 7. Testy dołożone w tej rundzie — czy sprawdzają zachowanie, czy tylko to, że kod
>    się wykonał; czy któryś zostawia pliki w prawdziwych `dane/`/`wyniki/`
>    (pułapka 25)?

> Czego **nie** zgłaszać: nazw po polsku (to konwencja projektu), braku typów
> generycznych, sugestii przejścia na framework frontendowy, propozycji drugiego
> generatora PDF — te decyzje są opisane w `CLAUDE.md` wraz z powodami.
>
> Format odpowiedzi: lista znalezisk, każde z `plik:linia`, jednym zdaniem co jest
> nie tak i **konkretnym scenariuszem**, przy jakich danych to wybuchnie. Jeśli
> czegoś nie jesteś pewien, napisz to wprost zamiast zgadywać.

Alternatywa dla całej gałęzi: `/code-review ultra` (uruchamiasz go sam — jest płatny
i nie mogę go odpalić za ciebie).

---

## Po zielonym review

Opis pisze się w stałym kształcie: **same punkty**, w dwóch listach, bez zdań wstępu.
Najwygodniej podać go przez wejście standardowe (`-`), bo wtedy nie trzeba walczyć
z cudzysłowami:

```bat
.venv\Scripts\python narzedzia\wydaj.py "opis dla brata"
```

```bash
.venv/bin/python narzedzia/wydaj.py - <<'OPIS'
Zmiany:
- co działa inaczej niż dotąd

Nowości:
- co doszło
OPIS
```

Numer i `ZMIANY.md` stempluje skrypt — **nie wpisuj ich ręcznie** (oba człony już się
kiedyś pomyliły). Potem `git push`, i dopiero to wysyła nową wersję do brata.

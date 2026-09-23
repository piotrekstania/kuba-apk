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

*(pusto — wydanie 2026.09.23-114 poszło 23.09 z Windowsa. Sprawdzone tam na instalacjach
„jak u brata” z commitów wydań 113 i 112, z prawdziwym Wordem i prawdziwymi blokadami
plików: przejście ze starego `start.bat` na nowy (także podmiana pliku w trakcie pracy —
nic nie doczytane), drugi i trzeci start, aktualizacja przy formatce otwartej w Wordzie,
`pip` bez sieci, brakująca biblioteka, czcionki, kolor po restarcie, lista na pół ekranu,
zmiana numeru operatu i numeru roboty przy plikach zamkniętych i otwartych, pytanie przy
wysokim numerze, „Popraw”/„Usuń” przy otwartym pliku, zapis w trakcie podglądu na
prawdziwym Wordzie, `pytest -m word` 11/11 i testy przeglądarkowe w Chrome na Windowsie)*

**Do sprawdzenia przy następnym wydaniu** (działa dopiero od aktualizacji **po** 114 —
pułapka 7b): na instalacji testowej z wersją 114 otwórz w Wordzie
`szablony\spis_tresci_wzor.docx`, cofnij numer w `WERSJA` i uruchom `start.bat` — na liście
operatów ma stać czerwony pasek z nazwą tego pliku. Po zamknięciu Worda i starcie
aktualizacja przechodzi, a pasek znika.

**Do rozważenia (znalezione w przeglądzie, świadomie niepoprawione):**
1. Sekcja wyczyszczona **i** odznaczona w tym samym zapisie wraca przy ponownym
   zaznaczeniu ze starą treścią (`_dane_wylaczonych` nie odróżni tego od samego
   odznaczenia — przeglądarka nie wysyła wyłączonych pól). Widać to w formularzu,
   więc waga niska; naprawa wymagałaby znacznika z JS przy zmianie wyłączonej sekcji.
2. `wybor_wielokrotny` nie zachowuje zapisanej wartości spoza dzisiejszych opcji
   (filtr jest też w `odczytaj_dane`). Dziś nieosiągalne — wróci przy pierwszej zmianie
   nazwy pozycji spisu treści w `.json`.
3. Jednorazowa luka przy przejściu ze starego `start.bat` (dopisek do pułapki 37).

**Zostało do obejrzenia okiem** (z wydania 112) — tego testy ani przeglądarka nie sprawdzą:
otworzyć **złożony PDF w prawdziwym czytniku** i potwierdzić, że karta, panel stron
i pole „Tytuł” we właściwościach pokazują numer roboty, a plik otwiera się normalnie.
Metadane dopisujemy przy sklejaniu, więc gdyby coś poszło nie tak, ucierpiałby cały
operat, a `pypdf` w testach czyta tylko sam siebie (sprawdzone pypdf-em na Windowsie:
tytuł = numer roboty; panel przeglądarki Claude'a PDF-ów nie wyświetla).

---

## C. Zlecenie review (do wklejenia Fable)

> Zrób przegląd kodu zmian z zakresu `cd4b92d..HEAD` w tym repozytorium
> (`git log --oneline cd4b92d..HEAD`, `git diff cd4b92d..HEAD`) — to wszystko, co
> przyszło po ostatnim wydaniu (`2026.09.23-114`). Kontekst projektu jest w `CLAUDE.md` —
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

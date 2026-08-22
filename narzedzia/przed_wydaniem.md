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
3. Złóż operat (`Złóż PDF operatu`) i sprawdź, że po konwersji **nie został**
   `WINWORD.EXE` w Menedżerze zadań.
4. Poprawianie operatu (`Popraw ten operat`): dane wracają do formularza, numer
   operatu **się nie zmienia**, katalog ten sam, układ kafelków zapamiętany.

---

## B. Co doszło w tej rundzie

Wszystko od ostatniego wydania — numer i skrót commita znajdziesz w `ZMIANY.md`
i `git log`. Dopisuj punkty przy każdej rundzie zmian, kasuj po wydaniu.

Runda znów **czysto ekranowa** — poza jedną zmianą w `app/main.py` (formularz dostaje
datę utworzenia poprawianego operatu). Żaden `.docx` ani ścieżka PDF nie były ruszane.

1. **Szczyt strony operatu**: „Operat: 004/2026”, pod spodem data utworzenia, po prawej
   komplet akcji („Złóż PDF”, „Otwórz katalog”, „Popraw”, „Powiel”, „Usuń”), pod tym
   kreska. Sprawdź przy **zwężonym oknie**, czy pasek zsuwa się pod numer, zamiast
   uciekać poza ekran.
2. **Kasowanie operatu** przeniesione z dołu strony na górę — potwierdzenie ma nadal
   wyskakiwać, a po skasowaniu ma zniknąć katalog.
3. **Szczyt formularza**: przy „Popraw” wygląda jak szczyt strony operatu, przy nowym
   operacie nagłówek to „Nowy operat”. **Górny „Zapisz” musi zapisywać** — stoi poza
   formularzem i wskazuje go atrybutem `form`, więc kliknij go w prawdziwej przeglądarce
   (Edge/Chrome u brata), a nie tylko na dole strony.
4. **Ostrzeżenie o niezapisanych zmianach** nadal wyskakuje przy „Anuluj” i przy
   zamykaniu karty, a po kliknięciu „Zapisz” już nie.
5. **Lista operatów**: akcje jako małe przyciski przy prawej krawędzi, wiersz nie urósł.
   „Otwórz katalog” ma otwierać Eksplorator na wierzchu (pułapka 20) — to jedyna
   z tych rzeczy, której nie da się sprawdzić na Linuksie.
6. **Edytor opisów** (Ustawienia i „Przebieg wykonanych prac”): uchwyt w prawym dolnym
   rogu ma powiększać pole.
7. **Podpisy pól**: „Data zgłoszenia” i „Data zakończenia” zamiast pełnych nazw;
   w wykazach długa wartość (rodzaj budynku wg KŚT) ma być wyśrodkowana także wtedy,
   gdy zawija się na dwie linijki, a użytki wpisane w kilku linijkach mają zostać
   wyrównane do lewej.
8. **Kolumna „Utworzono”** na liście zamiast „Data”.
9. Operat **sprzed** tej rundy (np. z historii) — czy strona i formularz poprawiania
   nadal się otwierają.

---

## C. Zlecenie review (do wklejenia Fable)

> Zrób przegląd kodu zmian z zakresu `40a63b8..HEAD` w tym repozytorium
> (`git log --oneline 40a63b8..HEAD`, `git diff 40a63b8..HEAD`) — to wszystko, co
> przyszło po ostatnim wydaniu (`2026.08.20-100`). Kontekst projektu jest w `CLAUDE.md` —
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
>    skasowane, zmieniony typ, wpis niebędący słownikiem, podpole, którego wtedy
>    nie było. Czy któraś ścieżka wywala stronę zamiast pominąć dane?
> 2. Szablony HTML — czy znaczniki domykają się przy **każdej** kombinacji danych
>    (grupa bez sekcji, sekcja bez wierszy, brak opisu)? Niedomknięta karta wciąga
>    w siebie resztę strony, a testy patrzące na napisy tego nie widzą.
> 3. Kontekst stron budowany poza `_widok` — brak jednej zmiennej to w Jinja wyjątek,
>    nie pustka, i strona po cichu leci do zapasowego gołego HTML-a (pułapka 28).
> 4. Testy dołożone w tej rundzie — czy sprawdzają zachowanie, czy tylko to, że kod
>    się wykonał. Te czytające `style.css` napisami: czy da się je obejść zapisem,
>    który znaczy to samo? Czy któryś zostawia pliki w prawdziwych `dane/`/`wyniki/`?
>
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

```bat
.venv\Scripts\python narzedzia\wydaj.py "opis dla brata"
```

Numer i `ZMIANY.md` stempluje skrypt — **nie wpisuj ich ręcznie** (oba człony już się
kiedyś pomyliły). Potem `git push`, i dopiero to wysyła nową wersję do brata.

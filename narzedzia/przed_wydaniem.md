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

*(pusto — wydanie 2026.08.24-102 poszło 24.08; czerwień całego użytku obejrzana
w DOCX i na PDF z prawdziwego Worda, kontrola sumy przeklikana w siedmiu
przypadkach łącznie z „0," w połowie pisania)*

---

## C. Zlecenie review (do wklejenia Fable)

> Zrób przegląd kodu zmian z zakresu `6683bfa..HEAD` w tym repozytorium
> (`git log --oneline 6683bfa..HEAD`, `git diff 6683bfa..HEAD`) — to wszystko, co
> przyszło po ostatnim wydaniu (`2026.08.24-102`). Kontekst projektu jest w `CLAUDE.md` —
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
>    (grupa bez sekcji, sekcja bez wierszy, brak opisu)? Czy wzorzec do klonowania
>    kart ma dokładnie to samo co karta pierwsza?
> 3. Kontekst stron budowany poza `_widok` — brak jednej zmiennej to w Jinja wyjątek,
>    nie pustka, i strona po cichu leci do zapasowego gołego HTML-a (pułapka 28).
> 4. Cokolwiek, co zapamiętuje węzły XML — nie po `id()` obiektu lxml (pułapka 29):
>    ten sam `id()` bywa po zebraniu śmieci użyty dla innego węzła, a objaw wychodzi
>    dopiero w CI.
> 5. Testy dołożone w tej rundzie — czy sprawdzają zachowanie, czy tylko to, że kod
>    się wykonał; czy któryś zostawia pliki w prawdziwych `dane/`/`wyniki/`?

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

Opis pisze się w stałym kształcie — jedno–dwa zdania, a pod nimi listy. Najwygodniej
podać go przez wejście standardowe (`-`), bo wtedy nie trzeba walczyć z cudzysłowami:

```bat
.venv\Scripts\python narzedzia\wydaj.py "opis dla brata"
```

```bash
.venv/bin/python narzedzia/wydaj.py - <<'OPIS'
Jedno–dwa zdania, o co w tym wydaniu chodzi.

Zmiany:
- co działa inaczej niż dotąd

Nowości:
- co doszło
OPIS
```

Numer i `ZMIANY.md` stempluje skrypt — **nie wpisuj ich ręcznie** (oba człony już się
kiedyś pomyliły). Potem `git push`, i dopiero to wysyła nową wersję do brata.

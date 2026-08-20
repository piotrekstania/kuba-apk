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

Runda **czysto ekranowa**: żaden `.docx`, `app/generator.py` ani ścieżka PDF nie były
ruszane (`git diff --stat 564a6cc..HEAD` — same `main.py`, szablony HTML, CSS i testy).
Word sprawdzasz więc tylko przez stały rytuał z części A, a resztę okiem w przeglądarce:

1. **Strona operatu (`Podgląd`) w kartach z niebieskimi tytułami** — te same co
   w formularzu (`fieldset` + `legend`), tytuł siedzi na górnej kresce, czarnych
   nagłówków „Opis" i „Wpisane dane" już nie ma. Sprawdź, czy któraś karta nie
   połknęła reszty strony (raz już się to zdarzyło przez zgubione `</section>`).
2. **Nagłówek pozycji wykazu w jednej linijce**: `Działka 1: 119/80`, numer pogrubiony.
   Przy wykazie budynku (bez podpola wspólnego) ma zostawać samo `Wykaz 1`.
3. **Tabele wykazów**: nagłówki stanów i wartości wyśrodkowane, pionowa kreska między
   stanem dotychczasowym a nowym. Obejrzyj oba wykazy — z podkolumnami (działka)
   i bez nich (budynek).
4. **Odstępy nad pierwszą kartą**: przyciski → linijka ze ścieżką katalogu → karta
   „Opis" mają być takie same jak między kartami.
5. Operat **sprzed** tej rundy (np. z historii) — czy strona podglądu nadal się
   otwiera i pokazuje stare dane.

---

## C. Zlecenie review (do wklejenia Fable)

> Zrób przegląd kodu zmian z zakresu `564a6cc..HEAD` w tym repozytorium
> (`git log --oneline 564a6cc..HEAD`, `git diff 564a6cc..HEAD`) — to wszystko, co
> przyszło po ostatnim wydaniu (`2026.08.20-99`). Kontekst projektu jest w `CLAUDE.md` —
> przeczytaj go najpierw, zwłaszcza listę pułapek i zasady pracy nad kodem.
> Odpowiadaj po polsku.
>
> Odbiorcą programu jest geodeta, nie programista, a aktualizacja instaluje się
> u niego sama przy starcie — więc szukam **błędów, które on zobaczy**, a nie
> uwag o stylu.
>
> Na czym się skup:
> 1. `app/main.py` — `_wypelnione_sekcje` i `_dane_w_grupach`: dane operatu bywają
>    starsze niż dzisiejszy szablon (pole skasowane, zmieniony typ, wpis niebędący
>    słownikiem, podpole wspólne, którego wtedy nie było). Czy któraś ścieżka wywala
>    stronę operatu zamiast pominąć dane? Interesują mnie zwłaszcza operaty sprzed
>    przebudowy wykazu działki.
> 2. `app/web/templates/dokument.html` — strona operatu przepisana na `fieldset`
>    + `legend`. Czy znaczniki domykają się przy **każdej** kombinacji: grupa bez
>    sekcji, sekcja bez wierszy, wiersz bez podkolumn, brak opisu? Raz już zgubiony
>    `</section>` wsadził całą stronę do środka pierwszej karty i test tego nie łapał.
> 3. `dokument.html` i `formularz.html` — nagłówki `colspan` i podpisy podkolumn:
>    czy liczba komórek w wierszu zgadza się z nagłówkiem przy sekcji **bez**
>    podkolumn (wykaz budynku) i przy sekcji z nimi (wykaz działki)? Wartości
>    atrybutów HTML pisane są `{% if %}`, nie `{{ }}` — Jinja escapuje cudzysłowy
>    i nagłówek rozjeżdżał się po cichu.
> 4. Nagłówek pozycji (`Działka 1: 119/80`) składany z podpól wspólnych — co przy
>    kilku podpolach wspólnych, pustej wartości i wartości z HTML-em w środku?
> 5. `app/main.py` — `wersja_zasobow()` przelicza się teraz w kopii roboczej gita.
>    Czy u brata (bez `.git`) nadal liczy się raz i czy znacznik nie zmienia się
>    przy każdym żądaniu, co kasowałoby cache przeglądarki?
> 6. Testy w `tests/test_sekcje.py`, `test_trasy.py` i `test_notatka.py` — czy
>    sprawdzają zachowanie, czy tylko to, że kod się wykonał. Test odstępów czyta
>    `style.css` napisami: czy da się go obejść zapisem, który znaczy to samo?
>    Przy okazji: czy któryś zostawia po sobie pliki w prawdziwych `dane/`
>    albo `wyniki/`?
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

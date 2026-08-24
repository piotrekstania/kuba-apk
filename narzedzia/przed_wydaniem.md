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

Ta runda **zmienia treść dokumentu**, więc rytuał windowsowy z części A obowiązuje
w całości: `.docx` otwierany w prawdziwym Wordzie i obejrzany na kartce. Formatek nikt
nie ruszał (`git diff b29bcd0..HEAD -- szablony/` pokazuje sam `.json`, i to jedną
rzecz: deklarację `suma_rowna` przy polach PPU).

1. **Czerwień w wykazie działki obejmuje cały użytek.** Wypełnij działkę tak, żeby
   w użytku zmieniła się **tylko jedna** wartość — np. OFU `R` → `R`+`B` przy tej samej
   klasie `IIIb` i zmienionym PPU. W dokumencie **wszystkie cztery** wartości stanu
   nowego (OFU, OZU, OZK, PPU) mają być czerwone i pogrubione, także ta niezmieniona.
   To jest ta poprawka, którą Kuba nanosił dotąd ręcznie.
2. **Numer działki i pole powierzchni zostają czarne**, jeśli się nie zmieniły —
   czerwienieje użytek, a nie cała tabela.
3. **Wykaz budynku bez zmian**: tam w wierszu stoi jedna para, więc czerwienieje sam
   zmieniony atrybut. Wygeneruj oba wykazy w jednym operacie i porównaj.
4. **Kontrola sumy PPU** w formularzu, pod tabelą stanów: zielono, gdy suma zgadza się
   z polem powierzchni, czerwono z różnicą, gdy nie. Sprawdź **kropkę i przecinek**
   (`0.3110` i `0,3110`) — brat pisze inaczej niż autor — oraz to, że przy wpisywaniu
   („0,”) nie wyskakuje „nie rozumiem”.
5. **Puste PPU przy wypełnionym polu powierzchni** ma być czerwone; obie rzeczy puste —
   cicho (świeżo dołożona karta nie ma straszyć).
6. **Druga działka**: dołóż kartę przyciskiem i sprawdź, że każda liczy swoje, a po
   „Popraw” komunikaty wracają policzone od danych z bazy.
7. Kontrola **nie blokuje** zapisu — zapisz operat z niezgodną sumą i sprawdź, że
   dokument powstał. To ta sama zasada co przy numerze działki z ULDK.
8. Przy okazji, jeśli nie było sprawdzane po 101: **„Otwórz katalog” z listy** — czy
   Eksplorator wychodzi na wierzch (pułapka 20).

---

## C. Zlecenie review (do wklejenia Fable)

> Zrób przegląd kodu zmian z zakresu `b29bcd0..HEAD` w tym repozytorium
> (`git log --oneline b29bcd0..HEAD`, `git diff b29bcd0..HEAD`) — to wszystko, co
> przyszło po ostatnim wydaniu (`2026.08.22-101`). Kontekst projektu jest w `CLAUDE.md` —
> przeczytaj go najpierw, zwłaszcza listę pułapek i zasady pracy nad kodem.
> Odpowiadaj po polsku.
>
> Odbiorcą programu jest geodeta, nie programista, a aktualizacja instaluje się
> u niego sama przy starcie — więc szukam **błędów, które on zobaczy**, a nie
> uwag o stylu.
>
> Na czym się skup:
> 1. `app/generator.py` — `_zmienione_w_wierszu` i grupowanie kluczy po wierszu formatki
>    (`_wiersz_tabeli`, próg „więcej niż dwa klucze”). Czy da się doprowadzić do
>    zaczerwienienia czegoś, co się nie zmieniło: scalone komórki, wiersz z trzema
>    parami, dwa różne wykazy w jednym pliku, pętla obejmująca cały wiersz? Czy wykaz
>    budynku na pewno zachowuje się jak dotąd?
> 2. `formularz.html` — kontrola sumy PPU (JS): parsowanie kropki i przecinka, wpis
>    w połowie pisania (`0,`), rozdzielanie enterem/spacją/średnikiem, wartości ujemne
>    i bardzo długie listy, klonowanie karty, „Popraw” z danymi z bazy. Czy komunikat
>    może trafić do **cudzej** karty albo cudzego stanu? Czy tolerancja 0,00005 nie daje
>    fałszywego „zgadza się” przy danych z czterema miejscami po przecinku?
> 3. `formularz.html` + `.json` — `suma_rowna` i wiersz `kontrola-sum`: czy liczba
>    komórek zgadza się z nagłówkiem tabeli przy sekcji **bez** podkolumn i czy wiersz
>    nie pojawia się w sekcji, która nie ma czego kontrolować? Czy wzorzec do klonowania
>    ma dokładnie to samo co karta pierwsza?
> 4. `app/main.py` — dane operatu bywają starsze niż dzisiejszy szablon: pole skasowane,
>    zmieniony typ, wpis niebędący słownikiem. Czy któraś ścieżka wywala stronę zamiast
>    pominąć dane?
> 5. Testy dołożone w tej rundzie — czy sprawdzają zachowanie, czy tylko to, że kod się
>    wykonał; czy któryś zostawia pliki w prawdziwych `dane/`/`wyniki/`? Kontrola sumy
>    jest w JS, więc pytest sprawdza samo podpięcie — czy da się je zepsuć tak, żeby
>    testy nadal przechodziły?

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

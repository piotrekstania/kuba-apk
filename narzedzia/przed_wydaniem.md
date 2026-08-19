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

*(pusto — wydanie 2026.08.19-95 poszło 19.08; wyrównanie do góry sprawdzone
na PDF z prawdziwego Worda przy poprawce)*

---

## C. Zlecenie review (do wklejenia Fable)

> Zrób przegląd kodu zmian z zakresu `c9c66c4..HEAD` w tym repozytorium
> (`git log --oneline c9c66c4..HEAD`, `git diff c9c66c4..HEAD`) — to wszystko, co
> przyszło po ostatnim wydaniu (`2026.08.19-92`). Kontekst projektu jest w `CLAUDE.md` —
> przeczytaj go najpierw, zwłaszcza listę pułapek i zasady pracy nad kodem.
> Odpowiadaj po polsku.
>
> Odbiorcą programu jest geodeta, nie programista, a aktualizacja instaluje się
> u niego sama przy starcie — więc szukam **błędów, które on zobaczy**, a nie
> uwag o stylu.
>
> Na czym się skup:
> 1. `app/generator.py` — `sformatuj_pod_znaczniki`, `_zaznacz_zmiany` i `_zmienione`:
>    nowy mechanizm zamienia pola wykazów na `RichText` (czerwień przy zmienionym stanie
>    nowym). Kluczowe pytanie: czy `RichText` może trafić do formatki, która w tym
>    miejscu ma **zwykłe** `{{ }}` — bo taki plik Word odmawia otworzyć. Sprawdź też,
>    co się dzieje, gdy w danych siedzi liczba, `None` albo lista zamiast napisu,
>    i czy oryginalny kontekst na pewno zostaje napisami dla kolejnej formatki.
> 2. `narzedzia/utworz_wykaz_dzialki.py` — buduje formatkę działki z formatki budynku,
>    klonując komórki spod ustalonych indeksów wierszy. Co się stanie, gdy brat przyśle
>    wykaz budynku o innej liczbie wierszy? Czy skrypt powie to wprost, czy zbuduje
>    dokument bez sensu?
> 3. `app/szablony.py` — `podpola_wspolne` i `wiersze_sekcji`: co przy niepełnym albo
>    sprzecznym opisie `.json` (podpole bez `wiersz`, kolumna spoza `kolumny`,
>    `opcje` wskazujące nieistniejącą listę)?
> 4. `app/main.py` — `_wypelnione_sekcje`: dane z bazy bywają starsze niż dzisiejszy
>    szablon (pole skasowane, zmieniony typ, wpis niebędący słownikiem). Czy któraś
>    ścieżka wywala stronę operatu zamiast pominąć dane? Zwróć uwagę na operaty sprzed
>    przebudowy wykazu działki — mają dane pod kluczami, których już nie ma.
> 5. `app/web/templates/formularz.html` — numeracja pól przy dokładaniu i usuwaniu kart
>    (`sek__<pole>__<nr>__<podpole>`), nowe pola wielolinijkowe i podpola wspólne,
>    strażnik `beforeunload`. Czy da się doprowadzić do stanu, w którym dane trafiają
>    pod zły indeks albo giną?
> 6. Testy w `tests/test_sekcje.py` — czy sprawdzają zachowanie, czy tylko to, że kod
>    się wykonał. Przy okazji: czy któryś zostawia po sobie pliki w prawdziwych
>    `dane/` albo `wyniki/`?
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

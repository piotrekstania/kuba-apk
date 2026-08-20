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

*(pusto — wydanie 2026.08.20-99 poszło 20.08; przeprowadzka oznaczeń użytków
pod punkt 2 zaakceptowana przez użytkownika na PDF z prawdziwego Worda)*

---

## C. Zlecenie review (do wklejenia Fable)

> Zrób przegląd kodu zmian z zakresu `1fade12..HEAD` w tym repozytorium
> (`git log --oneline 1fade12..HEAD`, `git diff 1fade12..HEAD`) — to wszystko, co
> przyszło po ostatnim wydaniu (`2026.08.20-97`). Kontekst projektu jest w `CLAUDE.md` —
> przeczytaj go najpierw, zwłaszcza listę pułapek i zasady pracy nad kodem.
> Odpowiadaj po polsku.
>
> Odbiorcą programu jest geodeta, nie programista, a aktualizacja instaluje się
> u niego sama przy starcie — więc szukam **błędów, które on zobaczy**, a nie
> uwag o stylu.
>
> Na czym się skup:
> 1. `narzedzia/utworz_wykaz_dzialki.py` — tabela wykazu działki zbudowana od nowa:
>    dwa piętra nagłówka, `gridSpan` na stanach, `vMerge` na L.p. i opisie, krawędzie
>    ustawiane po zbudowaniu wiersza (`_domknij_prawa_krawedz`). Czy siatka `tblGrid`
>    zgadza się z liczbą komórek w każdym wierszu, czy scalenia są poprawne wg schematu
>    OOXML i czy suma szerokości nie przekracza szerokości tekstu? To plik, który
>    LibreOffice składa bez mrugnięcia, a Word potrafi odrzucić. Skrypt klonuje komórki
>    spod **ustalonych indeksów** wierszy formatki budynku — co się stanie, gdy brat
>    przyśle wykaz budynku o innej liczbie wierszy: powie to wprost czy zbuduje
>    dokument bez sensu?
> 2. `app/generator.py` — `wyrownaj_komorki_stanow`: dopisuje `w:vAlign` do komórek
>    **gotowego** dokumentu, po renderze i przed zapisem, na podstawie liczby linijek
>    w treści. Kolumny stanów liczy teraz od lewej (`KOLUMNY_OPISU = 2`) — czy to trafia
>    w te komórki, o które chodzi, także przy scaleniach pionowych i `gridSpan`,
>    w tabeli o innej liczbie kolumn i w dokumencie bez tabel? Czy kolejność w `tcPr`
>    zostaje poprawna, gdy elementu wcześniej nie było?
> 3. `app/generator.py` — `sformatuj_pod_znaczniki`, `_zaznacz_zmiany` i `_zmienione`:
>    mechanizm zamienia pola wykazów na `RichText` (czerwień przy zmienionym stanie
>    nowym). Kluczowe pytanie: czy `RichText` może trafić do formatki, która w tym
>    miejscu ma **zwykłe** `{{ }}` — bo taki plik Word odmawia otworzyć. Sprawdź też,
>    co się dzieje, gdy w danych siedzi liczba, `None` albo lista zamiast napisu,
>    i czy oryginalny kontekst na pewno zostaje napisami dla kolejnej formatki.
> 4. `app/szablony.py` — `podpola_wspolne` i `wiersze_sekcji` (nowy podział na
>    `podkolumny`): co przy niepełnym albo sprzecznym opisie `.json` — podpole bez
>    `wiersz`, kolumna spoza `kolumny`, `podkolumna` spoza `podkolumny`, wiersz mieszany
>    (część podpól z podkolumną, część bez), `opcje` wskazujące nieistniejącą listę?
>    Czy któryś z tych przypadków gubi dane po cichu albo wywala stronę?
> 4a. `app/web/templates/formularz.html` i `dokument.html` — nagłówki `colspan` i podpisy
>    podkolumn. Czy liczba komórek w wierszu zgadza się z nagłówkiem przy sekcji **bez**
>    podkolumn (wykaz budynku) i przy sekcji z nimi?
> 5. `app/main.py` — `_wypelnione_sekcje`: dane z bazy bywają starsze niż dzisiejszy
>    szablon (pole skasowane, zmieniony typ, wpis niebędący słownikiem). Czy któraś
>    ścieżka wywala stronę operatu zamiast pominąć dane? Zwróć uwagę na operaty sprzed
>    przebudowy wykazu działki — mają dane pod kluczami, których już nie ma.
> 6. `app/web/templates/formularz.html` — numeracja pól przy dokładaniu i usuwaniu kart
>    (`sek__<pole>__<nr>__<podpole>`), nowe pola wielolinijkowe i podpola wspólne,
>    strażnik `beforeunload`. Czy da się doprowadzić do stanu, w którym dane trafiają
>    pod zły indeks albo giną?
> 7. Testy w `tests/test_sekcje.py` — czy sprawdzają zachowanie, czy tylko to, że kod
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

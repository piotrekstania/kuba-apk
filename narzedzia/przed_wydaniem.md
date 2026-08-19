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

## B. Co doszło w tej rundzie (wszystko od wydania `2026.08.14-90`,
czyli `git log --oneline 3a23109..HEAD`)

### Wykazy zmian danych ewidencyjnych w formularzu

- [ ] Karta **„Wykaz zmian danych budynku”**: `+ dodaj kolejny wykaz` dokłada komplet
      pól, krzyżyk usuwa, numeracja kart idzie po kolei po każdym usunięciu.
- [ ] Dwa wykazy → **jeden plik, dwie strony**, drugi wykaz od nowej strony,
      a po ostatnim **nie ma pustej kartki**.
- [ ] Karta **„Wykaz zmian danych działki”**: kolejne działki to **kolejne wiersze
      jednej tabeli**, L.p. nadaje program.
- [ ] Wykaz działki: podpis stoi **linijkę niżej** pod tabelą (nie przyklejony),
      dane w tabeli **nie są pogrubione**, pogrubiony zostaje sam nagłówek.
- [ ] Pole **„Identyfikator działki”** wchodzi do nagłówka za kropkę:
      `[247301_1.0112.1765/311]`. Puste zostawia samą kropkę.
- [ ] Zaznaczony wykaz, ale **żadne pole niewypełnione** → plik w ogóle nie powstaje,
      a na stronie operatu stoi zdanie, dlaczego go nie ma.
- [ ] Przy trzech i więcej działkach tabela nadal mieści się na jednej stronie,
      a nagłówek powtarza się na kolejnej (`w:tblHeader`).

### Spis treści jako włącznik dokumentów

- [ ] Odznaczenie „Sprawozdanie techniczne” w spisie → pola sprawozdania wyszarzone
      **i plik nie powstaje**.
- [ ] Nigdzie w formularzu **nie ma już checkboxów „Wygeneruj”** przy dokumentach.
- [ ] Na stałe zaznaczony zostaje wyłącznie „Spis treści”.

### Strona operatu

- [ ] Przy wykazach widać **wpisane wiersze**, a nie „2 wierszy”; każdy wykaz ma
      nagłówek („Wykaz 2”, „Działka 2”), puste atrybuty są pominięte.

### Ostrzeżenie o niezapisanych zmianach

- [ ] Wpisz cokolwiek → **F5**, **Alt+←** i **zamknięcie karty** pytają, czy wyjść.
      „Zostań na stronie” wraca do wypełnionego formularza.
- [ ] Po kliknięciu **Generuj dokument** / **Zapisz poprawki** okienko **nie** wyskakuje.
- [ ] Przy **Anuluj** wyskakuje (celowo — stoi tuż obok zapisu).
- [ ] Samo wejście na formularz i wyjście bez dotykania niczego **nie pyta**.
- [ ] Sprawdź w tej przeglądarce, w której brat naprawdę pracuje.

---

## C. Zlecenie review (do wklejenia Fable)

> Zrób przegląd kodu zmian z zakresu `3a23109..HEAD` w tym repozytorium
> (`git log --oneline 3a23109..HEAD`, `git diff 3a23109..HEAD`) — to wszystko,
> co przyszło po ostatnim wydaniu. Kontekst
> projektu jest w `CLAUDE.md` — przeczytaj go najpierw, zwłaszcza listę pułapek
> i zasady pracy nad kodem. Odpowiadaj po polsku.
>
> Odbiorcą programu jest geodeta, nie programista, a aktualizacja instaluje się
> u niego sama przy starcie — więc szukam **błędów, które on zobaczy**, a nie
> uwag o stylu.
>
> Na czym się skup:
> 1. `app/main.py` — `_wypelnione_sekcje` i `_dane_w_grupach`: dane z bazy bywają
>    starsze niż dzisiejszy szablon (pole skasowane, zmieniony typ, wpis niebędący
>    słownikiem). Czy któraś ścieżka wywala stronę operatu zamiast pominąć dane?
> 2. `app/szablony.py` — `wiersze_sekcji` i nowe pola `Pole`: co się dzieje przy
>    niepełnym albo sprzecznym opisie `.json` (podpole bez `wiersz`, kolumna,
>    której nie ma w `kolumny`)?
> 3. `app/web/templates/formularz.html` — JS: numeracja pól przy dokładaniu
>    i usuwaniu kart (`sek__<pole>__<nr>__<podpole>`), oraz strażnik `beforeunload`
>    na końcu skryptu. Czy da się doprowadzić do stanu, w którym dane z formularza
>    trafiają pod zły indeks albo giną?
> 3a. `tests/conftest.py` — fixtury `bez_prawdziwej_bazy` i `baza`: czy zostaje jeszcze
>    jakaś ścieżka, którą test bez `srodowisko` dosięga prawdziwych `dane/` albo
>    `wyniki/` autora?
> 4. Reguła pomijania pustego dokumentu (`"wymaga"` w `.json`) — czy pomija dokładnie
>    to, co ma, i czy użytkownik zawsze dowiaduje się, że pliku nie ma?
> 5. Testy w `tests/test_sekcje.py` i `tests/test_trasy.py` — czy sprawdzają
>    zachowanie, czy tylko to, że kod się wykonał.
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

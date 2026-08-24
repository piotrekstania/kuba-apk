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

*(pusto — wydanie 2026.08.24-105 poszło 24.08; okno nowości bierze opis
z ZMIANY.md — użytkownik sprawdza na swojej kopii, czy po aktualizacji do -105
okno staje i ma listy punktów)*

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
> Na czym się skup:
> 1. `formularz.html` — `podepnijSprawdzanieDzialki`: podpinanie per pole, znacznik
>    `data-sprawdzanie`, listener na obrębie zakładany raz na pole (przy dziesięciu
>    kartach jest ich dziesięć — czy to gdzieś boli?), odrzucanie odpowiedzi na
>    nieaktualne pytanie. Czy komunikat może trafić do cudzej karty? Czy klon karty
>    dostaje wszystko, co ma pierwsza?
> 2. `app/zmiany.py` — `rozbierz_opis`: nagłówek listy rozpoznawany po dwukropku
>    i długości, punkt po myślniku, linijka bez myślnika doklejana do poprzedniego
>    punktu. Co przy opisie z samymi myślnikami bez nagłówka, z dwukropkiem w środku
>    zdania, z pustym punktem („- ”), z myślnikiem w treści punktu? Czy sto starych
>    wpisów na pewno czyta się jak dotąd?
> 3. `app/main.py` — `_co_nowego` i `index.html`: znacznik kasuje się przy odczycie,
>    więc okno ma się pokazać **raz**. Czy da się doprowadzić do sytuacji, w której
>    zniknie, zanim ktokolwiek je zobaczy (błąd renderu strony głównej, przekierowanie,
>    drugie okno przeglądarki otwarte równolegle)?
> 4. `<dialog>` + `showModal()` — czy strona działa, gdy skrypt się nie wykona
>    (okno zostanie zamknięte, ale treść ukryta?), i czy „OK” w `<form method="dialog">`
>    nie wysyła przypadkiem formularza operatu?
> 5. `narzedzia/wydaj.py` i `zbuduj_zmiany.py` — opis wielolinijkowy z wejścia
>    standardowego: puste wejście, sam numer bez opisu, BOM, znaki `\r\n` z Windowsa.
>    Czy `ZMIANY.md` po przebudowie zgadza się z `WERSJA` co do znaku?
> 6. Testy dołożone w tej rundzie — czy sprawdzają zachowanie, czy tylko to, że kod
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

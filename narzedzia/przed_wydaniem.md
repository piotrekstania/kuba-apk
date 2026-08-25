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

*(pusto — wydanie 2026.08.25-112 poszło 25.08. Sprawdzone w przeglądarce: kółko „do
góry” nie koliduje z dolnym paskiem akcji przy 1280, 768 ani przy szerokości telefonu,
na krótkiej stronie głównej go nie ma, a na formularzu (3647 px) jest i wraca na szczyt)*

**Zostało do obejrzenia okiem** — tego testy ani przeglądarka nie sprawdzą:
otworzyć **złożony PDF w prawdziwym czytniku** i potwierdzić, że karta, panel stron
i pole „Tytuł” we właściwościach pokazują numer roboty, a plik otwiera się normalnie.
Metadane dopisujemy przy sklejaniu, więc gdyby coś poszło nie tak, ucierpiałby cały
operat, a `pypdf` w testach czyta tylko sam siebie.

---

## C. Zlecenie review (do wklejenia Fable)

> Zrób przegląd kodu zmian z zakresu `cdd17c4..HEAD` w tym repozytorium
> (`git log --oneline cdd17c4..HEAD`, `git diff cdd17c4..HEAD`) — to wszystko, co
> przyszło po ostatnim wydaniu (`2026.08.24-111`). Kontekst projektu jest w `CLAUDE.md` —
> przeczytaj go najpierw, zwłaszcza listę pułapek i zasady pracy nad kodem.
> Odpowiadaj po polsku.
>
> Odbiorcą programu jest geodeta, nie programista, a aktualizacja instaluje się
> u niego sama przy starcie — więc szukam **błędów, które on zobaczy**, a nie
> uwag o stylu.
>
> Na czym się skup:
> 1. `app/pdf.py` — `polacz_pdf` dopisuje `/Title` do gotowego PDF-a. Czy `add_metadata`
>    nie gubi tego, co pypdf zapisuje samo, i czy nie psuje pliku przy dziwnych znakach
>    w numerze roboty (ukośnik, apostrof, spacje, znaki spoza ASCII)? Co przy pustym
>    tytule i przy operacie bez numeru roboty?
> 2. `app/web/templates/dokument.html` — makro `akcje_operatu()` woła się dwa razy, więc
>    na stronie są **dwa** formularze kasowania i dwa „Otwórz katalog”. Czy nie powstają
>    zdublowane identyfikatory, czy potwierdzenie działa w obu i czy nic w JS-ie nie
>    zakłada, że taki formularz jest jeden?
> 3. `base.html` — przycisk „do góry”: widoczność liczona z długości strony (bez
>    zdarzenia `scroll`, bo bywa nieodpalane). Czy da się doprowadzić do sytuacji,
>    w której przycisk zasłania coś klikalnego — wąskie okno, strona krótsza po
>    zwinięciu sekcji, telefon? Czy `hidden` na `<button>` na pewno go chowa
>    (pułapka 17: reguła `display` przebijała `[hidden]`)?
> 4. `historia.html` — kolor przy zainstalowanej wersji zamiast plakietki: co, gdy
>    `ZMIANY.md` nie ma wpisu dla uruchomionej wersji (dziura w historii)?
> 5. Testy dołożone w tej rundzie — czy sprawdzają zachowanie, czy tylko to, że kod
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

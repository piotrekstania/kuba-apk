"""Wypełnianie szablonu .docx danymi z formularza."""
from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime
from pathlib import Path
from typing import Any

from docxtpl import DocxTemplate, RichText

from . import db, operaty, teryt
from .szablony import SUFIKS_JEST, Szablon
from .tekst import na_richtext, na_zwykly_tekst

MIESIACE = ["stycznia", "lutego", "marca", "kwietnia", "maja", "czerwca", "lipca",
            "sierpnia", "września", "października", "listopada", "grudnia"]


# Znaki, których rozkład NFKD nie rusza, bo nie są „litera + znak diakrytyczny”,
# tylko osobnymi literami alfabetu. Bez tej tablicy wypadały z nazwy bez śladu:
# „Sułkowice” robiło się „Sukowice”, a „Łódź” — „odz”.
PODMIANY_LITER = str.maketrans({
    "ł": "l", "Ł": "L", "đ": "d", "Đ": "D", "ø": "o", "Ø": "O",
    "ß": "ss", "æ": "ae", "Æ": "Ae", "œ": "oe", "Œ": "Oe",
})


def _bez_ogonkow(tekst: str) -> str:
    tekst = tekst.translate(PODMIANY_LITER)
    return "".join(z for z in unicodedata.normalize("NFKD", tekst) if not unicodedata.combining(z))


def bezpieczna_nazwa(tekst: str) -> str:
    """Nazwa pliku bezpieczna również na Windowsie."""
    tekst = _bez_ogonkow(tekst).replace("/", "-").replace("\\", "-")
    tekst = re.sub(r"[^A-Za-z0-9 ._-]", "", tekst).strip(" .")
    tekst = re.sub(r"\s+", "_", tekst)
    return tekst[:120] or "dokument"


def data_slownie(wartosc: str | date) -> str:
    """'2026-07-31' -> '31 lipca 2026 r.' Puste/nieznane zwraca bez zmian."""
    if isinstance(wartosc, str):
        try:
            wartosc = datetime.strptime(wartosc.strip(), "%Y-%m-%d").date()
        except ValueError:
            return wartosc
    return f"{wartosc.day} {MIESIACE[wartosc.month - 1]} {wartosc.year} r."


def data_pl(wartosc: str) -> str:
    """'2026-07-31' -> '31.07.2026'."""
    try:
        return datetime.strptime(wartosc.strip(), "%Y-%m-%d").strftime("%d.%m.%Y")
    except (ValueError, AttributeError):
        return wartosc


def pola_teryt(klucz: str, wybor: dict[str, str]) -> dict[str, str]:
    """Z wybranych identyfikatorów robi komplet tagów do wstawienia w Wordzie.

    Dla pola `polozenie` powstają m.in. `polozenie_gmina`, `polozenie_gmina_teryt`,
    `polozenie_obreb`, `polozenie_obreb_teryt` — nazwa i identyfikator osobno, bo
    w operacie potrzebne są oba.
    """
    wynik: dict[str, str] = {}
    opis: list[str] = []

    for poziom in ("wojewodztwo", "powiat", "gmina"):
        jednostka = teryt.jednostka(wybor.get(poziom, ""))
        wynik[f"{klucz}_{poziom}"] = jednostka["nazwa"] if jednostka else ""
        wynik[f"{klucz}_{poziom}_teryt"] = jednostka["id"] if jednostka else ""

    obreb = teryt.obreb(wybor.get("obreb", ""))
    wynik[f"{klucz}_obreb"] = obreb["nazwa"] if obreb else ""
    wynik[f"{klucz}_obreb_teryt"] = obreb["id"] if obreb else ""
    # sam czterocyfrowy numer obrębu — w operatach cytuje się często tylko jego
    wynik[f"{klucz}_obreb_numer"] = obreb["id"].rpartition(".")[2] if obreb else ""

    if wynik[f"{klucz}_obreb"]:
        opis.append(f"obręb {wynik[f'{klucz}_obreb']} ({wynik[f'{klucz}_obreb_teryt']})")
    if wynik[f"{klucz}_gmina"]:
        opis.append(f"gmina {wynik[f'{klucz}_gmina']}")
    if wynik[f"{klucz}_powiat"]:
        opis.append(f"powiat {wynik[f'{klucz}_powiat']}")
    if wynik[f"{klucz}_wojewodztwo"]:
        opis.append(f"województwo {wynik[f'{klucz}_wojewodztwo']}")
    wynik[klucz] = ", ".join(opis)
    return wynik


def przygotuj_kontekst(szablon: Szablon, dane: dict[str, Any], ustawienia: dict[str, str],
                       rezerwacje: list[tuple[str, int, int]] | None = None) -> dict[str, Any]:
    """Łączy dane z formularza, dane stałe i wartości wyliczane automatycznie.

    Do `rezerwacje` (jeśli podana) dopisują się pobrane numery jako (licznik, rok, numer).
    Dzięki temu `generuj` potrafi je oddać, gdy wypełnianie szablonu się nie uda.
    """
    dzis = date.today()
    kontekst: dict[str, Any] = dict(ustawienia)     # dane stałe (geodeta, uprawnienia, firma)
    kontekst.update(dane)

    for pole in szablon.pola:
        if pole.typ == "auto_numer" and not kontekst.get(pole.klucz):
            nazwa_licznika = szablon.licznik or szablon.id
            numer = db.nastepny_numer(nazwa_licznika, dzis.year)
            if rezerwacje is not None:
                rezerwacje.append((nazwa_licznika, dzis.year, numer))
            wzor = pole.domyslnie or "{numer}/{rok}"
            kontekst[pole.klucz] = wzor.format(numer=numer, numer3=f"{numer:03d}", rok=dzis.year)
        elif pole.typ == "wybor_wielokrotny" and pole.wzor_wartosci:
            # Zaznaczone pozycje przepuszczone przez wzorzec, np. „{nr_roboty}-{opcja}.gml”
            # daje listę nazw plików GML oddawanych do ośrodka. Wzorzec siedzi w .json,
            # więc zmiana konwencji nazw nie wymaga ruszania programu.
            class _Luzny(dict):
                def __missing__(self, klucz):     # brak pola we wzorcu nie może nic wywalić
                    return ""
            wybrane = kontekst.get(pole.klucz) or []
            kontekst[f"{pole.klucz}_pliki"] = [
                pole.wzor_wartosci.format_map(_Luzny(kontekst, opcja=opcja))
                for opcja in wybrane]
        elif pole.typ == "teryt":
            wybor = kontekst.get(pole.klucz)
            kontekst.update(pola_teryt(pole.klucz, wybor if isinstance(wybor, dict) else {}))
        elif pole.typ == "date" and kontekst.get(pole.klucz):
            # do dokumentu idzie format polski, ale surową datę zostawiamy pod _iso
            kontekst[f"{pole.klucz}_iso"] = kontekst[pole.klucz]
            kontekst[f"{pole.klucz}_slownie"] = data_slownie(kontekst[pole.klucz])
            kontekst[pole.klucz] = data_pl(kontekst[pole.klucz])

    # Pola z formatowaniem trzymamy jako fragment HTML, a do Worda idą jako `RichText`,
    # czyli sformatowane biegi tekstu. Znacznik w formatce **musi** wtedy mieć postać
    # `{{r pole }}` — i odwrotnie: skoro ma, to tu zawsze musi trafić RichText, także
    # pusty. Zwykły napis wjechałby w to miejsce bez ucieczek i pierwszy znak `<`
    # w opisie rozwaliłby plik.
    #
    # `<klucz>_jest` ustawiamy **tutaj**, zanim wartość przestanie być napisem: pusty
    # `RichText` jest prawdziwy jak każdy obiekt, więc pętla niżej uznałaby, że opis
    # jest zawsze — i formatka przestałaby kiedykolwiek pisać „brak”.
    for pole in szablon.pola:
        if pole.formatowanie:
            kontekst[f"{pole.klucz}{SUFIKS_JEST}"] = bool(
                na_zwykly_tekst(str(kontekst.get(pole.klucz) or "")))

    # `<klucz>_jest` dla każdego pola: czy brat cokolwiek tam wpisał. Formatka pyta o to
    # w `{%p if ... %}`, żeby wybrać między treścią a słowem „brak” — a skoro odpowiedź
    # widać po samej wartości, nie ma po co trzymać na to osobnego checkboxa w formularzu
    # (miał go „Opis przebiegu” i był to jeden klik na darmo). Liczymy **po** pętli wyżej,
    # bo daty są tam podmieniane na format polski, a pusta data pusta zostaje.
    for pole in szablon.pola:
        kontekst.setdefault(f"{pole.klucz}{SUFIKS_JEST}", bool(kontekst.get(pole.klucz)))

    kontekst.setdefault("data_dzisiaj", dzis.strftime("%d.%m.%Y"))
    kontekst.setdefault("data_dzisiaj_slownie", data_slownie(dzis))
    kontekst.setdefault("rok", str(dzis.year))
    return kontekst


def nazwa_pliku(szablon: Szablon, kontekst: dict[str, Any]) -> str:
    class Luzny(dict):
        def __missing__(self, klucz):    # brak pola we wzorcu nie może wywalić generowania
            return ""
    baza = szablon.wzor_nazwy.format_map(Luzny(kontekst, id_szablonu=szablon.id))
    return bezpieczna_nazwa(baza)


def sformatuj_pod_znaczniki(dokument: DocxTemplate, kontekst: dict[str, Any]) -> dict[str, Any]:
    """Zamienia pola z formatowaniem na `RichText`, biorąc krój i rozmiar **z formatki**.

    Sygnałem jest sam znacznik: `{{r pole }}` w pliku .docx znaczy „tu ma wejść
    sformatowany tekst". Szukamy go w dokumencie, odczytujemy ustawienia biegu, w którym
    stoi, i takie same nadajemy wstawianym biegom — dzięki temu opis wygląda jak tekst
    obok, a nie jak wklejka innym krojem.

    Robimy to **per dokument**, a nie raz w `przygotuj_kontekst`, bo ten sam kontekst
    wypełnia kilka formatek i każda może mieć w tym miejscu inną czcionkę. Kontekst
    zwracamy jako kopię — oryginał zostaje napisami, więc kolejny dokument dostanie to,
    co swoje.
    """
    from docx.oxml.ns import qn

    # Bez tego `dokument.docx` jest `None` — plik wczytuje się dopiero przy renderowaniu
    # (ta sama pułapka co przy `get_xml()`). `reload=False`, żeby nie porzucić tego,
    # co docxtpl zdążył już wczytać.
    dokument.init_docx(reload=False)
    gotowy = dict(kontekst)
    w_petli: dict[str, tuple[str, int]] = {}
    for akapit in dokument.docx.element.body.iter(qn("w:p")):
        biegi = list(akapit.iter(qn("w:r")))
        tekst_akapitu = "".join(w.text or "" for b in biegi for w in b.iter(qn("w:t")))
        for nazwa in re.findall(r"\{\{r\s+([\w.]+)", tekst_akapitu):
            krój, rozmiar = _ustawienia_biegu(biegi, qn)
            if "." in nazwa:
                # `{{r dzialka.numer_nowy }}` — pole wewnątrz pętli po liście słowników.
                # Nie wiemy tutaj, po której liście chodzi pętla, więc zapamiętujemy sam
                # klucz i podmieniamy go wszędzie, gdzie występuje (patrz `_zaznacz_zmiany`).
                w_petli[nazwa.split(".", 1)[1]] = (krój, rozmiar)
                continue
            wartosc = kontekst.get(nazwa)
            if not isinstance(wartosc, str):
                continue
            gotowy[nazwa] = na_richtext(wartosc, krój, rozmiar)
    if w_petli:
        gotowy = _zaznacz_zmiany(gotowy, w_petli)
    return gotowy


# Stan nowy różny od dotychczasowego wyróżniamy w wykazie **na czerwono i grubo** —
# tak brat zaznaczał to dotąd ręcznie w Wordzie, a ośrodek po tym czyta, co się zmieniło.
# Czerwień jest ta sama co numeru roboty w nagłówku formatek.
CZERWONY = "FF0000"
SUFIKS_NOWY = "_nowy"
SUFIKS_DOTYCHCZAS = "_dotychczas"


def _zmienione(wpis: dict[str, Any], klucz: str) -> bool:
    """Czy to stan nowy, który różni się od dotychczasowego?

    Puste pole dotychczasowe też jest różnicą (wpisano coś, czego nie było), ale puste
    pole nowe nie — nie ma czego malować, a brak wpisu nie znaczy „wykreślono”.
    """
    if not klucz.endswith(SUFIKS_NOWY):
        return False
    nowa = str(wpis.get(klucz, "") or "").strip()
    if not nowa:
        return False
    poprzednia = wpis.get(klucz[: -len(SUFIKS_NOWY)] + SUFIKS_DOTYCHCZAS, "")
    return nowa != str(poprzednia or "").strip()


def _zaznacz_zmiany(kontekst: dict[str, Any],
                    w_petli: dict[str, tuple[str, int]]) -> dict[str, Any]:
    """Zamienia pola z list (wykazy) na `RichText`, czerwieniąc zmienione stany nowe.

    Kopiujemy listy i słowniki, zamiast poprawiać je w miejscu: ten sam kontekst wypełnia
    kilka formatek, a `RichText` w miejscu zwykłego `{{ }}` daje plik, którego Word nie
    otworzy. Podmieniamy **tylko** klucze, dla których ta formatka ma `{{r }}` — czyli
    dokładnie tam, gdzie się ich spodziewa.
    """
    gotowy = dict(kontekst)
    for nazwa, wartosc in kontekst.items():
        if not isinstance(wartosc, list) or not any(isinstance(w, dict) for w in wartosc):
            continue
        nowa_lista = []
        for wpis in wartosc:
            if not isinstance(wpis, dict):
                nowa_lista.append(wpis)
                continue
            kopia = dict(wpis)
            for klucz, (krój, rozmiar) in w_petli.items():
                tresc = kopia.get(klucz)
                if not isinstance(tresc, str):
                    continue
                kopia[klucz] = RichText(
                    tresc, font=krój or None, size=rozmiar or None,
                    color=CZERWONY if _zmienione(wpis, klucz) else None,
                    bold=_zmienione(wpis, klucz))
            nowa_lista.append(kopia)
        gotowy[nazwa] = nowa_lista
    return gotowy


def _ustawienia_biegu(biegi: list, qn) -> tuple[str, int]:
    """Krój i rozmiar (w półpunktach) z pierwszego biegu, który ma je ustawione."""
    for bieg in biegi:
        wlasciwosci = bieg.find(qn("w:rPr"))
        if wlasciwosci is None:
            continue
        czcionki = wlasciwosci.find(qn("w:rFonts"))
        rozmiar = wlasciwosci.find(qn("w:sz"))
        krój = czcionki.get(qn("w:ascii")) if czcionki is not None else None
        if krój or rozmiar is not None:
            return krój or "", int(rozmiar.get(qn("w:val"))) if rozmiar is not None else 0
    return "", 0


# Ile kolumn od prawej to kolumny stanów („dotychczasowy” i „nowy”). Reszta wiersza —
# L.p., nazwa atrybutu, podwiersz — zostaje wyśrodkowana zawsze.
KOLUMNY_STANOW = 2


def wyrownaj_komorki_stanow(dokument) -> int:
    """Komórki stanów: do góry, gdy w wierszu jest kilka linijek; inaczej na środek.

    Jedna działka bywa podzielona na kilka użytków i brat wpisuje je jeden pod drugim,
    a wartość w sąsiedniej kolumnie musi wypaść na wysokości **swojej** linijki (do tego
    służą puste linijki na początku wpisu). Przy wyśrodkowaniu w pionie krótsza kolumna
    pływała i nic się nie zgadzało — więc takie wiersze wyrównujemy do góry.

    Ale wiersz z jedną wartością po każdej stronie wyrównany do góry wygląda źle:
    liczba klei się do górnej krawędzi, a nazwa atrybutu obok stoi na środku, bo jej
    komórka bywa wyższa (dwuwierszowa etykieta, sąsiedni podwiersz). Dlatego decyduje
    **treść**, a nie formatka: to jedyne miejsce, które wie, ile linijek naprawdę wpisano.
    Robimy to po wypełnieniu, tuż przed zapisem.
    """
    from docx.oxml.ns import qn

    # `w:vAlign` stoi w `tcPr` przed `w:hideMark` i po `w:tcMar` — kolejność w OOXML jest
    # częścią schematu, a nie kwestią gustu (pułapka 12d)
    po_wyrownaniu = ("hideMark",)

    zmienione = 0
    for tabela in dokument.tables:
        for wiersz in tabela.rows:
            komorki = wiersz.cells[-KOLUMNY_STANOW:]
            if len(komorki) < KOLUMNY_STANOW:
                continue
            wielolinijkowa = any(len(k.text.splitlines()) > 1 for k in komorki)
            for komorka in komorki:
                tcPr = komorka._tc.get_or_add_tcPr()
                vAlign = tcPr.find(qn("w:vAlign"))
                if vAlign is None:
                    from docx.oxml import OxmlElement            # noqa: PLC0415
                    vAlign = OxmlElement("w:vAlign")
                    for dziecko in tcPr:
                        if dziecko.tag.split("}")[1] in po_wyrownaniu:
                            dziecko.addprevious(vAlign)
                            break
                    else:
                        tcPr.append(vAlign)
                vAlign.set(qn("w:val"), "top" if wielolinijkowa else "center")
                zmienione += 1
    return zmienione


def dopisz_dokument(szablon: Szablon, kontekst: dict[str, Any], katalog: Path) -> Path:
    """Wypełnia dodatkowy szablon **tym samym kontekstem** i kładzie go w katalogu operatu.

    Kontekst jest gotowy, więc numer operatu, daty i położenie są identyczne jak
    w dokumencie głównym — a `auto_numer` nie sięgnie po kolejny numer z licznika,
    bo widzi, że wartość już jest.
    """
    dokument = DocxTemplate(szablon.plik)
    dokument.render(sformatuj_pod_znaczniki(dokument, kontekst), autoescape=True)
    wyrownaj_komorki_stanow(dokument.docx)
    plik = katalog / operaty.nazwa_dokumentu(szablon.id)
    dokument.save(plik)
    return plik


def _numer_operatu(szablon: Szablon, kontekst: dict[str, Any]) -> str:
    for pole in szablon.pola:
        if pole.typ == "auto_numer" and kontekst.get(pole.klucz):
            return str(kontekst[pole.klucz])
    return ""


def generuj(szablon: Szablon, dane: dict[str, Any], ustawienia: dict[str, str],
            poprzedni: dict[str, Any] | None = None) -> tuple[Path, dict, list[str]]:
    """Zakłada katalog operatu i wkłada do niego dokument główny.

    `poprzedni` = opis operatu, który poprawiamy — zwykle z `operat.json`, a gdy folder
    pojechał do archiwum, złożony z wpisu w historii (patrz `main.generuj`). Wtedy numer
    operatu bierze się stamtąd, a nie z licznika, i wszystko ląduje w tym samym katalogu —
    poprawianie dokumentu nie może zjadać kolejnych numerów. Wystarczą dwa klucze:
    `nr_operatu` i `nr_roboty`.

    Zwraca (plik .docx, kontekst, ostrzeżenia do pokazania użytkownikowi).
    """
    rezerwacje: list[tuple[str, int, int]] = []
    if poprzedni and poprzedni.get("nr_operatu"):
        # Numer wpisujemy z góry — `auto_numer` po niego nie sięgnie, bo widzi wartość.
        dane = dict(dane)
        for pole in szablon.pola:
            # Uwaga: `setdefault` tu nie wystarczy. Przeglądarka wysyła pole numeru
            # zawsze, tylko puste, więc klucz w danych *jest* — z pustą wartością.
            # Trzeba sprawdzić wartość, nie obecność klucza, inaczej `przygotuj_kontekst`
            # uzna, że numeru brak, i weźmie kolejny z licznika.
            if pole.typ == "auto_numer" and not dane.get(pole.klucz):
                dane[pole.klucz] = poprzedni["nr_operatu"]
    kontekst = przygotuj_kontekst(szablon, dane, ustawienia, rezerwacje)
    try:
        dokument = DocxTemplate(szablon.plik)
        dokument.render(sformatuj_pod_znaczniki(dokument, kontekst), autoescape=True)
        wyrownaj_komorki_stanow(dokument.docx)

        # Katalog nazywa się numerem operatu; gdy szablon go nie ma, bierzemy nazwę
        # z wzorca nazwy pliku, żeby robota i tak dostała swój folder.
        #
        # Przy poprawianiu wracamy do **tego samego** katalogu, i to nawet wtedy, gdy
        # szablon nie ma licznika. Nazwa zastępcza ma w sobie znacznik czasu co do
        # sekundy, więc poprawka trafiała w inną sekundę, czyli w katalog obok:
        # poprzednie dokumenty zostawały w starym folderze, a wpis w historii wskazywał
        # już nowy. Wychodziło to jako losowe padnięcia testów — za każdym razem w innym,
        # bo zależało od tego, czy zegar tyknął między jednym żądaniem a drugim.
        numer = _numer_operatu(szablon, kontekst)
        znacznik = datetime.now().strftime("%Y%m%d-%H%M%S")
        katalog, ostrzezenia = operaty.zaloz(
            numer or str((poprzedni or {}).get("katalog") or "")
            or f"{nazwa_pliku(szablon, kontekst)}__{znacznik}",
            str(kontekst.get("nr_roboty", "")), szablon.id, dane,
            poprzedni_numer_roboty=str((poprzedni or {}).get("nr_roboty", "")))

        plik = katalog / operaty.nazwa_dokumentu(szablon.id)
        dokument.save(plik)
    except Exception:
        # Numer musi być znany przed wypełnianiem, bo wchodzi do treści dokumentu.
        # Gdy generowanie padnie, oddajemy go — inaczej każda literówka w szablonie
        # zostawiałaby dziurę w numeracji operatów.
        for nazwa_licznika, rok, numer_licznika in rezerwacje:
            db.zwolnij_numer(nazwa_licznika, rok, numer_licznika)
        raise
    return plik, kontekst, ostrzezenia

"""Historia wersji pokazywana bratu.

U brata nie ma gita — dostaje rozpakowany `.zip` — więc historia musi jechać z kodem
jako plik `ZMIANY.md`. Testy pilnują, żeby ten plik faktycznie do niego dotarł
i żeby zgadzał się z wydaną wersją.
"""
from __future__ import annotations

from app import aktualizacja, zmiany
from app.config import BAZA

PRZYKLAD = """# Historia zmian

Wstęp, który nie jest wydaniem.

## 2026.08.02.7 — 2026-08-02

Drobne sprzątanie przy pierwszym uruchomieniu.

## 2026.08.01.12 — 2026-08-01

Program pewniej zwalnia plik bazy danych.
Druga linia opisu.
"""


def test_czyta_wydania_od_najnowszego(tmp_path, monkeypatch):
    plik = tmp_path / "ZMIANY.md"
    plik.write_text(PRZYKLAD, encoding="utf-8")
    monkeypatch.setattr(zmiany, "PLIK", plik)

    wpisy = zmiany.wpisy()

    assert [w["wersja"] for w in wpisy] == ["2026.08.02.7", "2026.08.01.12"]
    assert wpisy[0]["data"] == "2026-08-02"
    assert wpisy[0]["opis"] == "Drobne sprzątanie przy pierwszym uruchomieniu."
    # kilka linii opisu skleja się w jedno zdanie, a wstęp nie udaje wydania
    assert wpisy[1]["opis"].endswith("Druga linia opisu.")


def test_opis_wydania_rozbija_sie_na_wstep_i_listy(tmp_path, monkeypatch):
    """Wydanie to kilkanaście commitów, więc opis ma stały kształt: zdanie–dwa wstępu,
    a pod nimi listy „Zmiany:” i „Nowości:”. Jednym akapitem robiła się z tego ściana
    tekstu, w której nie dało się znaleźć konkretnej zmiany."""
    plik = tmp_path / "ZMIANY.md"
    plik.write_text("""# Historia zmian

## 2026.08.25-103 — 2026-08-25

Porządki w wykazach. Drugie zdanie wstępu.

Zmiany:
- czerwień obejmuje cały użytek, a punkt bywa długi
  i zawija się w Notatniku na drugą linijkę
- numer działki sprawdza się też w karcie wykazu

Nowości:
- kontrola sumy PPU
""", encoding="utf-8")
    monkeypatch.setattr(zmiany, "PLIK", plik)

    wpis = zmiany.wpisy()[0]

    assert wpis["wstep"] == "Porządki w wykazach. Drugie zdanie wstępu."
    assert [g["tytul"] for g in wpis["grupy"]] == ["Zmiany", "Nowości"]
    assert wpis["grupy"][0]["punkty"][0].endswith("na drugą linijkę"), \
        "zawinięty punkt rozpadł się na dwa"
    assert len(wpis["grupy"][0]["punkty"]) == 2
    assert wpis["grupy"][1]["punkty"] == ["kontrola sumy PPU"]


def test_stary_opis_bez_list_czyta_sie_dalej(tmp_path, monkeypatch):
    """W historii jest sto wydań opisanych jednym akapitem — mają wyglądać jak dotąd."""
    plik = tmp_path / "ZMIANY.md"
    plik.write_text(PRZYKLAD, encoding="utf-8")
    monkeypatch.setattr(zmiany, "PLIK", plik)

    wpis = zmiany.wpisy()[0]

    assert wpis["wstep"] == "Drobne sprzątanie przy pierwszym uruchomieniu."
    assert wpis["grupy"] == []


def _znacznik_nowosci(tresc: str) -> None:
    from app import aktualizacja

    aktualizacja.ZNACZNIK_NOWOSCI.parent.mkdir(parents=True, exist_ok=True)
    aktualizacja.ZNACZNIK_NOWOSCI.write_text(tresc, encoding="utf-8")


def test_co_nowego_pokazuje_sie_w_oknie_na_srodku(klient):
    """Po aktualizacji staje okno z przyciskiem „OK”, a reszta strony jest przyciemniona.

    Pasek nad listą operatów dawało się przewinąć i nie przeczytać, a to jedyny moment,
    w którym brat dowiaduje się, co się zmieniło. Treść ma ten sam kształt co w historii
    wersji — punkty w listach — bo rozbiera ją to samo miejsce w kodzie.
    """
    _znacznik_nowosci("2026.08.25-103\nNowości:\n- kontrola sumy PPU\n")

    strona = klient.get("/").text

    assert "<dialog" in strona, "komunikat nie jest oknem"
    assert "showModal()" in strona, "okno bez `showModal` nie przyciemnia strony"
    assert 'action="/nowosci/przeczytane"' in strona, \
        "„OK” ma potwierdzać przeczytanie na serwerze — inaczej okno zgaśnie bez kliknięcia"
    assert "zaktualizował się do wersji 2026.08.25-103" in strona
    assert "<li>kontrola sumy PPU</li>" in strona


def test_okno_bierze_opis_z_historii_a_nie_ze_znacznika(klient, tmp_path, monkeypatch):
    """Znacznik pisze STARY aktualizator (pułapka 7b), a jego `_czytaj_wersje` skleja
    opis w jedną linijkę — okno pokazywało ścianę tekstu z myślnikami w środku, choć
    historia obok miała listy (zgłoszone zrzutem z instalacji testowej, 24.08.2026).
    ZMIANY.md przyjeżdża w tej samej paczce co nowy kod, więc wpis świeżo
    zainstalowanej wersji zawsze tam jest — i to on ma zasilać okno."""
    _znacznik_nowosci("2026.08.25-105\nZmiany: - pierwsza rzecz - druga rzecz")
    plik = tmp_path / "ZMIANY.md"
    plik.write_text("""# Historia zmian

## 2026.08.25-105 — 2026-08-25

Zmiany:
- pierwsza rzecz
- druga rzecz
""", encoding="utf-8")
    monkeypatch.setattr(zmiany, "PLIK", plik)

    strona = klient.get("/").text

    assert "<li>pierwsza rzecz</li>" in strona, \
        "okno pokazuje sklejony znacznik zamiast list z ZMIANY.md"
    assert "<li>druga rzecz</li>" in strona
    assert "Zmiany: - pierwsza" not in strona, "ściana tekstu ze znacznika została w oknie"


def test_okno_pokazuje_znacznik_gdy_wersji_nie_ma_w_historii(klient, tmp_path, monkeypatch):
    """Zapas na wypadek dziury w ZMIANY.md — lepszy sklejony opis niż puste okno."""
    _znacznik_nowosci("2026.08.25-106\nNowości:\n- rzecz spoza historii")
    plik = tmp_path / "ZMIANY.md"
    plik.write_text("# Historia zmian\n", encoding="utf-8")
    monkeypatch.setattr(zmiany, "PLIK", plik)

    strona = klient.get("/").text

    assert "zaktualizował się do wersji 2026.08.25-106" in strona
    assert "<li>rzecz spoza historii</li>" in strona


def test_okno_z_nowosciami_wraca_dopoki_nie_klikniesz_ok(klient):
    """Znacznik gaśnie dopiero po „OK”, nie przy samym pokazaniu strony.

    Kasowanie przy odczycie miało dwa skutki, oba złe: kontrola startu z `uruchom.py`
    pobiera stronę główną (pułapka 21) i zjadała okno, zanim przeglądarka w ogóle się
    otworzyła — u brata okno nie pokazało się nigdy; a kto zamknął przeglądarkę bez
    klikania, tracił komunikat bezpowrotnie."""
    _znacznik_nowosci("2026.08.25-103\nNowości:\n- kontrola sumy PPU\n")

    assert "<dialog" in klient.get("/").text, "pierwsze wejście bez okna"
    assert "<dialog" in klient.get("/").text, \
        "okno zgasło od samego odczytu — kontrola startu zjadałaby je przed przeglądarką"

    odpowiedz = klient.post("/nowosci/przeczytane", follow_redirects=False)

    assert odpowiedz.status_code == 303
    assert "<dialog" not in klient.get("/").text, "po „OK” okno ma zniknąć na dobre"


def test_strona_historii_pokazuje_listy(klient, tmp_path, monkeypatch):
    """Punkty mają dojechać do brata jako lista, a nie jako ciąg myślników w akapicie."""
    plik = tmp_path / "ZMIANY.md"
    plik.write_text("""# Historia zmian

## 2026.08.25-103 — 2026-08-25

Wstęp.

Nowości:
- kontrola sumy PPU
""", encoding="utf-8")
    monkeypatch.setattr(zmiany, "PLIK", plik)

    strona = klient.get("/pomoc/historia").text

    assert "<li>kontrola sumy PPU</li>" in strona
    assert "Nowości:" in strona


def test_wydania_sa_ponumerowane_od_pierwszego(tmp_path, monkeypatch):
    """Lista idzie od najnowszego, więc numery maleją: ostatnie wydanie ma najwyższy.

    Numer liczymy przy czytaniu pliku, a nie zapisujemy w nim — wynika wprost z tego,
    ile wydań już było, więc wpisany osobno mógłby się z listą rozjechać.
    """
    plik = tmp_path / "ZMIANY.md"
    plik.write_text(PRZYKLAD, encoding="utf-8")
    monkeypatch.setattr(zmiany, "PLIK", plik)

    wpisy = zmiany.wpisy()

    assert [w["numer"] for w in wpisy] == [2, 1]
    assert wpisy[-1]["numer"] == 1, "najstarsze wydanie musi być pierwsze"


def test_ograniczona_lista_nie_przenumerowuje_wydan(tmp_path, monkeypatch):
    """`limit` obcina listę, ale numery mają zostać takie jak w pełnej historii."""
    plik = tmp_path / "ZMIANY.md"
    plik.write_text(PRZYKLAD, encoding="utf-8")
    monkeypatch.setattr(zmiany, "PLIK", plik)

    assert [w["numer"] for w in zmiany.wpisy(limit=1)] == [2]


def test_strona_historii_pokazuje_numery(klient):
    tresc = klient.get("/pomoc/historia").text
    assert 'class="numer' in tresc


def test_brak_pliku_nie_wywraca_strony(tmp_path, monkeypatch):
    monkeypatch.setattr(zmiany, "PLIK", tmp_path / "nie-ma-mnie.md")
    assert zmiany.wpisy() == []


def test_plik_z_bom_em_czyta_sie_poprawnie(tmp_path, monkeypatch):
    """Notatnik zapisuje z BOM-em — na tym już raz poległ plik WERSJA."""
    plik = tmp_path / "ZMIANY.md"
    plik.write_text(PRZYKLAD, encoding="utf-8-sig")
    monkeypatch.setattr(zmiany, "PLIK", plik)

    assert zmiany.wpisy()[0]["wersja"] == "2026.08.02.7"


# --- to, co naprawdę może się rozjechać przy wydaniu -------------------------

def test_historia_jedzie_do_brata_przy_aktualizacji():
    """Bez tego wpisu historia zostałaby u autora, a brat miałby pustą stronę."""
    assert "ZMIANY.md" in aktualizacja.AKTUALIZOWANE


def test_wydana_wersja_ma_wpis_w_historii():
    """Najłatwiejszy błąd przy wydaniu: podbita WERSJA bez wpisu w ZMIANY.md.

    Sam program działałby dalej, ale brat po aktualizacji zobaczyłby komunikat
    „co nowego” i pustkę w historii — czyli dokładnie to, po co ta strona powstała.
    """
    monkeypatch_free_wpisy = zmiany.wpisy()          # prawdziwy plik z repozytorium
    assert monkeypatch_free_wpisy, "ZMIANY.md jest puste albo go nie ma"

    wersja = (BAZA / "WERSJA").read_text(encoding="utf-8-sig").strip().splitlines()[0].strip()
    assert monkeypatch_free_wpisy[0]["wersja"] == wersja, (
        "najnowszy wpis w ZMIANY.md nie odpowiada wydanej wersji — "
        "uruchom `python narzedzia/zbuduj_zmiany.py --zapisz` po podbiciu WERSJA")


def test_strona_historii_pokazuje_wydania(klient):
    odpowiedz = klient.get("/pomoc/historia")

    assert odpowiedz.status_code == 200
    assert "Historia wersji" in odpowiedz.text
    assert zmiany.wpisy()[0]["wersja"] in odpowiedz.text


def test_menu_pomocy_prowadzi_do_obu_stron(klient):
    tresc = klient.get("/").text

    assert 'href="/pomoc"' in tresc
    assert 'href="/pomoc/historia"' in tresc


# --- stempel nowego wydania --------------------------------------------------

def test_numer_wydania_ma_date_i_kolejny_numer():
    """`2026.08.06-82`: data z dnia wydania i numer po kolei od pierwszego.

    Numer porządkowy zastąpił licznik wydań w danym dniu — niesie tę samą
    informację (dwa wydania jednego dnia mają różne numery), a przy okazji mówi,
    które to wydanie z rzędu.
    """
    import sys
    from datetime import date

    sys.path.insert(0, str(BAZA / "narzedzia"))
    import wydaj

    assert wydaj.numer_wydania(date(2026, 8, 6), 82) == "2026.08.06-82"
    assert wydaj.numer_wydania(date(2026, 12, 1), 100) == "2026.12.01-100"


def test_nastepny_numer_liczy_tylko_zacommitowane_wydania(monkeypatch):
    """Powtórne uruchomienie skryptu przed commitem ma dać ten sam numer.

    To, co leży w katalogu roboczym, jest właśnie tym wydaniem, które stemplujemy —
    gdyby liczyło się do sumy, każde uruchomienie przesuwałoby numer o jeden.
    """
    import sys
    from datetime import date

    sys.path.insert(0, str(BAZA / "narzedzia"))
    import wydaj

    monkeypatch.setattr(wydaj.zbuduj_zmiany, "wydania_zacommitowane",
                        lambda: [("x", "", "")] * 81)

    assert wydaj.nastepny_numer(date(2026, 8, 6)) == "2026.08.06-82"
    assert wydaj.nastepny_numer(date(2026, 8, 6)) == "2026.08.06-82"

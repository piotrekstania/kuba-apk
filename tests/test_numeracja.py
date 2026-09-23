"""Numer operatu: licznik, numer wpisany z ręki i zmiana numeru przy poprawianiu.

Numer operatu to nazwa katalogu w `wyniki/`, więc każde zderzenie numerów jest od razu
zderzeniem katalogów: operat, który dostał cudzy numer, wchodził do cudzego folderu
i nadpisywał mu `operat.json` i dokumenty, a mapy i skany brata zaczynały należeć
do dwóch operatów naraz. Tu pilnujemy trzech dróg, którymi do tego dochodziło:
licznika, który nie wiedział o numerach spoza siebie, braku ostatniej zapory przy
zakładaniu katalogu i zmiany numeru przy „Popraw”, która rozbijała operat na dwa.
"""
from __future__ import annotations

import json
import re
import shutil
import zipfile
from datetime import date
from pathlib import Path

from app import db, generator, operaty
from test_trasy import FORMULARZ, _dodaj_operat, _prawdziwy_pdf   # tests/ nie jest pakietem

ROK = date.today().year          # licznik liczy w bieżącym roku — test nie może się starzeć


def nr(numer: int, rok: int = ROK) -> str:
    return f"{numer:03d}/{rok}"


def kat(numer: int, rok: int = ROK) -> str:
    return f"{numer:03d}.{rok}"


def _nowy(klient, **pola) -> dict:
    odpowiedz = klient.post("/generuj/spis_tresci_wzor", data={**FORMULARZ, **pola},
                            follow_redirects=False)
    assert odpowiedz.status_code == 303, odpowiedz.text[-600:]
    return db.dokumenty()[0]


def _adres_przekierowania(odpowiedz) -> str:
    from urllib.parse import unquote
    return unquote(odpowiedz.headers.get("location", ""))


def _popraw(klient, wpis, **pola):
    return klient.post(f"/generuj/spis_tresci_wzor?edytuj={wpis['id']}",
                       data={**FORMULARZ, **pola}, follow_redirects=False)


def _komunikat_bledu(strona: str) -> str:
    znaleziony = re.search(r'<div class="komunikat zle">(.*?)</div>', strona, re.DOTALL)
    return znaleziony.group(1) if znaleziony else ""


def _zawartosc(katalog: Path) -> dict[str, bytes]:
    return {p.name: p.read_bytes() for p in katalog.iterdir()}


def _tekst_docx(plik: Path) -> str:
    with zipfile.ZipFile(plik) as archiwum:
        return re.sub(r"<[^>]+>", "", archiwum.read("word/document.xml").decode("utf-8"))


# --- licznik nie wydaje numeru, który ktoś już ma -----------------------------

def test_licznik_omija_numer_wpisany_wczesniej_z_reki(klient):
    """Nie trzeba było utraty bazy: wystarczyło raz wpisać numer z ręki wyżej niż
    licznik. Gdy licznik do niego doszedł, nowy operat wchodził do katalogu tamtego,
    nadpisywał mu opis i spis treści, a w historii dwa wpisy z tym samym numerem
    wskazywały ten sam katalog. Licznik idzie teraz od najwyższego numeru, jaki
    program zna — luka w numeracji nic nie psuje, dwa operaty z jednym numerem tak."""
    _dodaj_operat(klient)
    _nowy(klient, pole__nr_operatu=nr(2), pole__nr_roboty="RECZNY.1")
    reczny = klient.srodowisko.wyniki / kat(2)
    _prawdziwy_pdf(reczny / "mapa.pdf")
    przed = {p.name: p.read_bytes() for p in reczny.iterdir()}

    nowy = _nowy(klient, pole__nr_roboty="Z.LICZNIKA.1")

    assert nowy["nr_operatu"] == nr(3) and nowy["katalog"] == kat(3)
    assert {p.name: p.read_bytes() for p in reczny.iterdir()} == przed, \
        "nowy operat wszedł do katalogu operatu z numerem wpisanym z ręki"
    assert sorted(w["nr_operatu"] for w in db.dokumenty()) == [nr(2), nr(3)]


def test_po_utracie_bazy_licznik_nie_wchodzi_do_istniejacego_katalogu(klient):
    """Nowy komputer z przegranym `wyniki/`, ale bez `dane/` (albo baza uszkodzona):
    licznik startował od 001 i wchodził do katalogu najstarszego operatu roku."""
    _dodaj_operat(klient)
    _nowy(klient, pole__nr_roboty="STARY.1")
    _nowy(klient, pole__nr_roboty="STARY.2")
    _prawdziwy_pdf(klient.srodowisko.wyniki / kat(1) / "mapa.pdf")
    przed = {p.name: p.read_bytes() for p in (klient.srodowisko.wyniki / kat(1)).iterdir()}
    with db.polaczenie() as con:
        con.execute("DELETE FROM dokumenty")
        con.execute("DELETE FROM liczniki")

    nowy = _nowy(klient, pole__nr_roboty="NOWY.1")

    assert nowy["nr_operatu"] == nr(3)
    assert {p.name: p.read_bytes() for p in (klient.srodowisko.wyniki / kat(1)).iterdir()} == przed


def test_licznik_pamieta_numery_operatow_z_archiwum(klient):
    """Operat przeniesiony do archiwum nie ma już katalogu w `wyniki/`, ale jego numer
    jest zajęty — zna go historia. Bez niej licznik po wyzerowaniu wydałby go drugi raz,
    a ośrodek dostałby dwa operaty z jednym numerem."""
    import shutil

    _dodaj_operat(klient)
    for numer in (1, 2, 3):
        _nowy(klient, pole__nr_roboty=f"GK.{numer}")
    shutil.rmtree(klient.srodowisko.wyniki / kat(3))            # „do archiwum”
    with db.polaczenie() as con:
        con.execute("DELETE FROM liczniki")

    assert _nowy(klient, pole__nr_roboty="GK.4")["nr_operatu"] == nr(4)


def test_licznik_patrzy_tylko_na_biezacy_rok(klient):
    """Numery z zeszłego roku nie przesuwają licznika — w nowym roku zaczyna od 001."""
    _dodaj_operat(klient)
    _nowy(klient, pole__nr_operatu=nr(90, ROK - 1), pole__nr_roboty="ZESZLY.1")

    assert _nowy(klient, pole__nr_roboty="TEN.1")["nr_operatu"] == nr(1)


def test_podpowiedz_numeru_w_formularzu_to_numer_ktory_dostanie_operat(klient):
    """Szary numer w pustym polu „Nr operatu” ma mówić prawdę — także wtedy, gdy licznik
    przeskakuje numery wpisane z ręki."""
    _dodaj_operat(klient)
    _nowy(klient, pole__nr_operatu=nr(50), pole__nr_roboty="RECZNY.1")

    formularz = klient.get("/nowy/spis_tresci_wzor").text

    assert f'placeholder="{nr(51)}"' in formularz
    assert _nowy(klient, pole__nr_roboty="GK.2")["nr_operatu"] == nr(51)


def test_nastepny_numer_nie_schodzi_ponizej_znanego(baza):
    """Arytmetyka licznika: nigdy nie wydaje numeru nie większego niż znany spoza niego,
    a numer oddany po nieudanym generowaniu wraca do puli także po takim przeskoku."""
    assert db.nastepny_numer("operat", ROK, co_najmniej=5) == 6        # licznik od zera
    assert db.nastepny_numer("operat", ROK, co_najmniej=3) == 7        # znany niższy — nic
    assert db.podglad_numeru("operat", ROK, co_najmniej=20) == 21
    assert db.nastepny_numer("operat", ROK, co_najmniej=20) == 21
    assert db.zwolnij_numer("operat", ROK, 21)                         # nieudane generowanie
    assert db.nastepny_numer("operat", ROK, co_najmniej=20) == 21      # ten sam numer wraca
    assert db.nastepny_numer("operat", ROK) == 22                      # bez znanych jak dotąd


def test_najwyzszy_znany_numer_czyta_historie_i_katalogi(srodowisko):
    """Numery rozpoznajemy wzorcem pola (`{numer3}/{rok}`), także gdy ktoś wpisał je
    bez zer z przodu. Katalog bez `operat.json` (założony przez brata z góry, z mapami
    na nową robotę) nie jest operatem, więc licznika nie przesuwa — trafi do niego
    operat z tym numerem, jak dotąd."""
    db.zapisz_dokument("spis_tresci_wzor", "GK.1", "x/spis_tresci.docx", {}, "x", f"7/{ROK}")
    operaty.zaloz(nr(12), "GK.2", "spis_tresci_wzor", {})
    (srodowisko.wyniki / kat(40)).mkdir()                                 # bez operat.json
    operaty.zaloz(nr(99, ROK - 1), "GK.3", "spis_tresci_wzor", {})        # zeszły rok
    # literówka na 22 cyfry: SQLite nie zmieści takiej liczby i każdy następny operat
    # padałby na przepełnieniu — takich „numerów” licznik nie bierze pod uwagę
    db.zapisz_dokument("spis_tresci_wzor", "GK.4", "y/spis_tresci.docx", {}, "y",
                       f"1234567890123456789012/{ROK}")

    assert generator.najwyzszy_znany_numer("{numer3}/{rok}", ROK) == 12


def test_opis_operatu_nie_bedacy_slownikiem_nie_wywraca_stron(klient):
    """`operat.json` z `[]` albo `null` (ręczna edycja, przerwany zapis) wywracał listę
    operatów, a odkąd licznik czyta katalogi — także formularz i zapis nowego operatu."""
    _dodaj_operat(klient)
    for nazwa, tresc in ((kat(3), "[]"), (kat(4), "null")):
        (klient.srodowisko.wyniki / nazwa).mkdir()
        (klient.srodowisko.wyniki / nazwa / operaty.PLIK_OPISU).write_text(tresc, encoding="utf-8")

    assert klient.get("/").status_code == 200
    assert klient.get("/nowy/spis_tresci_wzor").status_code == 200
    assert _nowy(klient, pole__nr_roboty="GK.1")["nr_operatu"]


def test_numer_z_reki_bez_zer_to_ten_sam_numer(klient):
    """Licznik porównuje numery po wartości, strażnik też musi: „1/2026” obok „001/2026”
    to osobne katalogi, ale dla ośrodka dwa operaty z jednym numerem."""
    _dodaj_operat(klient)
    _nowy(klient, pole__nr_roboty="GK.1")                                   # 001

    odpowiedz = klient.post("/generuj/spis_tresci_wzor", follow_redirects=False,
                            data={**FORMULARZ, "pole__nr_operatu": f"1/{ROK}",
                                  "pole__nr_roboty": "GK.2"})

    assert odpowiedz.status_code == 200 and "ma już inny operat" in odpowiedz.text
    assert len(db.dokumenty()) == 1


# --- ostatnia zapora: nowy operat nie wchodzi do cudzego katalogu -------------

def test_nowy_operat_nigdy_nie_nadpisuje_cudzego_katalogu(srodowisko):
    katalog, _ = operaty.zaloz(nr(1), "GK.1", "spis_tresci_wzor", {"a": 1})
    opis_przed = (katalog / operaty.PLIK_OPISU).read_bytes()

    try:
        operaty.zaloz(nr(1), "GK.2", "spis_tresci_wzor", {"a": 2}, nowy=True)
    except operaty.KatalogZajety as blad:
        assert blad.katalog == katalog
    else:
        raise AssertionError("nowy operat wszedł do katalogu, w którym leży inny")
    assert (katalog / operaty.PLIK_OPISU).read_bytes() == opis_przed


def test_zapora_w_trasie_mowi_co_zrobic_i_oddaje_numer(klient, monkeypatch):
    """Gdyby licznik jednak nie wiedział o jakimś operacie (tu udajemy to podmianą),
    zapora zatrzymuje zapis: nic nie jest nadpisane, numer wraca do puli, a brat
    dostaje formularz z danymi i wskazówkę, żeby wpisał wolny numer."""
    _dodaj_operat(klient)
    obcy = _nowy(klient, pole__nr_roboty="OBCY.1")                          # 001
    opis_przed = (klient.srodowisko.wyniki / obcy["katalog"] / operaty.PLIK_OPISU).read_bytes()
    with db.polaczenie() as con:
        con.execute("DELETE FROM liczniki")
    monkeypatch.setattr(generator, "najwyzszy_znany_numer", lambda wzor, rok: 0)

    odpowiedz = klient.post("/generuj/spis_tresci_wzor", follow_redirects=False,
                            data={**FORMULARZ, "pole__nr_roboty": "NOWY.1"})

    assert odpowiedz.status_code == 200
    assert "należy już do innego operatu" in odpowiedz.text and "NOWY.1" in odpowiedz.text
    assert (klient.srodowisko.wyniki / obcy["katalog"] / operaty.PLIK_OPISU).read_bytes() \
        == opis_przed
    assert len(db.dokumenty()) == 1
    assert db.podglad_numeru("operat", ROK) == 1, "numer nie wrócił do puli"


# --- zmiana numeru przy „Popraw” ----------------------------------------------

def test_zmiana_numeru_przy_poprawianiu_przenosi_caly_katalog(klient):
    """Katalog nazywa się numerem, więc zmiana numeru przenosi go w całości — razem
    z mapami brata i ułożeniem kafelków. Dotąd poprawka zakładała katalog obok:
    dokumenty szły do nowego, mapy zostawały w starym, historia mówiła stary numer
    i wskazywała nowy katalog, a na liście stały dwa wiersze ze starym numerem."""
    _dodaj_operat(klient)
    wpis = _nowy(klient)
    stary = klient.srodowisko.wyniki / wpis["katalog"]
    _prawdziwy_pdf(stary / "mapa.pdf")
    klient.post(f"/scal/{wpis['katalog']}", follow_redirects=False,
                data={"plik": ["mapa.pdf", "spis_tresci.docx"], "obrot__mapa.pdf": "90"})

    odpowiedz = _popraw(klient, wpis, pole__nr_operatu=nr(5))

    assert odpowiedz.status_code == 303, odpowiedz.text[-600:]
    nowy = klient.srodowisko.wyniki / kat(5)
    assert not stary.exists(), "stary katalog został obok nowego"
    assert (nowy / "mapa.pdf").exists(), "mapa brata nie przyjechała z operatem"
    assert operaty.opis(nowy)["nr_operatu"] == nr(5)
    assert operaty.uklad(nowy)["kolejnosc"] == ["mapa.pdf", "spis_tresci.docx"]
    assert nr(5) in _tekst_docx(nowy / "spis_tresci.docx")
    wiersz = db.dokument(wpis["id"])
    assert (wiersz["nr_operatu"], wiersz["katalog"]) == (nr(5), kat(5))
    assert len(db.dokumenty()) == 1
    lista = klient.get("/").text
    assert "spoza historii" not in lista and nr(5) in lista and nr(1) not in lista
    # złożony PDF przyjechał z katalogiem, ale ma w środku dawny numer operatu
    adres = _adres_przekierowania(odpowiedz)
    assert "numer operatu się zmienił" in adres.lower() and "złóż operat jeszcze raz" in adres.lower()


def test_zmiana_numeru_przy_otwartym_pliku_niczego_nie_rusza(klient, monkeypatch):
    """Katalogu z plikiem otwartym w Wordzie albo w czytniku Windows nie przemianuje.
    Wtedy nic się nie zmienia — ani katalog, ani historia — a formularz wraca
    z danymi i mówi, co zamknąć."""
    _dodaj_operat(klient)
    wpis = _nowy(klient)
    stary = klient.srodowisko.wyniki / wpis["katalog"]
    prawdziwa_zmiana_nazwy = Path.rename

    def jak_windows(sciezka, cel):
        if sciezka == stary:
            raise PermissionError(13, "Proces nie może uzyskać dostępu do pliku", str(sciezka))
        return prawdziwa_zmiana_nazwy(sciezka, cel)

    monkeypatch.setattr(Path, "rename", jak_windows)
    odpowiedz = _popraw(klient, wpis, pole__nr_operatu=nr(5), pole__uwagi="poprawka")

    assert odpowiedz.status_code == 200
    assert "Nic nie zostało zmienione" in odpowiedz.text and "poprawka" in odpowiedz.text
    assert stary.exists() and not (klient.srodowisko.wyniki / kat(5)).exists()
    wiersz = db.dokument(wpis["id"])
    assert (wiersz["nr_operatu"], wiersz["katalog"]) == (wpis["nr_operatu"], wpis["katalog"])


def test_przeniesiony_katalog_zostaje_w_historii_gdy_dokument_nie_powstanie(klient,
                                                                          monkeypatch):
    """Katalog przenosimy **przed** wypełnianiem dokumentów. Gdy wypełnianie potem padnie
    (dokument otwarty w Wordzie, literówka w formatce), historia ma już wskazywać katalog,
    który naprawdę leży na dysku — inaczej operat wyglądałby na przeniesiony do archiwum,
    a jego własny katalog na liście stałby jako operat „spoza historii”."""
    _dodaj_operat(klient)
    wpis = _nowy(klient)

    def odmowa(self, plik, *args, **kwargs):
        raise PermissionError(13, "Odmowa dostępu", str(plik))

    with monkeypatch.context() as podmiana:
        podmiana.setattr(generator.DocxTemplate, "save", odmowa)
        odpowiedz = _popraw(klient, wpis, pole__nr_operatu=nr(5))

    assert odpowiedz.status_code == 200 and "otwarty w innym programie" in odpowiedz.text
    wiersz = db.dokument(wpis["id"])
    assert (wiersz["nr_operatu"], wiersz["katalog"]) == (nr(5), kat(5))
    assert (klient.srodowisko.wyniki / kat(5)).is_dir()
    lista = klient.get("/").text
    assert "spoza historii" not in lista and "w archiwum" not in lista


def test_po_przeniesieniu_i_padnietym_wypelnianiu_operat_sie_nie_rozbija(klient, monkeypatch):
    """Katalog już przeniesiony, a wypełnianie formatki padło (literówka w znaczniku).
    `operat.json` zostawał wtedy ze starym numerem, a następne zwykłe „Popraw” (z pustym
    polem numeru) brało numer stamtąd i zakładało katalog obok — mapa zostawała
    w przeniesionym jako „spoza historii”. Formularz po błędzie mówi już nowy numer."""
    _dodaj_operat(klient)
    wpis = _nowy(klient)
    wyniki = klient.srodowisko.wyniki
    _prawdziwy_pdf(wyniki / kat(1) / "mapa.pdf")

    def literowka(self, *args, **kwargs):
        raise ValueError("literówka w znaczniku")

    with monkeypatch.context() as podmiana:
        podmiana.setattr(generator.DocxTemplate, "render", literowka)
        odpowiedz = _popraw(klient, wpis, pole__nr_operatu=nr(5))

    assert odpowiedz.status_code == 200
    assert f"zachowa numer {nr(5)}" in odpowiedz.text
    assert operaty.opis(wyniki / kat(5))["nr_operatu"] == nr(5)

    assert _popraw(klient, wpis).status_code == 303                # pole numeru puste
    assert sorted(k.name for k in wyniki.iterdir()) == [kat(5)]
    assert (wyniki / kat(5) / "mapa.pdf").exists()
    assert db.dokument(wpis["id"])["nr_operatu"] == nr(5)


def test_przeniesiony_numer_z_reki_nie_wraca_przy_nastepnej_poprawce(klient, monkeypatch):
    """Numer wpisany z ręki siedzi w danych formularza. Po przeniesieniu i padniętym
    wypełnianiu dane w historii miały dalej stary numer: formularz podsuwał go przy
    następnym „Popraw”, a zapis po cichu przenosił katalog z powrotem."""
    _dodaj_operat(klient)
    wpis = _nowy(klient, pole__nr_operatu=nr(1))

    def literowka(self, *args, **kwargs):
        raise ValueError("literówka w znaczniku")

    with monkeypatch.context() as podmiana:
        podmiana.setattr(generator.DocxTemplate, "render", literowka)
        _popraw(klient, wpis, pole__nr_operatu=nr(5))

    formularz = klient.get(f"/nowy/spis_tresci_wzor?edytuj={wpis['id']}").text
    assert re.search(r'id="p_nr_operatu"[^>]*value="' + re.escape(nr(5)) + '"', formularz)
    assert _popraw(klient, wpis, pole__nr_operatu=nr(5)).status_code == 303
    assert sorted(k.name for k in klient.srodowisko.wyniki.iterdir()) == [kat(5)]


def test_zmiana_numeru_na_katalog_brata_nie_radzi_kasowania(klient):
    """Katalog o nowym numerze bez `operat.json` to zwykle folder brata z mapami na inną
    robotę — komunikat nie może mu radzić, żeby go usunął. Nic się nie przenosi."""
    _dodaj_operat(klient)
    wpis = _nowy(klient)
    wyniki = klient.srodowisko.wyniki
    folder_brata = wyniki / kat(5)
    folder_brata.mkdir()
    _prawdziwy_pdf(folder_brata / "mapa innej roboty.pdf")
    przed = _zawartosc(folder_brata)

    odpowiedz = _popraw(klient, wpis, pole__nr_operatu=nr(5))

    komunikat = _komunikat_bledu(odpowiedz.text)
    assert odpowiedz.status_code == 200 and "już istnieje" in komunikat
    assert "usuń" not in komunikat.lower()
    assert _zawartosc(folder_brata) == przed and (wyniki / kat(1)).is_dir()


# --- dane po dawnych błędach: dwa wpisy w historii, jeden katalog -------------

def _dawny_dubel(klient):
    """Stan, jaki zostawiał stary licznik: operat B wszedł do katalogu operatu A. Oba
    wpisy w historii wskazują jeden katalog, a `operat.json` i dokumenty są już B —
    tak samo wygląda katalog operatu z archiwum zajęty potem numerem wpisanym z ręki."""
    _dodaj_operat(klient)
    a = _nowy(klient, pole__nr_roboty="GK.A")                     # 001
    b = _nowy(klient, pole__nr_roboty="GK.B")                     # 002
    wyniki = klient.srodowisko.wyniki
    wspolny = wyniki / a["katalog"]
    for plik in (wyniki / b["katalog"]).iterdir():
        shutil.copy2(plik, wspolny / plik.name)
    shutil.rmtree(wyniki / b["katalog"])
    opis = operaty.opis(wspolny)
    opis["nr_operatu"] = a["nr_operatu"]
    opis.pop("wpis", None)          # dane sprzed tej zmiany nie mają znacznika właściciela
    (wspolny / operaty.PLIK_OPISU).write_text(json.dumps(opis), encoding="utf-8")
    with db.polaczenie() as con:
        con.execute("UPDATE dokumenty SET nr_operatu = ?, katalog = ? WHERE id = ?",
                    (a["nr_operatu"], a["katalog"], b["id"]))
    _prawdziwy_pdf(wspolny / "mapa B.pdf")
    klient.post(f"/scal/{wspolny.name}", data={"plik": ["spis_tresci.docx", "mapa B.pdf"]},
                follow_redirects=False)
    assert (wspolny / "GK.B.pdf").exists()                        # złożony PDF operatu B
    return db.dokument(a["id"]), db.dokument(b["id"]), wspolny


def _kafelki(klient, katalog: Path) -> list[str]:
    return re.findall(r'<div class="kafelek"[^>]*data-nazwa="([^"]+)"',
                      klient.get(f"/scal/{katalog.name}").text)


def test_literowka_w_numerze_nie_wpuszcza_do_cudzego_katalogu(klient):
    """„001/2026.” (kropka na końcu) i „001.2026” to po zamianie na nazwę katalogu ten
    sam wspólny katalog. Wpis A, do którego katalog nie należy, wchodził tak do katalogu B:
    nadpisywał mu opis i dokument, kasował złożony PDF i ogłaszał „własny katalog”."""
    a, _, wspolny = _dawny_dubel(klient)
    przed = _zawartosc(wspolny)

    for numer in (a["nr_operatu"] + ".", a["nr_operatu"].replace("/", ".")):
        odpowiedz = _popraw(klient, a, pole__nr_roboty="GK.A", pole__nr_operatu=numer)
        assert odpowiedz.status_code == 200, numer
        assert _zawartosc(wspolny) == przed, numer


def test_wpis_bez_katalogu_nie_wchodzi_do_folderu_zalozonego_przez_brata(klient):
    """Odmowa podpowiada kolejny wolny numer — a brat zakłada czasem folder na następną
    robotę właśnie pod nim. Wpis A wchodził wtedy do tego folderu i brał mapę nowej
    roboty za swoją. Teraz folder zostaje nietknięty, a podpowiedź go omija."""
    a, _, _ = _dawny_dubel(klient)
    wyniki = klient.srodowisko.wyniki
    kolejny = klient.get("/nowy/spis_tresci_wzor").text
    kolejny = re.search(r'id="p_nr_operatu"[^>]*placeholder="([^"]+)"', kolejny).group(1)
    folder_brata = wyniki / operaty.nazwa_katalogu(kolejny)
    folder_brata.mkdir()
    _prawdziwy_pdf(folder_brata / "mapa nowej roboty.pdf")
    przed = _zawartosc(folder_brata)

    odmowa = _popraw(klient, a, pole__nr_roboty="GK.A")
    wejscie = _popraw(klient, a, pole__nr_roboty="GK.A", pole__nr_operatu=kolejny)

    assert f"np. {kolejny})" not in _komunikat_bledu(odmowa.text), "podpowiedź wskazuje folder brata"
    assert wejscie.status_code == 200 and "już istnieje" in _komunikat_bledu(wejscie.text)
    assert _zawartosc(folder_brata) == przed


def test_wlasciciel_wspolnego_katalogu_zmieniajac_numer_mowi_o_drugim_wpisie(klient):
    """Właściciel przenosi katalog w całości — także z plikami, które drugi wpis miał tam
    sprzed dawnego błędu, a tamten zostaje „w archiwum”. Nie może się to stać po cichu."""
    a, b, _ = _dawny_dubel(klient)

    odpowiedz = _popraw(klient, b, pole__nr_roboty="GK.B", pole__nr_operatu=nr(7))

    assert odpowiedz.status_code == 303
    adres = _adres_przekierowania(odpowiedz)
    assert "GK.A" in adres and "w archiwum" in adres


def test_po_usunieciu_wlasciciela_poprawka_drugiego_nie_kasuje_jego_pdf(klient):
    """Co jest „starym wynikiem”, program wnioskował z `operat.json`, a nie z poprzedniego
    numeru roboty **poprawianego** wpisu. Po „Usuń” właściciela (katalog zostaje) zwykła
    poprawka drugiego wpisu kasowała więc złożony PDF usuniętego — z komunikatem, że
    numer roboty się zmienił, choć nikt go nie zmieniał. Kafelkiem ten PDF i tak nie jest."""
    a, b, wspolny = _dawny_dubel(klient)
    klient.post(f"/dokument/{b['id']}/usun", follow_redirects=False)

    odpowiedz = _popraw(klient, a, pole__nr_roboty="GK.A", pole__uwagi="literówka")

    assert odpowiedz.status_code == 303
    assert (wspolny / "GK.B.pdf").exists()
    assert "numer roboty się zmienił" not in _adres_przekierowania(odpowiedz).lower()
    assert "GK.B.pdf" not in _kafelki(klient, wspolny)


def test_nieudany_zapis_nie_przerzuca_wlasnosci_wspolnego_katalogu(klient, monkeypatch):
    """Własność katalogu poznawaliśmy tylko po numerze roboty w `operat.json` — a zapis
    wpisuje tam nowy numer roboty, zanim powstanie dokument. Nieudana poprawka (spis
    otwarty w Wordzie) przerzucała więc własność na drugi wpis i ponowne „Zapisz”
    właściciela dostawało odmowę. Właściciel jest teraz zapisany w `operat.json`."""
    a, b, wspolny = _dawny_dubel(klient)
    opis = operaty.opis(wspolny)
    opis["nr_roboty"] = "GK.A"                           # katalog należy do A (starszego)
    (wspolny / operaty.PLIK_OPISU).write_text(json.dumps(opis), encoding="utf-8")

    def odmowa(self, plik, *args, **kwargs):
        raise PermissionError(13, "Odmowa dostępu", str(plik))

    with monkeypatch.context() as podmiana:
        podmiana.setattr(generator.DocxTemplate, "save", odmowa)
        assert _popraw(klient, a, pole__nr_roboty="GK.A2").status_code == 200

    assert _popraw(klient, a, pole__nr_roboty="GK.A2").status_code == 303
    assert operaty.opis(wspolny)["nr_roboty"] == "GK.A2"


def test_numer_z_katalogu_o_nietypowej_nazwie_tez_jest_zajety(klient):
    """Katalog przemianowany przy archiwizacji („005.2026 Kowalski”) albo kopia
    „- Kopia” ma numer już tylko w `operat.json`. Licznik czyta katalogi po nazwach,
    więc dla takich zagląda do opisu — inaczej numer 005 przechodził drugi raz."""
    _dodaj_operat(klient)
    inny = klient.srodowisko.wyniki / f"{kat(5)} Kowalski"
    inny.mkdir()
    (inny / operaty.PLIK_OPISU).write_text(
        json.dumps({"nr_operatu": nr(5), "nr_roboty": "GK.K"}), encoding="utf-8")

    odpowiedz = klient.post("/generuj/spis_tresci_wzor", follow_redirects=False,
                            data={**FORMULARZ, "pole__nr_operatu": nr(5)})

    assert odpowiedz.status_code == 200 and "ma już inny operat" in odpowiedz.text
    assert generator.najwyzszy_znany_numer("{numer3}/{rok}", ROK) == 5


def test_katalog_z_innego_komputera_nie_jest_nadpisywany_przez_poprawke(klient):
    """Operat 001 poszedł do archiwum, a do `wyniki/` trafił katalog 001 z laptopa —
    inny operat. W historii jest jeden wpis z tym katalogiem, więc własności nikt nie
    sprawdzał i „Popraw” nadpisywał opis i dokument z laptopa. Znacznik właściciela
    wskazuje tam inny, istniejący wpis — to wystarczy, żeby katalog był cudzy."""
    _dodaj_operat(klient)
    lokalny = _nowy(klient, pole__nr_roboty="GK.LOKALNY")                   # 001
    drugi = _nowy(klient, pole__nr_roboty="GK.DRUGI")                       # 002
    wyniki = klient.srodowisko.wyniki
    shutil.rmtree(wyniki / lokalny["katalog"])                              # „do archiwum”
    z_laptopa = wyniki / lokalny["katalog"]
    z_laptopa.mkdir()
    (z_laptopa / operaty.PLIK_OPISU).write_text(json.dumps(
        {"nr_operatu": lokalny["nr_operatu"], "nr_roboty": "GK.LAPTOP", "wpis": drugi["id"]}),
        encoding="utf-8")
    _prawdziwy_pdf(z_laptopa / "mapa z laptopa.pdf")
    przed = _zawartosc(z_laptopa)

    odpowiedz = _popraw(klient, lokalny, pole__nr_roboty="GK.LOKALNY")

    assert odpowiedz.status_code == 200
    assert "GK.LAPTOP" in _komunikat_bledu(odpowiedz.text)
    assert _zawartosc(z_laptopa) == przed


def test_nieudany_zapis_znacznika_nie_psuje_zalozonego_operatu(klient, monkeypatch):
    """Znacznik właściciela nie jest krytyczny: gdy jego zapis padnie po założeniu
    operatu, brat nie może dostać strony błędu — operat już jest w historii, a drugie
    „Zapisz” założyłoby drugi."""
    _dodaj_operat(klient)

    def odmowa(*args, **kwargs):
        raise PermissionError(13, "Odmowa dostępu")

    monkeypatch.setattr(operaty, "oznacz_wpis", odmowa)
    odpowiedz = klient.post("/generuj/spis_tresci_wzor", data=FORMULARZ, follow_redirects=False)

    assert odpowiedz.status_code == 303
    assert len(db.dokumenty()) == 1


def test_poprawka_wpisu_bez_wlasnego_katalogu_niczego_tam_nie_rusza(klient):
    """„Popraw” wpisu A bez żadnej zmiany kasował złożony PDF operatu B („numer roboty
    się zmienił”) i nadpisywał mu opis i dokumenty. Katalog należy do B — tego, czyj
    numer roboty stoi w jego `operat.json` — więc A dostaje odmowę i wskazówkę."""
    a, _, wspolny = _dawny_dubel(klient)
    przed = _zawartosc(wspolny)

    odpowiedz = _popraw(klient, a, pole__nr_roboty="GK.A")

    assert odpowiedz.status_code == 200
    assert "innego operatu" in _komunikat_bledu(odpowiedz.text)
    assert _zawartosc(wspolny) == przed


def test_nowy_numer_daje_takiemu_wpisowi_wlasny_katalog(klient):
    """Z nowym numerem wpis A przenosił cały katalog B (mapy, skany) pod swój numer,
    a B zostawał „w archiwum”. Teraz A dostaje własny katalog, a katalog B zostaje."""
    a, b, wspolny = _dawny_dubel(klient)
    przed = _zawartosc(wspolny)

    odpowiedz = _popraw(klient, a, pole__nr_roboty="GK.A", pole__nr_operatu=nr(7))

    assert odpowiedz.status_code == 303
    assert _zawartosc(wspolny) == przed
    nowy = klient.srodowisko.wyniki / kat(7)
    assert operaty.opis(nowy)["nr_roboty"] == "GK.A" and (nowy / "spis_tresci.docx").exists()
    assert (db.dokument(a["id"])["katalog"], db.dokument(b["id"])["katalog"]) == (kat(7), wspolny.name)
    assert "zostały" in _adres_przekierowania(odpowiedz)


def test_poprawka_wlasciciela_wspolnego_katalogu_dziala_jak_zwykle(klient):
    _, b, wspolny = _dawny_dubel(klient)

    odpowiedz = _popraw(klient, b, pole__nr_roboty="GK.B", pole__uwagi="poprawka B")

    assert odpowiedz.status_code == 303
    assert operaty.opis(wspolny)["nr_roboty"] == "GK.B"
    assert (wspolny / "GK.B.pdf").exists()


def test_usuniecie_wpisu_ze_wspolnym_katalogiem_nie_kasuje_katalogu(klient):
    """Dwa wiersze z jednym numerem na liście aż proszą, żeby jeden usunąć — a „Usuń”
    kasował wtedy katalog, w którym leżą pliki obu operatów. Teraz znika sam wpis."""
    a, b, wspolny = _dawny_dubel(klient)
    przed = _zawartosc(wspolny)
    pytanie = klient.get("/").text

    klient.post(f"/dokument/{a['id']}/usun", follow_redirects=False)

    assert db.dokument(a["id"]) is None and db.dokument(b["id"]) is not None
    assert _zawartosc(wspolny) == przed
    assert "wskazuje też inny operat" in pytanie


def test_plik_nazwany_jak_dawny_wynik_nie_znika_przy_kazdej_poprawce(klient):
    """Brat odkłada do katalogu wersję wysłaną do ośrodka (np. `GK.1.2026.pdf` z poczty).
    Usuwamy stary złożony PDF raz — przy tej poprawce, która zmienia numer roboty —
    a nie przy każdej następnej, nawet samej literówce."""
    _dodaj_operat(klient)
    wpis = _nowy(klient, pole__nr_roboty="GK.1.2026")
    katalog = klient.srodowisko.wyniki / wpis["katalog"]
    klient.post(f"/scal/{katalog.name}", data={"plik": ["spis_tresci.docx"]},
                follow_redirects=False)
    _popraw(klient, wpis, pole__nr_roboty="GK.2.2026")
    assert not (katalog / "GK.1.2026.pdf").exists()
    _prawdziwy_pdf(katalog / "GK.1.2026.pdf")                  # wersja z poczty

    _popraw(klient, wpis, pole__nr_roboty="GK.2.2026", pole__uwagi="literówka")

    assert (katalog / "GK.1.2026.pdf").exists()


def test_numer_operatu_z_archiwum_jest_zajety(klient):
    """Strażnik numerów zna też historię: operat przeniesiony do archiwum nie ma
    katalogu w `wyniki/`, ale jego numer nadal jest jego."""
    import shutil

    _dodaj_operat(klient)
    archiwalny = _nowy(klient, pole__nr_roboty="ARCH.1")                       # 001
    drugi = _nowy(klient, pole__nr_roboty="GK.2")                              # 002
    shutil.rmtree(klient.srodowisko.wyniki / archiwalny["katalog"])

    nowy = klient.post("/generuj/spis_tresci_wzor", follow_redirects=False,
                       data={**FORMULARZ, "pole__nr_operatu": archiwalny["nr_operatu"],
                             "pole__nr_roboty": "GK.3"})
    poprawka = _popraw(klient, drugi, pole__nr_operatu=archiwalny["nr_operatu"],
                       pole__nr_roboty="GK.2")

    for odpowiedz in (nowy, poprawka):
        assert odpowiedz.status_code == 200
        assert "ma już inny operat" in odpowiedz.text and "ARCH.1" in odpowiedz.text
    assert len(db.dokumenty()) == 2
    assert db.dokument(drugi["id"])["nr_operatu"] == drugi["nr_operatu"]
    assert (klient.srodowisko.wyniki / drugi["katalog"]).exists()


def test_podpowiedz_przy_poprawianiu_mowi_ze_numer_zostaje(klient):
    """„Zostaw puste, żeby program nadał kolejny numer” przy poprawianiu było nieprawdą:
    puste pole zostawia operatowi jego numer."""
    _dodaj_operat(klient)
    wpis = _nowy(klient)

    formularz = klient.get(f"/nowy/spis_tresci_wzor?edytuj={wpis['id']}").text
    pole = formularz.split('id="p_nr_operatu"')[1].split("</div>")[0]

    assert f"zachowa numer {wpis['nr_operatu']}" in pole
    assert "kolejny numer" not in pole

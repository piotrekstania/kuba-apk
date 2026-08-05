"""Robi z logo plik .ico dla Windowsa — do skrótu, paska zadań i okna programu.

Plik `.bat` nie ma własnej ikony: Windows rysuje mu systemową ikonkę wiersza poleceń
i nie da się tego zmienić z wnętrza pliku. Ikonę niesie dopiero **skrót** (`.lnk`),
który `start.bat` zakłada przy pierwszym uruchomieniu — i to on pokazuje ten obrazek
na pasku zadań oraz w oknie konsoli.

Rysujemy tę samą geometrię co `app/web/static/logo.svg`, bo Pillow nie czyta SVG,
a doinstalowywanie konwertera tylko po to byłoby nieproporcjonalne. Kształt jest na
tyle prosty, że opisują go trzy figury — a że oba pliki muszą pozostać zgodne,
pilnuje tego test.

    python narzedzia/utworz_ikone.py
"""
from pathlib import Path

from PIL import Image, ImageDraw

KORZEN = Path(__file__).resolve().parent.parent
PLIK = KORZEN / "app" / "web" / "static" / "logo.ico"

# Te same liczby co w logo.svg, w układzie 32 x 32.
TLO = (0x1F, 0x6F, 0xEB, 0xFF)
ZNAK = (0xFF, 0xFF, 0xFF, 0xFF)
PROMIEN = 7
TROJKAT = [(16, 7.4), (26.2, 24.8), (5.8, 24.8)]
GRUBOSC = 2.6
KROPKA = (16, 19, 2.4)

# Rysujemy duże i zmniejszamy — Pillow nie wygładza krawędzi samo, więc bez tego
# przekątne trójkąta wyszłyby schodkami. 32 x 32 razy 32 = 1024 px.
SKALA = 32

# Rozmiary, których szuka Windows: 16 na pasku zadań i w tytule okna, 32 i 48
# na pulpicie i w Eksploratorze, 256 w podglądzie dużych ikon.
ROZMIARY = [16, 32, 48, 64, 128, 256]


def narysuj(bok: int) -> Image.Image:
    """Znak w podanym rozmiarze, z wygładzonymi krawędziami."""
    duzy = bok * SKALA
    skala = duzy / 32
    obraz = Image.new("RGBA", (duzy, duzy), (0, 0, 0, 0))
    plotno = ImageDraw.Draw(obraz)

    plotno.rounded_rectangle([0, 0, duzy - 1, duzy - 1],
                             radius=PROMIEN * skala, fill=TLO)

    punkty = [(x * skala, y * skala) for x, y in TROJKAT]
    # `joint="curve"` zaokrągla łączenia — w SVG robi to stroke-linejoin="round"
    plotno.line([*punkty, punkty[0]], fill=ZNAK,
                width=round(GRUBOSC * skala), joint="curve")

    x, y, promien = KROPKA
    plotno.ellipse([(x - promien) * skala, (y - promien) * skala,
                    (x + promien) * skala, (y + promien) * skala], fill=ZNAK)

    return obraz.resize((bok, bok), Image.LANCZOS)


def zapisz(plik: Path = PLIK) -> Path:
    najwiekszy = narysuj(max(ROZMIARY))
    plik.parent.mkdir(parents=True, exist_ok=True)
    # Pillow sam przeskaluje do pozostałych rozmiarów zapisywanych w .ico
    najwiekszy.save(plik, format="ICO", sizes=[(b, b) for b in ROZMIARY])
    return plik


if __name__ == "__main__":
    zapisany = zapisz()
    print(f"Zapisano {zapisany} ({zapisany.stat().st_size / 1024:.1f} kB), "
          f"rozmiary: {', '.join(str(b) for b in ROZMIARY)}")

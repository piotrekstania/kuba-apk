"""Szkielety wykazów: strażnik `--nadpisz` chroni też opis pól.

Zapis `.json` stał poza strażnikiem — „bezpieczne” uruchomienie zostawiało `.docx`,
ale nadpisywało żywy opis pól szkieletem z `"pola": []`, kasując z niego `"wymaga"`,
czyli regułę pustego wykazu.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

KORZEN = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KORZEN / "narzedzia"))

import utworz_wzory_wykazow as wzory  # noqa: E402


def test_bez_nadpisz_nie_rusza_takze_opisu_pol(tmp_path, monkeypatch):
    monkeypatch.setattr(wzory, "SZABLONY", tmp_path)
    for opis in wzory.WYKAZY:
        plik = tmp_path / opis["plik"]
        plik.write_bytes(b"prawdziwa formatka brata")
        plik.with_suffix(".json").write_text(
            json.dumps({"pola": [], "wymaga": "wykazy_dzialek"}), encoding="utf-8")

    wzory.zbuduj_wszystkie(nadpisz=False)

    for opis in wzory.WYKAZY:
        plik = tmp_path / opis["plik"]
        assert plik.read_bytes() == b"prawdziwa formatka brata"
        dane = json.loads(plik.with_suffix(".json").read_text(encoding="utf-8"))
        assert dane.get("wymaga") == "wykazy_dzialek", \
            "szkielet nadpisał żywy opis pól mimo braku --nadpisz"

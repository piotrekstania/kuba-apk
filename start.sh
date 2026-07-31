#!/usr/bin/env bash
# Uruchamia Generator operatów (Linux / macOS).
cd "$(dirname "$0")"
if [ ! -d .venv ]; then
  python3 -m venv .venv
fi

# Aktualizacja przed instalacją bibliotek — nowa wersja może dokładać zależności.
.venv/bin/python -m app.aktualizacja

if ! cmp -s requirements.txt .venv/zainstalowane.txt; then
  .venv/bin/pip install --upgrade pip
  .venv/bin/pip install -r requirements.txt || exit 1
  cp requirements.txt .venv/zainstalowane.txt
fi

exec .venv/bin/python uruchom.py

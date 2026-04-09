# Stadionzeitung SV Obertraubling

Dieses Projekt generiert automatisch die Stadionzeitung (LaTeX) inkl. Tabellen, Titel-Daten und FuPa-Widgets aus Saison-JSONs und FuPa-Widgets.

## Voraussetzungen

- Python 3.10+
- LaTeX mit `pdflatex`
- Python-Pakete (siehe requirements.txt)

## Installation (macOS)

```bash
brew install --cask mactex
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
python -m playwright install
```

## Installation (Windows)

1) MiKTeX installieren: https://miktex.org/download
2) Python 3.10+ installieren: https://www.python.org/downloads/

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
py -m playwright install
```

## Nutzung

```bash
python scripts/main.py weekly --matchday 21
```

Weitere Befehle findest du im CLI, siehe scripts/main.py.

## Lizenz

Dieses Projekt steht unter der MIT-Lizenz. Details siehe LICENSE.

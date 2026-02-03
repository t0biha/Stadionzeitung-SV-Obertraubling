import json
import os
from datetime import datetime

# --- KONFIGURATION ---
OUTPUT_VAR = "generated/daten_titel.tex"

TEAMS = [
    {
        "name": "SV Obertraubling",
        "json": "saison_datenk1.json",
        "liga": "Kreisliga 1",
        "suffix": "",
    },
    {
        "name": "SV Obertraubling II",
        "json": "saison_datena2.json",
        "liga": "A-Klasse 2",
        "suffix": "II",
    },
]

WOCHENTAGE = [
    "Montag",
    "Dienstag",
    "Mittwoch",
    "Donnerstag",
    "Freitag",
    "Samstag",
    "Sonntag",
]


def finde_naechstes_heimspiel(team_name, json_input):
    if not os.path.exists(json_input):
        print(f"Fehler: {json_input} fehlt.")
        return None

    with open(json_input, "r", encoding="utf-8") as f:
        alle_spiele = json.load(f)

    heute = datetime.now()

    for spiel in alle_spiele:
        try:
            datum_obj = datetime.strptime(spiel["datum"], "%d.%m.%Y")
            if datum_obj >= heute and spiel["heim"] == team_name:
                return spiel
        except Exception:
            continue

    return None


def generiere_tex_block(team, spiel):
    if not spiel:
        return rf"""
\newcommand{{\TitelSpieltage{team['suffix']}}}{{??. Spieltag / {team['liga']}}}
\newcommand{{\TitelDatume{team['suffix']}}}{{??.??.???? | ??:?? Uhr}}
\newcommand{{\TitelPartiee{team['suffix']}}}{{{team['name']} - Gegner unbekannt}}
"""

    datum_obj = datetime.strptime(spiel["datum"], "%d.%m.%Y")
    wochentag = WOCHENTAGE[datum_obj.weekday()]

    return rf"""
\newcommand{{\TitelSpieltage{team['suffix']}}}{{{spiel['spieltag']}. Spieltag / {team['liga']}}}
\newcommand{{\TitelDatume{team['suffix']}}}{{{wochentag} {spiel['datum']} | {spiel['uhrzeit']} Uhr}}
\newcommand{{\TitelPartiee{team['suffix']}}}{{{team['name']} - {spiel['gast']}}}
"""


def main():
    content = "% Automatisch generierte Daten (1. + 2. Mannschaft)\n"

    for team in TEAMS:
        print(f"Verarbeite {team['name']} …")
        spiel = finde_naechstes_heimspiel(team["name"], team["json"])
        content += generiere_tex_block(team, spiel)

    content += rf"""
% Ausgabe Nummer (global)
\newcommand{{\TitelAusgabeNr}}{{Ausgabe Nr. 10, Saison 25/26}}
"""

    with open(OUTPUT_VAR, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"\nDatei '{OUTPUT_VAR}' erfolgreich erstellt.")


if __name__ == "__main__":
    main()
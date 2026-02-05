from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

WOCHENTAGE = [
    "Montag",
    "Dienstag",
    "Mittwoch",
    "Donnerstag",
    "Freitag",
    "Samstag",
    "Sonntag",
]


def find_next_home_match(team_name: str, json_input: Path) -> dict[str, Any] | None:
    if not json_input.exists():
        return None

    alle_spiele: list[dict[str, Any]] = json.loads(
        json_input.read_text(encoding="utf-8")
    )

    heute = datetime.now()

    for spiel in alle_spiele:
        try:
            datum_obj = datetime.strptime(spiel["datum"], "%d.%m.%Y")
            if datum_obj >= heute and spiel["heim"] == team_name:
                return spiel
        except Exception:
            continue

    return None


def generate_block(team: dict[str, str], spiel: dict[str, Any] | None) -> str:
    if not spiel:
        return rf"""
\newcommand{{\TitelSpieltage{team['suffix']}}}{{??. Spieltag / {team['league']}}}
\newcommand{{\TitelDatume{team['suffix']}}}{{??.??.???? | ??:?? Uhr}}
\newcommand{{\TitelPartiee{team['suffix']}}}{{{team['name']} - Gegner unbekannt}}
"""

    datum_obj = datetime.strptime(spiel["datum"], "%d.%m.%Y")
    wochentag = WOCHENTAGE[datum_obj.weekday()]

    return rf"""
\newcommand{{\TitelSpieltage{team['suffix']}}}{{{spiel['spieltag']}. Spieltag / {team['league']}}}
\newcommand{{\TitelDatume{team['suffix']}}}{{{wochentag} {spiel['datum']} | {spiel['uhrzeit']} Uhr}}
\newcommand{{\TitelPartiee{team['suffix']}}}{{{team['name']} - {spiel['gast']}}}
"""


def generate_title_data(
    *,
    teams: list[dict[str, str]],
    json_paths: dict[str, Path],
    output_tex: Path,
    issue_text: str,
) -> None:
    content = "% Automatisch generierte Daten (1. + 2. Mannschaft)\n"

    for team in teams:
        team_name = team["name"]
        key = team["key"]
        spiel = find_next_home_match(team_name, json_paths[key])
        content += generate_block(team, spiel)

    content += rf"""
% Ausgabe Nummer (global)
\newcommand{{\TitelAusgabeNr}}{{{issue_text}}}
"""

    output_tex.parent.mkdir(parents=True, exist_ok=True)
    output_tex.write_text(content, encoding="utf-8")

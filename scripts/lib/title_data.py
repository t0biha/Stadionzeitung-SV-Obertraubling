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


def _normalize_team_name(name: str) -> str:
    cleaned = (
        name.lower()
        .replace("(", " ")
        .replace(")", " ")
        .replace(".", " ")
        .replace("  ", " ")
        .strip()
    )

    prefixes = (
        "sv ",
        "fc ",
        "tsv ",
        "vfr ",
        "spvgg ",
        "sg ",
        "freier ",
        "sc ",
        "nk ",
        "atsv ",
        "fk ",
    )
    for prefix in prefixes:
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix) :].lstrip()
            break

    return " ".join(cleaned.split())


def _is_spielfrei(spiel: dict[str, Any]) -> bool:
    return str(spiel.get("gast", "")).strip().lower() == "spielfrei"


def _team_label(team: dict[str, str]) -> str:
    if team.get("suffix") == "II":
        return "2. Mannschaft"
    if team.get("suffix") == "":
        return "1. Mannschaft"
    return team.get("name", "Mannschaft")


def find_match_for_matchday(
    team_name: str, json_input: Path, matchday: int
) -> dict[str, Any] | None:
    if not json_input.exists():
        return None

    alle_spiele: list[dict[str, Any]] = json.loads(
        json_input.read_text(encoding="utf-8")
    )

    normalized_team = _normalize_team_name(team_name)

    for spiel in alle_spiele:
        try:
            if int(spiel.get("spieltag")) != matchday:
                continue

            heim = spiel.get("heim", "")
            if heim == team_name:
                return spiel
            if _normalize_team_name(heim) == normalized_team:
                return spiel
        except Exception:
            continue

    return None


def generate_block(
    team: dict[str, str], spiel: dict[str, Any] | None, matchday: int
) -> str:
    if not spiel:
        return rf"""
\newcommand{{\TitelSpieltage{team['suffix']}}}{{{matchday}. Spieltag / {team['league']}}}
\newcommand{{\TitelDatume{team['suffix']}}}{{??.??.???? | ??:?? Uhr}}
\newcommand{{\TitelPartiee{team['suffix']}}}{{{team['name']} - Gegner unbekannt}}
"""

    datum_obj = datetime.strptime(spiel["datum"], "%d.%m.%Y")
    wochentag = WOCHENTAGE[datum_obj.weekday()]

    if _is_spielfrei(spiel):
        label = _team_label(team)
        return rf"""
\newcommand{{\TitelSpieltage{team['suffix']}}}{{{spiel['spieltag']}. Spieltag / {team['league']}}}
\newcommand{{\TitelDatume{team['suffix']}}}{{{wochentag} {spiel['datum']} | Spielfrei}}
\newcommand{{\TitelPartiee{team['suffix']}}}{{{label} Spielfrei}}
"""

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
    matchday: int,
) -> None:
    content = "% Automatisch generierte Daten (1. + 2. Mannschaft)\n"

    for team in teams:
        team_name = team["name"]
        key = team["key"]
        spiel = find_match_for_matchday(team_name, json_paths[key], matchday)
        content += generate_block(team, spiel, matchday)

    content += rf"""
% Ausgabe Nummer (global)
\newcommand{{\TitelAusgabeNr}}{{{issue_text}}}
"""

    output_tex.parent.mkdir(parents=True, exist_ok=True)
    output_tex.write_text(content, encoding="utf-8")

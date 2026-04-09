from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from lib.latex_tables import find_logo

WEEKDAYS_SHORT = {
    0: "Mo.",
    1: "Di.",
    2: "Mi.",
    3: "Do.",
    4: "Fr.",
    5: "Sa.",
    6: "So.",
}


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


def _is_team(name: str, team_name: str) -> bool:
    return name == team_name or _normalize_team_name(name) == _normalize_team_name(team_name)


def _clean_time(raw_time: str) -> str:
    cleaned = raw_time.strip()
    if re.match(r"^\d{1,2}:\d{2}$", cleaned):
        return cleaned
    return ""


def _format_date(date_str: str, time_str: str) -> str:
    try:
        dt = datetime.strptime(date_str, "%d.%m.%Y")
        weekday = WEEKDAYS_SHORT[dt.weekday()]
        base = f"{weekday} {dt.strftime('%d.%m.%y')}"
    except Exception:
        base = date_str

    time_part = _clean_time(time_str)
    return f"{base} {time_part}".strip()


def _format_result(result: str, is_home: bool) -> str:
    if not re.match(r"^\d+:\d+$", result.strip()):
        return ""

    home_goals, away_goals = [int(x) for x in result.split(":", 1)]
    if home_goals == away_goals:
        color = "gray"
    else:
        win = home_goals > away_goals if is_home else away_goals > home_goals
        color = "green!60!black" if win else "VereinsRot"

    return f"\\textbf{{\\color{{{color}}} {result}}}"


def generate_term_list(
    *,
    json_input: Path,
    output_tex: Path,
    logos: dict[str, str],
    logos_dir: str,
    team_name: str,
) -> bool:
    if not json_input.exists():
        raise FileNotFoundError(f"JSON fehlt: {json_input}")

    all_matches: list[dict[str, Any]] = json.loads(
        json_input.read_text(encoding="utf-8")
    )

    team_matches = []
    for match in all_matches:
        home_team = str(match.get("heim", ""))
        away_team = str(match.get("gast", ""))
        if _is_team(home_team, team_name) or _is_team(away_team, team_name):
            team_matches.append(match)

    if not team_matches:
        return False

    team_matches.sort(key=lambda match: int(match.get("spieltag", 0)))

    latex = r"""
\setlength{\tabcolsep}{4pt}
\renewcommand{\arraystretch}{1.35}
\begin{tabularx}{\textwidth}{ r l c c X r }
"""

    for match in team_matches:
        matchday = str(match.get("spieltag", ""))
        home_team = str(match.get("heim", ""))
        away_team = str(match.get("gast", ""))
        match_date = str(match.get("datum", ""))
        match_time = str(match.get("uhrzeit", ""))
        match_result = str(match.get("ergebnis", ""))

        is_home_game = _is_team(home_team, team_name)
        home_or_away = "H" if is_home_game else "A"

        opponent = away_team if is_home_game else home_team
        logo_file = find_logo(opponent, logos)
        logo = (
            f"\\raisebox{{-0.35\\height}}{{\\includegraphics[height=2.8ex]{{{logos_dir}/{logo_file}}}}}"
            if logo_file
            else ""
        )

        date_text = _format_date(match_date, match_time)
        result_text = _format_result(match_result, is_home_game)

        if opponent.strip().lower() == "spielfrei":
            home_or_away = ""
            result_text = ""

        latex += (
            f"\\textbf{{{matchday}.}} & "
            f"{date_text} & "
            f"\\textbf{{{home_or_away}}} & "
            f"{logo} & "
            f"{opponent} & "
            f"{result_text} \\\\\n"
        )

    latex += r"\end{tabularx}"

    output_tex.parent.mkdir(parents=True, exist_ok=True)
    output_tex.write_text(latex, encoding="utf-8")
    return True

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
import re


def _is_spielfrei(name: str) -> bool:
    return name.strip().lower() == "spielfrei"


def _clean_time(raw_time: str) -> str:
    cleaned = raw_time.strip()
    if re.match(r"^\d{1,2}:\d{2}$", cleaned):
        return cleaned
    return ""


def find_logo(team_name: str, logos: dict[str, str]) -> str | None:
    if _is_spielfrei(team_name):
        return None
    if team_name in logos:
        return logos[team_name]
    for key, val in logos.items():
        if key in team_name:
            return val
    return None


def _fix_team_name_for_spielfrei(
    *,
    team_name: str,
    opponent_name: str,
    raw_time: str,
    logos: dict[str, str],
) -> str:
    """Repair truncated team names in malformed SPIELFREI rows.

    Some extracted rows contain e.g. uhrzeit="VfR", heim="Regensburg II", gast="SPIELFREI".
    In that case we merge the broken token and resolve against known logo keys.
    """
    if not _is_spielfrei(opponent_name):
        return team_name

    if find_logo(team_name, logos):
        return team_name

    token = raw_time.strip()
    if not token or _clean_time(token):
        return team_name

    merged = f"{token} {team_name}".strip()
    if merged in logos:
        return merged

    for key in logos:
        if key.lower() == merged.lower():
            return key
    return team_name


def generate_matchday_table(
    *,
    json_input: Path,
    output_tex: Path,
    logos: dict[str, str],
    logos_dir: str,
    matchday: int,
) -> bool:
    if not json_input.exists():
        raise FileNotFoundError(f"JSON fehlt: {json_input}")

    all_matches: list[dict[str, Any]] = json.loads(
        json_input.read_text(encoding="utf-8")
    )

    matchday_matches = [match for match in all_matches if match.get("spieltag") == matchday]
    if not matchday_matches:
        return False

    latex = f"""
% --- SPIELTAG ÜBERSCHRIFT ---
\\vspace{{1em}}
\\begin{{center}}
    {{\\Large\\bfseries\\color{{VereinsBlau}} {matchday}. Spieltag}}
\\end{{center}}
\\vspace{{0.8em}}

% --- TABELLE ---
\\setlength{{\\tabcolsep}}{{3pt}}
\\renewcommand{{\\arraystretch}}{{1.6}}
\\arrayrulecolor{{gray!50}}

\\begin{{tabularx}}{{\\textwidth}}{{ l >{{\\raggedleft\\arraybackslash}}X c c c >{{\\raggedright\\arraybackslash}}X }}
    \\hline
"""

    for match in matchday_matches:
        home_team = str(match.get("heim", ""))
        away_team = str(match.get("gast", ""))
        result = str(match.get("ergebnis", ""))

        raw_time = str(match.get("uhrzeit", ""))
        home_team = _fix_team_name_for_spielfrei(
            team_name=home_team,
            opponent_name=away_team,
            raw_time=raw_time,
            logos=logos,
        )
        away_team = _fix_team_name_for_spielfrei(
            team_name=away_team,
            opponent_name=home_team,
            raw_time=raw_time,
            logos=logos,
        )

        home_logo_file = find_logo(home_team, logos)
        away_logo_file = find_logo(away_team, logos)

        logo_h = (
            f"\\raisebox{{-0.4\\height}}{{\\includegraphics[height=3.5ex]{{{logos_dir}/{home_logo_file}}}}}"
            if home_logo_file
            else ""
        )
        logo_g = (
            f"\\raisebox{{-0.4\\height}}{{\\includegraphics[height=3.5ex]{{{logos_dir}/{away_logo_file}}}}}"
            if away_logo_file
            else ""
        )

        date_text = str(match.get("datum", ""))[:-5]
        time_text = _clean_time(raw_time)

        line = (
            f"    \\footnotesize \\color{{gray}} {date_text} {time_text} & "
            f"\\textbf{{{home_team}}} & "
            f"{logo_h} & "
            f"\\large \\textbf{{{result}}} & "
            f"{logo_g} & "
            f"\\textbf{{{away_team}}} \\\\ \\hline"
        )
        latex += line + "\n"

    latex += r"\end{tabularx}"

    output_tex.parent.mkdir(parents=True, exist_ok=True)
    output_tex.write_text(latex, encoding="utf-8")
    return True

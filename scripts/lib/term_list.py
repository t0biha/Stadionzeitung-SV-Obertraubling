from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from lib.latex_tables import find_logo

WOCHENTAGE_KURZ = {
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
        wtag = WOCHENTAGE_KURZ[dt.weekday()]
        base = f"{wtag} {dt.strftime('%d.%m.%y')}"
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

    alle_spiele: list[dict[str, Any]] = json.loads(
        json_input.read_text(encoding="utf-8")
    )

    spiele = []
    for spiel in alle_spiele:
        heim = str(spiel.get("heim", ""))
        gast = str(spiel.get("gast", ""))
        if _is_team(heim, team_name) or _is_team(gast, team_name):
            spiele.append(spiel)

    if not spiele:
        return False

    spiele.sort(key=lambda s: int(s.get("spieltag", 0)))

    latex = r"""
\setlength{\tabcolsep}{4pt}
\renewcommand{\arraystretch}{1.35}
\begin{tabularx}{\textwidth}{ r l c c X r }
"""

    for spiel in spiele:
        spieltag = str(spiel.get("spieltag", ""))
        heim = str(spiel.get("heim", ""))
        gast = str(spiel.get("gast", ""))
        datum = str(spiel.get("datum", ""))
        zeit = str(spiel.get("uhrzeit", ""))
        res = str(spiel.get("ergebnis", ""))

        is_home = _is_team(heim, team_name)
        ha = "H" if is_home else "A"

        opponent = gast if is_home else heim
        logo_file = find_logo(opponent, logos)
        logo = (
            f"\\raisebox{{-0.35\\height}}{{\\includegraphics[height=2.8ex]{{{logos_dir}/{logo_file}}}}}"
            if logo_file
            else ""
        )

        date_text = _format_date(datum, zeit)
        result_text = _format_result(res, is_home)

        if opponent.strip().lower() == "spielfrei":
            ha = ""
            result_text = ""

        latex += (
            f"\\textbf{{{spieltag}.}} & "
            f"{date_text} & "
            f"\\textbf{{{ha}}} & "
            f"{logo} & "
            f"{opponent} & "
            f"{result_text} \\\\\n"
        )

    latex += r"\end{tabularx}"

    output_tex.parent.mkdir(parents=True, exist_ok=True)
    output_tex.write_text(latex, encoding="utf-8")
    return True

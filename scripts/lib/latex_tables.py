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

    alle_spiele: list[dict[str, Any]] = json.loads(
        json_input.read_text(encoding="utf-8")
    )

    spiele = [s for s in alle_spiele if s.get("spieltag") == matchday]
    if not spiele:
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

    for spiel in spiele:
        heim = str(spiel.get("heim", ""))
        gast = str(spiel.get("gast", ""))
        res = str(spiel.get("ergebnis", ""))

        f_heim = find_logo(heim, logos)
        f_gast = find_logo(gast, logos)

        logo_h = (
            f"\\raisebox{{-0.4\\height}}{{\\includegraphics[height=3.5ex]{{{logos_dir}/{f_heim}}}}}"
            if f_heim
            else ""
        )
        logo_g = (
            f"\\raisebox{{-0.4\\height}}{{\\includegraphics[height=3.5ex]{{{logos_dir}/{f_gast}}}}}"
            if f_gast
            else ""
        )

        datum = str(spiel.get("datum", ""))[:-5]
        zeit = _clean_time(str(spiel.get("uhrzeit", "")))

        line = (
            f"    \\footnotesize \\color{{gray}} {datum} {zeit} & "
            f"\\textbf{{{heim}}} & "
            f"{logo_h} & "
            f"\\large \\textbf{{{res}}} & "
            f"{logo_g} & "
            f"\\textbf{{{gast}}} \\\\ \\hline"
        )
        latex += line + "\n"

    latex += r"\end{tabularx}"

    output_tex.parent.mkdir(parents=True, exist_ok=True)
    output_tex.write_text(latex, encoding="utf-8")
    return True

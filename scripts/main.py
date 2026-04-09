from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from lib.config import load_config, resolve_path
from lib.latex_tables import generate_matchday_table
from lib.pdf_extract import extract_from_pdf
from lib.term_list import generate_term_list
from lib.title_data import generate_title_data
from lib.fupa_widget import export_widget


def _prompt_matchday() -> int:
    user_input = input("Welchen Spieltag möchtest du erstellen? (z.B. 2): ")
    return int(user_input)


def run_extract(cfg: dict) -> None:
    first_team_pdf = resolve_path(cfg["pdf"]["first_team"])
    first_team_json = resolve_path(cfg["json"]["first_team"])
    second_team_pdf = resolve_path(cfg["pdf"]["second_team"])
    second_team_json = resolve_path(cfg["json"]["second_team"])

    print("Lese PDF ein (1. Mannschaft)...")
    first_team_match_count = extract_from_pdf(first_team_pdf, first_team_json)
    print(f"Erfolg! {first_team_match_count} Spiele extrahiert -> {first_team_json}")

    print("Lese PDF ein (2. Mannschaft)...")
    second_team_match_count = extract_from_pdf(second_team_pdf, second_team_json)
    print(f"Erfolg! {second_team_match_count} Spiele extrahiert -> {second_team_json}")


def run_tables(cfg: dict, matchday_input: int | None) -> None:
    if matchday_input is None:
        matchday_input = _prompt_matchday()

    matchday_previous = matchday_input - 1
    matchday_current = matchday_input
    matchday_next = matchday_input + 1

    logos_dir = cfg["paths"]["logos_dir"]

    first_team_previous_ok = generate_matchday_table(
        json_input=resolve_path(cfg["json"]["first_team"]),
        output_tex=resolve_path(cfg["latex"]["first_team_previous"]),
        logos=cfg["logos"]["first_team"],
        logos_dir=logos_dir,
        matchday=matchday_previous,
    )

    first_team_current_ok = generate_matchday_table(
        json_input=resolve_path(cfg["json"]["first_team"]),
        output_tex=resolve_path(cfg["latex"]["first_team_current"]),
        logos=cfg["logos"]["first_team"],
        logos_dir=logos_dir,
        matchday=matchday_current,
    )

    first_team_next_ok = generate_matchday_table(
        json_input=resolve_path(cfg["json"]["first_team"]),
        output_tex=resolve_path(cfg["latex"]["first_team_next"]),
        logos=cfg["logos"]["first_team"],
        logos_dir=logos_dir,
        matchday=matchday_next,
    )

    second_team_previous_ok = generate_matchday_table(
        json_input=resolve_path(cfg["json"]["second_team"]),
        output_tex=resolve_path(cfg["latex"]["second_team_previous"]),
        logos=cfg["logos"]["second_team"],
        logos_dir=logos_dir,
        matchday=matchday_previous,
    )

    second_team_current_ok = generate_matchday_table(
        json_input=resolve_path(cfg["json"]["second_team"]),
        output_tex=resolve_path(cfg["latex"]["second_team_current"]),
        logos=cfg["logos"]["second_team"],
        logos_dir=logos_dir,
        matchday=matchday_current,
    )

    second_team_next_ok = generate_matchday_table(
        json_input=resolve_path(cfg["json"]["second_team"]),
        output_tex=resolve_path(cfg["latex"]["second_team_next"]),
        logos=cfg["logos"]["second_team"],
        logos_dir=logos_dir,
        matchday=matchday_next,
    )

    if all(
        [
            first_team_previous_ok,
            first_team_current_ok,
            first_team_next_ok,
            second_team_previous_ok,
            second_team_current_ok,
            second_team_next_ok,
        ]
    ):
        print("Tabellen aktualisiert.")
    else:
        print("Hinweis: Für mindestens einen Spieltag wurden keine Spiele gefunden.")


def run_title(cfg: dict, matchday_input: int | None) -> None:
    if matchday_input is None:
        matchday_input = _prompt_matchday()

    teams = [
        {
            "key": "first_team",
            "name": cfg["teams"]["first_team"]["name"],
            "league": cfg["teams"]["first_team"]["league"],
            "suffix": cfg["teams"]["first_team"]["suffix"],
        },
        {
            "key": "second_team",
            "name": cfg["teams"]["second_team"]["name"],
            "league": cfg["teams"]["second_team"]["league"],
            "suffix": cfg["teams"]["second_team"]["suffix"],
        },
    ]

    json_paths = {
        "first_team": resolve_path(cfg["json"]["first_team"]),
        "second_team": resolve_path(cfg["json"]["second_team"]),
    }

    output_tex = resolve_path(cfg["title"]["output"])
    issue_text = cfg["title"]["issue"]

    generate_title_data(
        teams=teams,
        json_paths=json_paths,
        output_tex=output_tex,
        issue_text=issue_text,
        matchday=matchday_input,
    )

    print(f"Titel-Daten geschrieben: {output_tex}")


def run_widgets(cfg: dict) -> None:
    output_dir = resolve_path(cfg["paths"]["generated_dir"])

    for key in [
        "league_table_first_team",
        "league_table_second_team",
        "match_schedule_widget_first_team",
        "match_schedule_widget_second_team",
    ]:
        widget_cfg = cfg["widgets"][key]
        export_widget(
            output_dir=output_dir,
            name=widget_cfg["output"],
            widget_root_id=widget_cfg["id"],
            club_url=cfg["widgets"]["club_url"],
            viewport=widget_cfg["viewport"],
            max_height_px=widget_cfg.get("max_height_px"),
            max_height_ratio=widget_cfg.get("max_height_ratio"),
        )

    print("Widgets exportiert.")


def run_terms(cfg: dict) -> None:
    logos_dir = cfg["paths"]["logos_dir"]

    first_team_fixture_list_ok = generate_term_list(
        json_input=resolve_path(cfg["json"]["first_team"]),
        output_tex=resolve_path(cfg["latex"]["fixture_list_first_team"]),
        logos=cfg["logos"]["first_team"],
        logos_dir=logos_dir,
        team_name=cfg["teams"]["first_team"]["name"],
    )

    second_team_fixture_list_ok = generate_term_list(
        json_input=resolve_path(cfg["json"]["second_team"]),
        output_tex=resolve_path(cfg["latex"]["fixture_list_second_team"]),
        logos=cfg["logos"]["second_team"],
        logos_dir=logos_dir,
        team_name=cfg["teams"]["second_team"]["name"],
    )

    if first_team_fixture_list_ok and second_team_fixture_list_ok:
        print("Terminlisten aktualisiert.")
    else:
        print("Hinweis: Für mindestens eine Terminliste wurden keine Spiele gefunden.")


def _run_script(script_name: str, args: list[str]) -> None:
    script_path = Path(__file__).resolve().parent / script_name
    cmd = [sys.executable, str(script_path), *args]
    subprocess.run(cmd, check=True)


def run_scorers(cfg: dict) -> None:
    top_scorers_limit = int(cfg["scorers"]["top"])
    first_team_league_slug = cfg["scorers"]["first_team_league_slug"]
    second_team_league_slug = cfg["scorers"]["second_team_league_slug"]

    _run_script(
        "fetch_top_scorers_first_team.py",
        [
            "--league",
            first_team_league_slug,
            "--top",
            str(top_scorers_limit),
            "--out",
            "generated/top_scorers_first_team.json",
        ],
    )
    _run_script(
        "fetch_top_scorers_second_team.py",
        [
            "--league",
            second_team_league_slug,
            "--top",
            str(top_scorers_limit),
            "--out",
            "generated/top_scorers_second_team.json",
        ],
    )

    _run_script(
        "export_top_scorers_first_team_tex.py",
        [
            "--json",
            "generated/top_scorers_first_team.json",
            "--out",
            "generated/top_scorers_first_team.tex",
            "--top",
            str(top_scorers_limit),
        ],
    )
    _run_script(
        "export_top_scorers_second_team_tex.py",
        [
            "--json",
            "generated/top_scorers_second_team.json",
            "--out",
            "generated/top_scorers_second_team.tex",
            "--top",
            str(top_scorers_limit),
        ],
    )

    print("Torjäger aktualisiert.")


def main() -> None:
    cfg = load_config()

    parser = argparse.ArgumentParser(description="Stadionzeitung weekly runner")
    sub = parser.add_subparsers(dest="cmd", required=True)

    weekly = sub.add_parser("weekly", help="Alles für die Woche erzeugen")
    weekly.add_argument("--matchday", type=int, default=None)

    extract = sub.add_parser("extract", help="PDF -> JSON")
    tables = sub.add_parser("tables", help="Spieltag-Tabellen")
    tables.add_argument("--matchday", type=int, default=None)

    title = sub.add_parser("title", help="Titeldaten")
    title.add_argument("--matchday", type=int, default=None)
    sub.add_parser("widgets", help="FuPa Widgets")
    sub.add_parser("scorers", help="Torjäger")
    sub.add_parser("terms", help="Terminlisten")

    args = parser.parse_args()

    if args.cmd == "weekly":
        run_extract(cfg)
        run_tables(cfg, args.matchday)
        run_title(cfg, args.matchday)
        run_widgets(cfg)
        run_scorers(cfg)
        run_terms(cfg)
        return

    if args.cmd == "extract":
        run_extract(cfg)
        return

    if args.cmd == "tables":
        run_tables(cfg, args.matchday)
        return

    if args.cmd == "title":
        run_title(cfg, args.matchday)
        return

    if args.cmd == "widgets":
        run_widgets(cfg)
        return

    if args.cmd == "scorers":
        run_scorers(cfg)
        return

    if args.cmd == "terms":
        run_terms(cfg)
        return


if __name__ == "__main__":
    main()

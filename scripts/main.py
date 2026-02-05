from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from lib.config import load_config, resolve_path
from lib.latex_tables import generate_matchday_table
from lib.pdf_extract import extract_from_pdf
from lib.title_data import generate_title_data
from lib.fupa_widget import export_widget


def _prompt_matchday() -> int:
    eingabe = input("Welchen Spieltag möchtest du erstellen? (z.B. 2): ")
    return int(eingabe)


def run_extract(cfg: dict) -> None:
    pdf_k1 = resolve_path(cfg["pdf"]["k1"])
    json_k1 = resolve_path(cfg["json"]["k1"])
    pdf_a2 = resolve_path(cfg["pdf"]["a2"])
    json_a2 = resolve_path(cfg["json"]["a2"])

    print("Lese PDF ein (K1)...")
    count_k1 = extract_from_pdf(pdf_k1, json_k1)
    print(f"Erfolg! {count_k1} Spiele extrahiert -> {json_k1}")

    print("Lese PDF ein (A2)...")
    count_a2 = extract_from_pdf(pdf_a2, json_a2)
    print(f"Erfolg! {count_a2} Spiele extrahiert -> {json_a2}")


def run_tables(cfg: dict, matchday_input: int | None) -> None:
    if matchday_input is None:
        matchday_input = _prompt_matchday()

    # kompatibel zu bisherigen Skripten:
    # "dspieltag" = matchday - 1, "nspieltag" = matchday + 1
    matchday_current = matchday_input - 1
    matchday_next = matchday_input + 1

    logos_dir = cfg["paths"]["logos_dir"]

    ok_k1_current = generate_matchday_table(
        json_input=resolve_path(cfg["json"]["k1"]),
        output_tex=resolve_path(cfg["latex"]["k1_current"]),
        logos=cfg["logos"]["k1"],
        logos_dir=logos_dir,
        matchday=matchday_current,
    )

    ok_k1_next = generate_matchday_table(
        json_input=resolve_path(cfg["json"]["k1"]),
        output_tex=resolve_path(cfg["latex"]["k1_next"]),
        logos=cfg["logos"]["k1"],
        logos_dir=logos_dir,
        matchday=matchday_next,
    )

    ok_a2_current = generate_matchday_table(
        json_input=resolve_path(cfg["json"]["a2"]),
        output_tex=resolve_path(cfg["latex"]["a2_current"]),
        logos=cfg["logos"]["a2"],
        logos_dir=logos_dir,
        matchday=matchday_current,
    )

    ok_a2_next = generate_matchday_table(
        json_input=resolve_path(cfg["json"]["a2"]),
        output_tex=resolve_path(cfg["latex"]["a2_next"]),
        logos=cfg["logos"]["a2"],
        logos_dir=logos_dir,
        matchday=matchday_next,
    )
    if all([ok_k1_current, ok_k1_next, ok_a2_current, ok_a2_next]):
        print("Tabellen aktualisiert.")
    else:
        print("Hinweis: Für mindestens einen Spieltag wurden keine Spiele gefunden.")


def run_title(cfg: dict, matchday_input: int | None) -> None:
    if matchday_input is None:
        matchday_input = _prompt_matchday()

    teams = [
        {
            "key": "k1",
            "name": cfg["teams"]["k1"]["name"],
            "league": cfg["teams"]["k1"]["league"],
            "suffix": cfg["teams"]["k1"]["suffix"],
        },
        {
            "key": "a2",
            "name": cfg["teams"]["a2"]["name"],
            "league": cfg["teams"]["a2"]["league"],
            "suffix": cfg["teams"]["a2"]["suffix"],
        },
    ]

    json_paths = {
        "k1": resolve_path(cfg["json"]["k1"]),
        "a2": resolve_path(cfg["json"]["a2"]),
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

    for key in ["tabelle_k1", "tabelle_a2", "spielplan_1", "spielplan_2"]:
        widget_cfg = cfg["widgets"][key]
        export_widget(
            output_dir=output_dir,
            name=widget_cfg["output"],
            widget_root_id=widget_cfg["id"],
            club_url=cfg["widgets"]["club_url"],
            viewport=widget_cfg["viewport"],
        )

    print("Widgets exportiert.")


def _run_script(script_name: str, args: list[str]) -> None:
    script_path = Path(__file__).resolve().parent / script_name
    cmd = [sys.executable, str(script_path), *args]
    subprocess.run(cmd, check=True)


def run_scorers(cfg: dict) -> None:
    top = int(cfg["scorers"]["top"])
    k1_league = cfg["scorers"]["k1_league"]
    a2_league = cfg["scorers"]["a2_league"]

    _run_script("12_final_export_torjaegerk1.py", ["--league", k1_league, "--top", str(top)])
    _run_script("14_export_torjaegera2.py", ["--league", a2_league, "--top", str(top)])

    _run_script("13_json2tex_torjaegerk1.py", ["--league", k1_league, "--top", str(top)])
    _run_script("15_json2tex_torjaegera2.py", ["--league", a2_league, "--top", str(top)])

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

    args = parser.parse_args()

    if args.cmd == "weekly":
        run_extract(cfg)
        run_tables(cfg, args.matchday)
        run_title(cfg, args.matchday)
        run_widgets(cfg)
        run_scorers(cfg)
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


if __name__ == "__main__":
    main()

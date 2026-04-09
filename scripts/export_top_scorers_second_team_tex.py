#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Optional

# Mapping Vereinsname (wie er in deiner JSON steht) -> Logodatei in Bilder/logos
LOGO_NAMEN: dict[str, str] = {
  "O`traubling": "obertraubling.pdf",
  "Stadtamhof": "stadtamhof.png",
  "FK Phönix": "phoenix.png",
  "TV Barbing": "barbing.pdf",
  "SG SC Matting": "matting_oberndorf.pdf",
  "FC Kosova": "kosova.pdf",
  "Prüfening": "pruefening.pdf",
  "Oberhinkofen": "oberhinkofen.pdf",
  "TSV Oberisling Rgbg II": "oberisling.pdf",
  "SV Burgweinting Rgbg. II": "burgweinting.pdf",
  "VfR Regensburg II": "vfr_regensburg.pdf",
  "NK Hrvatska": "hrvatska.pdf",
  "TSV Neutraubling II zg.": "neutraubling.pdf"
}

LATEX_SPECIALS = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}


def latex_escape(s: str) -> str:
    return "".join(LATEX_SPECIALS.get(ch, ch) for ch in s)


def tex_path(path: Path) -> str:
    # Robust gegen Sonderzeichen/Unterstriche in Dateipfaden
    return r"\detokenize{" + str(path).replace("\\", "/") + "}"


def resolve_root_dirs(root: Path) -> tuple[Path, Path]:
    """
    Unterstützt sowohl 'bilder' als auch 'Bilder' als Ordnernamen.
    """
    bilder = root / "bilder"
    if bilder.exists():
        return root / "generated", bilder

    bilder = root / "Bilder"
    if bilder.exists():
        return root / "generated", bilder

    # Default: lege 'generated' an, Bilder-Pfad bleibt 'bilder'
    return root / "generated", root / "bilder"


def pick_player_image(images_dir: Path, slug: str, exts: list[str]) -> Optional[Path]:
    for ext in exts:
        p = images_dir / f"{slug}.{ext}"
        if p.exists():
            return p
    return None


def club_logo_path(logos_dir: Path, club: str) -> Optional[Path]:
    filename = LOGO_NAMEN.get(club)
    if not filename:
        return None
    p = logos_dir / filename
    return p if p.exists() else None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--json",
        default="",
        help="Input JSON (Default: generated/scorers_<league>.json)",
    )
    parser.add_argument(
        "--league",
        default="regensburg-a-klasse-2",
        help="Wird nur genutzt, wenn --json leer ist",
    )
    parser.add_argument(
        "--out",
        default="",
        help="Output .tex (Default: generated/scorers_<league>.tex)",
    )

    parser.add_argument(
        "--images-dir",
        default="",
        help="Ordner mit Spielerbildern (Default: bilder/scorers_<league>)",
    )
    parser.add_argument(
        "--logos-dir",
        default="",
        help="Ordner mit Vereinslogos (Default: bilder/logos)",
    )

    parser.add_argument("--top", type=int, default=10)

    # Caption default leer => keine Caption ohne CLI-Anpassung
    parser.add_argument("--caption", default="")
    parser.add_argument("--label", default="")

    parser.add_argument("--player-img-width-mm", type=int, default=10)
    parser.add_argument("--club-logo-width-mm", type=int, default=7)

    parser.add_argument(
        "--exts",
        default="png,jpg,jpeg,pdf",
        help="Spielerbild-Endungen (comma-separated)",
    )

    parser.add_argument("--include-assists", action="store_true")
    parser.add_argument("--include-games", action="store_true")

    parser.add_argument(
        "--no-table-env",
        action="store_true",
        help="Gibt nur tabularx aus (ohne table-Umgebung)",
    )
    parser.add_argument(
        "--strict-images",
        action="store_true",
        help="Wenn Spielerbilder fehlen: Exit-Code 2",
    )
    parser.add_argument(
        "--strict-logos",
        action="store_true",
        help="Wenn Vereinslogos fehlen: Exit-Code 3",
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    generated_dir, bilder_dir = resolve_root_dirs(root)

    json_path = Path(args.json) if args.json else generated_dir / (
        f"scorers_{args.league}.json"
    )
    out_path = Path(args.out) if args.out else generated_dir / (
        f"scorers_{args.league}.tex"
    )

    images_dir = (
        Path(args.images_dir)
        if args.images_dir
        else bilder_dir / f"scorers_{args.league}"
    )
    logos_dir = Path(args.logos_dir) if args.logos_dir else bilder_dir / "logos"

    exts = [e.strip().lower() for e in args.exts.split(",") if e.strip()]

    data: list[dict[str, Any]] = json.loads(json_path.read_text(encoding="utf-8"))
    data = data[: args.top]

    missing_player_images: list[str] = []
    missing_logos: list[str] = []

    # Layout: tabularx füllt die verfügbare Breite durch X-Spalten
    # Spalten: Spielerfoto | Pl | Spieler | Logo | Verein | Tore (+ optional)
    cols = ["c", "r", "X", "c", "X", "r"]
    head = ["", "Pl.", "Spieler", "", "Verein", "Tore"]

    if args.include_assists:
        cols.append("r")
        head.append("Assists")
    if args.include_games:
        cols.append("r")
        head.append("Sp.")

    lines: list[str] = []
    lines.append("% Auto-generated. Do not edit by hand.")
    lines.append("% Requires: \\usepackage{graphicx}")
    lines.append("% Requires: \\usepackage{booktabs}")
    lines.append("% Requires: \\usepackage{tabularx}")
    lines.append("% Note: table uses tabularx to fill \\linewidth.")

    if not args.no_table_env:
        lines.append("\\begin{table}[ht]")
        lines.append("\\centering")

    if args.caption.strip():
        lines.append("\\caption{" + latex_escape(args.caption) + "}")
    if args.label.strip():
        lines.append("\\label{" + latex_escape(args.label) + "}")

    lines.append("\\renewcommand{\\arraystretch}{1.25}")
    lines.append("\\setlength{\\tabcolsep}{6pt}")
    lines.append("\\begin{tabularx}{\\linewidth}{@{} " + " ".join(cols) + " @{} }")
    lines.append("\\toprule")
    lines.append(" & ".join(head) + " \\\\")
    lines.append("\\midrule")

    for row in data:
        rank = int(row["rank"])
        player = str(row["player"])
        club = str(row.get("club", ""))
        goals = int(row["goals"])

        slug = str(row.get("image_slug") or "").strip()
        if not slug:
            # Wenn du die JSON manuell editierst, sollte image_slug drin sein.
            # Fallback: nutze Spielername "roh" (kann Sonderzeichen enthalten).
            slug = player.strip().lower().replace(" ", "_")

        # Spielerbild
        p_img = pick_player_image(images_dir, slug, exts)
        if p_img is None:
            missing_player_images.append(f"{slug}.*")
            player_img_tex = (
                r"\rule{"
                + f"{args.player_img_width_mm}mm"
                + "}{"
                + f"{args.player_img_width_mm}mm"
                + "}"
            )
        else:
            player_img_tex = (
                r"\raisebox{-0.5\height}{\includegraphics[width="
                + f"{args.player_img_width_mm}mm"
                + "]{"
                + tex_path(p_img)
                + "}}"
            )

        # Vereinslogo
        c_logo = club_logo_path(logos_dir, club)
        if c_logo is None:
            if club.strip():
                missing_logos.append(club)
            club_logo_tex = (
                r"\rule{"
                + f"{args.club_logo_width_mm}mm"
                + "}{"
                + f"{args.club_logo_width_mm}mm"
                + "}"
            )
        else:
            club_logo_tex = (
                r"\raisebox{-0.5\height}{\includegraphics[width="
                + f"{args.club_logo_width_mm}mm"
                + "]{"
                + tex_path(c_logo)
                + "}}"
            )

        cells = [
            player_img_tex,
            str(rank),
            latex_escape(player),
            club_logo_tex,
            latex_escape(club),
            str(goals),
        ]

        if args.include_assists:
            assists = row.get("assists")
            cells.append("" if assists is None else str(int(assists)))

        if args.include_games:
            games = row.get("games")
            cells.append("" if games is None else str(int(games)))

        lines.append(" & ".join(cells) + " \\\\")

    lines.append("\\bottomrule")
    lines.append("\\end{tabularx}")

    if not args.no_table_env:
        lines.append("\\end{table}")

    lines.append("")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")

    print(f"Wrote {out_path}")
    print(f"Player images dir: {images_dir}")
    print(f"Club logos dir: {logos_dir}")

    # Dedupe missing lists but keep readable output
    if missing_player_images:
        missing_player_images = sorted(set(missing_player_images))
        print("Fehlende Spielerbilder:")
        for m in missing_player_images:
            print(f"  {m}")
        if args.strict_images:
            raise SystemExit(2)

    if missing_logos:
        missing_logos = sorted(set(missing_logos))
        print("Fehlende Vereinslogos (Mapping fehlt oder Datei fehlt):")
        for m in missing_logos:
            print(f"  {m}")
        if args.strict_logos:
            raise SystemExit(3)


if __name__ == "__main__":
    main()
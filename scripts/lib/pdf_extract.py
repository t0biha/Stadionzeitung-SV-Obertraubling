from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pdfplumber


def extract_from_pdf(pdf_path: Path, json_output: Path) -> int:
    if not pdf_path.exists():
        raise FileNotFoundError(f"Datei nicht gefunden: {pdf_path}")

    matches: list[dict[str, Any]] = []
    current_spieltag = 0

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue

            for line in text.split("\n"):
                line = line.strip()

                # 1. Spieltag erkennen (z.B. "1 . SPIELTAG")
                if "SPIELTAG" in line:
                    parts = line.split(".")
                    if parts[0].strip().isdigit():
                        current_spieltag = int(parts[0].strip())
                    continue

                # 2. Spielzeile erkennen
                # Beispiel: "008 25.07.2025 18:30 Team A - Team B"
                if len(line) > 10 and line[:3].isdigit():
                    parts = line.split()
                    if len(parts) < 5:
                        continue

                    try:
                        datum = parts[1]
                        uhrzeit = parts[2]

                        rest_text = " ".join(parts[3:])
                        if " - " in rest_text:
                            teams_raw = rest_text.split(" - ")
                            heim = teams_raw[0].strip()
                            gast_part = teams_raw[1].strip()

                            ergebnis = "-:-"
                            gast = gast_part

                            last_word = gast_part.split()[-1]
                            if ":" in last_word and any(c.isdigit() for c in last_word):
                                ergebnis = last_word
                                gast = " ".join(gast_part.split()[:-1])

                            matches.append(
                                {
                                    "spieltag": current_spieltag,
                                    "datum": datum,
                                    "uhrzeit": uhrzeit,
                                    "heim": heim,
                                    "gast": gast,
                                    "ergebnis": ergebnis,
                                }
                            )
                    except Exception:
                        continue

    json_output.parent.mkdir(parents=True, exist_ok=True)
    json_output.write_text(
        json.dumps(matches, ensure_ascii=False, indent=4), encoding="utf-8"
    )

    return len(matches)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import json
import os
import re
import unicodedata
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


@dataclass(frozen=True)
class ScorerRow:
    rank: int
    player: str
    club: str
    goals: int
    assists: Optional[int] = None
    games: Optional[int] = None
    image_slug: str = ""


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def now_stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def clean_lines(text: str) -> list[str]:
    lines = []
    for raw in text.splitlines():
        s = raw.replace("￼", "").replace("\u200b", "").strip()
        s = re.sub(r"\s+", " ", s).strip()
        if s:
            lines.append(s)
    return lines


def parse_int_line(s: str) -> Optional[int]:
    s = s.strip()
    if re.fullmatch(r"\d+", s):
        return int(s)
    return None


def parse_rank_line(s: str) -> Optional[int]:
    s = s.strip()
    m = re.fullmatch(r"(\d+)\.", s)
    if not m:
        return None
    return int(m.group(1))


def split_player_club_if_glued(s: str) -> tuple[str, str]:
    """
    Fallback, falls Spieler+Verein ohne Zeilenumbruch zusammenkleben.
    Wir splitten an typischen Vereins-Präfixen.
    """
    prefixes = [
        "FC ",
        "SV ",
        "TSV ",
        "SC ",
        "SG ",
        "SpVgg ",
        "DJK ",
        "TSG ",
        "TuS ",
        "TV ",
        "ASV ",
        "FSV ",
        "SSV ",
        "VfB ",
        "VfR ",
    ]

    for p in prefixes:
        idx = s.find(p)
        if idx > 0:
            player = s[:idx].strip()
            club = s[idx:].strip()
            if player and club:
                return player, club

    return s.strip(), ""


def slugify_player(name: str) -> str:
    """
    Stabiler Dateiname aus Spielernamen:
    - lowercase
    - Umlaute/Diakritika entfernen
    - nur a-z0-9 und _
    """
    s = name.strip().lower()
    s = s.replace("ß", "ss")

    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))

    s = s.replace("&", " und ")
    s = re.sub(r"[^\w\s-]", "", s, flags=re.UNICODE)
    s = re.sub(r"[\s-]+", "_", s).strip("_")

    if not s:
        return "unknown"
    return s


def click_consent(page, mode: str) -> bool:
    if mode == "none":
        return False

    if mode == "accept":
        patterns = [
            re.compile(r"alle\s+akzeptieren", re.I),
            re.compile(r"\bakzeptieren\b", re.I),
            re.compile(r"\bzustimmen\b", re.I),
        ]
    else:
        patterns = [
            re.compile(r"\bablehnen\b", re.I),
            re.compile(r"einstellungen\s*/\s*ablehnen", re.I),
        ]

    def try_frame(frame) -> bool:
        for pat in patterns:
            try:
                btn = frame.get_by_role("button", name=pat)
                if btn.count() > 0 and btn.first.is_visible():
                    btn.first.click(timeout=2500)
                    return True
            except Exception:
                pass

            try:
                btn = frame.locator("button", has_text=pat)
                if btn.count() > 0 and btn.first.is_visible():
                    btn.first.click(timeout=2500)
                    return True
            except Exception:
                pass

        return False

    for frame in page.frames:
        if try_frame(frame):
            page.wait_for_timeout(800)
            return True

    return False


def wait_for_scorers_content(page, timeout_ms: int) -> None:
    js = """
    () => {
      const t = (document.body && document.body.innerText) || "";
      return t.includes("Torjäger")
        && t.includes("Pl.")
        && t.includes("Spieler")
        && t.includes("Tore");
    }
    """
    page.wait_for_function(js, timeout=timeout_ms)


def auto_scroll(page, steps: int, pause_ms: int) -> None:
    for _ in range(steps):
        page.mouse.wheel(0, 2000)
        page.wait_for_timeout(pause_ms)


def parse_scorers_from_text(text: str) -> list[ScorerRow]:
    lines = clean_lines(text)

    start = 0
    for i, l in enumerate(lines):
        ll = l.lower()
        if "pl." in ll and "spieler" in ll and "tore" in ll:
            start = i + 1
            break

    out: list[ScorerRow] = []
    i = start

    while i < len(lines):
        rank = parse_rank_line(lines[i])
        if rank is None:
            i += 1
            continue
        i += 1

        if i >= len(lines):
            break

        # Spielerzeile (und evtl. Verein in nächster Zeile)
        player_line = lines[i]
        i += 1

        club = ""
        if i < len(lines) and parse_int_line(lines[i]) is None:
            # nächste Zeile ist nicht rein numerisch -> wahrscheinlich Verein
            # (aber nicht, wenn es direkt der nächste Rank wäre)
            if parse_rank_line(lines[i]) is None:
                club = lines[i]
                i += 1

        # Wenn Spieler+Verein zusammengeklebt sind, splitten
        if not club:
            player_line, club = split_player_club_if_glued(player_line)

        if i >= len(lines):
            break

        goals = parse_int_line(lines[i])
        if goals is None:
            i += 1
            continue
        i += 1

        assists = None
        games = None

        if i < len(lines):
            assists = parse_int_line(lines[i])
            if assists is not None:
                i += 1

        if i < len(lines):
            games = parse_int_line(lines[i])
            if games is not None:
                i += 1

        out.append(
            ScorerRow(
                rank=rank,
                player=player_line,
                club=club,
                goals=goals,
                assists=assists,
                games=games,
                image_slug=slugify_player(player_line),
            )
        )

    out.sort(key=lambda r: r.rank)
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--league",
        default="regensburg-kreisliga-1",
        help="FuPa league slug, z.B. regensburg-kreisliga-1",
    )
    parser.add_argument(
        "--out",
        default="",
        help="Output JSON (Default: generated/scorers_<league>.json)",
    )
    parser.add_argument("--top", type=int, default=50)
    parser.add_argument("--headful", action="store_true")
    parser.add_argument(
        "--consent",
        default="accept",
        choices=["accept", "reject", "none"],
    )
    parser.add_argument("--timeout-seconds", type=int, default=120)
    parser.add_argument("--scroll-steps", type=int, default=12)
    parser.add_argument("--debug-dir", default="")
    args = parser.parse_args()

    url = f"https://www.fupa.net/league/{args.league}/scorers"
    timeout_ms = args.timeout_seconds * 1000

    root = Path(__file__).resolve().parents[1]
    generated_dir = root / "generated"

    out_path = Path(args.out) if args.out else generated_dir / (
        f"scorers_{args.league}.json"
    )

    debug_dir = Path(args.debug_dir) if args.debug_dir else None
    if debug_dir:
        debug_dir = debug_dir / now_stamp()
        ensure_dir(debug_dir)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not args.headful)
        context = browser.new_context(
            locale="de-DE",
            viewport={"width": 1400, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/121.0.0.0 Safari/537.36"
            ),
        )
        page = context.new_page()

        page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)

        if debug_dir:
            (debug_dir / "url.txt").write_text(url + "\n", encoding="utf-8")
            (debug_dir / "before_consent.html").write_text(
                page.content(), encoding="utf-8"
            )
            try:
                page.screenshot(path=str(debug_dir / "before_consent.png"))
            except Exception:
                pass

        clicked = click_consent(page, mode=args.consent)
        if clicked:
            page.reload(wait_until="domcontentloaded", timeout=timeout_ms)

        try:
            wait_for_scorers_content(page, timeout_ms=timeout_ms)
        except PlaywrightTimeoutError:
            if debug_dir:
                (debug_dir / "final.html").write_text(page.content(), encoding="utf-8")
                try:
                    page.screenshot(path=str(debug_dir / "final.png"))
                except Exception:
                    pass
            browser.close()
            raise SystemExit(
                "Timeout: Torjäger-Inhalte nicht geladen. "
                "Nutze --headful und --debug-dir."
            )

        if args.scroll_steps > 0:
            auto_scroll(page, steps=args.scroll_steps, pause_ms=300)
            page.wait_for_timeout(500)

        try:
            text = page.locator("main").inner_text(timeout=5000)
        except Exception:
            text = page.locator("body").inner_text(timeout=5000)

        if debug_dir:
            (debug_dir / "page_text.txt").write_text(text, encoding="utf-8")

        browser.close()

    rows = parse_scorers_from_text(text)[: args.top]
    if not rows:
        raise SystemExit("Keine Zeilen extrahiert (Parser). Nutze --debug-dir.")

    ensure_dir(out_path.parent)
    payload = [asdict(r) for r in rows]
    out_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"Wrote {out_path} ({len(rows)} rows)")
    print("Erwartete Bild-Dateinamen (im Bilder-Ordner):")
    for r in rows:
        print(f"  {r.image_slug}.png   # {r.player}")


if __name__ == "__main__":
    main()
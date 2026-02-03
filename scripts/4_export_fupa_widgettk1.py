from __future__ import annotations

from pathlib import Path

import fitz  # PyMuPDF
from playwright.sync_api import sync_playwright


# ============================================================
# Projektstruktur: project/Scripts/<dieses Skript>
#                 project/Generated/<Ausgaben>
# ============================================================

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
OUTPUT_DIR = PROJECT_ROOT / "Generated"

HTML_FILE = OUTPUT_DIR / "fupa_widgettk1.html"
RAW_PDF_FILE = OUTPUT_DIR / "fupa_widgettk1_raw.pdf"
FINAL_PDF_FILE = OUTPUT_DIR / "fupa_widgettk1.pdf"


# ============================================================
# Widget-Konfiguration
# ============================================================

WIDGET_ROOT_ID = "fp-widget_root-38UgvC3Apqel9wRchfYEpuB8oLR"
CLUB_URL = "https://www.fupa.net/club/sv-obertraubling"


# ============================================================
# HTML Wrapper (minimal)
# ============================================================

HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="de">
  <head>
    <meta charset="utf-8" />
    <title>FuPa Widget Export</title>
    <style>
      @page {{
        size: A4;
        margin: 12mm;
      }}
      body {{
        margin: 0;
        padding: 0;
        font-family: Arial, sans-serif;
      }}
      #{root_id} {{
        max-width: 180mm;
      }}
    </style>
  </head>
  <body>
    <div id="{root_id}">
      <a href="{club_url}" target="_blank" rel="noopener">
        SV Obertraubling auf FuPa
      </a>
    </div>

    <script src="https://widget-api.fupa.net/vendor/widget.js?v1"></script>
  </body>
</html>
"""


def write_html(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    html = HTML_TEMPLATE.format(root_id=WIDGET_ROOT_ID, club_url=CLUB_URL)
    path.write_text(html, encoding="utf-8")


def render_raw_pdf(html_path: Path, pdf_path: Path) -> None:
    html_url = html_path.resolve().as_uri()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 820, "height": 1400})

        # networkidle ist hier hilfreich, weil das Widget nachlädt
        page.goto(html_url, wait_until="networkidle")

        # warten bis irgendwas gerendert wurde (iframe oder zusätzlicher Inhalt)
        page.wait_for_selector(f"#{WIDGET_ROOT_ID}", state="attached")
        page.wait_for_function(
            """
            (rootId) => {
              const el = document.getElementById(rootId);
              if (!el) return false;
              const hasIframe = el.querySelector("iframe") !== null;
              const hasMoreContent = el.querySelectorAll("*").length > 1;
              return hasIframe || hasMoreContent;
            }
            """,
            arg=WIDGET_ROOT_ID,
            timeout=30_000,
        )

        # kleiner Puffer für Fonts/Bilder
        page.wait_for_timeout(1500)

        page.emulate_media(media="screen")
        page.pdf(
            path=str(pdf_path),
            format="A4",
            print_background=True,
            prefer_css_page_size=True,
        )

        browser.close()


def find_top_crop_y(page: fitz.Page) -> float | None:
    """
    Wir schneiden oberhalb der Tabellenkopfzeile ab.
    Statt nach "KREISLIGA" zu suchen (kann variieren), suchen wir nach
    typischen Spaltenüberschriften ("Pl.", "Team", "Sp.", ...).
    """
    header_terms = ["Pl.", "Team", "Sp.", "S-U-N", "Tore", "Diff.", "Pkt."]

    hits: list[fitz.Rect] = []
    for term in header_terms:
        hits.extend(page.search_for(term))

    if not hits:
        return None

    # kleinste y0-Position = weit oben
    return min(r.y0 for r in hits)


def find_bottom_crop_y(page: fitz.Page) -> float | None:
    """
    Wir schneiden den Footer ab. Typische Footer-Texte im Widget:
    "auf FuPa", "FuPa Widget", "©"
    Wir nehmen die oberste y0-Position des Footer-Blocks und schneiden darüber ab.
    """
    footer_terms = ["FuPa Widget", "auf FuPa", "© FuPa", "©"]

    hits: list[fitz.Rect] = []
    for term in footer_terms:
        hits.extend(page.search_for(term))

    if not hits:
        return None

    # Footer ist unten -> nimmt die größte y0 Position
    return max(r.y0 for r in hits)


def crop_header_footer(
    input_pdf: Path,
    output_pdf: Path,
    *,
    pad_top_pt: float = 6.0,
    pad_bottom_pt: float = 6.0,
    fallback_top_crop_pt: float = 70.0,
    fallback_bottom_crop_pt: float = 70.0,
) -> None:
    """
    Cropt Header und Footer weg.
    - bevorzugt per Text-Erkennung (stabiler)
    - fällt auf fixe Werte zurück, wenn Text nicht auffindbar ist
      (z.B. wenn Chromium es als Bild gerendert hat)
    """
    doc = fitz.open(input_pdf)

    for page in doc:
        rect = page.rect

        top_y = find_top_crop_y(page)
        bottom_y = find_bottom_crop_y(page)

        if top_y is None:
            crop_top = rect.y0 + fallback_top_crop_pt
        else:
            crop_top = max(rect.y0, top_y - pad_top_pt)

        if bottom_y is None:
            crop_bottom = rect.y1 - fallback_bottom_crop_pt
        else:
            crop_bottom = min(rect.y1, bottom_y - pad_bottom_pt)

        # Sicherheitsklemmen
        min_height = 200  # pt, verhindert "alles weg"
        if crop_bottom - crop_top < min_height:
            # fallback etwas konservativer, falls Erkennung Mist gebaut hat
            crop_top = rect.y0 + min(fallback_top_crop_pt, 40.0)
            crop_bottom = rect.y1 - min(fallback_bottom_crop_pt, 40.0)

        new_rect = fitz.Rect(rect.x0, crop_top, rect.x1, crop_bottom)
        page.set_cropbox(new_rect)

    # atomar überschreiben: erst in tmp speichern, dann ersetzen
    tmp = output_pdf.with_suffix(".tmp.pdf")
    doc.save(tmp)
    doc.close()
    tmp.replace(output_pdf)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 1) HTML & RAW-PDF immer überschreiben
    write_html(HTML_FILE)
    render_raw_pdf(HTML_FILE, RAW_PDF_FILE)

    # 2) Header + Footer wegcroppen und FINAL-PDF überschreiben
    crop_header_footer(RAW_PDF_FILE, FINAL_PDF_FILE)

    print("✅ Fertig (überschrieben):")
    print(f"   HTML:  {HTML_FILE}")
    print(f"   RAW:   {RAW_PDF_FILE}")
    print(f"   FINAL: {FINAL_PDF_FILE}")


if __name__ == "__main__":
    main()
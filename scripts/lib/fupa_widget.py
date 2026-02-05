from __future__ import annotations

from pathlib import Path

import fitz  # PyMuPDF
from playwright.sync_api import ViewportSize, sync_playwright

HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="de">
  <head>
    <meta charset="utf-8" />
    <title>FuPa Widget Export</title>
    <style>
      body {{
        margin: 0;
        padding: 0;
        font-family: Arial, sans-serif;
      }}
      #{root_id} {{
                width: 100%;
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


def write_html(path: Path, root_id: str, club_url: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    html = HTML_TEMPLATE.format(root_id=root_id, club_url=club_url)
    path.write_text(html, encoding="utf-8")


def render_raw_pdf(
    html_path: Path,
    pdf_path: Path,
    *,
    viewport: ViewportSize,
    widget_root_id: str,
) -> None:
    html_url = html_path.resolve().as_uri()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport=viewport)

        page.goto(html_url, wait_until="networkidle")

        page.wait_for_selector(f"#{widget_root_id}", state="attached")
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
            arg=widget_root_id,
            timeout=30_000,
        )

        page.wait_for_timeout(1500)

        bbox = page.evaluate(
            """
            (rootId) => {
                const el = document.getElementById(rootId);
                if (!el) return null;
                const rect = el.getBoundingClientRect();
                const iframe = el.querySelector("iframe");
                const iw = iframe ? iframe.offsetWidth : 0;
                const ih = iframe ? iframe.offsetHeight : 0;
                const width = Math.ceil(Math.max(rect.width, el.scrollWidth, iw));
                const height = Math.ceil(Math.max(rect.height, el.scrollHeight, ih));
                return { width, height };
            }
            """,
            arg=widget_root_id,
        )
        if bbox:
            content_width = int(bbox["width"])
            content_height = int(bbox["height"])
            pdf_width = max(content_width, int(viewport["width"]))
            pdf_height = max(content_height, int(viewport["height"]))
        else:
            content_height = int(viewport["height"])
            pdf_width = int(viewport["width"])
            pdf_height = int(viewport["height"])

        page.emulate_media(media="screen")
        page.pdf(
            path=str(pdf_path),
            width=f"{pdf_width}px",
            height=f"{pdf_height}px",
            print_background=True,
            prefer_css_page_size=False,
        )

        browser.close()


def find_top_crop_y(page: fitz.Page) -> float | None:
    header_terms = ["Pl.", "Team", "Sp.", "S-U-N", "Tore", "Diff.", "Pkt."]

    hits: list[fitz.Rect] = []
    for term in header_terms:
        hits.extend(page.search_for(term))

    if not hits:
        return None

    return min(r.y0 for r in hits)


def find_bottom_crop_y(page: fitz.Page) -> float | None:
    footer_terms = ["FuPa Widget", "auf FuPa", "© FuPa", "©"]

    hits: list[fitz.Rect] = []
    for term in footer_terms:
        hits.extend(page.search_for(term))

    if not hits:
        return None

    return max(r.y0 for r in hits)


def crop_header_footer(
    input_pdf: Path,
    output_pdf: Path,
    *,
    pad_top_pt: float = 6.0,
    pad_bottom_pt: float = 6.0,
    fallback_top_crop_pt: float = 70.0,
    fallback_bottom_crop_pt: float = 70.0,
    max_height_pt: float | None = None,
    max_height_ratio: float | None = None,
) -> None:
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

        min_height = 200
        if crop_bottom - crop_top < min_height:
            crop_top = rect.y0 + min(fallback_top_crop_pt, 40.0)
            crop_bottom = rect.y1 - min(fallback_bottom_crop_pt, 40.0)

        if max_height_pt is not None:
            crop_bottom = min(crop_bottom, crop_top + max_height_pt)
        elif max_height_ratio is not None:
            full_height = crop_bottom - crop_top
            crop_bottom = crop_top + max(200.0, full_height * max_height_ratio)

        new_rect = fitz.Rect(rect.x0, crop_top, rect.x1, crop_bottom)
        page.set_cropbox(new_rect)

    tmp = output_pdf.with_suffix(".tmp.pdf")
    doc.save(tmp)
    doc.close()
    tmp.replace(output_pdf)


def export_widget(
    *,
    output_dir: Path,
    name: str,
    widget_root_id: str,
    club_url: str,
    viewport: ViewportSize,
    max_height_px: int | None = None,
    max_height_ratio: float | None = None,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    html_file = output_dir / f"{name}.html"
    raw_pdf_file = output_dir / f"{name}_raw.pdf"
    final_pdf_file = output_dir / f"{name}.pdf"

    write_html(html_file, widget_root_id, club_url)
    render_raw_pdf(
        html_file,
        raw_pdf_file,
        viewport=viewport,
        widget_root_id=widget_root_id,
    )
    crop_header_footer(
        raw_pdf_file,
        final_pdf_file,
        max_height_pt=float(max_height_px) if max_height_px is not None else None,
        max_height_ratio=max_height_ratio,
    )

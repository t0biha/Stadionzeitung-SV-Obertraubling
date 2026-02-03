from pathlib import Path
import fitz  # PyMuPDF


# ============================================================
# Pfade (an deine Struktur angepasst)
# ============================================================

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
GENERATED_DIR = PROJECT_ROOT / "Generated"

PDF_IN = GENERATED_DIR / "fupa_widget.pdf"
PDF_OUT = GENERATED_DIR / "fupa_widget_cropped.pdf"


# ============================================================
# Crop-Werte (in Punkt, 72 pt = 1 inch)
# Feinjustierung möglich, diese Werte passen i. d. R. gut
# ============================================================

CROP_TOP_PT = 70     # Überschrift entfernen
CROP_BOTTOM_PT = 45  # FuPa-Footer entfernen


# ============================================================
# PDF zuschneiden
# ============================================================

def crop_pdf(input_pdf: Path, output_pdf: Path) -> None:
    doc = fitz.open(input_pdf)

    for page in doc:
        rect = page.rect

        new_rect = fitz.Rect(
            rect.x0,
            rect.y0 + CROP_TOP_PT,
            rect.x1,
            rect.y1 - CROP_BOTTOM_PT,
        )

        page.set_cropbox(new_rect)

    doc.save(output_pdf)
    doc.close()

 
# ============================================================
# Main
# ============================================================

if __name__ == "__main__":
    crop_pdf(PDF_IN, PDF_OUT)
    print("✅ PDF Header & Footer entfernt:")
    print(f"   {PDF_OUT}")
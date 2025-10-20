#!/usr/bin/env python3
"""
Robust PDF → Markdown OCR for macOS (Apple Silicon friendly).
Avoids pypdfium2 (which can "trace trap" on some PDFs). Uses PyMuPDF to render pages.

Setup once:
  brew install tesseract poppler
  pip install pymupdf pillow pytesseract

Hardcoded input path below. Edit PDF_PATH and run:  python ocr_pdf_to_md.py
"""

import os
from concurrent.futures import ThreadPoolExecutor, as_completed

import fitz  # PyMuPDF
from PIL import Image
import pytesseract

# --------- Hardcoded paths (edit these) ----------
PDF_PATH = "/Users/nic/Dropbox/Kaltura/clients/puig/250904 Puig Streaming Requirements_en.pdf"
OUTPUT_PATH = os.path.splitext(PDF_PATH)[0] + "_extracted.md"
# Optional: if tesseract isn't on PATH, set the binary explicitly:
# pytesseract.pytesseract.tesseract_cmd = "/opt/homebrew/bin/tesseract"
# -------------------------------------------------

LANG = "eng"    # e.g., "eng+deu" if you install extra language packs
DPI = 300       # 300 is a good balance for OCR quality
WORKERS = 4     # If you still see crashes, set to 1


def render_page_to_image(doc: fitz.Document, page_index: int, dpi: int) -> Image.Image:
    page = doc.load_page(page_index)
    # Compute zoom factor from desired DPI (72 DPI base)
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    return img


def ocr_page(pdf_path: str, page_index: int, dpi: int, lang: str) -> tuple[int, str]:
    # Re-open per thread to avoid shared state issues
    with fitz.open(pdf_path) as doc:
        img = render_page_to_image(doc, page_index, dpi)
    text = pytesseract.image_to_string(img, lang=lang)
    return page_index, f"\n\n<!-- Page {page_index + 1} -->\n\n{text.strip()}\n"


def main():
    if not os.path.isfile(PDF_PATH):
        raise FileNotFoundError(f"File not found: {PDF_PATH}")

    # Determine page count
    with fitz.open(PDF_PATH) as doc:
        total_pages = len(doc)

    results = {}
    with ThreadPoolExecutor(max_workers=max(1, WORKERS)) as ex:
        futures = [ex.submit(ocr_page, PDF_PATH, i, DPI, LANG) for i in range(total_pages)]
        for fut in as_completed(futures):
            idx, page_md = fut.result()
            results[idx] = page_md

    # Assemble in order
    md_text = "".join(results[i] for i in range(total_pages)).strip()

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(md_text)

    print(f"Done. Wrote Markdown to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
"""PDF parser: text/tables (pdfplumber) + page images (pymupdf)."""

from __future__ import annotations

from pathlib import Path
from typing import TypedDict

import pdfplumber
import pymupdf


class PDFTextPage(TypedDict):
    page_num: int
    text: str
    tables: list[list[list[str]]]


class PDFTextResult(TypedDict):
    file_type: str  # "pdf"
    page_count: int
    pages: list[PDFTextPage]


DEFAULT_TABLE_SETTINGS: dict = {
    "vertical_strategy": "text",
    "horizontal_strategy": "text",
    "snap_tolerance": 3,
}


def extract_pdf_text(path: str | Path) -> PDFTextResult:
    """Extract text + tables from all pages.

    Chinese title blocks typically have no visible borders, so
    `table_settings` is required to detect them heuristically.
    """
    p = Path(path)
    if not p.exists():
        return {"file_type": "pdf", "page_count": 0, "pages": []}
    pages: list[PDFTextPage] = []
    with pdfplumber.open(p) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            pages.append(
                {
                    "page_num": i,
                    "text": page.extract_text() or "",
                    "tables": page.extract_tables(table_settings=DEFAULT_TABLE_SETTINGS) or [],
                }
            )
    return {"file_type": "pdf", "page_count": len(pages), "pages": pages}


def extract_pdf_images(path: str | Path, dpi: int = 150) -> list[bytes]:
    """Render each page as PNG bytes (one per page)."""
    p = Path(path)
    if not p.exists():
        return []
    images: list[bytes] = []
    with pymupdf.open(p) as doc:
        for page in doc:
            pix = page.get_pixmap(dpi=dpi, alpha=False)
            images.append(pix.tobytes("png"))
    return images

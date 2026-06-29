"""Tests for src/deepdraw/tools/pdf.py."""

from __future__ import annotations

from deepdraw.tools.pdf import extract_pdf_images, extract_pdf_text


def test_extract_pdf_text_returns_pages(sample_pdf) -> None:
    result = extract_pdf_text(sample_pdf)
    assert result["file_type"] == "pdf"
    assert result["page_count"] == 1
    assert len(result["pages"]) == 1
    assert "DeepDraw Test Drawing" in result["pages"][0]["text"]
    assert "Q235B" in result["pages"][0]["text"]


def test_extract_pdf_text_handles_missing_file(tmp_path) -> None:
    result = extract_pdf_text(tmp_path / "nope.pdf")
    assert result["page_count"] == 0
    assert result["pages"] == []


def test_extract_pdf_images_returns_png_bytes(sample_pdf) -> None:
    images = extract_pdf_images(sample_pdf, dpi=72)
    assert len(images) == 1
    assert images[0][:8] == b"\x89PNG\r\n\x1a\n"  # PNG magic bytes


def test_extract_pdf_images_dpi_affects_size(sample_pdf) -> None:
    small = extract_pdf_images(sample_pdf, dpi=50)
    large = extract_pdf_images(sample_pdf, dpi=200)
    assert len(small[0]) < len(large[0])

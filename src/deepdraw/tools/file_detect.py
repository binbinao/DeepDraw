"""File type detection for engineering drawings."""

from __future__ import annotations

from pathlib import Path


def detect_file_type(path: str | Path) -> str:
    """Detect by magic bytes (primary) and extension (fallback).

    Returns: "pdf" | "dxf" | "unknown"
    """
    p = Path(path)
    if not p.exists():
        return "unknown"
    try:
        header = p.read_bytes()[:8]
    except OSError:
        return "unknown"
    if header.startswith(b"%PDF"):
        return "pdf"
    if p.suffix.lower() == ".dxf":
        return "dxf"
    if p.suffix.lower() == ".pdf":
        return "pdf"
    return "unknown"


def is_supported(path: str | Path) -> bool:
    return detect_file_type(path) != "unknown"

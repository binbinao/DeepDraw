"""FastMCP server exposing DeepDraw tools via Model Context Protocol.

Run as:  python -m deepdraw.tools.mcp_server
Transport: stdio (default) — for local subprocess clients
"""

from __future__ import annotations

import base64

from mcp.server.fastmcp import FastMCP

from deepdraw.tools.dxf import extract_dxf_entities
from deepdraw.tools.file_detect import detect_file_type
from deepdraw.tools.mcp_tools import lookup_internal_standard, query_material_price
from deepdraw.tools.pdf import extract_pdf_images, extract_pdf_text

mcp = FastMCP("deepdraw-tools")


@mcp.tool()
def detect_drawing_type(path: str) -> str:
    """Detect engineering drawing file type. Returns pdf/dxf/unknown."""
    return detect_file_type(path)


@mcp.tool()
def parse_pdf(path: str, extract_images: bool = True) -> dict:
    """Parse PDF: extract text/tables + render pages as base64 PNGs."""
    result = extract_pdf_text(path)
    if extract_images:
        result["images_b64"] = [
            base64.b64encode(img).decode("ascii") for img in extract_pdf_images(path)
        ]
    return result


@mcp.tool()
def parse_dxf(path: str) -> dict:
    """Parse DXF: extract geometry entities from model space."""
    return extract_dxf_entities(path)


@mcp.tool()
def get_material_price(material_code: str) -> str | None:
    """Get unit price (元/吨) for a material code."""
    price = query_material_price(material_code)
    return str(price) if price is not None else None


@mcp.tool()
def lookup_standard(standard_id: str) -> dict | None:
    """Look up internal standard by ID."""
    return lookup_internal_standard(standard_id)


if __name__ == "__main__":
    mcp.run()

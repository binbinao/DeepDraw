"""Tests for MCP tool stubs and FastMCP server."""

from __future__ import annotations

from decimal import Decimal

from deepdraw.tools.mcp_server import mcp
from deepdraw.tools.mcp_tools import lookup_internal_standard, query_material_price


def test_query_material_price_known() -> None:
    assert query_material_price("Q235B") == Decimal("5800.00")
    assert query_material_price("q235b") == Decimal("5800.00")  # case-insensitive


def test_query_material_price_unknown() -> None:
    assert query_material_price("UNKNOWN_MATERIAL") is None


def test_lookup_internal_standard_known() -> None:
    result = lookup_internal_standard("GB/T 3098.1-2010")
    assert result is not None
    assert "title" in result


def test_lookup_internal_standard_unknown() -> None:
    assert lookup_internal_standard("GB/NONEXISTENT") is None


def test_mcp_server_exposes_5_tools() -> None:
    """FastMCP server should have registered all 5 tools."""
    tools = mcp._tool_manager._tools  # internal API, stable in 1.x
    assert len(tools) == 5
    expected = {
        "detect_drawing_type",
        "parse_pdf",
        "parse_dxf",
        "get_material_price",
        "lookup_standard",
    }
    assert expected.issubset(set(tools.keys()))

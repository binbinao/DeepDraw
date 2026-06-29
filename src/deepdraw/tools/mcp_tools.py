"""MCP tool stubs for ERP/PDM integration. Phase 5 will replace with RAG/ERP."""

from __future__ import annotations

from decimal import Decimal

_MATERIAL_PRICES: dict[str, Decimal] = {
    "Q235B": Decimal("5800.00"),
    "Q345B": Decimal("6200.00"),
    "SS304": Decimal("22000.00"),
    "AL6061": Decimal("28000.00"),
}

_STANDARDS: dict[str, dict] = {
    "GB/T 3098.1-2010": {"title": "紧固件机械性能 螺栓、螺钉和螺柱", "scope": "M3-M64"},
    "GB/T 118-2000": {"title": "内六角圆柱头螺钉", "scope": "M3-M20"},
}


def query_material_price(material_code: str) -> Decimal | None:
    """Return the unit price (元/吨) for a material code, or None if unknown."""
    return _MATERIAL_PRICES.get(material_code.upper().replace(" ", ""))


def lookup_internal_standard(standard_id: str) -> dict | None:
    """Return metadata for a standard ID, or None if unknown."""
    return _STANDARDS.get(standard_id)

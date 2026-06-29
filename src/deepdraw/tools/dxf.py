"""DXF entity extractor (ezdxf, tolerant mode)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import ezdxf
from ezdxf import recover as ezdxf_recover

SUPPORTED_TYPES = {"LINE", "CIRCLE", "ARC", "TEXT", "MTEXT", "DIMENSION", "HATCH"}


def _iter_supported_types(msp, types: set[str]):
    """ezdxf 1.4: `|` is not supported in query string; use union() between per-type queries."""
    remaining = set(types)
    it = msp.query(remaining.pop())
    while remaining:
        it = it.union(msp.query(remaining.pop()))
    return it


def _entity_to_dict(entity: ezdxf.entities.DXFGraphic) -> dict[str, Any]:
    """Serialize one DXF entity to a JSON-friendly dict."""
    et = entity.dxftype()
    base: dict[str, Any] = {"type": et, "layer": entity.dxf.layer}
    if et == "LINE":
        base["start"] = list(entity.dxf.start)
        base["end"] = list(entity.dxf.end)
    elif et == "CIRCLE":
        base["center"] = list(entity.dxf.center)
        base["radius"] = entity.dxf.radius
    elif et == "ARC":
        base["center"] = list(entity.dxf.center)
        base["radius"] = entity.dxf.radius
        base["start_angle"] = entity.dxf.start_angle
        base["end_angle"] = entity.dxf.end_angle
    elif et in ("TEXT", "MTEXT"):
        base["text"] = entity.dxf.text if et == "TEXT" else entity.text
        base["insert"] = list(entity.dxf.insert)
    elif et == "DIMENSION":
        try:
            geom = entity.get_geometry()
            base["text"] = geom.get("text", "")
        except Exception:
            base["text"] = entity.dxf.get("text", "")
    return base


def extract_dxf_entities(path: str | Path) -> dict[str, Any]:
    """Extract geometry entities from a DXF file (tolerant mode)."""
    p = Path(path)
    if not p.exists():
        return {"file_type": "dxf", "entity_count": 0, "entities": []}
    # ezdxf 1.4: `errors="surrogateescape"` (not `encoding="gbk"`)
    # Actual encoding is read from $DWGCODEPAGE header var
    try:
        doc, _auditor = ezdxf_recover.readfile(p, errors="surrogateescape")
    except (ezdxf.DXFStructureError, ezdxf.DXFError, OSError):
        # Not a DXF / corrupt / unreadable — return empty result, don't raise
        return {"file_type": "dxf", "entity_count": 0, "entities": []}
    entities = [
        _entity_to_dict(e) for e in _iter_supported_types(doc.modelspace(), SUPPORTED_TYPES)
    ]
    return {
        "file_type": "dxf",
        "entity_count": len(entities),
        "entities": entities,
    }

# Plan: Phase 2 — Document Parsing Toolchain

## Summary
实现 PDF/DXF 解析 + 文件类型识别 + MCP Server 起步接口。Phase 1 的 5 个 Agent 节点从 echo 升级为真正调用工具：Spec Interpreter 解析 PDF 文字/标题栏、Drawing Auditor 接收图片块、StateGraph 流转结构化"中间表示"。FastMCP 包装让工具既可被 in-process 调用，也可独立启动为 MCP server。

## User Story
As a **Phase 3+ Agent 开发者**,
I want **一套 PDF/DXF 解析 + MCP 工具，能自动识别图纸类型并提取文字块、图片块、DXF 实体**,
so that **我能直接把图片块喂给 Vision-LLM，把文字块喂给 LLM 抽 Spec，不用自己重写 PDF 解析**。

## Problem → Solution
**当前状态**：Phase 1 的 Agent 节点是 echo，不解析图纸。CLI 跑任何 PDF 都输出空 JSON。
**目标状态**：CLI 跑 PDF 输出真实文字块 + 图片字节 + 文件类型元数据；跑 DXF 输出实体列表；MCP server 可独立启动供外部 client。

## Metadata
- **Complexity**: **Large**（18 个 task、5 个新文件、4 个新依赖、跨 state + agent + tools + CLI）
- **Source PRD**: `.claude/PRPs/prds/deepdraw-dfm-platform.prd.md`
- **PRD Phase**: Phase 2 — 文档解析工具链
- **Estimated Files**: 12（5 NEW src/ + 3 NEW test/ + 4 UPDATE）

---

## UX Design

**N/A — 内部工具链**。CLI 输出 JSON 字段会扩展（`intermediate` 段），但 UI 形态不变。

---

## Mandatory Reading

| Priority | File | Lines | Why |
|---|---|---|---|
| P0 | `.claude/PRPs/prds/deepdraw-dfm-platform.prd.md` (Phase 2 段) | all | 本阶段 PRD 契约 |
| P0 | `src/deepdraw/state.py` | all | 现有 State Schema，要扩展 |
| P0 | `src/deepdraw/agents/spec_interpreter.py` | all | 要接入 PDF 文字抽取 |
| P0 | `src/deepdraw/agents/drawing_auditor.py` | all | 要消费图片块 |
| P1 | `src/deepdraw/graph.py` | all | 5 节点图结构，Phase 2 不动 |
| P1 | `src/deepdraw/cli.py` | all | 输出 JSON 字段要扩展 |
| P1 | `src/deepdraw/tools/README.md` | all | Phase 1 留的工具占位描述（要更新） |
| P2 | `pyproject.toml` | all | 加新依赖的位置 |

## External Documentation

| Topic | Source | Key Takeaway |
|---|---|---|
| pdfplumber 0.11.x | github.com/jsvine/pdfplumber | `page.extract_text()` / `page.extract_tables(table_settings=...)`；中文明细栏需 `vertical_strategy="text", horizontal_strategy="text"` |
| pymupdf 1.26.x | pymupdf.readthedocs.io | **包名小写** `pymupdf`（不是 PyMuPDF）；`page.get_pixmap(dpi=200).pil_image()` 出图；AGPL-3.0 许可 |
| ezdxf 1.3.x | ezdxf.mozman.at | `ezdxf.readfile(path, encoding="gbk")` 中文 DXF；`msp.query("LINE")` 高效过滤；损坏文件用 `recover.readfile` |
| mcp 1.x | github.com/modelcontextprotocol/python-sdk | `FastMCP("name")` + `@mcp.tool()` 装饰器；`mcp.run(transport="stdio")` 本地子进程首选 |
| langchain-mcp-adapters | github.com/langchain-ai/langchain-mcp-adapters | Phase 5 才用：MultiServerMCPClient async 加载 MCP tools 进 LangGraph |

---

## Patterns to Mirror

**Phase 1 已建立的 patterns**（从现有代码发现）：

### ASYNC_AGENT_NODE
// SOURCE: src/deepdraw/agents/spec_interpreter.py
```python
async def spec_interpreter_node(state: AgentState) -> dict:
    """Read from state, return partial update dict."""
    return {"spec": {...}}
```

### STATE_EXTENSION_WITH_REDUCER
// SOURCE: src/deepdraw/state.py:60-64
```python
errors: Annotated[list[DrawingError], operator.add]
# 列表字段必须用 operator.add reducer；Phase 2 process_plan/intermediate 也用同样模式
```

### CLI_ASYNC_INVOKE
// SOURCE: src/deepdraw/cli.py:39
```python
# LangGraph 1.x: async node functions require ainvoke
final_state = asyncio.run(graph.ainvoke(initial_state, config=config))
```

### TOOL_AS_SYNC_FUNCTION
// SOURCE: Phase 1 留的 tools/README.md 接口契约
```python
# 工具是 sync 函数；agent node 内部用 asyncio.to_thread() 包成 async
def extract_pdf_text(path: str) -> dict: ...
def extract_dxf_entities(path: str) -> list[dict]: ...
```

---

## Files to Change

| File | Action | Justification |
|---|---|---|
| `pyproject.toml` | UPDATE | 加 pdfplumber / pymupdf / ezdxf / mcp 4 个新依赖 |
| `src/deepdraw/state.py` | UPDATE | 加 `DrawingIntermediate` 子 TypedDict + `intermediate` 字段到 `AgentState` |
| `src/deepdraw/tools/__init__.py` | UPDATE | 导出工具函数 + 同步加载 fixtures |
| `src/deepdraw/tools/pdf.py` | CREATE | PDF 解析：text + tables + images |
| `src/deepdraw/tools/dxf.py` | CREATE | DXF 实体抽取（容错模式） |
| `src/deepdraw/tools/file_detect.py` | CREATE | 文件类型自动识别（magic bytes） |
| `src/deepdraw/tools/mcp_tools.py` | CREATE | 2 个 MCP 工具 stub（query_material_price / lookup_internal_standard） |
| `src/deepdraw/tools/mcp_server.py` | CREATE | FastMCP server，把上面 5 个函数都包成 `@mcp.tool()` |
| `src/deepdraw/tools/README.md` | UPDATE | 把 Phase 1 占位描述更新为 Phase 2 实现状态 |
| `src/deepdraw/agents/spec_interpreter.py` | UPDATE | 调 PDF text parser；填 `intermediate.text_blocks` |
| `src/deepdraw/agents/drawing_auditor.py` | UPDATE | 消费 `intermediate.images_b64`（Phase 2 不调 Vision，仅 echo 记录） |
| `src/deepdraw/cli.py` | UPDATE | 输出 JSON 加 `intermediate` 段；图片字节用 base64 编码 |
| `tests/conftest.py` | UPDATE | 加 `sample_pdf` / `sample_dxf` fixtures（程序化生成） |
| `tests/test_state.py` | UPDATE | 加 `intermediate` 字段测试 |
| `tests/test_tools_pdf.py` | CREATE | PDF parser 单元测试（用 sample_pdf fixture） |
| `tests/test_tools_dxf.py` | CREATE | DXF parser 单元测试（用 sample_dxf fixture） |
| `tests/test_tools_mcp.py` | CREATE | 2 个 MCP stub 单测 + FastMCP server 启动 smoke test |
| `tests/test_agents.py` | UPDATE | 改 spec_interpreter / drawing_auditor 测试以反映真实行为 |

**总计**: 8 CREATE / 7 UPDATE

---

## NOT Building

明确不在 Phase 2 做：

- **Vision-LLM 真实调用**（Phase 3 才用 GPT-4o/Claude 看图）— Phase 2 只把图片字节存到 state
- **真实材料价格查询 / 标准库查询**（Phase 5 接 RAG/ERP）— Phase 2 只返回 mock 数据
- **DXF 实体几何可视化 / 渲染**（Phase 3+ 才有用）— Phase 2 只序列化为 dict
- **多页 PDF 流式处理**（Phase 3+ 性能优化）— Phase 2 一次性读全
- **扫描件 OCR**（Phase 4+ 才考虑 Tesseract / PaddleOCR）— Phase 2 假设 PDF 含可抽取文字
- **MCP 远程传输**（streamable-http）— Phase 5+ 才需要
- **`langchain-mcp-adapters` 集成**（MultiServerMCPClient）— Phase 5 才用；Phase 2 agent 直接 import 函数
- **Caching / 解析结果持久化**（Phase 7 PoC 100 张图才需要）— Phase 2 每次重新解析
- **错误恢复 / 重试**（LangGraph retry_policy 已够用）— Phase 2 不写业务级 try/except

---

## Step-by-Step Tasks

### Task 1: 加 4 个新依赖到 pyproject.toml
- **ACTION**: 在 `[project] dependencies` 数组加 4 个包
- **IMPLEMENT**:
  ```toml
  dependencies = [
      "langgraph==1.2.6",
      "langchain-core>=1.0,<2",
      "langgraph-checkpoint>=2,<5",
      "langgraph-checkpoint-sqlite==3.1.0",
      "pydantic>=2",
      "python-dotenv>=1.0",
      "typer>=0.12",
      # Phase 2 — 文档解析工具链
      "pdfplumber>=0.11,<0.12",
      "pymupdf>=1.24,<2",         # AGPL-3.0, 包名小写
      "ezdxf>=1.3,<2",
      "mcp>=1.0,<2",              # FastMCP server
  ]
  ```
- **MIRROR**: 现有 langgraph/pydantic 依赖风格
- **GOTCHA**: pymupdf 是 AGPL-3.0 — DeepDraw 是企业内部工具，AGPL OK（不分发）；如未来要 SaaS 化需买商业 license
- **VALIDATE**: `uv pip install -e ".[dev]"` 成功；`.venv/bin/python -c "import pdfplumber, pymupdf, ezdxf, mcp; print('ok')"`

### Task 2: 实现 src/deepdraw/tools/pdf.py（PDF 解析）
- **ACTION**: 两个同步函数：`extract_pdf_text` + `extract_pdf_images`
- **IMPLEMENT**:
  ```python
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

      中文明细栏通常无线框 → 必须传 table_settings。
      """
      p = Path(path)
      if not p.exists():
          return {"file_type": "pdf", "page_count": 0, "pages": []}
      pages: list[PDFTextPage] = []
      with pdfplumber.open(p) as pdf:
          for i, page in enumerate(pdf.pages, start=1):
              pages.append({
                  "page_num": i,
                  "text": page.extract_text() or "",
                  "tables": page.extract_tables(table_settings=DEFAULT_TABLE_SETTINGS) or [],
              })
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
  ```
- **MIRROR**: tools/README.md 中规划的接口签名
- **GOTCHA**: `with pdfplumber.open()` 必须用，文件句柄依赖；pymupdf 同理
- **VALIDATE**: `.venv/bin/python -c "from deepdraw.tools.pdf import extract_pdf_text, extract_pdf_images; print('ok')"`

### Task 3: 实现 src/deepdraw/tools/dxf.py（DXF 实体抽取）
- **ACTION**: 同步函数 `extract_dxf_entities`，容错模式 + 中文编码
- **IMPLEMENT**:
  ```python
  """DXF entity extractor (ezdxf, tolerant mode)."""
  from __future__ import annotations

  from pathlib import Path
  from typing import Any

  import ezdxf
  from ezdxf import recover as ezdxf_recover


  SUPPORTED_TYPES = {"LINE", "CIRCLE", "ARC", "TEXT", "MTEXT", "DIMENSION", "HATCH"}


  def _entity_to_dict(entity: ezdxf.entities.DXFGraphic) -> dict[str, Any]:
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
      """Extract geometry entities from a DXF file (tolerant)."""
      p = Path(path)
      if not p.exists():
          return {"file_type": "dxf", "entity_count": 0, "entities": []}
      try:
          doc, _auditor = ezdxf_recover.readfile(p, encoding="gbk")
      except ezdxf.DXFStructureError:
          doc = ezdxf.readfile(p, encoding="gbk")
      entities = [
          _entity_to_dict(e)
          for e in doc.modelspace().query(
              " | ".join(SUPPORTED_TYPES)
          )
      ]
      return {
          "file_type": "dxf",
          "entity_count": len(entities),
          "entities": entities,
      }
  ```
- **MIRROR**: ezdxf 官方 query API
- **GOTCHA**: 中文 DXF 必须 `encoding="gbk"`；损坏文件用 `recover.readfile` 容错；`get_geometry()` 可能抛异常需 try/except
- **VALIDATE**: `.venv/bin/python -c "from deepdraw.tools.dxf import extract_dxf_entities; print('ok')"`

### Task 4: 实现 src/deepdraw/tools/file_detect.py
- **ACTION**: 同步函数 `detect_file_type`，magic bytes + 扩展名
- **IMPLEMENT**:
  ```python
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
  ```
- **MIRROR**: 简单 utility
- **VALIDATE**: 单元测试覆盖 3 种 case

### Task 5: 实现 src/deepdraw/tools/mcp_tools.py
- **ACTION**: 2 个 stub：query_material_price + lookup_internal_standard
- **IMPLEMENT**:
  ```python
  """MCP tool stubs for ERP/PDM integration. Phase 5 will replace with RAG/ERP."""
  from __future__ import annotations

  from decimal import Decimal

  _MATERIAL_PRICES: dict[str, Decimal] = {
      "Q235B": Decimal("5800.00"),
      "Q345B": Decimal("6200.00"),
      "SS304":  Decimal("22000.00"),
      "AL6061": Decimal("28000.00"),
  }

  _STANDARDS: dict[str, dict] = {
      "GB/T 3098.1-2010": {"title": "紧固件机械性能 螺栓、螺钉和螺柱", "scope": "M3-M64"},
      "GB/T 118-2000":    {"title": "内六角圆柱头螺钉", "scope": "M3-M20"},
  }


  def query_material_price(material_code: str) -> Decimal | None:
      return _MATERIAL_PRICES.get(material_code.upper().replace(" ", ""))


  def lookup_internal_standard(standard_id: str) -> dict | None:
      return _STANDARDS.get(standard_id)
  ```
- **VALIDATE**: 单测覆盖 "Q235B" 命中 / "UNKNOWN" 返回 None

### Task 6: 实现 src/deepdraw/tools/mcp_server.py
- **ACTION**: FastMCP server 包 5 个函数
- **IMPLEMENT**:
  ```python
  """FastMCP server exposing DeepDraw tools.

  Run: python -m deepdraw.tools.mcp_server
  Transport: stdio (default)
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
              base64.b64encode(img).decode("ascii")
              for img in extract_pdf_images(path)
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
  ```
- **GOTCHA**: `@mcp.tool()` 函数签名同步或 async 都支持；返回类型必须 JSON-serializable
- **VALIDATE**: `.venv/bin/python -c "from deepdraw.tools.mcp_server import mcp; print(len(mcp._tool_manager._tools))"` = 5

### Task 7: 扩展 state.py — DrawingIntermediate
- **ACTION**: 新增子 TypedDict + `intermediate` 字段
- **IMPLEMENT** (in state.py):
  ```python
  class DrawingIntermediate(TypedDict, total=False):
      """Output of Phase 2 file parsers."""
      file_type: str  # "pdf" | "dxf"
      text_blocks: list[str]  # PDF per-page text
      images_b64: list[str]  # PDF per-page PNG as base64
      entities: list[dict]  # DXF entity list
      parsed_path: str

  class AgentState(TypedDict, total=False):
      # ... existing fields ...
      # Phase 2
      intermediate: DrawingIntermediate
  ```
- **VALIDATE**: 字段存在性测试

### Task 8: 更新 spec_interpreter.py
- **ACTION**: 真实调 PDF/DXF 解析
- **IMPLEMENT**:
  ```python
  """👓 Spec Interpreter — Phase 2: parses PDF/DXF, populates intermediate."""
  from __future__ import annotations

  import asyncio
  import base64
  from pathlib import Path

  from deepdraw.state import AgentState
  from deepdraw.tools.dxf import extract_dxf_entities
  from deepdraw.tools.file_detect import detect_file_type
  from deepdraw.tools.pdf import extract_pdf_images, extract_pdf_text


  async def spec_interpreter_node(state: AgentState) -> dict:
      drawing_path = state.get("drawing_path", "")
      if not drawing_path or not Path(drawing_path).exists():
          return {
              "spec": {"raw_requirements": {"drawing_path": drawing_path, "error": "file not found"}},
          }

      file_type = detect_file_type(drawing_path)
      intermediate: dict = {
          "file_type": file_type,
          "parsed_path": str(Path(drawing_path).absolute()),
      }

      if file_type == "pdf":
          text_result = await asyncio.to_thread(extract_pdf_text, drawing_path)
          intermediate["text_blocks"] = [p["text"] for p in text_result["pages"]]
          images = await asyncio.to_thread(extract_pdf_images, drawing_path, 150)
          intermediate["images_b64"] = [
              base64.b64encode(img).decode("ascii") for img in images
          ]
      elif file_type == "dxf":
          dxf_result = await asyncio.to_thread(extract_dxf_entities, drawing_path)
          intermediate["entities"] = dxf_result["entities"]

      return {
          "intermediate": intermediate,
          "spec": {
              "raw_requirements": {
                  "drawing_path": drawing_path,
                  "file_type": file_type,
                  "page_count": len(intermediate.get("text_blocks", [])),
                  "entity_count": len(intermediate.get("entities", [])),
              },
          },
      }
  ```
- **GOTCHA**: 同步 I/O 必须 `asyncio.to_thread()` 包装
- **VALIDATE**: 跑 sample PDF 路径 → text_blocks 非空

### Task 9: 更新 drawing_auditor.py
- **ACTION**: 消费 images_b64
- **IMPLEMENT**:
  ```python
  """🔍 Drawing Auditor — Phase 2: consumes images_b64, records readiness."""
  from __future__ import annotations

  from deepdraw.state import AgentState


  async def drawing_auditor_node(state: AgentState) -> dict:
      intermediate = state.get("intermediate", {}) or {}
      images = intermediate.get("images_b64", [])
      file_type = intermediate.get("file_type", "unknown")
      notes = [f"[Phase2] Drawing Auditor received {len(images)} page image(s) from {file_type}"]
      if file_type == "dxf":
          entities = intermediate.get("entities", [])
          notes.append(f"[Phase2] DXF has {len(entities)} geometry entities (Phase 3 will check via LLM)")
      return {"verification_notes": notes}
  ```
- **VALIDATE**: 单测覆盖 PDF/DXF 两种 input

### Task 10: 更新 CLI — 输出 intermediate 段
- **ACTION**: cli.py report dict 加 intermediate
- **IMPLEMENT** (in report dict):
  ```python
  intermediate = final_state.get("intermediate") or {}
  report = {
      "spec": final_state.get("spec", {}),
      "intermediate": {
          "file_type": intermediate.get("file_type"),
          "text_block_count": len(intermediate.get("text_blocks", [])),
          "image_count": len(intermediate.get("images_b64", [])),
          "entity_count": len(intermediate.get("entities", [])),
          "parsed_path": intermediate.get("parsed_path"),
      },
      "errors": final_state.get("errors", []),
      "bom": final_state.get("bom", []),
      "process_plan": final_state.get("process_plan", []),
      "verification_notes": final_state.get("verification_notes", []),
      "reflection_iterations": final_state.get("reflection_iterations", 0),
      "status": final_state.get("status", "unknown"),
  }
  ```
- **GOTCHA**: `intermediate` 可能 None（用 `or {}` 兜底）
- **VALIDATE**: E2E CLI 输出含 `intermediate.file_type: "pdf"`

### Task 11: conftest.py — 程序化 fixtures
- **ACTION**: 加 sample_pdf + sample_dxf fixtures
- **IMPLEMENT**:
  ```python
  @pytest.fixture
  def sample_pdf(tmp_path: Path) -> Path:
      """Generate a minimal single-page PDF with text + simple graphics."""
      import pymupdf
      p = tmp_path / "sample.pdf"
      doc = pymupdf.open()
      page = doc.new_page(width=595, height=842)
      page.insert_text((72, 72), "DeepDraw Test Drawing", fontsize=14)
      page.insert_text((72, 100), "Material: Q235B", fontsize=10)
      page.insert_text((72, 115), "Thickness: 5mm", fontsize=10)
      page.draw_rect(pymupdf.Rect(72, 200, 200, 400))
      doc.save(p)
      doc.close()
      return p

  @pytest.fixture
  def sample_dxf(tmp_path: Path) -> Path:
      """Generate a minimal DXF with LINE, CIRCLE, TEXT entities."""
      import ezdxf
      p = tmp_path / "sample.dxf"
      doc = ezdxf.new(setup=True)
      msp = doc.modelspace()
      msp.add_line((0, 0), (10, 0))
      msp.add_circle((5, 5), radius=2.5)
      msp.add_text("DeepDraw Test", insert=(0, 10))
      doc.saveas(p)
      return p
  ```
- **GOTCHA**: pymupdf `doc.close()` 释放文件句柄
- **VALIDATE**: `pytest --co -q tests/test_tools_pdf.py` 能 collect

### Task 12: tests/test_tools_pdf.py
- **ACTION**: 4 个测试
- **IMPLEMENT**:
  ```python
  """Tests for src/deepdraw/tools/pdf.py."""
  from __future__ import annotations

  from deepdraw.tools.pdf import extract_pdf_images, extract_pdf_text


  def test_extract_pdf_text_returns_pages(sample_pdf) -> None:
      result = extract_pdf_text(sample_pdf)
      assert result["file_type"] == "pdf"
      assert result["page_count"] == 1
      assert "DeepDraw Test Drawing" in result["pages"][0]["text"]
      assert "Q235B" in result["pages"][0]["text"]


  def test_extract_pdf_text_handles_missing_file(tmp_path) -> None:
      result = extract_pdf_text(tmp_path / "nope.pdf")
      assert result["page_count"] == 0


  def test_extract_pdf_images_returns_png_bytes(sample_pdf) -> None:
      images = extract_pdf_images(sample_pdf, dpi=72)
      assert len(images) == 1
      assert images[0][:8] == b"\x89PNG\r\n\x1a\n"


  def test_extract_pdf_images_dpi_affects_size(sample_pdf) -> None:
      small = extract_pdf_images(sample_pdf, dpi=50)
      large = extract_pdf_images(sample_pdf, dpi=200)
      assert len(small[0]) < len(large[0])
  ```
- **VALIDATE**: 4 pass

### Task 13: tests/test_tools_dxf.py
- **ACTION**: 4 个测试
- **IMPLEMENT**:
  ```python
  """Tests for src/deepdraw/tools/dxf.py."""
  from __future__ import annotations

  from deepdraw.tools.dxf import extract_dxf_entities


  def test_extract_dxf_entities_returns_3_types(sample_dxf) -> None:
      result = extract_dxf_entities(sample_dxf)
      types = {e["type"] for e in result["entities"]}
      assert "LINE" in types and "CIRCLE" in types and "TEXT" in types


  def test_extract_dxf_line_has_start_end(sample_dxf) -> None:
      result = extract_dxf_entities(sample_dxf)
      line = next(e for e in result["entities"] if e["type"] == "LINE")
      assert line["start"] == [0.0, 0.0, 0.0]
      assert line["end"] == [10.0, 0.0, 0.0]


  def test_extract_dxf_circle_has_radius(sample_dxf) -> None:
      result = extract_dxf_entities(sample_dxf)
      circle = next(e for e in result["entities"] if e["type"] == "CIRCLE")
      assert circle["radius"] == 2.5


  def test_extract_dxf_handles_corrupt_file(tmp_path) -> None:
      bad = tmp_path / "bad.dxf"
      bad.write_bytes(b"not a dxf file")
      result = extract_dxf_entities(bad)
      assert result["entity_count"] == 0
  ```
- **VALIDATE**: 4 pass

### Task 14: tests/test_tools_mcp.py
- **ACTION**: 5 个测试
- **IMPLEMENT**:
  ```python
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
      assert result is not None and "title" in result


  def test_lookup_internal_standard_unknown() -> None:
      assert lookup_internal_standard("GB/NONEXISTENT") is None


  def test_mcp_server_exposes_5_tools() -> None:
      tools = mcp._tool_manager._tools
      assert len(tools) == 5
      for name in ("detect_drawing_type", "parse_pdf", "parse_dxf", "get_material_price", "lookup_standard"):
          assert name in tools
  ```
- **VALIDATE**: 5 pass

### Task 15: 更新 test_state.py — intermediate 字段
- **ACTION**: 1 行测试
- **IMPLEMENT**:
  ```python
  def test_agent_state_has_intermediate_field() -> None:
      assert "intermediate" in AgentState.__annotations__
  ```

### Task 16: 更新 test_agents.py
- **ACTION**: 改 spec_interpreter / drawing_auditor 测试
- **IMPLEMENT**:
  - spec_interpreter 测试：传入 sample_pdf 路径，断言返回 `intermediate.text_blocks` 含 "DeepDraw Test"
  - drawing_auditor 测试：传入含 images_b64 的 state，断言 verification_notes 含 "received N page image(s)"
  - 其他 3 个 agent 保持 echo
- **VALIDATE**: 5 pass

### Task 17: 更新 tools/README.md — Phase 1 → Phase 2
- **ACTION**: 改 README，反映新实现
- **VALIDATE**: 内容更新

### Task 18: 5 级验证
- **COMMANDS**:
  ```bash
  .venv/bin/ruff check src/ tests/      # 0 errors
  .venv/bin/ruff format --check src/ tests/
  .venv/bin/pytest tests/ -v            # 24+ tests pass
  .venv/bin/python -m deepdraw.cli /tmp/sample.pdf  # E2E
  .venv/bin/python -c "from deepdraw.tools.mcp_server import mcp; print(len(mcp._tool_manager._tools))"  # 5
  ```

---

## Testing Strategy

### Unit Tests (16+ total)

| Test | Input | Expected |
|---|---|---|
| extract_pdf_text returns pages | sample PDF | file_type=pdf, 1 page with "DeepDraw" |
| extract_pdf_text missing file | nonexistent | page_count=0 |
| extract_pdf_images returns PNG | sample PDF | 1 image, PNG magic |
| extract_pdf_images dpi affects size | 50 vs 200 dpi | higher dpi → larger |
| extract_dxf_entities 3 types | sample DXF | LINE+CIRCLE+TEXT |
| extract_dxf_line coords | sample DXF | start/end correct |
| extract_dxf_circle radius | sample DXF | radius=2.5 |
| extract_dxf corrupt file | garbage | entity_count=0 |
| query_material_price known | "Q235B" | Decimal("5800") |
| query_material_price unknown | "X" | None |
| lookup_standard known | "GB/T 3098.1" | dict |
| lookup_standard unknown | "X" | None |
| mcp_server 5 tools | FastMCP | 5 tool names |
| state has intermediate | AgentState | "intermediate" in annotations |
| spec_interpreter with PDF | sample path | text_blocks non-empty |
| drawing_auditor consumes images | state | verification_notes 含 count |

### Edge Cases
- [x] Missing file (path doesn't exist)
- [x] Corrupt PDF / DXF
- [x] Unknown file extension
- [x] DXF without text (only geometry)
- [x] Material code lowercase (case insensitive)
- [x] Unknown material / standard

---

## Validation Commands

### Static
```bash
.venv/bin/ruff check src/ tests/    # Zero errors
.venv/bin/ruff format --check src/ tests/  # No changes
```

### Tests
```bash
.venv/bin/pytest tests/ -v          # 24+ pass
```

### E2E
```bash
.venv/bin/python -m deepdraw.cli /tmp/sample.pdf  # intermediate.file_type: "pdf"
```

### MCP
```bash
.venv/bin/python -c "from deepdraw.tools.mcp_server import mcp; print(len(mcp._tool_manager._tools))"  # 5
```

---

## Acceptance Criteria
- [ ] pyproject.toml 含 4 个新依赖
- [ ] `uv pip install` 成功
- [ ] 5 个新文件 + 7 个更新文件
- [ ] State 含 `intermediate: DrawingIntermediate`
- [ ] 5 个 MCP tool 注册
- [ ] 24+ tests pass（11 → 24+）
- [ ] ruff check + format 全过
- [ ] E2E CLI 跑 PDF 输出结构化中间表示
- [ ] FastMCP server 启动成功

## Risks

| Risk | L | I | Mitigation |
|---|---|---|---|
| pymupdf AGPL-3.0 未来商业化 | M | H | PoC 接受；SaaS 化换 pypdfium2 |
| 中文明细栏识别失败 | H | M | 已用 vertical_strategy="text" |
| 大文件内存爆 | L | M | Phase 7 才考虑分页 |
| DXF 编码不一致 | M | L | 默认 gbk，Phase 3 调 |
| FastMCP 内部 API 改名 | M | L | smoke test 性质，必要时换 API |
| 同步 I/O 阻塞 event loop | M | M | asyncio.to_thread() |

## Notes

- **AGPL-3.0**: pymupdf 是 AGPL。DeepDraw 内部工具不分发 = 不传染。未来 SaaS 化需买 license 或换库。
- **同步 vs 异步工具**: parser 全同步；agent node 用 `asyncio.to_thread()` 包；MCP tool 也同步
- **不引入 langchain-mcp-adapters**: Phase 5 才用；Phase 2 agent 直接 import
- **fixtures 程序化生成**: pymupdf/ezdxf 自己生成 sample 文件，避开涉密
- **MCP server 是可选**: agent workflow 不依赖它；MCP server 仅供外部 client
- **base64 图片**: 因为 LangGraph state 序列化；bytes 不友好
- **CLI 不默认输出 text_blocks**: 避免大 JSON
- **Phase 2 不动 graph.py**: 5 节点结构 Phase 1 已定

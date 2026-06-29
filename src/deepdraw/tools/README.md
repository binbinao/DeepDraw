# DeepDraw Tools (MCP 工具占位)

## Phase 1 状态
**此目录留空**。Phase 1 的 Agent 节点都是 echo 函数，不调用任何工具。

## Phase 2 计划
将在此目录实现以下 MCP 工具：

### PDF 解析
- `extract_pdf_text(path: str) -> str`（pdfplumber）
- `extract_pdf_images(path: str) -> list[bytes]`（PyMuPDF）

### DXF 解析
- `extract_dxf_entities(path: str) -> list[dict]`（ezdxf）

### MCP Server 接口
- `query_material_price(material_code: str) -> Decimal`
- `lookup_internal_standard(standard_id: str) -> dict`
- `search_similar_drawings(feature_vector: list[float]) -> list[DrawingRef]`

## 引用方式
Phase 2 的 Agent 将通过 `from deepdraw.tools import ...` 导入并使用。

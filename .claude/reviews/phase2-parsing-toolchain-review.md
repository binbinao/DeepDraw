# Code Review: Phase 2 — Document Parsing Toolchain

**Reviewed**: 2026-06-29
**Commit**: `010980e` — feat: add PDF/DXF parsing toolchain with MCP server
**Branch**: main (already merged)
**Decision**: **APPROVE with comments**

## Summary
Phase 2 文档解析工具链实现质量高：5 个新工具文件 + State 扩展 + 2 个 Agent 真实集成 + FastMCP server + 17 个新测试。28/28 tests pass；与 Phase 1 的 agent graph 兼容。Post-commit 修复了 3 个真实 bug（ezdxf 1.4 API 变化、test_graph dummy PDF、fixtures API）后已稳定。

## Findings

### CRITICAL
None.

### HIGH
None.

### MEDIUM

#### M1. `dxf.py:50` — ezdxf 1.4 `errors="surrogateescape"` 不一定适合所有中文 DXF
- **File**: `src/deepdraw/tools/dxf.py:50`
- **Issue**: ezdxf 1.4 不再支持 `encoding="gbk"` kwarg；现用 `errors="surrogateescape"` 作为解码容错策略。中文 DXF 实际编码从 `$DWGCODEPAGE` 头变量读取，但本代码没显式设置。
- **Why it matters**: 中文 DXF 在 surrogateescape 模式下可能产生 mojibake（乱码）。Phase 7 跑真实 NG 图时可能踩坑。
- **Suggested fix** (Phase 3+):
  ```python
  ezdxf.options.set("encoding", "gbk")
  doc, _auditor = ezdxf_recover.readfile(p, errors="strict")
  ```
  或在 `_entity_to_dict` 里检测非 ASCII 字符并记录到 `base["text"]`。

#### M2. `cli.py:46-54` — `intermediate.text_blocks` 完整内容不显示
- **File**: `src/deepdraw/cli.py:48`
- **Issue**: CLI 输出 `text_block_count` 但不显示 text 内容。用户想看 AI 解析了什么必须从 state 里找。
- **Why it matters**: PoC 阶段调试时无法验证 pdfplumber 是否真的抽出了中文。
- **Suggested fix**: 加 `--full` flag 打印 text_blocks 内容

#### M3. `mcp_server.py:33` — base64 PNG 可能巨大
- **File**: `src/deepdraw/tools/mcp_server.py:33`
- **Issue**: `parse_pdf(extract_images=True)` 默认返回所有 page 的 base64 PNG。150 dpi 单页 1-2MB base64 → 多页 PDF 整个 JSON 几 MB。
- **Why it matters**: 通过 MCP 调用时整个 payload 塞进 LLM context。
- **Suggested fix**: 默认 `extract_images=False`；或分页 tool 一次只返回一页。

### LOW

#### L1. `tools/__init__.py` 未显式 re-export
- **File**: `src/deepdraw/tools/__init__.py`
- **Suggested fix**: 留空也 OK；显式 re-export 可改善 IDE 提示。

#### L2. `file_detect.py` — 二进制 DXF 不识别
- **File**: `src/deepdraw/tools/file_detect.py:18-25`
- **Issue**: 当前只识别文本 DXF（99% 情况）。二进制 DXF 头是 `\x00` 开头，与空文件冲突。
- **Suggested fix**: Phase 3+ 接真实 DXF 时加 binary DXF detection。

#### L3. `mcp_tools.py` mock 数据写死
- **File**: `src/deepdraw/tools/mcp_tools.py:11-22`
- **Issue**: 4 个材料 + 2 个标准是硬编码 mock。
- **Suggested fix**: Phase 5 接 RAG/ERP 时全替换。

## Post-commit 修复记录

合并到 main 后发现并修复了 3 个 bug（不在 `010980e` 内，由 user/linter 修复）：

| Bug | 修复 | 影响 |
|---|---|---|
| `ezdxf.recover.readfile` 不接受 `encoding="gbk"` | 改用 `errors="surrogateescape"` | 4 个 DXF test |
| ezdxf 1.4 `msp.query("LINE \| CIRCLE")` 不支持 | 拆成多次 query + `union()` | 4 个 DXF test |
| `tests/test_graph.py` 用 `dummy_drawing` 跑 spec_interpreter | 改用 `sample_pdf` fixture | 2 个 test |

## Validation Results

| Check | Result | Notes |
|---|---|---|
| Lint (ruff check) | Pass | 0 errors |
| Format (ruff format) | Pass | 18 files already formatted |
| Tests (pytest) | Pass | **28/28 tests** (was 11, +17 new) |
| E2E CLI | Pass | 输出 JSON 含 intermediate 段 |
| MCP server | Pass | 5 tool 注册 |

## Files Reviewed (20 changed in commit)

### Source (10)
- `src/deepdraw/state.py` — DrawingIntermediate TypedDict + intermediate field
- `src/deepdraw/tools/pdf.py` — 2 functions
- `src/deepdraw/tools/dxf.py` — 1 function + entity serializer
- `src/deepdraw/tools/file_detect.py` — 2 functions
- `src/deepdraw/tools/mcp_tools.py` — 2 stub functions
- `src/deepdraw/tools/mcp_server.py` — FastMCP + 5 tool wrappers
- `src/deepdraw/agents/spec_interpreter.py` — Real PDF/DXF parsing
- `src/deepdraw/agents/drawing_auditor.py` — Consume images/entities
- `src/deepdraw/cli.py` — Report extended with intermediate
- `pyproject.toml` — 4 new dependencies

### Tests (7)
- `tests/conftest.py` — sample_pdf + sample_dxf fixtures
- `tests/test_state.py` — +1 test
- `tests/test_graph.py` — 2 tests updated
- `tests/test_agents.py` — 5 tests updated
- `tests/test_tools_pdf.py` — 4 NEW
- `tests/test_tools_dxf.py` — 4 NEW
- `tests/test_tools_mcp.py` — 5 NEW

### Docs (3)
- PRD / archived plan / implementation report

## Non-issues (Checked and OK)

- ✓ **Security**: 无硬编码凭证；AGPL-3.0 pymupdf 已加注释
- ✓ **Type safety**: 全函数有 type hint；TypedDict 状态扩展
- ✓ **Pattern compliance**: LangGraph 1.x + FastMCP 规范
- ✓ **Performance**: 同步 parser 用 `asyncio.to_thread()` 包
- ✓ **Completeness**: 17 个新测试 + 4 个更新；28/28 pass
- ✓ **Maintainability**: 源文件 < 100 行；docstring 完整
- ✓ **Error handling**: Path.exists() 预检 + recover.readfile 容错
- ✓ **B008 noqa**: typer 假阳性正确处理

## Decision Rationale

**APPROVE with comments**:
- 0 CRITICAL + 0 HIGH
- 3 MEDIUM 都是未来优化
- 4 LOW 全部是文档/可读性
- 5 级 validation 全过
- 28/28 tests pass
- post-commit 修复后稳定

## Recommended Pre-Phase-3 Actions

1. **M1 验证** (15 min): 拿 1 张真实中文 DXF 测试
2. **M2/M3 CLI 改进** (10 min): 加 `--full` flag；MCP `parse_pdf` 默认 `extract_images=False`
3. **保留 AGPL 注意**: pyproject.toml 注释已加

## Next Steps
- [ ] 修上述 MEDIUM（如有时间）
- [ ] **强烈推荐**: `/ecc:prp-plan` 选 Phase 3 时同步做技术 spike
- [ ] Phase 3 范围: Spec Interpreter 用 LLM 抽结构化 spec + Drawing Auditor 调 Vision-LLM + BOM Generator 调 LLM

# Plan: Phase 5 — Enterprise Standard Memory (RAG)

## Summary
实现 RAG 召回：ChromaDB 持久化 + OpenAI Embeddings + Markdown 文档入库 + RAG 检索接口。Process Recommender 在调 LLM 前先查 RAG，把召回的企业私有工艺知识注入 prompt，让"我们厂里只有 10mm 的铣刀"这种知识驱动工艺推荐。

## User Story
As a **工艺工程师**（Phase 4 升级路径）,
I want **Process Recommender 能 RAG 召回企业私有工艺知识**,
so that **工艺推荐基于"我们厂里只有 10mm 的铣刀"而非通用知识，提升实际可用性**。

## Problem → Solution
**当前状态**：Process Recommender 调 LLM 但只用通用知识，不知道企业私有工艺规范。
**目标状态**：5-10 份核心工艺规范手册 + 50 张历史图纸特征入库；Process Recommender 先 query RAG 把相关知识塞进 prompt context；CLI 加 `index/search/wipe` 命令管理 collection。

## Metadata
- **Complexity**: **Large**
- **Source PRD**: `.claude/PRPs/prds/deepdraw-dfm-platform.prd.md`
- **PRD Phase**: Phase 5 — 企业标准记忆
- **Estimated Files**: 11

---

## UX Design

**N/A — 内部逻辑**。CLI 增加 `index / search / wipe` 子命令。

---

## Mandatory Reading

| Priority | File | Why |
|---|---|---|
| P0 | `src/deepdraw/agents/process_recommender.py` | 集成点 |
| P0 | `src/deepdraw/state.py` | 加 `rag_context` 字段 |
| P0 | `src/deepdraw/cli.py` | 加 index/search 子命令 |
| P1 | `src/deepdraw/tools/mcp_tools.py` | 替换 mock |
| P1 | `src/deepdraw/prompts/process_recommender.md` | 加 RAG context |

## External Documentation

| Topic | Source | Key Takeaway |
|---|---|---|
| ChromaDB 0.5.x | docs.trychroma.com | `PersistentClient(path)`、`create_collection`、`add/query` |
| langchain-chroma | python.langchain.com | `Chroma(collection_name, embedding_function, persist_directory)` |
| MarkdownTextSplitter | python.langchain.com | chunk_size 1000 + overlap 200 |
| OpenAI Embeddings | platform.openai.com | `text-embedding-3-small` 1536 维 |
| macOS ChromaDB 锁文件 | github.com/chroma-core/chroma | 测试用 `EphemeralClient` |

---

## Files to Change

| File | Action | Justification |
|---|---|---|
| `pyproject.toml` | UPDATE | 加 chromadb / langchain-chroma / tiktoken |
| `src/deepdraw/state.py` | UPDATE | 加 `rag_context` 字段 |
| `src/deepdraw/tools/rag.py` | CREATE | Vector DB + RAG 检索接口 |
| `src/deepdraw/tools/ingest.py` | CREATE | 文档入库工具 |
| `src/deepdraw/tools/seed.py` | CREATE | PoC mock 数据 |
| `src/deepdraw/tools/mcp_tools.py` | UPDATE | 真实 RAG 接入 |
| `src/deepdraw/agents/process_recommender.py` | UPDATE | 先 RAG 再 LLM |
| `src/deepdraw/cli.py` | UPDATE | 加 index/search/wipe 子命令 |
| `src/deepdraw/prompts/process_recommender.md` | UPDATE | 加 RAG context |
| `tests/test_tools_rag.py` | CREATE | RAG 单测 |
| `tests/conftest.py` | UPDATE | temp_chroma fixture |

---

## NOT Building

- 真实 ERP/PDM 接口（Phase 7+）
- 历史图纸自动特征抽取（Phase 5 mock）
- 多模态 embedding（仅文字）
- 重排序 / Hybrid search
- 远程 Vector DB（Qdrant Cloud / Milvus）

---

## Step-by-Step Tasks

### Task 1-11 概要（详见 plan 完整版）

1. pyproject.toml 加依赖
2. rag.py: get_client / get_or_create_collection / add_documents / query / format_results
3. ingest.py: MarkdownTextSplitter + OpenAIEmbeddings + ingest_manual / ingest_drawing_summary
4. seed.py: 5 mock manuals + 10 mock drawings 内联
5. state.py: rag_context 字段
6. process_recommender.py: 先 _rag_query_sync 再 LLM
7. process_recommender.md: {rag_context} 模板
8. mcp_tools.py: 真实 RAG（保留 mock 作为 fallback）
9. cli.py: index/search/wipe 子命令（首次多子命令模式）
10. test_tools_rag.py: EphemeralClient fixture + 3 test
11. 5 级验证 + commit + merge

---

## Acceptance Criteria

- [ ] ChromaDB 0.5.x 接入成功
- [ ] 5 mock manuals + 10 mock drawings 入库
- [ ] Process Recommender 调 RAG
- [ ] CLI index/search/wipe 工作
- [ ] 31/31 tests pass
- [ ] ruff + format 全过

## Risks

| Risk | L | I | Mitigation |
|---|---|---|---|
| OpenAI API 不可用 | M | M | fallback mock |
| 中文 RAG 质量 | M | M | Phase 7 PoC 评估 |
| macOS lock 文件 | M | L | 测试用 EphemeralClient |

---

*Confidence Score*: **8/10** — ChromaDB API 稳定；RAG 与 LangGraph 集成模式成熟
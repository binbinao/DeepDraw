# Plan: Phase 3 — Core 3 Agents with LLM

## Summary
实现 3 个核心 Agent 的真实 LLM 调用：Spec Interpreter（GPT-4o 抽结构化 spec）、Drawing Auditor（Vision-LLM 审图生成 errors 列表）、BOM Generator（LLM 抽零件清单）。所有 Agent 用 `with_structured_output(PydanticModel)` 拿到类型安全输出。Tests 用 `FakeListChatModel` 避免真实 API 调用。

## User Story
As a **Phase 4-6 开发者**,
I want **3 个核心 Agent 真实调 LLM + Vision-LLM 并输出结构化 Pydantic 模型**,
so that **我可以在它们之上构建 Process Recommender / Chief Verifier / RAG，不用自己设计 LLM 调用模式**。

## Problem → Solution
**当前状态**：3 个 Agent 是 echo 函数，输出空数据。Phase 2 已建好 PDF/DXF 解析工具链。
**目标状态**：3 个 Agent 读 `intermediate` state，调 LLM，返回结构化 Pydantic 模型。Tests 用 mock LLM 跑过，10 张真实图上输出可读结果。

## Metadata
- **Complexity**: **Large**
- **Source PRD**: `.claude/PRPs/prds/deepdraw-dfm-platform.prd.md`
- **PRD Phase**: Phase 3 — 核心 3 Agent
- **Estimated Files**: 10（3 NEW src/ + 2 NEW test/ + 5 UPDATE）

---

## UX Design

**N/A — 内部逻辑**。CLI 输出 JSON 字段会扩展（`spec` 字段从占位变真实 LLM 输出），但 UI 形态不变。

---

## Mandatory Reading

| Priority | File | Why |
|---|---|---|
| P0 | `src/deepdraw/state.py` | DrawingSpec/DrawingError/BOMItem 子 TypedDict（已存在） |
| P0 | `src/deepdraw/llm.py` | LLM factory `get_llm(agent_name)`（已存在） |
| P0 | `src/deepdraw/agents/spec_interpreter.py` | 当前 PDF 解析逻辑（Phase 2） |
| P0 | `src/deepdraw/agents/drawing_auditor.py` | 当前图片消费逻辑（Phase 2） |
| P0 | `src/deepdraw/agents/bom_generator.py` | 当前 echo 实现 |
| P1 | `src/deepdraw/prompts/*.md` | 5 个 System Prompt（Phase 1 占位） |
| P1 | `src/deepdraw/tools/pdf.py` | `extract_pdf_text` / `extract_pdf_images` 返回值 |

## External Documentation

| Topic | Source | Key Takeaway |
|---|---|---|
| `init_chat_model` | langchain docs | `init_chat_model("openai:gpt-4o", temperature=0)` |
| `with_structured_output` | langchain docs | 直接传 Pydantic v2 model class |
| Vision 输入 | langchain multimodal docs | `HumanMessage(content=[{"type":"text"}, {"type":"image_url",...}])` |
| `FakeListChatModel` | langchain_core | 支持 `ainvoke`，可循环 scripted responses |
| Pydantic v2 field | pydantic docs | `Field(description="...")` 让 LLM 知道字段含义 |
| 错误处理 | langchain_classic | `OutputFixingParser` + `with_fallbacks` 三层 fallback |

---

## Patterns to Mirror

### EXISTING_ASYNC_AGENT_NODE
// SOURCE: src/deepdraw/agents/spec_interpreter.py
```python
async def spec_interpreter_node(state: AgentState) -> dict:
    """Read from state, return partial update dict."""
    return {"intermediate": {...}, "spec": {...}}
```

### EXISTING_LLM_FACTORY
// SOURCE: src/deepdraw/llm.py:21
```python
def get_llm(agent_name: str):
    return init_chat_model(**_LLM_CONFIG[agent_name])
```

---

## Files to Change

| File | Action | Justification |
|---|---|---|
| `src/deepdraw/prompts.py` | CREATE | Prompt 加载器 |
| `src/deepdraw/llm.py` | UPDATE | 加 `get_structured_llm` factory |
| `src/deepdraw/agents/spec_interpreter.py` | UPDATE | 调 LLM 抽 DrawingSpec |
| `src/deepdraw/agents/drawing_auditor.py` | UPDATE | 调 Vision-LLM 返回 errors |
| `src/deepdraw/agents/bom_generator.py` | UPDATE | 调 LLM 抽 BOM |
| `src/deepdraw/prompts/{spec,drawing_auditor,bom_generator}.md` | UPDATE | 升级为 few-shot 真实 prompt |
| `tests/conftest.py` | UPDATE | 加 fake_llm fixture |
| `tests/test_agents_mock.py` | CREATE | mock LLM 测试 3 agent |
| `tests/test_llm.py` | CREATE | LLM factory 单测 |
| `tests/test_agents.py` | UPDATE | 改用 mock LLM 验证新行为 |

---

## NOT Building

- Process Recommender / Chief Verifier（Phase 4）
- Vector DB / RAG（Phase 5）
- 自博弈 Reflection Loop（Phase 6）
- PoC 100 张 NG 图（Phase 7）
- 流式输出（sync `ainvoke` 即可）
- LLM 成本追踪（Phase 7）
- `OutputFixingParser` 自动重试（Phase 7）

---

## Step-by-Step Tasks

### Task 1-2: 创建 prompts.py + 扩展 llm.py
详见 plan 内容（含完整代码示例）

### Task 3-5: 升级 3 个 System Prompt（few-shot）
详见 plan 内容

### Task 6-8: 3 个 Agent 真实 LLM 实现
- spec_interpreter: Pydantic `SpecLLMResult` + `get_structured_llm`
- drawing_auditor: Vision `HumanMessage` + base64 image
- bom_generator: Pydantic `BOMLLMResult`

### Task 9-11: Tests (mock LLM + factory)
- conftest 加 fake_llm fixture
- test_agents_mock.py: 6 个新测试
- test_llm.py: 2 个新测试

### Task 12: 5 级验证
- ruff check + format
- pytest 35+ pass
- E2E with API key

---

## Acceptance Criteria
- [ ] 3 个 Agent 真实调 LLM
- [ ] Spec Interpreter 输出 material/thickness/batch
- [ ] Drawing Auditor 输出 errors 列表（Vision 真实调）
- [ ] BOM Generator 输出 BOM 列表
- [ ] LLM 错误优雅降级
- [ ] 5 个 prompt 升级
- [ ] 35+ tests pass
- [ ] ruff 全过

## Confidence Score: **7/10**
API 明确，但 Vision-LLM 对工程图准确率仍是黑盒（PRD 最高风险假设）。

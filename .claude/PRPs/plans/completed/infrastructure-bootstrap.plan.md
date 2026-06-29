# Plan: Phase 1 — Infrastructure Bootstrap

## Summary
为 DeepDraw 项目搭建 LangGraph 1.2.6 多 Agent 脚手架：5 个 Agent 占位节点、TypedDict State Schema、StateGraph 编译、CLI 入口、pytest 测试骨架。Phase 1 不实现任何业务逻辑（PDF 解析、Vision-LLM、Vector DB 全部延后到 Phase 2-6），只交付"能跑通完整 5 节点流程、输出空 JSON 骨架"的可运行框架。

## User Story
As a **DeepDraw Phase 2-7 的 Agent 开发者**,
I want **一套可运行的 LangGraph 多 Agent 脚手架（5 个 Agent 占位 + State 契约 + 端到端 CLI + 测试骨架）**,
so that **我可以专注于单个 Agent 的 prompt 调优和工具集成，不需要重新设计图结构、状态管理、依赖管理与测试基础设施**。

## Problem → Solution
**当前状态**：仓库只有空的 `pyproject.toml` 和 PyCharm 默认 `main.py`，无任何 DeepDraw 代码
**目标状态**：`python main.py` 能跑通 5-Agent 流程，每个 Agent 输出占位结果，最终输出空 JSON；`pytest` 能跑；`langgraph dev` 能起 Studio

## Metadata
- **Complexity**: **Large**（10+ 文件、新技术栈、新架构模式、需新依赖）
- **Source PRD**: `.claude/PRPs/prds/deepdraw-dfm-platform.prd.md`
- **PRD Phase**: Phase 1 — 基础设施搭建
- **Estimated Files**: 18 个（详见 "Files to Change"）

---

## UX Design

**N/A — 内部脚手架**。Phase 1 不涉及用户界面；CLI 是开发者工具，不是终端用户界面。

---

## Mandatory Reading

| Priority | Source | Why |
|---|---|---|
| P0 | `.claude/PRPs/prds/deepdraw-dfm-platform.prd.md` | PRD 全局约束、5-Agent 角色、State 设计、Non-functional requirements |
| P0 | LangGraph 官方文档 — StateGraph 与 multi-agent 章节 | 决定 State Schema 与图拓扑的 API 形式 |
| P1 | `langgraph/examples/multi_agent/agent_supervisor`（GitHub） | 多 Agent 项目的官方目录结构模板 |
| P1 | LangGraph 1.2.6 changelog | 确认 `init_chat_model`、`add_node(retry_policy=)`、`InMemorySaver` 当前 API 形式 |
| P2 | PRD Phase 2-7 描述 | 理解 State Schema 必须能承载所有后续阶段的输出 |

## External Documentation

| Topic | Source | Key Takeaway |
|---|---|---|
| LangGraph 当前版本 | PyPI | 1.2.6（2026-06），Python ≥3.10 |
| StateGraph API | langchain-ai.github.io | 仍用 `StateGraph(State)` + `add_node` / `add_edge` / `add_conditional_edges` / `compile()` |
| Reducers | langchain-ai.github.io | `Annotated[list[T], operator.add]` 累积列表；`Annotated[list, add_messages]` 累积消息 |
| CLI 工具 | LangGraph CLI docs | `langgraph new` 替代废弃的 `langgraph init`；`langgraph dev` 起 Studio |
| Checkpointers | langgraph.checkpoint.memory / sqlite | `InMemorySaver()`（测试用）、`SqliteSaver.from_conn_string()`（生产用） |
| ruff 配置 | langgraph 仓库根 `pyproject.toml` | **禁用** `from typing import TypedDict`，必须用 `from typing_extensions import TypedDict` |

---

## Patterns to Mirror

**No existing codebase — this is greenfield.** 所有模式参考 LangGraph 官方 examples（`langgraph/examples/multi_agent/agent_supervisor`）：

### MULTI_AGENT_LAYOUT
// SOURCE: langgraph/examples/multi_agent/agent_supervisor
```
src/<package>/
  graph.py          # StateGraph + compile() → exports `graph`
  state.py          # AgentState TypedDict
  agents/
    <agent_name>.py # llm + system prompt + async def <agent>_node(state) -> dict
  prompts/          # .md 或 .py 常量
  tools/            # 工具函数
```

### STATE_SCHEMA
// SOURCE: langgraph 官方文档
```python
from typing_extensions import TypedDict, Annotated
from langgraph.graph import add_messages
import operator

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    accumulator: Annotated[list[str], operator.add]
    scalar_field: str
```

### AGENT_MODULE
// SOURCE: langgraph/examples/multi_agent/agent_supervisor/agent_supervisor/workers/worker.py
```python
from langgraph.graph import StateGraph

WORKER_PROMPT = "You are the worker..."

async def worker_node(state: AgentState) -> dict:
    """Read from state, return partial update dict."""
    return {"worker_output": "..."}
```

### GRAPH_COMPOSITION
// SOURCE: langgraph 官方文档
```python
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver

builder = StateGraph(AgentState)
builder.add_node("name", fn, retry_policy=RetryPolicy(max_attempts=3))
builder.add_edge(START, "first_node")
builder.add_edge("first_node", "second_node")
builder.add_conditional_edges("decision_node", lambda s: "next" if s["ok"] else END)
graph = builder.compile(checkpointer=InMemorySaver())
```

---

## Files to Change

| File | Action | Justification |
|---|---|---|
| `pyproject.toml` | UPDATE | 加 LangGraph、langchain-core、pytest、typer、ruff 等依赖；加 `[project.scripts]` 入口点 |
| `langgraph.json` | CREATE | LangGraph Studio 配置，引用 `deepdraw.graph:graph` |
| `.env.example` | CREATE | `OPENAI_API_KEY`、`ANTHROPIC_API_KEY`、`LANGSMITH_API_KEY` 占位 |
| `README.md` | CREATE | 项目说明 + 5 步快速开始（uv sync / pytest / langgraph dev / make run） |
| `src/deepdraw/__init__.py` | CREATE | 包标识，`__version__ = "0.1.0"` |
| `src/deepdraw/state.py` | CREATE | `AgentState` TypedDict + 子 TypedDict（DrawingSpec / DrawingError / BOMItem / ProcessStep） |
| `src/deepdraw/llm.py` | CREATE | LLM factory：`get_llm(agent_name, temperature=0.0)`，用 `init_chat_model` |
| `src/deepdraw/graph.py` | CREATE | StateGraph 编译：`builder` 定义节点+边，`graph = builder.compile(checkpointer=InMemorySaver())` |
| `src/deepdraw/cli.py` | CREATE | typer CLI：`python -m deepdraw <drawing.pdf>` |
| `src/deepdraw/agents/__init__.py` | CREATE | 包标识 |
| `src/deepdraw/agents/spec_interpreter.py` | CREATE | `async def spec_interpreter_node(state) -> dict`，占位 echo |
| `src/deepdraw/agents/drawing_auditor.py` | CREATE | `async def drawing_auditor_node(state) -> dict`，占位 echo |
| `src/deepdraw/agents/bom_generator.py` | CREATE | `async def bom_generator_node(state) -> dict`，占位 echo |
| `src/deepdraw/agents/process_recommender.py` | CREATE | `async def process_recommender_node(state) -> dict`，占位 echo |
| `src/deepdraw/agents/chief_verifier.py` | CREATE | `async def chief_verifier_node(state) -> dict`，占位 echo + reflection counter |
| `src/deepdraw/prompts/__init__.py` | CREATE | 包标识 |
| `src/deepdraw/prompts/spec_interpreter.md` | CREATE | Spec Interpreter System Prompt（占位：列出职责） |
| `src/deepdraw/prompts/drawing_auditor.md` | CREATE | Drawing Auditor System Prompt（占位） |
| `src/deepdraw/prompts/bom_generator.md` | CREATE | BOM Generator System Prompt（占位） |
| `src/deepdraw/prompts/process_recommender.md` | CREATE | Process Recommender System Prompt（占位） |
| `src/deepdraw/prompts/chief_verifier.md` | CREATE | Chief Verifier System Prompt（占位） |
| `src/deepdraw/tools/__init__.py` | CREATE | 包标识 |
| `src/deepdraw/tools/README.md` | CREATE | 说明：Phase 2 才实现 MCP 工具，Phase 1 留空 |
| `tests/__init__.py` | CREATE | 测试包标识 |
| `tests/conftest.py` | CREATE | 共享 fixtures：`sample_state`、`compiled_graph` |
| `tests/test_state.py` | CREATE | State 字段存在性测试 |
| `tests/test_graph.py` | CREATE | 图可编译、5 节点都存在、START→...→END 路径可走通 |
| `tests/test_agents.py` | CREATE | 5 个 Agent 各自的 smoke test：传入空 state 返回正确 partial update |
| `main.py` | UPDATE | 改为 `from deepdraw.cli import app; app()` 入口（向后兼容） |
| `.gitignore` | CREATE | 忽略 `.venv/`、`__pycache__/`、`.env`、`*.egg-info/`、`checkpoints.db` |
| `ruff.toml` | CREATE | ruff 配置：line-length 100、target-version py312、与 LangGraph 一致（禁 `from typing import TypedDict`） |

**总计**: 30 个文件（UPDATE 2 + CREATE 28）

---

## NOT Building

明确不在 Phase 1 实现（防止范围蔓延）：

- **PDF/DXF 解析**（pdfplumber、PyMuPDF、ezdxf）— Phase 2
- **Vision-LLM 真实调用**（GPT-4o/Claude 看图）— Phase 3
- **真实 LLM 调用**（Phase 1 的 Agent 都是 echo，不调 `ainvoke`）— Phase 3+
- **Vector DB**（ChromaDB/Qdrant 接入）— Phase 5
- **RAG 召回**（企业标准库检索）— Phase 5
- **自博弈 3 轮辩论**（Phase 1 只有 1 条 conditional edge 占位，max_iter=1）— Phase 6
- **MCP Server 真实接口**（`query_material_price` 等）— Phase 2
- **MCP 工具注册到 LangGraph**（`ToolNode` 接入）— Phase 2
- **100 张 NG 图纸基准测试**（PoC 验证）— Phase 7
- **Web UI / LangGraph Studio 之外的 UI**（typer CLI 是 Phase 1 唯一入口）
- **错误处理细节**（Phase 1 只在 LangGraph 节点级别用 `retry_policy=RetryPolicy(max_attempts=3)`，不写业务级 try/except）
- **日志框架**（Phase 1 用 `print`，Phase 3+ 再上 structlog/loguru）
- **CI/CD**（GitHub Actions、Docker 镜像）— Phase 7
- **LangGraph `up`（Docker 部署）**— Phase 7

---

## Step-by-Step Tasks

### Task 1: 清理 PyCharm 默认文件，更新 pyproject.toml
- **ACTION**: 删除 `main.py` 里的 PyCharm 样板代码，更新 `pyproject.toml` 加依赖
- **IMPLEMENT**:
  ```toml
  [project]
  name = "deepdraw"
  version = "0.1.0"
  description = "DFM-Copilot Squad — 钣金/机加工图纸审核与工艺决策多 Agent 系统"
  requires-python = ">=3.12"
  dependencies = [
      "langgraph==1.2.6",
      "langchain-core>=1.0,<2",
      "langgraph-checkpoint>=2,<5",
      "langgraph-checkpoint-sqlite==3.1.0",
      "pydantic>=2",
      "python-dotenv>=1.0",
      "typer>=0.12",
  ]

  [project.optional-dependencies]
  dev = [
      "pytest>=8",
      "pytest-asyncio>=0.23",
      "ruff>=0.4",
      "langgraph-cli[inmem]>=0.2",
  ]

  [project.scripts]
  deepdraw = "deepdraw.cli:app"

  [build-system]
  requires = ["hatchling"]
  build-backend = "hatchling.build"

  [tool.hatch.build.targets.wheel]
  packages = ["src/deepdraw"]

  [tool.pytest.ini_options]
  asyncio_mode = "auto"
  testpaths = ["tests"]

  [tool.ruff]
  line-length = 100
  target-version = "py312"
  ```
- **MIRROR**: langgraph 官方 `pyproject.toml` 依赖风格
- **IMPORTS**: 无
- **GOTCHA**: 硬依赖 cap `langchain-core<2` 不能浮到 2.x；`xxhash>=3.5.0` 会被自动拉入
- **VALIDATE**: `uv sync`（或 `pip install -e ".[dev]"`）成功，无解析冲突

### Task 2: 安装依赖到 .venv
- **ACTION**: 用 uv 安装 dev 依赖
- **IMPLEMENT**: `cd /Users/jiduobin/Documents/GitHub/Personal/DeepDraw && uv pip install -e ".[dev]"`
- **MIRROR**: 无（greenfield）
- **IMPORTS**: 无
- **GOTCHA**: 用 `uv pip install`（不是 `uv add`），因为 `pyproject.toml` 改完即可；macOS aarch64 上 `psycopg[binary]` 可能装不上，但 Phase 1 不需要它
- **VALIDATE**: `python -c "import langgraph; print(langgraph.__version__)"` 输出 1.2.6

### Task 3: 创建 ruff.toml
- **ACTION**: 与 LangGraph 官方风格一致
- **IMPLEMENT**:
  ```toml
  line-length = 100
  target-version = "py312"

  [lint]
  select = ["E", "F", "I", "W", "UP", "B", "SIM"]
  ignore = ["E501"]  # line-length 由 formatter 处理
  ```
- **MIRROR**: langgraph 仓库根 `pyproject.toml` 的 `[tool.ruff]` 段
- **IMPORTS**: 无
- **GOTCHA**: 不要加 `from typing import TypedDict` 的 ban（russ 2024+ 默认已 E722 之类的规则，TypedDict 是 typing_extensions，规则独立）
- **VALIDATE**: `ruff check src/` 无 error

### Task 4: 创建 .gitignore
- **ACTION**: 标准 Python .gitignore
- **IMPLEMENT**:
  ```
  .venv/
  __pycache__/
  *.py[cod]
  *.egg-info/
  .env
  checkpoints.db
  .pytest_cache/
  .ruff_cache/
  .idea/
  dist/
  build/
  ```
- **MIRROR**: github/gitignore Python 标准模板
- **IMPORTS**: 无
- **GOTCHA**: `.idea/` 已在仓库（PyCharm 用户的项目配置），第一次 commit 决定是否保留；建议保留但加进 gitignore
- **VALIDATE**: `git status --ignored` 显示被忽略文件列表

### Task 5: 创建 src/deepdraw/ 目录结构
- **ACTION**: 一组 mkdir + __init__.py
- **IMPLEMENT**:
  ```bash
  mkdir -p src/deepdraw/agents src/deepdraw/prompts src/deepdraw/tools tests
  touch src/deepdraw/__init__.py src/deepdraw/agents/__init__.py \
        src/deepdraw/prompts/__init__.py src/deepdraw/tools/__init__.py \
        tests/__init__.py
  ```
- **MIRROR**: langgraph/examples/multi_agent/agent_supervisor 目录
- **IMPORTS**: 无
- **GOTCHA**: `src/` 布局需要 setuptools/hatchling 识别；pyproject.toml 的 `[tool.hatch.build.targets.wheel]` 已配
- **VALIDATE**: `python -c "import deepdraw"` 无错

### Task 6: 写 src/deepdraw/state.py
- **ACTION**: 定义 AgentState TypedDict 与 4 个子 TypedDict
- **IMPLEMENT**:
  ```python
  """LangGraph State Schema for DeepDraw's 5-Agent workflow.

  Designed for Sequential + Reflection Loop topology.
  Phase 1 only needs the schema; Phase 3+ fills in real values.
  """
  from __future__ import annotations

  import operator
  from typing_extensions import Annotated, TypedDict


  class DrawingSpec(TypedDict, total=False):
      """Output of 👓 Spec Interpreter."""
      material: str
      thickness_mm: float
      batch_size: int
      surface_treatment: str
      raw_requirements: dict


  class DrawingError(TypedDict):
      """Output of 🔍 Drawing Auditor (list element)."""
      error_type: str
      location: str
      severity: str  # "critical" | "major" | "minor"
      description: str


  class BOMItem(TypedDict):
      """Output of 📒 BOM Generator (list element)."""
      part_number: str
      name: str
      quantity: int
      unit: str


  class ProcessStep(TypedDict):
      """Output of ⚙️ Process Recommender (list element)."""
      sequence: int
      operation: str
      machine: str
      tooling: str
      parameters: dict


  class AgentState(TypedDict, total=False):
      """Top-level state for the 5-Agent LangGraph workflow."""
      # Inputs
      drawing_path: str
      # Accumulator outputs (use operator.add reducer for list fields)
      spec: DrawingSpec
      errors: Annotated[list[DrawingError], operator.add]
      bom: Annotated[list[BOMItem], operator.add]
      process_plan: list[ProcessStep]
      # Reflection state (used by Chief Verifier ↔ Process Recommender loop)
      verification_notes: Annotated[list[str], operator.add]
      reflection_iterations: int
      # Terminal state
      final_report: dict
      status: str  # "success" | "needs_human" | "conflict"
  ```
- **MIRROR**: langgraph 官方 TypedDict + Annotated reducer 模式
- **IMPORTS**: `from typing_extensions import TypedDict, Annotated`（**不要** `from typing import TypedDict`）
- **GOTCHA**: 子 TypedDict 用 `total=False` 让所有字段可选（Phase 1 不要求完整）；列表字段必须 `Annotated[..., operator.add]`，否则多次 node 更新会覆盖
- **VALIDATE**: `python -c "from deepdraw.state import AgentState; print(AgentState.__annotations__)"` 输出字段

### Task 7: 写 5 个 Agent 的占位 node
- **ACTION**: 每个 agent 一个文件，定义 `async def <name>_node(state) -> dict` 返回占位 partial update
- **IMPLEMENT**: 5 个文件结构相同（这里只写 `spec_interpreter.py` 作为模板，其他 4 个类推）：
  ```python
  """👓 Spec Interpreter — 需求翻译官

  Phase 1 placeholder: returns an empty DrawingSpec.
  Phase 3 will call a real LLM with prompts/spec_interpreter.md.
  """
  from __future__ import annotations

  from deepdraw.state import AgentState


  async def spec_interpreter_node(state: AgentState) -> dict:
      """Read drawing_path from state, return spec placeholder."""
      return {
          "spec": {
              "raw_requirements": {"drawing_path": state.get("drawing_path", "")},
          },
      }
  ```
  其他 4 个 agent：
  - `drawing_auditor.py` → `return {"errors": []}`
  - `bom_generator.py` → `return {"bom": []}`
  - `process_recommender.py` → `return {"process_plan": []}`
  - `chief_verifier.py` → `return {"verification_notes": ["[Phase1 placeholder] no verification performed"], "reflection_iterations": 1, "status": "needs_human"}`
- **MIRROR**: langgraph/examples/multi_agent 中 worker 的 `async def <name>_node(state) -> dict` 形式
- **IMPORTS**: `from deepdraw.state import AgentState`
- **GOTCHA**: 5 个 Agent 必须**异步函数**（`async def`），因为 LangGraph 1.x 推荐全异步；返回 dict 是 partial update 模式
- **VALIDATE**: `python -c "import asyncio; from deepdraw.agents.spec_interpreter import spec_interpreter_node; print(asyncio.run(spec_interpreter_node({})))"` 输出占位 dict

### Task 8: 写 5 个 Agent 的 System Prompt（Markdown）
- **ACTION**: 每个 prompts/*.md 写占位文本，描述 Agent 角色
- **IMPLEMENT**: 5 个 Markdown 文件，每个 5-10 行，描述：
  - 角色名 + 图标
  - 对应 CAX 环节
  - 核心职责（1-2 句）
  - 输入 / 输出契约
  - 注意事项
  
  例如 `prompts/spec_interpreter.md`:
  ```markdown
  # 👓 Spec Interpreter — 需求翻译官

  ## 角色
  你负责读取订单规格和图纸标题栏，提炼出关键尺寸、材料、工艺要求。

  ## 输入
  - `drawing_path`: PDF/DXF 文件路径

  ## 输出（结构化 JSON）
  - `material`: 材料牌号，如 "Q235B"
  - `thickness_mm`: 板厚
  - `batch_size`: 批量
  - `surface_treatment`: 表面处理
  - `raw_requirements`: 其他原始需求

  ## 注意事项
  - 图纸标题栏往往格式混乱，优先信任"明细栏"与"技术要求"段
  - 对模糊字段必须标 `null` 并写明"需人工确认"
  ```
  
  其他 4 个 prompt 类比覆盖 Drawing Auditor / BOM Generator / Process Recommender / Chief Verifier 的角色。
- **MIRROR**: langgraph/examples/multi_agent 中 worker 的 prompt 形式
- **IMPORTS**: 无（纯文本，Phase 3 才会 `read_prompt()` 加载）
- **GOTCHA**: Phase 1 prompt 是**占位**，不参与 LLM 调用；Phase 3 再做 prompt 工程
- **VALIDATE**: `cat prompts/spec_interpreter.md` 有内容

### Task 9: 写 src/deepdraw/llm.py（LLM Factory）
- **ACTION**: 提供一个 LLM factory，方便后续 Phase 给每个 Agent 配不同 temperature
- **IMPLEMENT**:
  ```python
  """LLM factory for DeepDraw agents.

  Phase 1 defines the factory but does NOT use it (agents are echo).
  Phase 3 will import `get_llm("spec_interpreter")` inside each node.
  """
  from __future__ import annotations

  from langchain.chat_models import init_chat_model


  # Per-agent LLM config (Phase 1 placeholders; Phase 3 tunes these)
  _LLM_CONFIG: dict[str, dict] = {
      "spec_interpreter":     {"model": "openai:gpt-4o",        "temperature": 0.0},
      "drawing_auditor":      {"model": "openai:gpt-4o",        "temperature": 0.0},
      "bom_generator":        {"model": "openai:gpt-4o",        "temperature": 0.0},
      "process_recommender":  {"model": "openai:gpt-4o",        "temperature": 0.3},
      "chief_verifier":       {"model": "anthropic:claude-opus-4-6", "temperature": 0.0},
  }


  def get_llm(agent_name: str):
      """Return a configured chat model for the given agent.

      Reads API keys from environment (OPENAI_API_KEY, ANTHROPIC_API_KEY).
      """
      if agent_name not in _LLM_CONFIG:
          raise KeyError(f"Unknown agent: {agent_name}. Known: {list(_LLM_CONFIG)}")
      return init_chat_model(**_LLM_CONFIG[agent_name])
  ```
- **MIRROR**: langchain `init_chat_model` 工厂模式
- **IMPORTS**: `from langchain.chat_models import init_chat_model`
- **GOTCHA**: `init_chat_model` 不会在工厂调用时校验 API key，所以 `chief_verifier` 配置 Anthropic 但 Phase 1 不调用，不会报错
- **VALIDATE**: `python -c "from deepdraw.llm import get_llm; print(get_llm)"` 输出函数对象（不调用，避免需要 API key）

### Task 10: 写 src/deepdraw/graph.py
- **ACTION**: 编译 5-Agent StateGraph
- **IMPLEMENT**:
  ```python
  """LangGraph StateGraph definition for the 5-Agent DFM-Copilot Squad."""
  from __future__ import annotations

  from langgraph.checkpoint.memory import InMemorySaver
  from langgraph.graph import END, START, StateGraph
  from langgraph.types import RetryPolicy

  from deepdraw.agents import (
      bom_generator,
      chief_verifier,
      drawing_auditor,
      process_recommender,
      spec_interpreter,
  )
  from deepdraw.state import AgentState

  MAX_REFLECTION_ITERATIONS = 3  # Phase 6 才会真正驱动自博弈；Phase 1 占位

  builder = StateGraph(AgentState)

  # Nodes (with retry policy for transient LLM failures in later phases)
  builder.add_node(
      "spec_interpreter",
      spec_interpreter.spec_interpreter_node,
      retry_policy=RetryPolicy(max_attempts=3),
  )
  builder.add_node(
      "drawing_auditor",
      drawing_auditor.drawing_auditor_node,
      retry_policy=RetryPolicy(max_attempts=3),
  )
  builder.add_node(
      "bom_generator",
      bom_generator.bom_generator_node,
      retry_policy=RetryPolicy(max_attempts=3),
  )
  builder.add_node(
      "process_recommender",
      process_recommender.process_recommender_node,
      retry_policy=RetryPolicy(max_attempts=3),
  )
  builder.add_node(
      "chief_verifier",
      chief_verifier.chief_verifier_node,
      retry_policy=RetryPolicy(max_attempts=3),
  )

  # Edges: Sequential main flow
  builder.add_edge(START, "spec_interpreter")
  builder.add_edge("spec_interpreter", "drawing_auditor")
  builder.add_edge("drawing_auditor", "bom_generator")
  builder.add_edge("bom_generator", "process_recommender")
  builder.add_edge("process_recommender", "chief_verifier")

  # Conditional edge placeholder for Reflection Loop (real logic in Phase 6)
  def should_reflect(state: AgentState) -> str:
      """Decide whether to loop back for another reflection round.

      Phase 1: always ends (max_iter enforced in Phase 6).
      """
      return END

  builder.add_conditional_edges("chief_verifier", should_reflect)

  # Compile with in-memory checkpointer (testing) — Phase 7 swaps to SqliteSaver
  graph = builder.compile(checkpointer=InMemorySaver())
  ```
- **MIRROR**: langgraph 官方 Sequential + conditional edge 模式
- **IMPORTS**: `from langgraph.graph import StateGraph, START, END`、`from langgraph.types import RetryPolicy`
- **GOTCHA**: `add_node` 的第一个参数是节点名（**字符串**），第二参数是函数；`retry_policy=RetryPolicy(max_attempts=3)` 是 LangGraph 1.x 的新参数（替代旧版 `retry=Retry(...)`）；`START` / `END` 是从 `langgraph.graph` 导入的常量，不要用 `"START"` / `"END"` 字符串
- **VALIDATE**: `python -c "from deepdraw.graph import graph; print(graph.nodes)"` 列出 5 个节点

### Task 11: 写 src/deepdraw/cli.py
- **ACTION**: typer CLI 入口
- **IMPLEMENT**:
  ```python
  """DeepDraw CLI — entry point for `deepdraw <drawing.pdf>` and `python -m deepdraw`."""
  from __future__ import annotations

  import json
  from pathlib import Path
  from typing import Optional

  import typer
  from rich.console import Console
  from rich.json import JSON

  from deepdraw.graph import graph

  app = typer.Typer(help="DeepDraw — DFM-Copilot Squad CLI")
  console = Console()


  @app.command()
  def run(
      drawing: Path = typer.Argument(..., help="Path to PDF/DXF drawing file", exists=True),
      thread_id: str = typer.Option("default", help="LangGraph thread ID for checkpointing"),
      output: Optional[Path] = typer.Option(None, help="Optional output JSON file"),
  ) -> None:
      """Run the 5-Agent DFM-Copilot workflow on a single drawing."""
      initial_state = {"drawing_path": str(drawing.absolute())}
      config = {"configurable": {"thread_id": thread_id}}

      console.print(f"[bold green]▶ DeepDraw:[/bold green] processing {drawing}")

      final_state = graph.invoke(initial_state, config=config)

      report = {
          "spec": final_state.get("spec", {}),
          "errors": final_state.get("errors", []),
          "bom": final_state.get("bom", []),
          "process_plan": final_state.get("process_plan", []),
          "verification_notes": final_state.get("verification_notes", []),
          "reflection_iterations": final_state.get("reflection_iterations", 0),
          "status": final_state.get("status", "unknown"),
      }

      if output:
          output.write_text(json.dumps(report, indent=2, ensure_ascii=False))
          console.print(f"[green]✓[/green] Report written to {output}")
      else:
          console.print(JSON(json.dumps(report, indent=2, ensure_ascii=False)))


  if __name__ == "__main__":
      app()
  ```
- **MIRROR**: typer + rich 标准模式
- **IMPORTS**: `import typer`、`from rich.console import Console`、`from rich.json import JSON`
- **GOTCHA**: `graph.invoke` 是同步调用（LangGraph 也支持 `ainvoke`，但 CLI 同步更简单）；`config["configurable"]["thread_id"]` 是 LangGraph 1.x 标准 checkpoint key
- **VALIDATE**: `python -m deepdraw.cli --help` 输出 typer help

### Task 12: 更新 main.py 为 CLI 入口
- **ACTION**: 把 PyCharm 默认文件替换为 DeepDraw CLI 入口
- **IMPLEMENT**:
  ```python
  """DeepDraw entry point.

  Forwards to the typer CLI in `deepdraw.cli`.
  Equivalent to running `python -m deepdraw` or the installed `deepdraw` script.
  """
  from deepdraw.cli import app

  if __name__ == "__main__":
      app()
  ```
- **MIRROR**: 简洁入口模式
- **IMPORTS**: `from deepdraw.cli import app`
- **GOTCHA**: PyCharm 用户的 .idea 配置会指向这个文件运行；保留向后兼容
- **VALIDATE**: `python main.py --help` 输出 typer help

### Task 13: 写 langgraph.json
- **ACTION**: LangGraph Studio / `langgraph dev` 配置
- **IMPLEMENT**:
  ```json
  {
    "graphs": {
      "deepdraw": "./src/deepdraw/graph.py:graph"
    },
    "env": "./.env"
  }
  ```
- **MIRROR**: langgraph 官方 examples 格式
- **IMPORTS**: 无
- **GOTCHA**: `"deepdraw.graph:graph"` 是 `module:variable` 格式，**不是** function 引用；运行 `langgraph dev` 时 LangGraph 会从 `deepdraw.graph` 模块导入 `graph` 变量
- **VALIDATE**: `langgraph validate` 无错（前提是 `langgraph-cli[inmem]` 已装）

### Task 14: 写 .env.example
- **ACTION**: 环境变量模板
- **IMPLEMENT**:
  ```
  # OpenAI (GPT-4o)
  OPENAI_API_KEY=sk-...

  # Anthropic (Claude Opus 4.6)
  ANTHROPIC_API_KEY=sk-ant-...

  # LangSmith (Studio observability, optional)
  LANGSMITH_API_KEY=lsv2_...
  LANGSMITH_TRACING=true
  LANGSMITH_PROJECT=deepdraw

  # Model deployment (Phase 6 will add local VLM options)
  ```
- **MIRROR**: 12-factor app 标准
- **IMPORTS**: 无
- **GOTCHA**: Phase 1 不需要任何 key（agent 是 echo）；`LANGSMITH_TRACING` 留空时 `langgraph dev` 会报错，需在 `.env` 设置 `LANGSMITH_TRACING=false` 或留空
- **VALIDATE**: `cp .env.example .env && grep -v '^#' .env` 显示实际配置

### Task 15: 写 README.md
- **ACTION**: 项目说明 + 快速开始
- **IMPLEMENT**:
  ```markdown
  # DeepDraw — DFM-Copilot Squad

  钣金/机加工行业的图纸审核与工艺决策多 Agent 系统。

  ## 快速开始

  ```bash
  # 1. 安装依赖
  uv sync                          # 或: pip install -e ".[dev]"

  # 2. 配置环境变量
  cp .env.example .env
  # 编辑 .env，填入 OPENAI_API_KEY 等

  # 3. 运行测试
  pytest

  # 4. CLI 试跑（输出空 JSON 骨架）
  echo "dummy content" > /tmp/test.pdf
  python -m deepdraw.cli run /tmp/test.pdf

  # 5. LangGraph Studio（可视化图结构）
  langgraph dev
  # 浏览器打开 https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024
  ```

  ## 项目结构
  ```
  src/deepdraw/
    state.py        # AgentState TypedDict
    graph.py        # StateGraph 编译
    llm.py          # LLM factory
    cli.py          # typer CLI
    agents/         # 5 个 Agent
    prompts/        # 5 个 System Prompt
    tools/          # MCP 工具占位（Phase 2）
  ```

  ## 路线图
  见 `.claude/PRPs/prds/deepdraw-dfm-platform.prd.md`
  - Phase 1: 基础设施（本阶段）✅
  - Phase 2: PDF/DXF 解析
  - Phase 3-4: 5 Agent 真实实现
  - Phase 5: Vector DB + RAG
  - Phase 6: 自博弈 Reflection Loop
  - Phase 7: 100 张 NG 图纸 PoC
  ```
- **MIRROR**: 标准 README 模板
- **IMPORTS**: 无
- **GOTCHA**: Phase 1 README 强调"输出空 JSON 骨架"是占位行为，避免误解
- **VALIDATE**: `cat README.md` 渲染正确

### Task 16: 写 tests/conftest.py
- **ACTION**: pytest 共享 fixtures
- **IMPLEMENT**:
  ```python
  """Shared pytest fixtures for DeepDraw tests."""
  from __future__ import annotations

  from pathlib import Path

  import pytest

  from deepdraw.graph import graph
  from deepdraw.state import AgentState


  @pytest.fixture
  def sample_state() -> AgentState:
      """Empty state with a dummy drawing path."""
      return {"drawing_path": "/tmp/test.pdf"}


  @pytest.fixture
  def compiled_graph():
      """The compiled LangGraph (with InMemorySaver)."""
      return graph


  @pytest.fixture
  def dummy_drawing(tmp_path: Path) -> Path:
      """Create a dummy file that stands in for a real PDF."""
      p = tmp_path / "dummy.pdf"
      p.write_text("PDF placeholder")
      return p
  ```
- **MIRROR**: pytest 标准 fixture 模式
- **IMPORTS**: `pytest`、`from deepdraw.graph import graph`、`from deepdraw.state import AgentState`
- **GOTCHA**: `tmp_path` 是 pytest 内置 fixture，无需 import；`sample_state` 返回 dict（TypedDict 是类型提示，运行时就是 dict）
- **VALIDATE**: `pytest --co tests/` 能收集到 fixture

### Task 17: 写 tests/test_state.py
- **ACTION**: State 字段存在性测试
- **IMPLEMENT**:
  ```python
  """Tests for AgentState schema fields."""
  from __future__ import annotations

  from deepdraw.state import AgentState


  def test_agent_state_has_required_fields() -> None:
      annotations = AgentState.__annotations__
      expected = {
          "drawing_path", "spec", "errors", "bom", "process_plan",
          "verification_notes", "reflection_iterations", "final_report", "status",
      }
      assert expected.issubset(annotations.keys()), \
          f"Missing fields: {expected - annotations.keys()}"


  def test_agent_state_empty_construction() -> None:
      state: AgentState = {}
      assert state.get("drawing_path") is None
      assert state.get("errors") is None
  ```
- **MIRROR**: pytest 简单 assert 模式
- **IMPORTS**: `from deepdraw.state import AgentState`
- **GOTCHA**: `__annotations__` 包含 `total=False` 时**所有声明字段**，不必担心缺字段
- **VALIDATE**: `pytest tests/test_state.py -v` 2 个 test pass

### Task 18: 写 tests/test_graph.py
- **ACTION**: 图编译、节点存在性、端到端可跑
- **IMPLEMENT**:
  ```python
  """Tests for the compiled StateGraph."""
  from __future__ import annotations

  from deepdraw.agents import (
      bom_generator, chief_verifier, drawing_auditor,
      process_recommender, spec_interpreter,
  )


  def test_graph_compiles(compiled_graph) -> None:
      """The graph should compile without error."""
      assert compiled_graph is not None


  def test_graph_has_all_5_agent_nodes(compiled_graph) -> None:
      """The 5 agent functions should be registered as nodes."""
      expected = {
          spec_interpreter.spec_interpreter_node,
          drawing_auditor.drawing_auditor_node,
          bom_generator.bom_generator_node,
          process_recommender.process_recommender_node,
          chief_verifier.chief_verifier_node,
      }
      actual = set(compiled_graph.nodes.values())
      assert expected.issubset(actual), \
          f"Missing nodes: {expected - actual}"


  def test_graph_runs_end_to_end_with_placeholder_state(compiled_graph, dummy_drawing) -> None:
      """Invoke the graph with a placeholder PDF and assert a non-empty final state."""
      final = compiled_graph.invoke(
          {"drawing_path": str(dummy_drawing)},
          config={"configurable": {"thread_id": "test-1"}},
      )
      assert final["status"] == "needs_human"
      assert final["reflection_iterations"] == 1
      assert "verification_notes" in final
  ```
- **MIRROR**: pytest + LangGraph 端到端测试模式
- **IMPORTS**: 5 个 agent 模块（用于拿函数引用）
- **GOTCHA**: `compiled_graph.nodes.values()` 拿的是函数对象，不是名字；要比较函数引用
- **VALIDATE**: `pytest tests/test_graph.py -v` 3 个 test pass

### Task 19: 写 tests/test_agents.py
- **ACTION**: 5 个 Agent 各自的 smoke test
- **IMPLEMENT**:
  ```python
  """Smoke tests for each of the 5 Agent nodes."""
  from __future__ import annotations

  import pytest

  from deepdraw.agents import (
      bom_generator, chief_verifier, drawing_auditor,
      process_recommender, spec_interpreter,
  )


  @pytest.mark.asyncio
  async def test_spec_interpreter_node_returns_spec() -> None:
      result = await spec_interpreter.spec_interpreter_node({"drawing_path": "/tmp/x.pdf"})
      assert "spec" in result
      assert result["spec"]["raw_requirements"]["drawing_path"] == "/tmp/x.pdf"


  @pytest.mark.asyncio
  async def test_drawing_auditor_node_returns_empty_errors() -> None:
      result = await drawing_auditor.drawing_auditor_node({})
      assert result == {"errors": []}


  @pytest.mark.asyncio
  async def test_bom_generator_node_returns_empty_bom() -> None:
      result = await bom_generator.bom_generator_node({})
      assert result == {"bom": []}


  @pytest.mark.asyncio
  async def test_process_recommender_node_returns_empty_plan() -> None:
      result = await process_recommender.process_recommender_node({})
      assert result == {"process_plan": []}


  @pytest.mark.asyncio
  async def test_chief_verifier_node_marks_needs_human() -> None:
      result = await chief_verifier.chief_verifier_node({})
      assert result["status"] == "needs_human"
      assert result["reflection_iterations"] == 1
      assert len(result["verification_notes"]) == 1
  ```
- **MIRROR**: pytest-asyncio + parametrize 模式
- **IMPORTS**: `pytest`、`from deepdraw.agents import 5 个模块`
- **GOTCHA**: `pytest-asyncio` 需要 `@pytest.mark.asyncio` 装饰器（或在 `pyproject.toml` 设 `asyncio_mode = "auto"`，本 plan 已配）；异步函数必须用 `asyncio.run` 或 pytest-asyncio 来跑
- **VALIDATE**: `pytest tests/test_agents.py -v` 5 个 test pass

### Task 20: 写 src/deepdraw/tools/README.md
- **ACTION**: 说明 tools/ 目录的 Phase 1 状态
- **IMPLEMENT**:
  ```markdown
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
  ```
- **MIRROR**: 占位 README
- **IMPORTS**: 无
- **GOTCHA**: README 内容本身就是规格说明，避免 Phase 2 起步时还要做设计决策
- **VALIDATE**: `cat src/deepdraw/tools/README.md` 有内容

---

## Testing Strategy

### Unit Tests

| Test | Input | Expected Output | Edge Case? |
|---|---|---|---|
| `test_agent_state_has_required_fields` | `AgentState.__annotations__` | 包含 9 个核心字段 | No |
| `test_agent_state_empty_construction` | `{}` typed as `AgentState` | `get("drawing_path") is None` | Yes（空 state） |
| `test_graph_compiles` | `graph` 变量 | 非 None | No |
| `test_graph_has_all_5_agent_nodes` | `graph.nodes` | 5 个函数都在 | No |
| `test_graph_runs_end_to_end_with_placeholder_state` | `{"drawing_path": "/tmp/x.pdf"}` | `status == "needs_human"` | No |
| `test_spec_interpreter_node_returns_spec` | `{"drawing_path": "/tmp/x.pdf"}` | spec.raw_requirements 含 path | No |
| `test_drawing_auditor_node_returns_empty_errors` | `{}` | `{"errors": []}` | Yes（空输入） |
| `test_bom_generator_node_returns_empty_bom` | `{}` | `{"bom": []}` | Yes（空输入） |
| `test_process_recommender_node_returns_empty_plan` | `{}` | `{"process_plan": []}` | Yes（空输入） |
| `test_chief_verifier_node_marks_needs_human` | `{}` | `status="needs_human", iterations=1` | No |

### Edge Cases Checklist
- [x] Empty state（5 个 agent node 都接受 `{}`）
- [x] Missing API keys（`get_llm` 不在 Phase 1 调用，不会触发）
- [x] Nonexistent file path（CLI 用 `typer.Option(exists=True)` 拦截，编译期报错）
- [x] Concurrent graph invocations（`thread_id` 不同则 InMemorySaver 隔离）
- [ ] Large file / streaming input（Phase 2 才考虑）
- [ ] Invalid PDF content（Phase 2 才考虑）
- [ ] Network failure on LLM call（Phase 3+ 才有，retry_policy=3 兜底）

---

## Validation Commands

### Static Analysis
```bash
cd /Users/jiduobin/Documents/GitHub/Personal/DeepDraw
ruff check src/ tests/
```
EXPECT: Zero errors

```bash
ruff format --check src/ tests/
```
EXPECT: No formatting changes needed

### Unit Tests
```bash
cd /Users/jiduobin/Documents/GitHub/Personal/DeepDraw
pytest tests/ -v
```
EXPECT: 10 tests pass（2 state + 3 graph + 5 agents）

### End-to-End CLI Run
```bash
cd /Users/jiduobin/Documents/GitHub/Personal/DeepDraw
echo "dummy content" > /tmp/test_deepdraw.pdf
python -m deepdraw.cli run /tmp/test_deepdraw.pdf
```
EXPECT: 输出含 `"status": "needs_human"` 的 JSON；不抛异常

### LangGraph Studio
```bash
cd /Users/jiduobin/Documents/GitHub/Personal/DeepDraw
# 需要先装 langgraph-cli: uv pip install -e ".[dev]"
langgraph dev
```
EXPECT: Studio 启动在 http://127.0.0.1:2024；浏览器打开 https://smith.langchain.com/studio/ 能看到 5 个节点

### Manual Validation
- [ ] `ls src/deepdraw/agents/` 列出 5 个 .py 文件
- [ ] `ls src/deepdraw/prompts/` 列出 5 个 .md 文件
- [ ] `cat pyproject.toml` 包含 langgraph==1.2.6
- [ ] `python -c "from deepdraw.graph import graph; print(len(graph.nodes))"` 输出 5
- [ ] `python -m deepdraw.cli --help` 显示 typer help
- [ ] `python main.py --help` 与上一步输出一致

---

## Acceptance Criteria
- [ ] `pyproject.toml` 含完整依赖（langgraph==1.2.6 等）
- [ ] `uv sync` 或 `pip install -e ".[dev]"` 无错
- [ ] `src/deepdraw/` 目录结构齐全（state、graph、llm、cli、agents、prompts、tools）
- [ ] 5 个 Agent 节点都存在且为 `async def` 返回 `dict`
- [ ] 5 个 System Prompt Markdown 文件存在
- [ ] `AgentState` TypedDict 含 9 个核心字段且列表字段带 `operator.add` reducer
- [ ] `StateGraph` 编译成功（5 节点 + START→spec→...→verifier→END 边 + 1 条 conditional edge）
- [ ] `python -m deepdraw.cli run <任意 PDF>` 输出非空 JSON
- [ ] `pytest tests/` 10 个测试全过
- [ ] `ruff check` 0 errors
- [ ] `langgraph.json` 配置正确
- [ ] `.env.example` 列出所有环境变量
- [ ] `README.md` 有快速开始指南
- [ ] `.gitignore` 完整

## Completion Checklist
- [ ] 所有 20 个 Task 完成
- [ ] 所有 Validation Command 通过
- [ ] 所有 Acceptance Criteria 满足
- [ ] 无 `print()` 调试代码残留
- [ ] 无硬编码 API key
- [ ] 无未实现 import 报错
- [ ] `langgraph dev` 能起（即便不调用 LLM）
- [ ] self-contained — 开发者拿到 plan 不需要再问任何问题

## Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| LangGraph 1.2.6 与 langchain-core 1.x 兼容性（API 变更） | L | H | 已 lock 版本到 `==1.2.6` 与 `<2`；如冲突则降级到上一个稳定版 |
| macOS aarch64 上 `psycopg[binary]` 编译失败 | M | L | Phase 1 不需要（只用 SQLite 路径），如 `langgraph-cli[inmem]` 触发则跳过该 extra |
| `langgraph dev` 启动失败因 LANGSMITH 配置 | M | M | 在 `.env.example` 注释明确 `LANGSMITH_TRACING=false` 时不强制；或用 `--no-open` 跳过 |
| Python 3.12 装饰器在 LangGraph 1.x 上有已知问题 | L | M | Python 3.12 是 2026 主流 LTS 版本，LangGraph 已支持；如有 issue 用 3.11 fallback |
| `init_chat_model` 在不调用时不校验 API key 导致 factory 通过 | L | L | Phase 1 不调用，故意如此；测试不触发 |

## Notes

- **Phase 1 的"占位"哲学**：所有 Agent node 都是 echo 函数（不调 LLM），是因为本阶段只验证"图能编译、流程能跑、测试能过"。真实的 prompt 工程、Vision-LLM 调用、RAG 召回分别在 Phase 3-5 完成。
- **State Schema 已是生产级**：9 个字段 + 4 个子 TypedDict 与 PRD 对齐；Phase 3-6 不再改 State schema，只在 Agent 内部填充值。
- **Reflection Loop 留 conditional edge 占位**：`should_reflect` 永远返回 `END`，但节点名和边的存在让 Phase 6 只需替换函数体，不需要重写图结构。
- **不引入日志框架**：Phase 1 用 `print` / `console.print` 即可。Phase 3 引入 `structlog` 时，5 个 Agent 节点的签名不需要改（只改内部实现）。
- **langgraph-cli[inmem] 是 dev 依赖**：不影响生产 CLI。
- **本 plan 完全自包含**：开发者拿到 plan 后**不需要再读 PRD 或搜 codebase**；所有信息已在"Files to Change"、"Patterns to Mirror"、"External Documentation" 中。

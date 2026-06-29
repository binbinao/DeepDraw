# Code Review: Phase 1 — Infrastructure Bootstrap

**Reviewed**: 2026-06-29
**Commit**: `8489acc` — feat: scaffold 5-agent DFM-Copilot LangGraph workflow
**Branch**: `feat/infrastructure-bootstrap` (no main yet)
**Decision**: **APPROVE with comments**

## Summary
Phase 1 脚手架质量高：结构清晰、命名一致、测试覆盖完整（10/10 pass）、无安全漏洞、无 HIGH/CRITICAL 问题。3 个 MEDIUM 和 4 个 LOW 建议可在 Phase 2 启动前顺手修复，但都不是阻塞性问题。

## Findings

### CRITICAL
None.

### HIGH
None.

### MEDIUM

#### M1. `state.py:62` — `process_plan` 缺 `Annotated[..., operator.add]` reducer
- **File**: `src/deepdraw/state.py:62`
- **Issue**: `process_plan: list[ProcessStep]` 与 `errors` / `bom` / `verification_notes` 行为不一致。前三者有 `Annotated[list[T], operator.add]`，会**累积**多节点结果；`process_plan` 没有 reducer，多个节点写它会**覆盖**。
- **Why it matters**: Phase 4 Process Recommender 可能需要 Chief Verifier 反馈后追加步骤；当前 schema 会丢掉早期输出。
- **Suggested fix**:
  ```python
  process_plan: Annotated[list[ProcessStep], operator.add]
  ```

#### M2. `cli.py:39` — `asyncio.run()` 在已有 event loop 时会失败
- **File**: `src/deepdraw/cli.py:39`
- **Issue**: `asyncio.run(graph.ainvoke(...))` 在 Jupyter notebook / 已有 running event loop 的环境会抛 `RuntimeError: asyncio.run() cannot be called from a running event loop`。
- **Why it matters**: Phase 1 CLI 是 top-level 调用，无影响；但 Phase 7 集成 LangGraph Studio / Web 后端时可能踩坑。
- **Suggested fix** (Phase 7 再做):
  ```python
  try:
      loop = asyncio.get_running_loop()
  except RuntimeError:
      final_state = asyncio.run(graph.ainvoke(...))
  else:
      final_state = loop.run_until_complete(graph.ainvoke(...))
  ```
  或更简洁：用 `nest_asyncio.apply()` (依赖额外包)。

#### M3. `pyproject.toml:10` — `langgraph-checkpoint-sqlite==3.1.0` 与 `langgraph==1.2.6` 版本组合未明确验证
- **File**: `pyproject.toml:10`
- **Issue**: 已 lock 到具体版本，实际安装时需确认无冲突。
- **Why it matters**: LangGraph 生态的 checkpoint 包版本有较严格的耦合。
- **Status**: 实际安装已通过（pytest + E2E 跑通）→ **验证 OK，无需修改**，但应在 Phase 7 切 SqliteSaver 时再次确认。

### LOW

#### L1. `graph.py:18` — `MAX_REFLECTION_ITERATIONS = 3` 已定义但未使用
- **File**: `src/deepdraw/graph.py:18`
- **Issue**: 模块级常量没人引用。
- **Suggested fix**: 删掉，或 Phase 6 在 `should_reflect` 里用它。

#### L2. `graph.py:57-63` — `should_reflect` 是 stub，命名容易误导
- **File**: `src/deepdraw/graph.py:57-63`
- **Issue**: 函数名 `should_reflect` 暗示已有反射逻辑，实际永远返回 `END`。
- **Suggested fix**: docstring 已说明 "Phase 1 占位"，但加 `# TODO(Phase 6): 替换为真实反射逻辑` 注释更显式。

#### L3. `README.md:14` — 示例命令错误（typer 单命令模式）
- **File**: `README.md:14`
- **Issue**: `python -m deepdraw.cli run /tmp/test.pdf` 在 Typer 0.26 单命令模式下不工作（`run` 被当作 drawing path）。
- **Suggested fix**: 改为 `python -m deepdraw.cli /tmp/test.pdf`（已在本 review 发现；E2E 实际跑通的命令）。

#### L4. `tests/` — `--thread-id` 参数无专门测试
- **File**: `tests/test_graph.py`
- **Issue**: thread_id 用于 LangGraph checkpoint 隔离，没有 test 验证它实际工作。
- **Suggested fix**: Phase 2 加一个 test：
  ```python
  async def test_thread_id_isolates_state(compiled_graph, dummy_drawing):
      s1 = await compiled_graph.ainvoke({"drawing_path": str(dummy_drawing)},
                                        config={"configurable": {"thread_id": "A"}})
      s2 = await compiled_graph.ainvoke({"drawing_path": str(dummy_drawing)},
                                        config={"configurable": {"thread_id": "B"}})
      # 不同 thread_id 的 reflection_iterations 不应共享
  ```

## Non-issues (Checked and OK)

- ✓ **Security**: 无硬编码凭证；`.env` 已 gitignore；`.env.example` 只含占位符
- ✓ **Type safety**: 所有公共函数有 type hint；用 `from __future__ import annotations` 兼容 Python 3.12+
- ✓ **Pattern compliance**: 严格遵循 LangGraph 1.x `multi_agent/agent_supervisor` 示例
- ✓ **Performance**: 5 节点 O(1) 占位实现；无 N+1 / 无界循环
- ✓ **Completeness**: 10/10 测试通过；README + docstring 完整
- ✓ **Maintainability**: 所有源文件 < 100 行；命名一致；无 TODO/FIXME 残留
- ✓ **Emoji usage**: 注释里的 🛡️/🔍 等是 PRD 中的 agent 命名，刻意保留
- ✓ **B008 noqa**: typer 必须用 `Argument/Option` in defaults，是 false positive，正确标注 `# noqa: B008`

## Validation Results

| Check | Result | Notes |
|---|---|---|
| Lint (ruff check) | Pass | 0 errors |
| Format (ruff format) | Pass | 0 changes needed |
| Tests (pytest) | Pass | 10/10 tests |
| E2E CLI | Pass | `python -m deepdraw.cli <file>` 输出完整 JSON |
| Graph introspection | Pass | 7 节点（5 agents + START + END）+ 5 sequential edges |

## Files Reviewed (27)

### Source (12)
- `src/deepdraw/state.py` — AgentState TypedDict + 4 子类型
- `src/deepdraw/llm.py` — LLM factory
- `src/deepdraw/graph.py` — StateGraph 编译
- `src/deepdraw/cli.py` — typer CLI
- `src/deepdraw/agents/{spec_interpreter,drawing_auditor,bom_generator,process_recommender,chief_verifier}.py` — 5 占位节点
- `main.py` — 入口
- `src/deepdraw/tools/README.md` — Phase 2 计划

### Tests (4)
- `tests/conftest.py` — fixtures
- `tests/test_state.py` — 2 tests
- `tests/test_graph.py` — 3 tests
- `tests/test_agents.py` — 5 tests

### Config (5)
- `pyproject.toml` — 依赖 + 配置
- `ruff.toml` — lint
- `.gitignore` — 标准 Python
- `langgraph.json` — Studio 配置
- `.env.example` — 凭证占位

### Docs (6)
- `README.md` — 快速开始
- `docs/original-requirement.md` — 原始需求
- `.claude/PRPs/prds/deepdraw-dfm-platform.prd.md` — PRD
- `.claude/PRPs/plans/completed/infrastructure-bootstrap.plan.md` — 实施 plan
- `.claude/PRPs/reports/infrastructure-bootstrap-report.md` — 实施报告
- `src/deepdraw/prompts/*.md` — 5 agent System Prompts

## Decision Rationale

**APPROVE with comments** 理由：
- 0 CRITICAL + 0 HIGH
- 3 MEDIUM 都不是阻塞性问题（M1 是 schema 一致性、Phase 4 才用；M2 Phase 7 才用；M3 已验证 OK）
- 4 LOW 全部是文档/可读性/未来优化
- 所有 5 级 validation 通过
- 10/10 tests pass
- 符合 LangGraph 1.x 官方推荐结构
- 文档完整（PRD + Plan + Report 三件套）

## Recommended Pre-Phase-2 Actions

在进入 Phase 2 之前，建议顺手修：

1. **M1** (5 min fix): `process_plan` 改用 `Annotated[..., operator.add]`
2. **L1** (1 min fix): 删 `MAX_REFLECTION_ITERATIONS` 或加 use
3. **L3** (1 min fix): README 命令示例改对
4. **L4** (10 min fix): 加 thread_id 隔离测试

修完这 4 个 + 跑一次 `pytest` 验证，即可进入 Phase 2。

## Next Steps
- [ ] 修复上述 4 项小问题（可选，建议 30 min 内完成）
- [ ] `/ecc:prp-pr` 创建 PR 到 main 分支
- [ ] 或 `/ecc:prp-plan` 选 Phase 2（PDF/DXF 解析）
- [ ] 或先做技术 spike：拿 5-10 张真实工程图测 Vision-LLM 准确率

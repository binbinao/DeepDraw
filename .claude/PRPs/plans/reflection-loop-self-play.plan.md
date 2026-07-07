# Plan: Phase 6 — Self-Play Reflection Loop

## Summary
实现 Chief Verifier ↔ Process Recommender 辩论循环（最多 3 轮）。Chief Verifier 充当 Challenger 挑刺 Process Recommender 输出，Process Recommender 读 verification_notes 后修正。每次 Refiner 必须记录"为什么改"。循环在 status=success 或达到 MAX_REFLECTION_ITERATIONS=3 时结束。

## User Story
As a **Phase 7 PoC 测试员**,
I want **高风险工艺决策有 3 轮自博弈验证**,
so that **关键错误（如折弯回弹系数、表面处理兼容性）能被 Challenger 挑出 + Refiner 修正**。

## Problem → Solution
**当前状态**：Chief Verifier 调用一次 LLM 设 status，should_reflect 永远返回 END。
**目标状态**：should_reflect 根据 reflection_iterations + status 决定循环；process_recommender 读 chief_verifier 反馈修正；状态含 process_plan_history 保留所有轮次。

## Metadata
- **Complexity**: **Medium**（5 task、4 UPDATE 文件、0 NEW 依赖）
- **Source PRD**: `.claude/PRPs/prds/deepdraw-dfm-platform.prd.md`
- **PRD Phase**: Phase 6 — 自博弈 Reflection Loop

---

## Mandatory Reading

| Priority | File | Why |
|---|---|---|
| P0 | `src/deepdraw/graph.py` | should_reflect 当前是 stub |
| P0 | `src/deepdraw/agents/chief_verifier.py` | 已读 spec/errors/bom/process_plan |
| P0 | `src/deepdraw/agents/process_recommender.py` | 读 spec + RAG；要让它读 feedback |
| P0 | `src/deepdraw/state.py` | 加 process_plan_history |

## External Documentation

| Topic | Key Takeaway |
|---|---|
| LangGraph 循环边 | `add_conditional_edges(node, router, path_map)` 返回 String 路由下一个节点 |
| Reflection Loop 模式 | router 返回 `"__end__"` 或下一个节点名；state 用 Annotated 累积 |

## Files to Change

| File | Action |
|---|---|
| `src/deepdraw/state.py` | UPDATE 加 process_plan_history |
| `src/deepdraw/graph.py` | UPDATE should_reflect 实现 + 路由 |
| `src/deepdraw/agents/process_recommender.py` | UPDATE 读 feedback + append history |
| `src/deepdraw/agents/chief_verifier.py` | UPDATE 读 history 最后一轮 |

---

## NOT Building

- 自博弈 > 3 轮
- 嵌套子图
- Token 硬性限制（Phase 7）

---

## Step-by-Step Tasks

### Task 1: state.py — process_plan_history
```python
process_plan_history: Annotated[list[list[ProcessStep]], operator.add]
```

### Task 2: process_recommender.py
- 每次生成新 plan 时 append to history
- prompt 注入 chief_verifier feedback from verification_notes

### Task 3: chief_verifier.py
- 读 `state.get("process_plan_history", [[]])[-1]` 作为当前 plan

### Task 4: graph.py — should_reflect
```python
MAX_REFLECTION_ITERATIONS = 3

def should_reflect(state: AgentState) -> str:
    if state.get("status") == "success":
        return END
    if state.get("reflection_iterations", 0) >= MAX_REFLECTION_ITERATIONS:
        return END
    return "process_recommender"
```

### Task 5: 5 级验证
- ruff + pytest + E2E

---

## Testing Strategy

### Unit Tests (3 new)

| Test | 验证 |
|---|---|
| test_should_reflect_end_on_success | success 立即退出 |
| test_should_reflect_loops_back_on_conflict | conflict + iter<3 → process_recommender |
| test_should_reflect_end_at_max_iter | iter=3 → END |

---

## Validation Commands

```bash
.venv/bin/ruff check src/ tests/
.venv/bin/pytest tests/ -v    # 32 → 35
.venv/bin/python -m deepdraw.cli /tmp/test.pdf
```

---

## Acceptance Criteria

- [ ] should_reflect 根据 status + reflection_iterations 路由
- [ ] success 立即退出，conflict 循环，iter=3 退出
- [ ] process_plan_history 累积（reducer）
- [ ] 35/35 tests pass
- [ ] ruff + format 全过

## Risks

| Risk | L | I | Mitigation |
|---|---|---|---|
| 循环边 API | L | L | add_conditional_edges 稳定 |
| reducer 覆盖 | M | L | Annotated[..., operator.add] |
| 自博弈成本 | M | M | MAX=3 hard cap |

---

*Confidence Score*: **9/10** — LangGraph 循环边 API 稳定
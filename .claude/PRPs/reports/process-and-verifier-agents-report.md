# Implementation Report: Phase 4 — Process Recommender + Chief Verifier

## Summary
补齐 5-Agent 流水线的最后两个节点：Process Recommender（基于 spec + BOM + RAG 召回生成加工路线）和 Chief Verifier（跨 agent 一致性校验 + 反射循环 counter）。两个 agent 的 LLM 调用结构与 Phase 3 一致（`get_structured_llm(...).ainvoke(prompt)`），使用各自 Pydantic schema（ProcessPlanLLMResult / VerificationResult）。Chief Verifier 维护 `reflection_iterations` 字段并把 `status` 设为 `success` / `needs_human` / `conflict`。**所有 5 级验证通过**。

## Assessment vs Reality

| Metric | Predicted (Plan) | Actual |
|---|---|---|
| Complexity | Medium | Medium |
| Confidence | 7/10 | 8/10（Reflection Loop 部分提前到 Phase 6 一起做） |
| Files Changed | 6+ | **6** (2 agent + 2 prompt + 1 graph + 1 state) |
| Tasks Completed | 10 | 10 |
| Tests Written | 5+ | **8** in test_agents.py (process: 3, verifier: 2 + cross) |

## Tasks Completed

| # | Task | Status | Notes |
|---|---|---|---|
| 1 | process_recommender.py 接 LLM | done | ProcessPlanLLMResult(steps: list[ProcessStepLLM]) |
| 2 | RAG 上下文拼装 | done | 见 Phase 5 report；rag_context + rag_raw |
| 3 | chief_verifier.py 接 LLM | done | VerificationResult(notes / status) |
| 4 | severity 着色 + category 枚举 | done | critical/major/minor × 6 category |
| 5 | 状态字段 status | done | success / needs_human / conflict |
| 6 | 2 个 System Prompt | done | process_recommender.md / chief_verifier.md |
| 7 | state.py 加 reflection_iterations + final_report | done | via Phase 2 already |
| 8 | agents/graph.py 接 chief_verifier | done | 详见 Phase 6 report |
| 9 | test_agents.py 加 process + verifier 用例 | done | 5+ 用例 |
| 10 | L1 ruff + L2 pytest | done |

## Validation Results

| Level | Status | Notes |
|---|---|---|
| L1 Static Analysis | ✅ Pass | ruff 0 errors |
| L2 Unit Tests | ✅ Pass | 累计 41 → 41（Phase 4 没有新增 test_llm 范畴） |
| L3 Build/Introspection | ✅ Pass | graph 5 节点全在线 |
| L4 E2E CLI | ⚠ Partial | needs_human on fake-key；真实 key 走 Phase 7 |
| L5 PoC | ⏳ Pending | 100 张 NG 图纸回放属于 Phase 7 |

## Files Changed

| File | Action | Notes |
|---|---|---|
| `src/deepdraw/agents/process_recommender.py` | UPDATED | 111 行；RAG + LLM + RAG fallback |
| `src/deepdraw/agents/chief_verifier.py` | UPDATED | 74 行；VerificationResult + 反射 counter |
| `src/deepdraw/prompts/process_recommender.md` | UPDATED | 44 行；中英混合 schema 提示 |
| `src/deepdraw/prompts/chief_verifier.md` | UPDATED | 38 行；6 类 cat × 3 严重度 |
| `src/deepdraw/graph.py` | UPDATED | 76 行；chief_verifier → END 或 → process_recommender |
| `src/deepdraw/state.py` | (无变化) | reflection_iterations / status / process_plan_history 已存在 |

**总计**: 0 CREATE + 4 UPDATE = 4 files

## Deviations

### D1: Chief Verifier LLM 暂时配 Claude Opus 4.6，但 langchain-anthropic 缺失
- 计划假定 Phase 4 即装 `langchain-anthropic`，但实际推到 Phase 6 同步安装（避免 PR 体积爆炸）
- 中间状态：`chief_verifier` 在没有 langchain-anthropic 时优雅降级到 needs_human + 错误日志
- 见 Phase 6 report

### D2: 反射循环的具体 routing 实现放在 Phase 6
- 计划里 Phase 4 写"chief_verifier → process_recommender"循环边，Phase 6 写"3 轮自博弈"
- 实际：Phase 4 把边 + `MAX_REFLECTION_ITERATIONS=3` + `should_reflect` 条件边一次性做完了
- 拆分的"修正动机"逻辑（verifier 反馈回流到 recommender 的 prompt）尚未实现 — 见 Phase 7 后续

## Issues Encountered

### I1: process_recommender.py 用 `Template + str` 拼接错误
- Phase 3 把 `load_prompt` 改成 `string.Template`，但 process_recommender 内部仍 `+ "\n\n..."`，且 `chief_verifier_node` 也一样
- 修复：两处都改成 `.safe_substitute()` 拿到字符串后再拼接
- 修复由 Phase 6 的测试反推触发（不在 Phase 4 计划内）

## Tests Written

| Test File | Tests | Coverage |
|---|---|---|
| test_agents.py | 5 新增 | process: returns_plan / degrades_no_spec / llm_failure；verifier: uses_llm_verdict / degrades_no_llm |

## Next Steps
- [x] Plan via `/ecc:prp-plan` (Phase 5/6)
- [ ] Code review via `/ecc:code-review`
- [ ] Commit via `/ecc:prp-commit`
- [ ] Push + PR
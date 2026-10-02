# Implementation Report: Phase 7 — PoC Validation Harness (Partial)

## Summary
实现 PoC harness 框架：场景加载 / 运行 / 聚合 / Markdown 报告渲染；交付物可编程，但缺 100 张历史 NG 图纸 ground truth、`deepdraw poc` CLI 子命令、以及与 ground truth 的回归评测脚本。**完成度 ~60%**。

## Assessment vs Reality

| Metric | Predicted (Plan) | Actual |
|---|---|---|
| Complexity | Medium | Medium |
| Confidence | 7/10 | 6/10（100 张 NG 图纸获取路径未定） |
| Files Changed | 3 | **4** (2 NEW + 1 + tests) |
| Tasks Completed | 8 | **5 of 8** |
| Tests Written | 4+ | **5** in test_poc.py |

## Tasks Completed

| # | Task | Status | Notes |
|---|---|---|---|
| 1 | PoCScenario / PoCResult dataclass | ✅ done | tools/poc.py |
| 2 | load_scenarios("Expected list" 契约) | ✅ done | tests/test_poc.py 守门 |
| 3 | run_scenario / aggregate | ✅ done | tools/poc.py |
| 4 | render_report → Markdown | ✅ done | tools/poc_report.py |
| 5 | 5 个合成场景 (Q235B-5mm-bracket 等) | ✅ done | tests/fixtures/poc_scenarios.json |
| 6 | `deepdraw poc` CLI 子命令 | ⏳ pending | 需 Typer 子命令 |
| 7 | 100 张 NG 图纸 ground truth | ⏳ pending | PRD Open Question |
| 8 | docs/poc-runbook.md | ⏳ pending | PRD Open Question |

## Validation Results

| Level | Status | Notes |
|---|---|---|
| L1 Static Analysis | ✅ Pass | ruff 0 |
| L2 Unit Tests | ✅ Pass | 5/5 poc + 74 total |
| L3 Build/Introspection | ✅ Pass | dataclass / JSON 序列化 OK |
| L4 E2E CLI | ⚠ Partial | `deepdraw run` 已跑通；但 `poc` 子命令尚未挂 |
| L5 PoC ROI | ⏳ Pending | 100 张 NG 图纸回放 + 漏检率统计 |

## Files Changed

| File | Action | Notes |
|---|---|---|
| `src/deepdraw/tools/poc.py` | CREATED | 140 行；PoCScenario / PoCResult / load_scenarios / run_scenario / aggregate / run_poc |
| `src/deepdraw/tools/poc_report.py` | CREATED | 70 行；render_report → Markdown KPI 表 |
| `tests/fixtures/poc_scenarios.json` | CREATED | 5 合成样例 + expected_* + ground truth 字段 |
| `tests/test_poc.py` | CREATED | 5 用例（含 Expected-list 契约） |

## Deviations

### D1: 真实 100 张 NG 图纸回放未做
- PRD Open Question 仍未关闭：从哪家合作工厂获取？当年人工审图记录就是 ground truth 吗？
- 暂以 5 个合成场景 (Q235B-5mm-bracket 等) 跑 harness 框架；真实回放需要业务侧解锁

### D2: deepdraw poc 子命令未挂
- 当前只有 `run` / `index` / `search` / `wipe` 4 个子命令
- 待 Phase 7 完成时挂 `poc run` / `poc report` 两个子命令

### D3: 漏检率/采纳率指标计算函数已写，但参数化为 PoCResult 字段；真实回归脚本待 Phase 7 落地时基于业务数据接入

## Issues Encountered

### I1: load_scenarios 的 ValueError 契约
- 业务要求非 list 顶层 → 必须抛 `ValueError("Expected list")`
- 测试断言守门；当前实现 `if not isinstance(data, list): raise ValueError("Expected list")`

## Tests Written

| Test File | Tests | Coverage |
|---|---|---|
| test_poc.py | 5 | load_scenarios happy / load_scenarios missing / "Expected list" ValueError / aggregate / render_report sections |

## Next Steps
- [ ] **挂 `deepdraw poc` 子命令** — PoC `run` / `report` 两个命令
- [ ] **业务侧解锁** — 100 张 NG 图纸获取 + ground truth 规范化
- [ ] **漏检率/采纳率真实回归** — 接入业务数据后跑 harness
- [ ] **docs/poc-runbook.md** — 写 PoC 跑通手册
- [ ] **PRD Status Table 更新** — Phase 7 拆分为 `PoC Harness` complete / `PoC Validation` pending
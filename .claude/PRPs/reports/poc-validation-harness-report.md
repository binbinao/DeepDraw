# Implementation Report: Phase 7 — PoC Validation Harness (CLI Surface Complete, Validation Pending)

## Summary
实现 PoC harness 框架：场景加载 / 运行 / 聚合 / Markdown 报告渲染；并通过 `deepdraw poc` typer 子应用（`run` / `report` / `validate`）落地 CLI 表面。同时修复 harness 的两个真实缺陷：(1) `run_scenario` 把 graph 崩溃外抛，污染整个 batch；(2) 缺失 PDF 时自动创建 0 字节文件触发 pdfplumber `PdfminerException`。剩余：100 张历史 NG 图纸 ground truth 与真实回归评测脚本。**完成度 ~80%**。

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
| 6 | `deepdraw poc` CLI 子命令 | ✅ done | Typer sub-app: `run` / `report` / `validate` (exit 2 on incomplete ground truth) |
| 7 | harness 容错 (graph 崩溃 / 0-byte PDF) | ✅ done | run_scenario try/except；移除 touch()；pipeline_failure PoCResult |
| 8 | 100 张 NG 图纸 ground truth | ⏳ pending | PRD Open Question |
| 9 | docs/poc-runbook.md | ⏳ pending | PRD Open Question |

## Validation Results

| Level | Status | Notes |
|---|---|---|
| L1 Static Analysis | ✅ Pass | ruff 0 |
| L2 Unit Tests | ✅ Pass | 11/11 poc + 80 total |
| L3 Build/Introspection | ✅ Pass | dataclass / JSON 序列化 OK |
| L4 E2E CLI | ✅ Pass | `deepdraw poc run` 跑通 5 scenarios；`poc report` 写 Markdown；`poc validate` 在 ground-truth 不完整时 exit 2 |
| L5 PoC ROI | ⏳ Pending | 100 张 NG 图纸回放 + 漏检率统计 |

## Files Changed

| File | Action | Notes |
|---|---|---|
| `src/deepdraw/tools/poc.py` | CREATED | 140 行；PoCScenario / PoCResult / load_scenarios / run_scenario / aggregate / run_poc |
| `src/deepdraw/tools/poc_report.py` | CREATED | 70 行；render_report → Markdown KPI 表 |
| `tests/fixtures/poc_scenarios.json` | CREATED | 5 合成样例 + expected_* + ground truth 字段 |
| `tests/test_poc.py` | CREATED | 11 用例（5 原有 + 6 新增：run_scenario 容错 + CliRunner 覆盖 run/report/validate） |
| `src/deepdraw/cli.py` | UPDATED | +poc_app sub-typer + 3 子命令 + Rich 表格 / 容错打印 |

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
- [x] **挂 `deepdraw poc` 子命令** — Typer sub-app: `run` / `report` / `validate`
- [x] **Harness 容错** — run_scenario try/except + 移除 phantom PDF touch()
- [x] **PRD Status Table 更新** — Phase 7 标记为 complete (CLI surface + harness)；剩余为 NG 数据业务侧解锁
- [ ] **业务侧解锁** — 100 张 NG 图纸获取 + ground truth 规范化
- [ ] **漏检率/采纳率真实回归** — 接入业务数据后跑 harness
- [ ] **docs/poc-runbook.md** — 写 PoC 跑通手册
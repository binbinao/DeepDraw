# Plan: Phase 7 — PoC Validation Harness

## Summary
实现 PoC 测试 harness：metrics 收集（latency/iterations）、程序化测试场景生成（带已知 ground truth 的合成 PDF）、结果聚合、Markdown 报告生成。真实 100 张 NG 图纸由用户手动跑。

## User Story
As a **项目发起人**,
I want **一个可重复运行的 PoC 测试框架**,
so that **我可以拿真实 NG 图纸（自备）评估 DeepDraw 漏检率，输出 Phase 7 主指标报告**。

## Problem → Solution
**当前状态**：手工跑 `deepdraw run <file>` 看输出，无 metrics、无 ground truth 对比、无批量。
**目标状态**：`deepdraw poc <test_set.json>` 批量跑 + 漏检率/采纳率统计 + 自动 Markdown 报告。

## Metadata
- **Complexity**: **Medium**
- **Estimated Files**: 7 NEW + 1 UPDATE

---

## Files to Change

| File | Action | Justification |
|---|---|---|
| `src/deepdraw/tools/poc.py` | CREATE | Test scenario loader + metrics collection |
| `src/deepdraw/tools/poc_report.py` | CREATE | Markdown 报告生成 |
| `src/deepdraw/cli.py` | UPDATE | 加 `poc` 子命令 |
| `tests/test_poc.py` | CREATE | PoC harness 单测 |
| `tests/fixtures/poc_scenarios.json` | CREATE | 5 个程序化测试场景 |
| `docs/poc-runbook.md` | CREATE | 真实 100 张图的手动跑步骤 |

---

## Step-by-Step Tasks

### Task 1: 实现 src/deepdraw/tools/poc.py
```python
"""PoC harness: load test scenarios, run pipeline, collect metrics."""

@dataclass
class PoCScenario:
    name: str
    pdf_path: str
    expected_material: str | None
    expected_thickness: float | None
    expected_errors: list[dict]
    expected_process_steps_min: int


@dataclass
class PoCResult:
    scenario: str
    duration_sec: float
    reflection_iterations: int
    final_status: str
    detected_material: str | None
    detected_thickness: float | None
    detected_errors: list[dict]
    detected_process_steps: int
    material_match: bool
    thickness_match: bool
    error_recall: float
    error_precision: float


def load_scenarios(json_path: str) -> list[PoCScenario]: ...
async def run_scenario(s: PoCScenario) -> PoCResult: ...
def aggregate(results: list[PoCResult]) -> dict: ...
```

### Task 2: 实现 poc_report.py — Markdown 输出
- 输入：list[PoCResult]
- 输出：含主指标 summary + per-scenario 表格

### Task 3: 5 synthetic scenarios
```json
[
  {"name": "Q235B-5mm-bracket", "expected_material": "Q235B",
   "expected_thickness": 5.0, "expected_errors": [], "expected_process_steps_min": 2},
  ... (4 more)
]
```

### Task 4: CLI `poc` 子命令
```python
@app.command()
def poc(scenarios: Path, report: Path | None = None): ...
```

### Task 5: docs/poc-runbook.md
- 真实 100 张图手动跑步骤

### Task 6: tests/test_poc.py
- load / aggregate / report 单测

### Task 7: 5 级验证

---

## Acceptance Criteria
- [ ] `deepdraw poc <json>` 命令
- [ ] 5 scenarios 跑通
- [ ] Markdown 报告含主指标
- [ ] 40/40 tests pass
- [ ] User manual runbook

## Risks

| Risk | L | I | Mitigation |
|---|---|---|---|
| 真实 NG 图纸不可得 | H | H | 用户自备 |
| Vision 准确率 | H | H | 基线 |
| 单次 100 张 > 3h | H | M | 并发（Phase 7.5） |

---

*Confidence Score*: **7/10** — Harness clear；真实 PoC 依赖 API + 用户数据
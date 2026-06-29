# DeepDraw — DFM-Copilot Squad

> 钣金/机加工行业的图纸审核与工艺决策 Agent 协作系统

**Status**: DRAFT — needs validation
**Generated**: 2026-06-29
**Source**: `docs/original-requirement.md` (业务方向论述) → 重写为产品需求文档

---

## Problem Statement

钣金/机加工厂的工艺工程师每天需要人工审读 PDF/DXF 工程图，从图中提取关键尺寸、识别标注矛盾、发现工艺不可制造特征，并据此填 BOM、选工艺。图纸上的隐含几何关系（虚线投影、同心度、孔径 < 工艺极限）以及特殊工艺要求（材料牌号、表面处理、回弹系数）经常被人工漏检；这种漏检在批量生产时转化为废件与质量事故，单次成本肉眼可见。当前市场上没有 AI 工具能在"读图-审图-出工艺卡"这个垂直场景里替代人工经验。

## Evidence

- **行业经验值**：原文档（来源：项目发起人）明确指出"OCR 经常把 Ø10 看成 Ø16"，是 LLM 视觉推理引入前的真实痛点
- **BOM 工时占比**：工程师手动填 BOM 占工时约 20%（原文档行业经验值）
- **私有知识决定性**："我们厂里只有 10mm 的铣刀"或"上次用这个参数烧了刀"——工艺决策高度依赖企业私有知识而非通用机械原理
- **量化数据 TBD**：典型钣金厂的年废件率、单次废件成本、人工审图漏检率基线值需要在 PoC 启动前从合作工厂采集，作为后续 ROI 测算的依据
- **Assumption - needs validation**：5-Agent 协作系统的端到端准确率与延迟在真实工程图上的表现，目前无公开 benchmark 可参考

## Proposed Solution

构建一个名为 **"DFM-Copilot Squad"** 的 5-Agent 协作系统，在 PDF/DXF 图纸和企业工艺规范库之间提供端到端的 DFM（Design for Manufacturability）审核与工艺决策：

1. **👓 Spec Interpreter**（需求翻译官）解析订单规格与图纸标题栏
2. **🔍 Drawing Auditor**（图纸审计员）识别缺尺寸、标注矛盾、视图缺失、工艺不可制造特征
3. **📒 BOM Generator**（物料管家）从图纸提取零件并匹配企业物料编码
4. **⚙️ Process Recommender**（工艺军师）基于特征推荐加工方式、刀具、加工顺序
5. **🛡️ Chief Verifier**（总质检师）以 L5 级别自博弈校验前四者输出的自洽性

**为什么选这个方案而不是单一 LLM**：
- 分工清晰：每个 Agent 可独立迭代、独立 prompt 工程、独立评测
- 自博弈友好：Chief Verifier 单独成 Agent 才能做 3 轮 Reflection Loop
- 失败隔离：BOM 出错不会污染审图结论，便于人工定位修复

## Key Hypothesis

We believe **一个端到端 5-Agent 协作的"读图-审图-出工艺卡"系统** will **把图纸审核漏检率相对人工降低 50% 以上** for **钣金/机加工厂的工艺工程师**。
We'll know we're right when **在 100 张历史 NG（不合格）图纸的回放测试中，AI 检出的关键错误中至少 50% 是当年人工审图漏掉的**（即相对漏检率 > 50%）。

## What We're NOT Building

- **CAD 几何内核 / 求解器** — 保守派策略：只做"图纸→结构化数据→工艺决策"链路，不碰几何计算
- **多租户 SaaS 平台** — v1 是单一企业内部工具，图纸不出内网
- **ERP/MES 深度集成** — 通过 MCP Server 留接口占位，不做双向同步
- **自动出图/改图功能** — 只做审核与建议，不修改源图纸
- **移动端 App** — v1 是 CLI + Web 后台即可
- **实时工艺仿真** — 不做切削力、热变形等物理仿真
- **CAD 二次开发** — 不写 AutoCAD/SolidWorks 插件

## Success Metrics

| Metric | Target | How Measured |
|--------|--------|--------------|
| **AI 审核覆盖率**（主指标） | > 95% | 100 张历史 NG 图纸基准测试，对照当年人工审图记录 |
| **相对漏检率降低**（主指标） | > 50% | AI 新检出的关键错误数 / 当年人工漏掉的错误数 |
| **单张审图时间**（副） | < 5 分钟 | 从 PDF 上传到输出工艺卡的端到端延迟 |
| **工艺方案采纳率**（副） | > 70% | 工艺工程师对 AI 推荐方案的"采纳 / 拒绝 / 修改"分布 |
| **BOM 准确率**（副） | > 98% | AI 生成 BOM 与人工对照的正确字段占比 |
| **PoC ROI 回正**（商业） | 3 个月内 | 废件成本节省 vs 项目投入 |

---

## Users & Context

**Primary User**
- **Who**：钣金/机加工厂的工艺工程师，5-15 年经验，熟悉本厂设备/刀具/材料体系
- **Current behavior**：收到客户 PDF 图纸后用 CAD 软件打开，人工审图（30 分钟/张），查企业工艺手册，填 BOM 表，走工艺路线
- **Trigger**：销售/项目部转来新订单 PDF，需要快速判断"能不能做、怎么做"
- **Success state**：5 分钟内拿到 AI 给出的"审图错误清单 + 工艺方案 + 异常报告"，人工只需做最后审核

**Job to Be Done**
When **收到一张新的 PDF/DXF 工程图订单**，I want **AI 自动读完图、审出错误、给出可制造的工艺方案**，so I can **把审图与工艺设计时间从 30 分钟压到 5 分钟，漏检率降低 50%**。

**Non-Users**
- **设计端工程师**（画图的人）—— DeepDraw 只审不改，不替代 CAD 工具
- **CNC 操作工**——DeepDraw 不下到机床控制层
- **质量终检员**——DeepDraw 是工艺前置审核，不替代终检
- **其他行业**（注塑/PCB/装配）——v1 专注钣金/机加工

---

## Solution Detail

### Core Capabilities (MoSCoW)

| Priority | Capability | Rationale |
|----------|------------|-----------|
| **Must** | 5-Agent 完整工作流（Sequential + Hierarchical） | 端到端覆盖"读图-审图-出工艺卡"主链路 |
| **Must** | PDF + DXF 解析（pdfplumber/PyMuPDF + ezdxf） | 客户图纸主流格式，缺一不可 |
| **Must** | 企业工艺规范库 RAG 召回 | "我们厂里只有 10mm 铣刀"等私有知识是核心护城河 |
| **Must** | 错误清单 + 工艺卡 + 异常报告输出 | 工艺工程师的实际交付物 |
| **Must** | MCP Server 接口（ERP/PDM 查询占位） | 为后续集成留口子，不做深度集成 |
| **Should** | Vision-LLM 视觉推理（识别虚线/同心/隐含几何关系） | 解决传统 OCR 把 Ø10 看成 Ø16 的痛点 |
| **Should** | 端到端 < 5 分钟 | 主成功指标的前置条件 |
| **Should** | 内部私有部署能力 | 图纸涉密，不能上传云端 |
| **Could** | Chief Verifier 自博弈 3 轮（Reflection Loop） | 极大降低 Hallucination，但耗 token |
| **Could** | 历史图纸相似度 RAG（成功案例召回） | 增强对长尾工艺方案的覆盖 |
| **Could** | Chief Verifier 反馈回流到 Process Recommender | 持续学习机制 |
| **Won't (v1)** | 实时工艺仿真 | 物理仿真超出 LLM 能力，需另起项目 |
| **Won't (v1)** | CAD 二次开发 | 与现有 CAD 工具解耦 |
| **Won't (v1)** | 自动出图/改图 | 边界：只审核不修改 |
| **Won't (v1)** | 移动端 App | 工程师工作场景在工位 PC，不需要手机 |

### MVP Scope

**完整 5-Agent 全流程跑通 1 张 PDF 图纸 → 结构化 JSON + 工艺卡 + 异常报告的端到端闭环**，并能在 100 张历史 NG 图纸的基准测试上达到漏检率指标。

### User Flow

```
[输入: 一张 PDF 工程图]
        ↓
[1] Spec Interpreter: "这是一张 Q235B 的支架，厚度 5mm，批量 500 件"
        ↓
[2] Drawing Auditor: "检测到 3 个缺失尺寸，2 个视图投影关系存疑，已标出"
        ↓
[3] BOM Generator: "识别到 1 种板材，5 种标准件，已匹配内部编码"
        ↓
[4] Process Recommender: "建议激光切割外形，后续折弯；孔径 < 0.5mm，建议钻孔而非冲压"
        ↓
[5] Chief Verifier: "警告：Process Recommender 推荐的刀具直径与 Spec 中的粗糙度要求冲突"
        ↓
[可选 6] Reflection Loop: 3 轮自博弈，Process Recommender 修正方案
        ↓
[输出]: 结构化 JSON + 修正后的工艺路线 + 异常报告
```

---

## Technical Approach

**Feasibility**: **HIGH**
- 团队架构清晰：5 个 Agent 角色边界明确，输入输出可形式化
- 技术栈成熟：LangGraph、ezdxf、pdfplumber、PyMuPDF、ChromaDB/Qdrant 均为生产级
- Vision-LLM 已能处理简单工程图（GPT-4o/Claude 3.5+）
- PoC 路径明确：5 天路线图可执行

**Architecture Notes**
- **编排层**：LangGraph 状态机，原生支持 Reflection Loop 和 State Management
- **Agent 层**：5 个 LLM Agent，每个独立 System Prompt，独立评测
- **工具层**：
  - `pdfplumber` / `PyMuPDF` 解析 PDF
  - `ezdxf` 读取 DXF（精度高，源文件可用时优先）
  - **MCP Server** 封装企业 ERP/PDM 查询（如 `query_material_price("Q235B")`）
- **记忆层**：
  - Short-term: LangGraph State（当前图纸的分析过程）
  - Long-term: Vector DB（ChromaDB/Qdrant）存储历史图纸特征向量 + 工艺方案
- **模型选型**（TBD）：GPT-4o vs Claude Opus 4.6 vs 本地开源 VLM（涉密要求决定）

**Technical Risks**

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Vision-LLM 对工程图真实准确率低于演示样本 | H | PoC 阶段先做 100 张回放测试，准确率不达 70% 不进入完整开发 |
| 5-Agent 端到端延迟超 5 分钟 | M | 优先做 Spec Interpreter 提前剪枝（明显不达标的图直接返工）；Chief Verifier 默认 1 轮自博弈 |
| 自博弈 3 轮 Reflection Loop 成本爆炸 | M | token 预算封顶；Reflection 回合数可配置；只对高风险决策触发自博弈 |
| 企业工艺规范库冷启动数据不足 | H | 显式区分"通用知识"（可走公版教材）与"私有知识"（必须人工录入）；MVP 接受只覆盖头部 20% 高频工艺 |
| Chief Verifier 的"机械设计常识库"质量 | H | 公版机械设计手册 + 内部历史事故案例；Verdict 不确定时降级为"需人工复核"标记 |
| PDF 扫描件 / 模糊图纸鲁棒性 | M | OCR + Vision 二段式：先 OCR 抽文字，Vision-LLM 看图；OCR 失败时回退到人工上传 |
| DXF 文件来源不可控（客户只给 PDF） | M | DXF 优先，PDF 降级；MCP Server 留接口后续可向客户要源文件 |

---

## Implementation Phases

<!--
  STATUS: pending | in-progress | complete
  PARALLEL: phases that can run concurrently
  DEPENDS: phases that must complete first
-->

| # | Phase | Description | Status | Parallel | Depends |
|---|-------|-------------|--------|----------|---------|
| 1 | 基础设施搭建 | LangGraph 框架 + 5-Agent 骨架 + State 定义 + 项目脚手架 | complete | - | - | [infrastructure-bootstrap.plan.md](../plans/completed/infrastructure-bootstrap.plan.md) ([report](../reports/infrastructure-bootstrap-report.md)) |
| 2 | 文档解析工具链 | PDF/DXF 解析封装为 MCP Tools；MCP Server 起步 | in-progress | - | 1 | [document-parsing-toolchain.plan.md](../plans/document-parsing-toolchain.plan.md) |
| 3 | 核心 3 Agent 实现 | Spec Interpreter + Drawing Auditor + BOM Generator | pending | 内部 3 并行 | 2 |
| 4 | 工艺与质检 2 Agent | Process Recommender + Chief Verifier | pending | 内部 2 并行 + 与 5 并行 | 2 |
| 5 | 企业标准记忆 | Vector DB 接入 + 长上下文企业标准手册注入 + RAG 召回 | pending | 与 3、4 并行 | 2 |
| 6 | 自博弈 Reflection Loop | Chief Verifier 3 轮辩论 + Process Recommender 修正机制 | pending | - | 3, 4, 5 |
| 7 | PoC 端到端测试 | 100 张历史 NG 图纸回放 + 漏检率统计 + 指标验证 | pending | - | 6 |

### Phase Details

**Phase 1: 基础设施搭建**
- **Goal**：搭建可运行的 LangGraph 框架，定义 5 个 Agent 的输入输出契约与 State Schema
- **Scope**：
  - `pyproject.toml` 完善（LangGraph、ezdxf、pdfplumber、PyMuPDF、ChromaDB 等依赖）
  - 5 个 Agent 节点的占位实现（每个 Agent 一个 Python 文件 + System Prompt）
  - LangGraph StateGraph 定义：节点、边、条件分支
  - CLI 入口（`python main.py --input drawing.pdf`）
  - 最小可运行闭环（5 个 Agent 各 echo 一句话）
- **Success signal**：`python main.py` 能跑通完整流程，输出空 JSON

**Phase 2: 文档解析工具链**
- **Goal**：把 PDF/DXF 解析能力封装为 LangGraph 可调用的工具
- **Scope**：
  - PDF 解析：pdfplumber（抽文字、表格）+ PyMuPDF（抽图片块给 Vision-LLM）
  - DXF 解析：ezdxf 抽实体（LINE/CIRCLE/ARC/TEXT/DIMENSION/HATCH）
  - MCP Server 起步：`query_material_price(material_code)`、`lookup_internal_standard(standard_id)` 两个占位接口
  - 文件类型自动识别（PDF 优先提取嵌入 DXF，否则 OCR + Vision）
- **Success signal**：给一张 PDF，能输出结构化的"文字块 + 图片块 + DXF 实体（如有）"中间表示

**Phase 3: 核心 3 Agent 实现**（可并行）
- **Goal**：Spec Interpreter + Drawing Auditor + BOM Generator 三个 Agent 能独立工作
- **Scope**：
  - 3a: Spec Interpreter — 解析标题栏、明细栏、技术要求，输出结构化规格 JSON
  - 3b: Drawing Auditor — Vision-LLM 审图，输出错误清单（缺尺寸、标注矛盾、视图缺失、不可制造特征）
  - 3c: BOM Generator — 从图纸提取零件列表，匹配企业内部物料编码库
- **Success signal**：3 个 Agent 各自能在 10 张样本图上输出可读结果

**Phase 4: 工艺与质检 2 Agent**（可并行 + 与 Phase 5 并行）
- **Goal**：Process Recommender + Chief Verifier 两个 Agent 能独立工作
- **Scope**：
  - 4a: Process Recommender — 基于特征（孔/槽/折弯）推荐加工方式、刀具、加工顺序
  - 4b: Chief Verifier — 单轮校验前 3 个 Agent 输出的自洽性
- **Success signal**：能在 10 张样本图上输出"工艺方案 + 异常报告"

**Phase 5: 企业标准记忆**（与 Phase 3、4 并行）
- **Goal**：把企业私有知识注入到 Agent 决策中
- **Scope**：
  - ChromaDB/Qdrant 接入
  - 企业工艺规范手册向量化（首批 5-10 份核心手册）
  - 长上下文注入测试（验证 100k tokens 级别手册召回质量）
  - 历史图纸特征向量 + 工艺方案对（首批 50 对）
  - RAG 召回接口实现（供 Process Recommender 调用）
- **Success signal**：问"我们厂里有哪些规格的铣刀"，能正确召回

**Phase 6: 自博弈 Reflection Loop**
- **Goal**：实现 L5 级别的 3 轮 Chief Verifier ↔ Process Recommender 辩论
- **Scope**：
  - LangGraph 循环边实现（Conditional Edge + Loop Counter）
  - token 预算封顶与回合数可配置
  - 高风险决策检测（只对冲压/折弯/焊接/热处理等关键工艺触发自博弈）
  - 修正理由记录（可追溯到 RAG 召回来源）
- **Success signal**：在 5 个典型争议场景上，自博弈能修正至少 1 个错误

**Phase 7: PoC 端到端测试**
- **Goal**：验证主成功指标
- **Scope**：
  - 100 张历史 NG 图纸回放测试集准备（含当年人工审图记录 ground truth）
  - 端到端漏检率统计
  - 工艺方案采纳率人工评测
  - 端到端延迟打点
  - PoC 报告：是否达到主指标，决定是否进入正式产品化
- **Success signal**：AI 漏检率降低 > 50%，PoC 报告通过

### Parallelism Notes

- **Phase 3 内部**：3 个 Agent 可并行开发（独立文件、独立 prompt、独立评测）
- **Phase 4 内部**：2 个 Agent 可并行开发
- **Phase 5 与 Phase 3、4 并行**：Vector DB 接入是基础设施工作，不依赖具体 Agent
- **Phase 6 必须等 3-5**：Reflection Loop 需要所有 Agent 与 RAG 到位
- **Phase 7 必须等 6**：端到端测试需要完整自博弈链路

---

## Decisions Log

| Decision | Choice | Alternatives | Rationale |
|----------|--------|--------------|-----------|
| 5-Agent 协作 vs 单一 LLM | 5-Agent | 单 Agent + 工具调用 / 端到端 VLM | 分工清晰可独立迭代；自博弈友好；失败隔离 |
| 编排框架 | LangGraph | CrewAI / AutoGen / 自研 | 原生支持循环（Reflection Loop）和状态管理；自博弈场景刚需 |
| 视觉理解 | Vision-LLM (VLM) | 传统 OCR + 规则 | 需要理解"虚线代表什么"、"圆是否同心"等隐含几何关系 |
| 记忆策略 | 长上下文 + RAG 混合 | 纯长上下文 / 纯 RAG | 标准手册放长上下文（需要全局连贯），相似案例用 RAG（按特征召回） |
| 自博弈回合数 | 默认 3 回合 | 1 回合 / 5 回合 / 可配置 | 3 回合在准确率与 token 成本间的平衡点；可配置留弹性 |
| MVP 范围 | 完整 5-Agent 全流程 | 极简 2 Agent / 核心 3 Agent | 用户决策：5-Agent 端到端价值流可一次性验证 |
| 商业模式 | 单一企业内部工具 | SaaS 多租户 / 开源框架 | 用户决策：图纸涉密，先做透一个工厂再考虑扩张 |
| 成功指标 | 漏检率（相对降低 > 50%） | 效率 / 商业化 / 准确率 | 用户决策：DFM 场景的核心痛点是漏检，不是慢 |
| CAD 几何内核 | 不碰 | 自研 / 集成 | 保守派策略：几何内核是红海，工艺决策是蓝海 |
| ERP/MES 集成 | MCP Server 占位，不深度集成 | 直接 API 集成 | 留口子不绑死，避免 v1 范围爆炸 |

---

## Research Summary

**Market Context**
- **国产 CAD 厂商**（中望/浩辰/华天）已有 Copilot 产品，但都深度绑定自有 CAD 平台，PDF 审图场景覆盖弱
- **国际厂商**（Autodesk Fusion 360 AI、Onshape）以 SaaS 为主，私有化部署困难
- **DeepDraw 差异化定位**：垂直于"PDF/DXF 审图 + 工艺决策"场景，单一企业内部私有化部署，与 CAD 工具解耦
- **市场空白**：钣金/机加工厂的"PDF 审图"刚需长期被忽略，CAD Copilot 都假设用户有源文件
- **TBD**：典型钣金厂规模（人数 / 年产值 / 图纸量 / 审图岗人数）需在 PoC 前从合作工厂采集

**Technical Context**
- **LangGraph**：LangChain 团队出品，原生 StateGraph + 条件边 + 循环，2025 年起成为多 Agent 编排事实标准
- **ezdxf**：成熟 DXF 库，支持 AutoCAD R12-R2024 格式，能抽取实体几何与图层信息
- **pdfplumber / PyMuPDF**：PDF 文字与图片抽取，前者对工程图标题栏识别更准，后者对嵌入图片提取更完整
- **Vision-LLM**：GPT-4o / Claude Opus 4.6 / Qwen2-VL 等已能处理简单工程图（标题栏、明细栏），但对复杂装配图与模糊扫描件准确率待验证
- **Vector DB**：ChromaDB（轻量、本地友好）适合 PoC；Qdrant（生产级、亿级向量）适合产品化
- **未验证假设**：Vision-LLM 对"虚线投影""同心度""公差带"等隐含几何关系的真实识别能力，需要在 Phase 3 PoC 中测试

---

## Open Questions

- [ ] **模型部署形态**：内部私有化部署（Qwen2-VL / InternVL） vs 调用云端 API（GPT-4o / Claude Opus 4.6）——涉密要求决定，必须尽早决策
- [ ] **100 张 NG 图纸的获取渠道与数据脱敏规范**：从哪个合作工厂获取？是否需要脱敏（删客户名称/图号）？
- [ ] **Chief Verifier 的"机械设计常识库"冷启动**：用公版机械设计手册（公开教材）还是内部事故案例蒸馏？
- [ ] **PDF 扫描件/老旧图纸的鲁棒性边界**：客户发来的 PDF 经常是 10 年前的扫描件，Vision-LLM 在这上面的准确率未知
- [ ] **自博弈 Reflection Loop 的回合数与成本平衡**：默认 3 回合是否最优？需不需要 A/B 测试？
- [ ] **历史图纸相似度 RAG 的语料准备**：成功案例怎么定义？谁来标注？
- [ ] **Chief Verifier 拒绝决策时的人工兜底机制**：所有 Agent 都拒签时，UI 怎么呈现？
- [ ] **Phase 7 的 100 张 NG 图纸的 ground truth 怎么定**：用当年人工审图记录就是 ground truth 吗？人工自己也有错

---

*Generated: 2026-06-29*
*Status: DRAFT — needs validation*
*Source: `docs/original-requirement.md` (rewritten from business narrative to PRD)*

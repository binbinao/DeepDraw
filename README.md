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
python -m deepdraw.cli /tmp/test.pdf

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

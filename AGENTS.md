# Repository Guidelines

> Concise guide for AI assistants working in the DeepDraw repo. Ground truth beats memory: when in doubt, read the file.

## Project Overview

DeepDraw is a **LangGraph multi-agent DFM (Design for Manufacturing) copilot** for sheet-metal / machining drawing review. Five specialised agents ingest a 2D drawing (PDF or DXF), interpret its spec, audit geometry via vision, derive a BOM, propose a process plan grounded in enterprise manuals (RAG), and cross-verify with a self-play reflection loop. Output: a `final_report` with status `success` / `needs_human`.

Roadmap lives at `.claude/PRPs/prds/deepdraw-dfm-platform.prd.md`. Phases 1–6 are complete (infra, parsing, 3 core agents, process+verifier agents, RAG, reflection loop + provider abstraction). Phase 7 (harness + 100-drawing validation) is in progress — `deepdraw poc` CLI subcommand and ground-truth data are still pending.

## Architecture & Data Flow

```
PDF / DXF ─▶ spec_interpreter ─▶ drawing_auditor ─▶ bom_generator
            ─▶ process_recommender ─▶ chief_verifier
                                              │
                                       should_reflect?
                                       ├── success → END
                                       ├── conflict → loop to process_recommender
                                       └── ≥ MAX_REFLECTION_ITERATIONS (3) → END
```

- **Graph**: `src/deepdraw/graph.py` — `StateGraph(AgentState)` compiled with `RetryPolicy(max_attempts=3)`. Checkpointer is `InMemorySaver` (`langgraph-checkpoint-sqlite==3.1.0` is installed but unused; reserved for Phase 7).
- **State**: `src/deepdraw/state.py` — `AgentState` `TypedDict(total=False)` with `operator.add` reducers on `errors`, `verification_notes`, `process_plan_history`, `intermediate["llm_errors"]`. Fields: `drawing_path`, `intermediate`, `rag_context`, `spec`, `errors`, `bom`, `process_plan`, `verification_notes`, `reflection_iterations`, `process_plan_history`, `final_report`, `status`. Sub-TypedDicts: `DrawingSpec`, `DrawingError`, `BOMItem`, `ProcessStep`, `DrawingIntermediate`.
- **LLM factory**: `src/deepdraw/llm.py` — `get_llm(agent_name)`, `get_structured_llm(agent_name, pydantic_schema)`, `get_profile(agent_name)` returning a `ModelProfile`. `_LLM_CONFIG` maps each agent to a *profile name* (not a raw model string). Built-in profiles: `gpt4o`, `gpt4o_mini`, `claude_opus_46`, `claude_sonnet_45`, `deepseek_chat`, `openai_compat`. Third-party OpenAI-compatible providers (DeepSeek, Moonshot, Volcengine Ark, SiliconFlow, OpenRouter, Ollama, self-hosted vLLM, ...) are routed by setting `OPENAI_COMPAT_BASE_URL` + `OPENAI_COMPAT_API_KEY`; the factory calls `ChatOpenAI` directly with `openai_api_base` (langchain 1.x's `init_chat_model` strips `base_url`, so we bypass it for the third-party path).
- **Prompts**: `src/deepdraw/prompts/<agent>.md` loaded via `prompts.load_prompt(agent_name)` returning a `string.Template`; agents call `.safe_substitute(...)`. Do **not** use `str.format` — backtick-fenced names like `` `material` `` in prompts get treated as field references and raise `KeyError`.
- **RAG**: `src/deepdraw/tools/rag.py` — ChromaDB helpers (`get_client`, `get_or_create_collection` with cosine + MiniLM default embedding, `query`, `format_results`). Persisted at `./.chroma_db`.
- **PoC harness**: `src/deepdraw/tools/poc.py` + `poc_report.py`; scenarios in `fixtures/poc_scenarios.json` (5 entries; `load_scenarios` enforces a "non-list top-level → ValueError('Expected list')" contract at line ~39).
- **MCP**: `src/deepdraw/tools/mcp_server.py` — FastMCP stdio server exposing 5 tools (`detect_drawing_type`, `parse_pdf`, `parse_dxf`, `get_material_price`, `lookup_standard`); in-memory stubs in `mcp_tools.py`.

## Key Directories

| Path | Purpose |
|------|---------|
| `src/deepdraw/` | Main package. |
| `src/deepdraw/agents/` | Five LangGraph nodes (one per agent). |
| `src/deepdraw/tools/` | Parsers (pdf/dxf), RAG, ingest/seed, MCP server, PoC harness. |
| `src/deepdraw/prompts/` | Markdown prompt templates, one per agent. |
| `tests/` | Mirrors `src/deepdraw/` layout 1:1. |
| `tests/fixtures/` | Runtime-generated only — `poc_scenarios.json` is the sole real fixture. |
| `.claude/PRPs/` | PRD, per-phase plans, reports, reviews. |
| `docs/` | `original-requirement.md` (founding brief, Chinese). |
| `.chroma_db/` | Chroma persistence (created on first `index`). |

## Development Commands

Activate the venv first — bash sessions are non-persistent:

```bash
source .venv/bin/activate
```

```bash
# install (editable + dev extras)
pip install -e '.[dev]'

# run the agent pipeline on a drawing
deepdraw run path/to/drawing.pdf
# or: python -m deepdraw.cli run ... / python main.py run ...

# seed enterprise_manuals collection + drawings
deepdraw index

# query RAG
deepdraw search "Q235B forming" -n 5

# wipe the ChromaDB directory (irreversible)
deepdraw wipe

# LangGraph Studio / dev server (loads langgraph.json → ./src/deepdraw/graph.py:graph)
langgraph dev
```

Tests & lint:

```bash
pytest                      # all tests, asyncio_mode = "auto"
pytest tests/test_graph.py  # one file
ruff check .                # lint (line-length 100, rules E/F/I/W/UP/B/SIM, ignore E501)
ruff format .               # formatter (optional)
```

## Code Conventions & Common Patterns

- **Formatting**: `ruff` line-length 100, `target-version = py312`. `E501` ignored — let the formatter win.
- **Imports / typing**: `from __future__ import annotations` at the top of every module. `typing_extensions.TypedDict` for state. `Annotated[..., operator.add]` for reducer-bearing fields.
- **Naming**: snake_case modules and functions; agent node identifiers are string literals matching the `_LLM_CONFIG` keys (`spec_interpreter`, `drawing_auditor`, `bom_generator`, `process_recommender`, `chief_verifier`).
- **Async everywhere**:
  - Graph nodes are `async def node(state) -> dict`.
  - Blocking work (PDF/DXF parsing, Chroma calls) is wrapped in `asyncio.to_thread(...)` — never block the event loop.
  - CLI commands call `asyncio.run(graph.ainvoke(...))`.
  - Tests rely on `asyncio_mode = "auto"`; write `async def test_*` without decorators.
- **Error handling — graceful degradation**: nodes **must not raise**. Failed LLM calls and tool errors accumulate into `state["errors"]`, `state["verification_notes"]`, or `state["intermediate"]["llm_errors"]`. `chief_verifier` flips `status` to `needs_human` rather than throwing.
- **Dependency injection (lightweight, function-level)**: factories return resources instead of globals:
  - `get_llm(agent_name)`, `get_structured_llm(agent_name, schema)` from `llm.py`.
  - `get_client()`, `get_or_create_collection(name)`, `get_default_embedding()` from `tools/rag.py` and `tools/ingest.py`.
  - `mcp_tools` is an in-memory module — tests reach into `mcp._tool_manager._tools` (internal API) to enumerate tools; be aware this is brittle.
- **State management**: agents return partial dicts (`{"spec": ..., "errors": [...]}`); LangGraph merges them. Mutating the input `state` in place is fine for local-only changes, but prefer returning new dicts for fields with reducers.
- **Retry**: graph nodes carry `RetryPolicy(max_attempts=3)`; do not add ad-hoc `try/except` loops inside nodes.
- **File-type detection**: use `tools/file_detect.detect_file_type(path)` (`is_supported`) before dispatching to PDF vs. DXF parsers.
- **Prompt edits**: change the `.md` files in `src/deepdraw/prompts/`, not hardcoded strings.

## Important Files

- `pyproject.toml` — hatchling build (`packages = ["src/deepdraw"]`), console script `deepdraw = "deepdraw.cli:app"`, Python `>=3.12`, pytest `asyncio_mode = "auto"`.
- `langgraph.json` — wires graph `deepdraw` → `./src/deepdraw/graph.py:graph`; loads `./.env`.
- `ruff.toml` — standalone ruff config (duplicates pyproject's ruff section).
- `.env.example` — template for `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `OPENAI_COMPAT_*` (third-party base_url/api_key/model/headers), `DEEPDRAW_LLM_DEFAULT` / `DEEPDRAW_LLM_<AGENT>` (per-agent profile override), optional `LANGSMITH_*`.
- `main.py` — 3-line forwarder to `deepdraw.cli:app` (equivalent to `python -m deepdraw.cli`).
- `src/deepdraw/cli.py` — typer app; commands: `run`, `index`, `search`, `wipe`. *(A `poc` subcommand is planned but not yet present.)*
- `src/deepdraw/graph.py`, `src/deepdraw/state.py`, `src/deepdraw/llm.py` — graph/state/LLM wiring.
- `src/deepdraw/agents/*.py` — five agent nodes.
- `src/deepdraw/tools/{pdf,dxf,file_detect,rag,ingest,seed,mcp_server,mcp_tools,poc,poc_report}.py`.
- `fixtures/poc_scenarios.json` — 5 scenarios; non-list top-level must raise `ValueError("Expected list")`.
- `tests/conftest.py` — runtime-generated `sample_pdf`, `sample_dxf`, `sample_state`, `compiled_graph` (no binary fixtures in repo).
- `.claude/PRPs/prds/deepdraw-dfm-platform.prd.md` — canonical roadmap with phase status table; per-phase plan + report pairs under `.claude/PRPs/plans/completed/` and `.claude/PRPs/reports/`.

## Runtime/Tooling Preferences

- **Python**: 3.12 only. Venv at `.venv/` (gitignored). No `uv.lock` / `requirements.txt`; install via `pip install -e '.[dev]'`.
- **Build backend**: hatchling. Wheel packages `src/deepdraw`.
- **LangGraph**: pinned `langgraph==1.2.6`, `langchain-core>=1.0,<2`, `langgraph-checkpoint-sqlite==3.1.0` (currently unused — InMemorySaver). LLM integrations installed: `langchain-openai` (official OpenAI + any third-party OpenAI-compatible), `langchain-anthropic` (Claude), `langchain-deepseek` (reserved).
- **Parsing deps**: `pdfplumber>=0.11,<0.12`, `pymupdf>=1.24,<2` (AGPL-3.0), `ezdxf>=1.3,<2`, `mcp>=1.0,<2` (FastMCP).
- **Package manager**: pip into `.venv` (no uv/poetry in repo). Dev extra installs `pytest`, `pytest-asyncio`, `ruff`, `langgraph-cli[inmem]`.
- **No Bun/Node tooling**; this is a pure Python project. Bash is non-persistent — always chain `source .venv/bin/activate && ...`.

## Testing & QA

- **Framework**: `pytest` + `pytest-asyncio` (asyncio_mode = "auto"). No markers, no `addopts`.
- **Layout**: `tests/test_<module>.py` mirrors `src/deepdraw/<module>.py`. Coverage scope:
  - `test_graph.py` — graph compile, node registration, e2e `ainvoke` with real PDF, reflection-loop conditional edges, `MAX_REFLECTION_ITERATIONS == 3`.
  - `test_agents.py` — per-node async smoke tests; every node must degrade gracefully without API keys.
  - `test_state.py` — TypedDict field presence (incl. `intermediate` from Phase 2).
  - `test_tools_pdf.py`, `test_tools_dxf.py`, `test_tools_rag.py`, `test_tools_mcp.py` — pure unit tests for tool modules.
  - `test_poc.py` — PoC harness: `load_scenarios` (incl. the "Expected list" error contract at line ~39), `aggregate`, `render_report` markdown sections.
- **Fixtures**: `tests/conftest.py` generates `sample_pdf` (pymupdf, A4, text "Q235B" + "5mm") and `sample_dxf` (ezdxf LINE/CIRCLE/TEXT) at runtime; **no binary fixtures are committed**. `tests/fixtures/poc_scenarios.json` is the only static fixture.
- **LLM mocking**: agent tests patch `deepdraw.agents.<name>.get_structured_llm` with a tiny fake returning a pre-built Pydantic instance (Phase 3 plan). Provider/CLI tests in `test_llm.py` exercise the real factory with fake API keys and override env (`monkeypatch.setenv("OPENAI_COMPAT_BASE_URL", ...)`).
- **RAG tests**: use ChromaDB `EphemeralClient` (avoids macOS file locks).
- **MCP tests**: inspect `mcp._tool_manager._tools` directly (internal API) — fragile to MCP library upgrades; revisit if FastMCP version bumps.
- **Coverage expectations**: every node must have at least one smoke test confirming graceful degradation without keys. New tools must ship with `tests/test_tools_<name>.py` mirroring the existing pattern. **Do not** test wiring/mock echoes/source-text tautologies — assert behaviour, boundaries, error contracts.

---

## Quick Reference for AI Assistants

- Touching state? Update both `AgentState` annotations **and** `tests/test_state.py` field assertions.
- Adding an agent? Register it in `graph.py`, `_LLM_CONFIG` in `llm.py`, add `src/deepdraw/prompts/<name>.md`, write `tests/test_agents.py` + `tests/test_graph.py` coverage, extend CLI if user-facing.
- Changing PoC scenarios? Preserve the `Expected list` error contract in `load_scenarios`; `tests/test_poc.py` enforces it.
- Editing CLI? Mirror typer `app` structure (`run`, `index`, `search`, `wipe`); a `poc` subcommand is on the roadmap.
- Modifying the RAG layer? Watch the macOS file-lock issue — prefer `EphemeralClient` in tests, persistent `./.chroma_db` only at runtime.
- Always run `pytest` + `ruff check .` before yielding on non-trivial changes; smoke a real drawing through `deepdraw run` when touching graph/agent code.

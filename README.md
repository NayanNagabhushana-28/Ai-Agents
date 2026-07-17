# Ai-Agents

AI agents for finding approachable [PyTorch](https://github.com/pytorch/pytorch) GitHub issues. The project combines a **GitHub Issues MCP server**, **issue summaries with enrichment**, and (in progress) an **agentic triage runner** with a **provider-agnostic LLM wrapper** (planned; Anthropic in v1).

Canonical implementation plan: `~/.cursor/plans/easy_issue_triage_workflow_eb1c532e.plan.md`

---

## Workflow

End-to-end goal: return **easy, open, unassigned issues with no open linked PR** suitable for newcomers (v1 default: **1** issue).

| Step | Description | Status |
|------|-------------|--------|
| 1 | **MCP / GitHub fetch** — list and get issues via MCP or `github_api` | Done |
| 2 | **Spec / contract** — filters, easy rules, JSON output shape in prompt | Done |
| 3 | **Prompt template** — [`prompts/easy_issue_finder/`](prompts/easy_issue_finder/) | Done |
| 4 | **Runtime** — Python CLI (mode A); Cursor + MCP for manual use | Pending |
| 5 | **LLM provider wrapper** — `LLMProvider` Protocol; Anthropic v1 only; OpenAI/etc. in v2 | Pending |
| 6 | **Agentic dry run** — tool loop (`list_issues`) until 1 easy issue or caps; pre-filter in tool handlers | Pending |
| 7 | **Validate & tune** — parse JSON, schema check, refine prompt from failures | Pending |
| 8 | **Scale** — raise scan caps (toward 1000), cache, logging, tests | Pending |

**Progress: 2 / 7 plan todos complete** (see [Implementation status](#implementation-status) below).

> **Maintainer convention:** When a plan todo is completed, update this README in the same change set. Every new module needs a **module docstring** (purpose, who calls it) and **function docstrings** written for beginners.

---

## Code conventions (all todos)

**File names** — short, self-explanatory nouns (not `utils.py` or `helpers.py`):

| Area | File | Purpose |
|------|------|---------|
| GitHub HTTP | `github_api.py` | REST calls to api.github.com |
| Issue shaping | `issue_summary.py` | Raw issue JSON → compact summary dict |
| MCP tools | `mcp_tools/issue_list_tools.py` | Issue list/get tools (more modules later) |
| MCP app | `mcp_server.py` | Registers all `mcp_tools` groups |
| Prompts | `prompts/<agent_name>/` | One folder per agent |
| *Planned* finder | `agents/easy_issue_finder/finder_runner.py` | easy_issue_finder loop |
| *Planned* finder tools | `agents/easy_issue_finder/github_issue_tools.py` | LLM-callable GitHub tools |
| *Planned* finder validate | `agents/easy_issue_finder/result_validator.py` | JSON output checks |
| *Planned* triage | `agents/triage_agent/` | Second agent (Phase 2+) |
| *Planned* LLM types | `src/llm/chat_types.py` | Messages, tools, config |
| *Planned* LLM contract | `src/llm/provider_protocol.py` | `LLMProvider` interface |
| *Planned* LLM factory | `src/llm/provider_factory.py` | `get_llm_provider()` |
| *Planned* Anthropic | `src/llm/providers/anthropic_provider.py` | Only file that imports `anthropic` |

**Documentation:** Each public function explains *what*, *parameters*, and *returns* in plain language.

---

## Architecture

### Current (built)

```text
Cursor chat  →  MCP (stdio)  →  github_api  →  GitHub REST API
                                      ↓
                              issue_summary.format_issue_summary
                              (assignees, open_linked_pr)
```

Optional enrichment: `list_issues(..., enrich_linked_prs=True)` uses Issue Timeline + `GET pulls/{n}` to set **`open_linked_pr`**.

```text
Cursor chat  →  MCP (stdio)  →  mcp_tools/issue_list_tools  →  github_api
                                      ↓
                              issue_summary.format_issue_summary
```

```text
src/llm/                           shared by all agents (planned)
src/agents/
  easy_issue_finder/               Phase 1 agent (runner planned)
  triage_agent/                    Phase 2+ agent (reserved)
prompts/
  easy_issue_finder/               prompt + prompt_loader
  triage_agent/                    reserved
```

### Target (planned — easy_issue_finder runner)

```text
scripts/run_easy_issue_finder.py
       ↓
agents/easy_issue_finder/finder_runner.py
       ↓                    ↓
get_llm_provider()    github_issue_tools  →  github_api
       ↓
result_validator.py  →  final JSON
```

**Design choices:**

- **Agentic v1:** The model calls **`list_issues`** (paginate) until it returns **1 easy** issue or hits **`max_tool_rounds` / `max_issues_scanned`**.
- **Pre-filter in Python:** Tool handlers drop issues that are not open, assigned, or have an open linked PR (when enrichment is on). The LLM focuses on **easy vs hard**.
- **Prompt:** [`prompts/easy_issue_finder/`](prompts/easy_issue_finder/) via `load_easy_issue_finder_prompt()`.
- **Multi-agent:** Shared `github_api` + `llm`; each agent gets its own folder under `src/agents/` and `prompts/`.

### APIs used

| API | Role | Status |
|-----|------|--------|
| GitHub REST (`api.github.com`) | Issues, search, timeline, pulls | In use |
| MCP (stdio) | Cursor integration | In use |
| Anthropic Messages API | Agent + tool use | Planned ([`src/llm`](src/llm)) |
| OpenAI / other LLMs | Alternate providers | Planned (v2) |

---

## Implementation status

| Todo | Status | What shipped |
|------|--------|--------------|
| `gap-format-summary` | **Done** | [`issue_summary.py`](src/github_issues_mcp/issue_summary.py): `assignees`, `open_linked_pr` |
| `linked-pr-enrich` | **Done** | [`has_open_linked_pull_request`](src/github_issues_mcp/github_api.py); MCP `enrich_linked_prs` |
| `llm-provider-wrapper` | Pending | [`src/llm/`](src/llm): `LLMProvider`, `AnthropicProvider`, `get_llm_provider()` |
| `runtime-cli` | Pending | `scripts/run_easy_issue_finder.py` |
| `agent-loop` | Pending | Tool-use loop until 1 easy issue |
| `llm-invoke-validate` | Pending | JSON parse + schema check via `LLMProvider` |
| `polish-docs-test` | Pending | Unit tests, caching, extended CLI docs |

**Also done (not separate todos):** consolidated prompt in `user.txt` only; prompt loader with `<<<PLACEHOLDER>>>` substitution.

---

## Prompt templates

```python
from prompts.easy_issue_finder import load_easy_issue_finder_prompt

prompt = load_easy_issue_finder_prompt(
    owner="pytorch",
    repo="pytorch",
    issues_json='[{"number": 1, "title": "...", ...}]',
    target_easy_count=1,
    max_issues_cap=1000,
)
```

Placeholders in [`prompts/easy_issue_finder/user.txt`](prompts/easy_issue_finder/user.txt) are filled by the loader.

Legacy aliases: ``load_easy_issue_picker_prompt`` still works (imports from ``easy_issue_finder``).

---

## GitHub Issues MCP Server

MCP server exposing GitHub repository issues as tools for Cursor IDE. Defaults to [pytorch/pytorch](https://github.com/pytorch/pytorch).

### Setup

1. **Virtual environment and dependencies:**

   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **GitHub token:** [Create a PAT](https://github.com/settings/tokens) with `public_repo` (read-only).

3. **Authentication** — create `.env` in the project root (gitignored):

   ```bash
   GITHUB_TOKEN=your_github_token_here
   ```

   Or set `GITHUB_TOKEN` in `.cursor/mcp.json` under `env`. Restart Cursor after MCP config changes.

   If the MCP server fails to start, point `command` in `.cursor/mcp.json` at the project venv Python:

   ```json
   "command": "/path/to/Ai-Agents/.venv/bin/python",
   "args": ["run_server.py"]
   ```

### Usage in Cursor

Ask the AI to:

- "List open issues from PyTorch"
- "Get issue #12345 from pytorch/pytorch"
- "List 5 recent issues with enrich_linked_prs true"

### MCP tools

| Tool | Description |
|------|-------------|
| `list_issues` | List issues. Params: `owner`, `repo`, `state`, `labels`, `sort`, `per_page`, `page`, `include_pull_requests`, **`enrich_linked_prs`** (default `false`; extra API calls per issue when `true`) |
| `get_issue` | Full issue JSON by number |

### Issue summary fields (`list_issues`)

| Field | Description |
|-------|-------------|
| `assignees` | Login strings; empty list = unassigned |
| `open_linked_pr` | `true` / `false` when `enrich_linked_prs=true`; otherwise `null` |
| `body_excerpt`, `labels`, `html_url`, … | Standard list-view fields |

### Run MCP standalone

```bash
python run_server.py
```

Uses stdio transport; test with [MCP Inspector](https://github.com/modelcontextprotocol/inspector).

---

## Planned: easy_issue_finder CLI

Not implemented yet. Intended usage (v1):

```bash
# Future — requires ANTHROPIC_API_KEY, TRIAGE_MODEL
python scripts/run_easy_issue_finder.py --owner pytorch --repo pytorch --enrich-linked-prs
```

A separate **`triage_agent`** CLI (`scripts/run_triage_agent.py`) is reserved for Phase 2+.

Environment variables (see [`.env.example`](.env.example)):

| Variable | Purpose |
|----------|---------|
| `GITHUB_TOKEN` | GitHub REST (required for rate limits) |

When the LLM wrapper and CLI ship, `.env.example` will also document `ANTHROPIC_API_KEY`, `TRIAGE_MODEL`, and related settings.

---

## Project layout

```text
run_server.py                         MCP entrypoint
src/github_issues_mcp/                Shared GitHub + MCP (all agents)
  github_api.py
  issue_summary.py
  mcp_tools/issue_list_tools.py
  mcp_server.py
src/llm/                              Shared LLM wrapper (planned)
src/agents/
  easy_issue_finder/                  Phase 1 agent (runner planned)
  triage_agent/                       Phase 2+ (reserved)
prompts/
  easy_issue_finder/                  user.txt + prompt_loader.py
  triage_agent/                       reserved
scripts/
  run_easy_issue_finder.py            (planned)
  run_triage_agent.py                 (planned)
.env.example
```

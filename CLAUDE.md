# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

Node-RED MCP is a FastMCP server that exposes Node-RED flow management as MCP tools. It communicates with a Node-RED instance via the Admin HTTP API, allowing language models to read, create, update, and delete flows, manage nodes, trigger inject nodes, and inspect runtime settings. Unlike the original TypeScript `node-red-mcp-server`, this is a Python implementation using the mailmcp project conventions (FastMCP, Pydantic models, async httpx client).

## Commands

```bash
make all              # format + lint + test
make check            # lint + test (no format)
make test             # uv run pytest tests/ -v
make lint             # uv run ruff check src/ tests/
make format           # uv run ruff format src/ tests/
make fix              # uv run ruff check --fix --unsafe-fixes src/ tests/
```

Run a single test: `uv run pytest tests/test_models.py -v`
Run with coverage: `uv run pytest tests/ -v --cov=src/nodered_mcp --cov-report=term-missing`

Always use `uv run` to execute Python tools — never bare `python` or `pytest`.

Start the server: `uv run nodered-mcp`

## Architecture

```
src/nodered_mcp/
├── server.py              # FastMCP server, config loading, client init, tool imports
├── config.py              # Pydantic Settings (env vars: NODE_RED_URL, NODE_RED_TOKEN, NODE_RED_API_VERSION, auth fields)
├── client.py              # NodeRedClient: async httpx wrapper with auth
├── models/
│   ├── base.py            # BaseApiModel with from_api() classmethod
│   ├── flow.py            # Node, FlowTab, Flow, FlowState
│   ├── node.py            # NodeModule, NodeSet
│   ├── responses.py       # FlowList, FlowSummary, FlowCreateResult, Settings, DiagnosticsResult
│   └── layout.py          # LayoutIssue, LayoutReport (lint results)
└── tools/
    ├── flows.py           # 12 flow tools (get_flows, update_flows, list_tabs, etc.) + auto-lint on mutations
    ├── nodes.py           # 6 node tools (inject, get_nodes, find_nodes_by_type, etc.)
    ├── settings.py        # 2 settings tools (get_settings, get_diagnostics)
    ├── layout.py          # 1 layout tool (lint_flow) + pure lint helpers
    └── utility.py         # 1 api_help tool (static reference)
```

### Layer Diagram

```
Tools (thin @mcp.tool() functions)
  ↓
Client (async httpx wrapper, returns raw dicts)
  ↓
Node-RED Admin HTTP API
```

Tools convert raw dicts to Pydantic models using `Model.from_api()`.

### Key Pattern: Model Layering

Base models define the canonical schema. All models inherit from `BaseApiModel`:

```
BaseApiModel (from_api → model_validate)
  ├── Node (extra="allow" for type-specific fields)
  ├── FlowTab (tab workspace)
  ├── Flow (complete flow with nodes/configs/subflows)
  ├── FlowState (start/stop state)
  ├── NodeSet (installed node module)
  ├── NodeModule (node module info)
  ├── Response wrappers (FlowList, FlowSummary, Settings, DiagnosticsResult, etc.)
  └── Layout models (LayoutIssue, LayoutReport)
```

Tools accept/return base types. No provider hierarchy needed (single backend).

### Key Pattern: Client Singleton

`NodeRedClient` is a global singleton managed by `get_client()` / `reset_client()`:

```python
# Tools call get_client()
client = get_client()
data = await client.get_flows()
return FlowList.from_api(data)

# Tests call reset_client() to get fresh instances
await reset_client()  # closes old client to prevent connection leaks
```

Similar to mailmcp's `get_provider_manager()` pattern, but simpler (no provider abstraction).

### Key Pattern: Authentication

Three auth methods configured via `NODE_RED_AUTH_METHOD`:

| Method | Env Vars | Use Case |
|--------|----------|----------|
| `token` (default) | `NODE_RED_TOKEN` | Static bearer token |
| `basic` | `NODE_RED_AUTH_USERNAME`, `NODE_RED_AUTH_PASSWORD` | Forward auth proxy (e.g. authentik) |
| `oauth` | `NODE_RED_AUTH_USERNAME`, `NODE_RED_AUTH_PASSWORD`, `NODE_RED_OAUTH_TOKEN_URL`, `NODE_RED_OAUTH_CLIENT_ID` | OAuth2 client credentials grant |

- **token**: Sets `Authorization: Bearer {token}` header (existing behavior, backward compatible)
- **basic**: Uses `httpx.BasicAuth` — proxy validates credentials, sets cookies
- **oauth**: Lazy token fetch via client credentials grant, cached with 30s expiry buffer, single 401 retry

### Key Pattern: Heterogeneous Flow Arrays

`GET /flows` returns a flat array mixing tabs (`type=tab`), subflows (`type=subflow`), and nodes (all other types). **Tools must filter by `type` before parsing**:

```python
# Correct
flows_data = await client.get_flows()
tabs = [item for item in flows_data if item.get("type") == "tab"]
return FlowTab.from_api(tabs)

# Wrong - crashes on non-tab items
flows_data = await client.get_flows()
return FlowTab.from_api(flows_data)  # ERROR
```

Client returns the raw `list[dict]`; type-aware parsing happens in tool helpers.

## Tool List (22 tools)

### Flow Tools (12)
1. `get_flows` — GET /flows → FlowList
2. `update_flows` — POST /flows (deployment_type header)
3. `get_flow` — GET /flow/:id → Flow
4. `update_flow` — PUT /flow/:id → str
5. `list_tabs` — GET /flows, filter type=tab → list[FlowTab]
6. `create_flow` — POST /flow → FlowCreateResult
7. `delete_flow` — DELETE /flow/:id → str
8. `get_flows_state` — GET /flows/state → FlowState
9. `set_flows_state` — POST /flows/state → FlowState
10. `get_flows_formatted` — GET /flows, format client-side → FlowSummary
11. `visualize_flows` — GET /flows, format as markdown → str
12. `patch_flow` — GET /flow/:id, apply ops, PUT /flow/:id → str

### Node Tools (6)
12. `inject` — POST /inject/:id → str
13. `get_nodes` — GET /nodes → list[NodeSet]
14. `get_node_info` — GET /nodes/:module → NodeModule
15. `toggle_node_module` — PUT /nodes/:module → NodeModule
16. `find_nodes_by_type` — GET /flows, filter by type → list[Node]
17. `search_nodes` — GET /flows, search by query → list[Node]

### Settings Tools (2)
18. `get_settings` — GET /settings → Settings
19. `get_diagnostics` — GET /diagnostics → DiagnosticsResult

### Layout Tools (1)
20. `lint_flow` — GET /flow/:id, run layout checks → LayoutReport

### Utility Tools (1)
21. `api_help` — static reference → str

## Conventions (see conventions.md for full details)

- **All models inherit BaseApiModel**, never plain `BaseModel` or raw dicts
- **Never override `from_api()`** — use `validation_alias`, `@field_validator`, `@model_validator` instead
- **Transformation hierarchy**: `validation_alias` (key renames) → `@field_validator` (type conversions) → `@model_validator` (cross-field structural reshaping only)
- **MCP tools return Pydantic models**, raise exceptions on failure (no error dicts). **Exception**: simple confirmation strings for inject, delete, visualize.
- **Tools are thin wrappers** — business logic lives in client or helper functions
- **Client returns raw dicts** — tools convert to models via `Model.from_api()`
- **Heterogeneous flow arrays** — filter by `type` before calling `from_api()`
- **Node model uses `extra="allow"`** — Node-RED nodes have many type-specific fields
- **Client singleton** — `get_client()` / `reset_client()` manage global instance; `reset_client()` closes old client
- **Settings uses `validation_alias`** — `http_node_root: str = Field("", validation_alias="httpNodeRoot")`

## Quality Gates

All must pass: `ruff check`, `pytest` (22 tools covered), server starts cleanly via `uv run nodered-mcp`.

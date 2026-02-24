# nodered-mcp

A Python MCP server for Node-RED flow management, built on [FastMCP](https://github.com/jlowin/fastmcp) and [Pydantic](https://docs.pydantic.dev/).

Gives language models full read/write access to a Node-RED instance through the [Admin HTTP API](https://nodered.org/docs/api/admin/), with structured Pydantic responses, incremental flow patching, layout linting, and flexible authentication (token, basic, OAuth2).

## Compared to node-red-mcp-server

This project was inspired by [karavaev-evgeniy/node-red-mcp-server](https://github.com/karavaev-evgeniy/node-red-mcp-server) (TypeScript/npm). Key differences:

| | node-red-mcp-server (TS) | nodered-mcp (Python) |
|---|---|---|
| Runtime | Node.js / npm | Python 3.11+ / uv |
| Framework | Custom MCP SDK | FastMCP |
| Responses | Raw JSON strings | Typed Pydantic models |
| Auth | Token only | Token, Basic, OAuth2 |
| Deployment types | `full` only | `full`, `nodes`, `flows`, `reload` |
| Flow mutations | Replace entire flow | `patch_flow` with granular ops (add/remove/update/rewire) |
| Layout checks | None | `lint_flow` detects overlaps, spacing, wire crossings |
| Auto-lint | N/A | `update_flow` and `patch_flow` append warnings automatically |
| Tool count | 19 | 22 |

## Installation

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/):

```bash
git clone <repo-url> && cd nodered-mcp
uv sync
```

## Quick Start

```bash
# Minimal — token auth (default)
export NODE_RED_URL=http://localhost:1880
export NODE_RED_TOKEN=your-api-token
uv run nodered-mcp
```

## Configuration

All configuration is via environment variables with the `NODE_RED_` prefix.

| Variable | Default | Description |
|----------|---------|-------------|
| `NODE_RED_URL` | `http://localhost:1880` | Node-RED instance URL |
| `NODE_RED_TOKEN` | `""` | Bearer token (for `token` auth method) |
| `NODE_RED_API_VERSION` | `v1` | API version header |
| `NODE_RED_AUTH_METHOD` | `token` | Auth method: `token`, `basic`, or `oauth` |
| `NODE_RED_AUTH_USERNAME` | `""` | Username for `basic` or `oauth` auth |
| `NODE_RED_AUTH_PASSWORD` | `""` | Password/app password for `basic` or `oauth` auth |
| `NODE_RED_OAUTH_TOKEN_URL` | `""` | OAuth2 token endpoint URL |
| `NODE_RED_OAUTH_CLIENT_ID` | `""` | OAuth2 client ID |

## Authentication

### Token (default)

Static bearer token sent with every request. This is the simplest method and matches how `node-red-mcp-server` works:

```bash
NODE_RED_URL=http://localhost:1880
NODE_RED_TOKEN=your-api-token
```

### Basic Auth

HTTP Basic authentication, useful when Node-RED sits behind a forward auth proxy.

```bash
NODE_RED_AUTH_METHOD=basic
NODE_RED_AUTH_USERNAME=admin
NODE_RED_AUTH_PASSWORD=your-password
```

### Basic Auth with Authentik

If your Node-RED instance sits behind [Authentik](https://goauthentik.io/) as a forward auth proxy, the basic auth method works well. Authentik intercepts requests, validates credentials, and sets session cookies before forwarding to Node-RED.

1. **Create an Authentik application** for your Node-RED instance using the Forward Auth (single application) provider.

2. **Configure your reverse proxy** (Traefik, nginx, Caddy) to use Authentik's forward auth endpoint. For example, with Traefik:

    ```yaml
    # docker-compose.yml (Traefik labels on the Node-RED service)
    labels:
      - "traefik.http.routers.nodered.middlewares=authentik@docker"
    ```

3. **Create an Authentik service account** (or use an existing user) and generate an app password under the user's token settings. This avoids MFA prompts that would block API access.

4. **Configure nodered-mcp**:

    ```bash
    NODE_RED_URL=https://nodered.yourdomain.com
    NODE_RED_AUTH_METHOD=basic
    NODE_RED_AUTH_USERNAME=service-account
    NODE_RED_AUTH_PASSWORD=the-app-password-from-authentik
    ```

The basic auth credentials are sent to Authentik's proxy, which validates them and sets cookies. Subsequent requests use the session cookie, so Node-RED itself doesn't need auth enabled.

### OAuth2 Client Credentials

Fetches a short-lived JWT via OAuth2 client credentials grant. The token is cached and auto-refreshed with a 30-second expiry buffer. On a 401 response, the server retries once with a fresh token.

Works with Authentik out of the box — every application has a token endpoint and `client_id`:

```bash
NODE_RED_AUTH_METHOD=oauth
NODE_RED_AUTH_USERNAME=service-account
NODE_RED_AUTH_PASSWORD=service-password
NODE_RED_OAUTH_TOKEN_URL=https://auth.yourdomain.com/application/o/token/
NODE_RED_OAUTH_CLIENT_ID=your-client-id
```

## MCP Client Configuration

### Claude Desktop

```json
{
  "mcpServers": {
    "nodered": {
      "command": "uv",
      "args": ["--directory", "/path/to/nodered-mcp", "run", "nodered-mcp"],
      "env": {
        "NODE_RED_URL": "http://localhost:1880",
        "NODE_RED_TOKEN": "your-token"
      }
    }
  }
}
```

### Claude Code

```json
{
  "mcpServers": {
    "nodered": {
      "command": "uv",
      "args": ["--directory", "/path/to/nodered-mcp", "run", "nodered-mcp"],
      "env": {
        "NODE_RED_URL": "http://localhost:1880",
        "NODE_RED_TOKEN": "your-token"
      }
    }
  }
}
```

## Tools

### Flow Tools (12)

| Tool | Description |
|------|-------------|
| `get_flows` | Get all flows with summary statistics |
| `update_flows` | Replace all flows with deployment type control (`full`/`nodes`/`flows`/`reload`) |
| `get_flow` | Get a single flow by ID |
| `update_flow` | Update a single flow (auto-lints after save) |
| `list_tabs` | List all flow tabs (workspaces) |
| `create_flow` | Create a new flow tab |
| `delete_flow` | Delete a flow tab |
| `get_flows_state` | Get runtime state (started/stopped) |
| `set_flows_state` | Start or stop the flow runtime |
| `get_flows_formatted` | Get flows grouped by tabs/nodes/subflows with statistics |
| `visualize_flows` | Markdown-formatted per-tab structural overview |
| `patch_flow` | Incremental operations: `add_nodes`, `remove_nodes`, `update_node`, `rewire`, `set_label`, `set_info`, `set_disabled` (auto-lints after save) |

### Node Tools (6)

| Tool | Description |
|------|-------------|
| `inject` | Trigger an inject node |
| `get_nodes` | List installed node modules |
| `get_node_info` | Detailed info about a node module |
| `toggle_node_module` | Enable or disable a node module |
| `find_nodes_by_type` | Find all nodes of a given type |
| `search_nodes` | Search nodes by name or any property |

### Layout Tools (1)

| Tool | Description |
|------|-------------|
| `lint_flow` | Check a flow for node overlaps, insufficient spacing, and wire-through-node crossings. Optionally scoped to specific node IDs. |

### Settings Tools (2)

| Tool | Description |
|------|-------------|
| `get_settings` | Get Node-RED runtime settings |
| `get_diagnostics` | Get runtime diagnostics (Node.js version, OS, modules) |

### Utility Tools (1)

| Tool | Description |
|------|-------------|
| `api_help` | Node-RED Admin API endpoint reference |

## Architecture

```
src/nodered_mcp/
├── server.py              # FastMCP server, config, client init
├── config.py              # Pydantic Settings (env vars)
├── client.py              # Async httpx wrapper with auth
├── models/
│   ├── base.py            # BaseApiModel with from_api()
│   ├── flow.py            # Node, FlowTab, Flow, FlowState
│   ├── node.py            # NodeModule, NodeSet
│   ├── responses.py       # FlowList, FlowSummary, Settings, etc.
│   └── layout.py          # LayoutIssue, LayoutReport
└── tools/
    ├── flows.py           # Flow CRUD + patch + auto-lint
    ├── nodes.py           # Node management + search
    ├── layout.py          # Layout lint checks
    ├── settings.py        # Settings + diagnostics
    └── utility.py         # API help reference
```

The layer diagram is simple:

```
MCP Tools (thin async functions, return Pydantic models)
  ↓
NodeRedClient (async httpx, returns raw dicts)
  ↓
Node-RED Admin HTTP API
```

## Development

```bash
make all              # format + lint + test
make check            # lint + test (no format)
make test             # uv run pytest tests/ -v
make lint             # uv run ruff check src/ tests/
make format           # uv run ruff format src/ tests/
```

Run a single test file:

```bash
uv run pytest tests/tools/test_layout.py -v
```

Run with coverage:

```bash
uv run pytest tests/ -v --cov=src/nodered_mcp --cov-report=term-missing
```

Always use `uv run` — never bare `python` or `pytest`.

See [conventions.md](conventions.md) for detailed code patterns (model layering, tool conventions, client architecture).

## License

MIT

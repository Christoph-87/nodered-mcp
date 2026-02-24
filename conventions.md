# nodered-mcp Code Conventions

## Model Architecture

### BaseApiModel

All API response models inherit from `BaseApiModel` which provides a single `from_api()` classmethod. This method is **never overridden** - it simply calls `model_validate()`.

```python
class BaseApiModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    @classmethod
    def from_api(cls, data: dict | list) -> Self | list[Self]:
        if isinstance(data, list):
            return [cls.model_validate(item) for item in data]
        return cls.model_validate(data)
```

### Base Models (Thin Data Contracts)

Base models (`Node`, `FlowTab`, `Flow`, `FlowState`, `NodeSet`, `NodeModule`) are pure field definitions with minimal transformation logic. They define the canonical schema for Node-RED API responses.

```python
class FlowTab(BaseApiModel):
    id: str = ""
    label: str = ""
    disabled: bool = False
    info: str = ""
```

### Node Model: Permissive Extra Fields

The `Node` model uses `extra="allow"` because Node-RED nodes have many type-specific fields that vary by node type (inject nodes have different fields than function nodes, debug nodes, etc.). Strict modeling would require dozens of subclasses.

```python
class Node(BaseApiModel):
    model_config = ConfigDict(populate_by_name=True, extra="allow")

    id: str = ""
    type: str = ""
    z: str = ""  # parent flow ID
    name: str = ""
    wires: list[list[str]] = Field(default_factory=list)
    x: int = 0
    y: int = 0
    # All other type-specific fields captured via extra="allow"
```

### Transformation Layer

Unlike mailmcp (which has provider-specific subclasses), nodered-mcp has a single backend (Node-RED Admin HTTP API). Transformation happens via Pydantic's declarative tools in the base models themselves.

#### 1. `Field(validation_alias=...)` for key renames

Use when the API key is just a different name for the same value (typically camelCase → snake_case).

```python
class Settings(BaseApiModel):
    http_node_root: str = Field("", validation_alias="httpNodeRoot")
    version: str = ""
    user: dict | None = None
```

#### 2. `@field_validator` for individual type conversions

Use when a single field's value needs transformation (type conversion, format parsing, nested object wrapping). Currently not needed in nodered-mcp since the Node-RED API returns well-formed JSON with consistent types.

#### 3. `@model_validator(mode="before")` ONLY for cross-field structural reshaping

Use **only** when the API structure genuinely differs from the model structure in a way that requires cross-field access. Currently not needed in nodered-mcp.

### Response Models

Response wrappers (`FlowList`, `FlowSummary`, `FlowCreateResult`, `Settings`, `DiagnosticsResult`) also inherit `BaseApiModel` and follow the same conventions. Use `validation_alias` for camelCase API keys.

`DiagnosticsResult` is a thin wrapper around `data: dict` because the diagnostics response structure is too variable for strict modeling:

```python
class DiagnosticsResult(BaseApiModel):
    """Diagnostics result.

    Thin wrapper - diagnostics response structure is too variable
    for strict modeling.
    """
    data: dict = Field(default_factory=dict)
```

### Decision Hierarchy

When adding a new field or model, choose the **simplest** tool that works:

1. **Same value, different key?** → `Field(validation_alias="apiKey")` — zero code, pure declaration
2. **Reusable type coercion?** → Type alias with `Annotated[T, PlainSerializer(...)]` — defined once, used everywhere
3. **Single field needs transformation?** → `@field_validator("field", mode="before")` — isolated, testable
4. **Multiple fields need cross-referencing?** → `@model_validator(mode="before")` — minimal reshaping only
5. **Derived from other fields?** → `@computed_field`

Example from this project: `Settings.http_node_root` uses `validation_alias="httpNodeRoot"` (step 1) rather than a validator.

**Never** write a model_validator that manually maps every field into a new dict. If you find yourself writing `result["x"] = data.get("x")` for 10+ fields, you're doing it wrong.

---

## MCP Tool Conventions

### Return Pydantic models, never dicts

```python
# Good
return Settings.from_api(data)

# Bad
return {"http_node_root": data["httpNodeRoot"], "version": data["version"]}
```

**Exception**: Simple confirmation strings are allowed for operations with no meaningful response body:

```python
# Acceptable for inject, delete, visualize
return f"Successfully injected node {node_id}"
return "Flow deleted successfully"
return markdown_visualization  # str
```

On failure, **raise exceptions** (ValueError, RuntimeError) - don't return error dicts.

### Keep tools thin

Tool functions validate parameters and call a single client method. Business logic (formatting, filtering, aggregation) belongs in helper functions or the client, not the tool function itself.

```python
# Good - tool validates, client does the work, helper formats
@mcp.tool()
async def get_flows_formatted() -> FlowSummary:
    """Get flows with formatted summary and statistics."""
    client = get_client()
    flows_data = await client.get_flows()
    return _format_flows(flows_data)  # helper function handles grouping

# Bad - business logic in the tool
@mcp.tool()
async def get_flows_formatted() -> FlowSummary:
    client = get_client()
    flows_data = await client.get_flows()
    # 50 lines of grouping/formatting logic here
```

### Use `Model.from_api()` pattern

```python
# Good - handles both single and list
tabs = FlowTab.from_api(tabs_data)
settings = Settings.from_api(settings_data)

# Bad - manual construction
FlowTab(id=obj["id"], label=obj["label"])

# Bad - manual list comprehension (from_api handles lists)
[FlowTab.from_api(x) for x in items]
```

### Example: get_flows tool

```python
@mcp.tool()
async def get_flows() -> FlowList:
    """Get all flows from Node-RED."""
    client = get_client()
    flows_data = await client.get_flows()

    tabs = [item for item in flows_data if item.get("type") == "tab"]

    return FlowList(
        flows=flows_data,
        tabs=tabs,
        summary=f"Found {len(flows_data)} total items, {len(tabs)} tabs",
        statistics={"total": len(flows_data), "tabs": len(tabs)}
    )
```

---

## Client Architecture

### NodeRedClient: Single Async HTTP Client

Unlike mailmcp (which has a provider abstraction for multiple backends), nodered-mcp has a single backend (Node-RED Admin HTTP API), so we use a single client class instead of a provider hierarchy.

```python
class NodeRedClient:
    def __init__(self, base_url: str, token: str = "", api_version: str = "v1"):
        headers = {"Node-RED-API-Version": api_version}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        self._http = httpx.AsyncClient(
            base_url=base_url,
            headers=headers,
            timeout=30.0,
        )
```

### Centralized Request Handler

All HTTP calls go through `_request()` which handles:
- Auth headers (set on httpx.AsyncClient initialization)
- Per-request header overrides (needed for `Node-RED-Deployment-Type`)
- Error handling (raises RuntimeError on 4xx/5xx)
- JSON parsing (returns parsed response or None for 204)

```python
async def _request(
    self,
    method: str,
    path: str,
    data: Any = None,
    headers: dict[str, str] | None = None,
) -> Any:
    request_headers = headers or {}
    response = await self._http.request(method, path, json=data, headers=request_headers)

    if response.status_code == 204:
        return None

    if response.status_code >= 400:
        raise RuntimeError(f"Node-RED API error {response.status_code}: {response.text}")

    return response.json()
```

### Public Methods Return Raw Dicts

Client methods are thin wrappers around HTTP calls. They return raw `dict` or `list[dict]` - tools convert to models:

```python
# Client returns raw dict
async def get_settings(self) -> dict:
    return await self._request("GET", "/settings")

# Tool converts to model
@mcp.tool()
async def get_settings() -> Settings:
    client = get_client()
    data = await client.get_settings()
    return Settings.from_api(data)
```

### Global Singleton Pattern

`get_client()` / `reset_client()` manage a global `_client` instance:

```python
_client: NodeRedClient | None = None

def get_client() -> NodeRedClient:
    global _client
    if _client is None:
        config = get_config()
        _client = NodeRedClient(
            base_url=config.url,
            token=config.token,
            api_version=config.api_version,
        )
    return _client

async def reset_client() -> NodeRedClient:
    global _client
    if _client is not None:
        await _client.close()  # prevent connection leaks

    config = get_config()
    _client = NodeRedClient(...)
    return _client
```

**Important**: `reset_client()` calls `await close()` on the old client to prevent connection leaks in tests.

---

## Heterogeneous Flow Arrays

### The Problem

`GET /flows` returns a flat array mixing three types of objects:
- **Tabs** (`type=tab`): Flow workspaces
- **Subflows** (`type=subflow`): Reusable flow templates
- **Nodes** (all other types): Individual nodes

```json
[
  {"id": "abc", "type": "tab", "label": "Flow 1"},
  {"id": "def", "type": "inject", "z": "abc", "name": "Trigger"},
  {"id": "ghi", "type": "debug", "z": "abc", "name": "Output"}
]
```

### The Solution

**Client returns the raw `list[dict]`**. Type-aware parsing happens in tool-level helpers:

```python
# Client - returns heterogeneous array unchanged
async def get_flows(self) -> list[dict]:
    return await self._request("GET", "/flows")

# Tool helper - filters by type before parsing
def _get_tabs(flows_data: list[dict]) -> list[FlowTab]:
    tab_items = [item for item in flows_data if item.get("type") == "tab"]
    return FlowTab.from_api(tab_items)

def _get_nodes_by_type(flows_data: list[dict], node_type: str) -> list[Node]:
    node_items = [item for item in flows_data if item.get("type") == node_type]
    return Node.from_api(node_items)
```

### Tools Must Filter Before Parsing

**Never** call `FlowTab.from_api()` or `Node.from_api()` on the raw heterogeneous array. Always filter first:

```python
# Good
@mcp.tool()
async def list_tabs() -> list[FlowTab]:
    client = get_client()
    flows_data = await client.get_flows()
    tabs = [item for item in flows_data if item.get("type") == "tab"]
    return FlowTab.from_api(tabs)

# Bad - crashes on non-tab items
@mcp.tool()
async def list_tabs() -> list[FlowTab]:
    client = get_client()
    flows_data = await client.get_flows()
    return FlowTab.from_api(flows_data)  # ERROR: inject nodes don't have 'label'
```

---

## Quality Gates

All must pass before merge:

```bash
ruff check src/ tests/    # Fast linting
pytest tests/ -v          # Tests (all 20 tools covered)
uv run nodered-mcp        # Server starts cleanly
```

Run single test: `uv run pytest tests/test_models.py -v`

Always use `uv run` to execute Python tools — never bare `python` or `pytest`.

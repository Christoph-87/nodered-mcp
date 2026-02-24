"""Flow management tools for Node-RED."""

import json

from nodered_mcp.client import get_client
from nodered_mcp.models.flow import Flow, FlowState, FlowTab
from nodered_mcp.models.responses import FlowCreateResult, FlowList, FlowSummary
from nodered_mcp.server import mcp


def _build_flow_list(raw_flows: list[dict]) -> FlowList:
    """Build FlowList with summary and statistics from raw flow data."""
    tabs = [f for f in raw_flows if f.get("type") == "tab"]
    nodes = [f for f in raw_flows if f.get("type") not in ("tab", "subflow")]
    subflows = [f for f in raw_flows if f.get("type") == "subflow"]

    node_types: dict[str, int] = {}
    for node in nodes:
        node_type = node.get("type", "")
        node_types[node_type] = node_types.get(node_type, 0) + 1

    summary = f"Node-RED project: {len(tabs)} tabs, {len(nodes)} nodes, {len(subflows)} subflows"
    stats = {
        "tabCount": len(tabs),
        "nodeCount": len(nodes),
        "subflowCount": len(subflows),
        "nodeTypes": node_types,
    }

    return FlowList(flows=raw_flows, tabs=tabs, summary=summary, statistics=stats)


def _build_flow_summary(raw_flows: list[dict]) -> FlowSummary:
    """Build FlowSummary with grouped data and statistics."""
    tabs = [f for f in raw_flows if f.get("type") == "tab"]
    nodes = [f for f in raw_flows if f.get("type") not in ("tab", "subflow")]
    subflows = [f for f in raw_flows if f.get("type") == "subflow"]

    node_types: dict[str, int] = {}
    for node in nodes:
        node_type = node.get("type", "")
        node_types[node_type] = node_types.get(node_type, 0) + 1

    summary = f"Node-RED project: {len(tabs)} tabs, {len(nodes)} nodes, {len(subflows)} subflows"
    stats = {
        "tabCount": len(tabs),
        "nodeCount": len(nodes),
        "subflowCount": len(subflows),
        "nodeTypes": node_types,
    }
    data = {"tabs": tabs, "nodes": nodes, "subflows": subflows}

    return FlowSummary(summary=summary, statistics=stats, data=data)


@mcp.tool()
async def get_flows() -> FlowList:
    """Get all flows with summary statistics.

    Returns:
        FlowList with flows grouped into tabs/nodes/subflows and summary stats.
    """
    client = get_client()
    raw_flows = await client.get_flows()
    return _build_flow_list(raw_flows)


@mcp.tool()
async def update_flows(flows_json: str, deployment_type: str = "full") -> str:
    """Update all flows with deployment type.

    Args:
        flows_json: Flow configuration as JSON string
        deployment_type: Deployment type - valid values: full, nodes, flows, reload (default: full)

    Returns:
        Confirmation message.
    """
    client = get_client()
    flows = json.loads(flows_json)
    await client.update_flows(flows, deployment_type=deployment_type)
    return f"Flows updated with deployment type: {deployment_type}"


@mcp.tool()
async def get_flow(flow_id: str) -> Flow:
    """Get a single flow by ID.

    Args:
        flow_id: Flow ID

    Returns:
        Flow with nodes, configs, and subflows.
    """
    client = get_client()
    raw_flow = await client.get_flow(flow_id)
    return Flow.from_api(raw_flow)


@mcp.tool()
async def update_flow(flow_id: str, flow_json: str) -> str:
    """Update a single flow.

    Args:
        flow_id: Flow ID
        flow_json: Flow configuration as JSON string

    Returns:
        Confirmation message.
    """
    client = get_client()
    flow = json.loads(flow_json)
    await client.update_flow(flow_id, flow)
    result = f"Flow {flow_id} updated"

    # Auto-lint: re-fetch the flow and check layout
    from nodered_mcp.tools.layout import _lint_nodes, format_lint_report

    raw_flow = await client.get_flow(flow_id)
    report = _lint_nodes(raw_flow.get("nodes", []))
    result += format_lint_report(report)
    return result


@mcp.tool()
async def list_tabs() -> list[FlowTab]:
    """List all flow tabs.

    Returns:
        List of FlowTab objects (workspaces).
    """
    client = get_client()
    raw_flows = await client.get_flows()
    tabs = [f for f in raw_flows if f.get("type") == "tab"]
    return [FlowTab.from_api(t) for t in tabs]


@mcp.tool()
async def create_flow(flow_json: str) -> FlowCreateResult:
    """Create a new flow.

    Args:
        flow_json: Flow configuration as JSON string

    Returns:
        FlowCreateResult with the new flow ID.
    """
    client = get_client()
    flow = json.loads(flow_json)
    result = await client.create_flow(flow)
    return FlowCreateResult.from_api(result)


@mcp.tool()
async def delete_flow(flow_id: str) -> str:
    """Delete a flow.

    Args:
        flow_id: Flow ID to delete

    Returns:
        Confirmation message.
    """
    client = get_client()
    await client.delete_flow(flow_id)
    return f"Flow {flow_id} deleted"


@mcp.tool()
async def get_flows_state() -> FlowState:
    """Get the current flows runtime state.

    Returns:
        FlowState with current state (start/stop).
    """
    client = get_client()
    raw_state = await client.get_flows_state()
    return FlowState.from_api(raw_state)


@mcp.tool()
async def set_flows_state(state: str) -> FlowState:
    """Set the flows runtime state.

    Args:
        state: Target state - valid values: start, stop

    Returns:
        FlowState with new state.
    """
    client = get_client()
    raw_state = await client.set_flows_state(state)
    return FlowState.from_api(raw_state)


@mcp.tool()
async def get_flows_formatted() -> FlowSummary:
    """Get flows with formatted summary and grouped data.

    Returns:
        FlowSummary with tabs/nodes/subflows grouped and counted.
    """
    client = get_client()
    raw_flows = await client.get_flows()
    return _build_flow_summary(raw_flows)


@mcp.tool()
async def visualize_flows() -> str:
    """Visualize flow structure as markdown with per-tab breakdown.

    Returns:
        Markdown-formatted flow structure showing node counts and types per tab.
    """
    client = get_client()
    raw_flows = await client.get_flows()

    tabs = [f for f in raw_flows if f.get("type") == "tab"]
    nodes_by_tab: dict[str, list[dict]] = {}

    for tab in tabs:
        tab_id = tab.get("id", "")
        nodes_by_tab[tab_id] = [f for f in raw_flows if f.get("z") == tab_id]

    output = ["# Node-RED Flow Structure", "", "## Tabs", ""]

    for tab in tabs:
        tab_id = tab.get("id", "")
        tab_name = tab.get("label") or tab.get("name") or "Unnamed"
        nodes = nodes_by_tab.get(tab_id, [])

        node_types: dict[str, int] = {}
        for node in nodes:
            node_type = node.get("type", "")
            node_types[node_type] = node_types.get(node_type, 0) + 1

        node_types_str = ", ".join(f"{t}: {c}" for t, c in node_types.items())

        output.append(f"### {tab_name} (ID: {tab_id})")
        output.append(f"- Number of nodes: {len(nodes)}")
        output.append(f"- Node types: {node_types_str}")
        output.append("")

    return "\n".join(output)


def _apply_patch_ops(flow: dict, operations: list[dict]) -> tuple[dict, list[str]]:
    """Apply patch operations to a flow dict.

    Returns:
        Tuple of (modified_flow, log_messages).
    """
    log: list[str] = []

    for op_def in operations:
        op = op_def.get("op", "")

        if op == "remove_nodes":
            ids_to_remove = set(op_def["ids"])
            before = len(flow.get("nodes", []))
            flow["nodes"] = [n for n in flow.get("nodes", []) if n.get("id") not in ids_to_remove]
            removed = before - len(flow["nodes"])
            # Clean wires referencing removed nodes
            for node in flow.get("nodes", []):
                if "wires" in node:
                    node["wires"] = [
                        [w for w in output if w not in ids_to_remove]
                        for output in node["wires"]
                    ]
            log.append(f"removed {removed} nodes")

        elif op == "add_nodes":
            nodes = op_def["nodes"]
            flow_id = flow.get("id", "")
            for node in nodes:
                node.setdefault("z", flow_id)
            flow.setdefault("nodes", []).extend(nodes)
            log.append(f"added {len(nodes)} nodes")

        elif op == "update_node":
            target_id = op_def["id"]
            fields = op_def["set"]
            for node in flow.get("nodes", []):
                if node.get("id") == target_id:
                    node.update(fields)
                    log.append(f"updated node {target_id}")
                    break
            else:
                log.append(f"node {target_id} not found")

        elif op == "rewire":
            target_id = op_def["id"]
            output_idx = op_def["output"]
            targets = op_def["targets"]
            mode = op_def.get("mode", "replace")
            for node in flow.get("nodes", []):
                if node.get("id") == target_id:
                    wires = node.setdefault("wires", [])
                    while len(wires) <= output_idx:
                        wires.append([])
                    if mode == "append":
                        wires[output_idx] = [
                            w for w in wires[output_idx] if w not in targets
                        ] + targets
                    else:
                        wires[output_idx] = targets
                    log.append(f"rewired node {target_id} output {output_idx}")
                    break
            else:
                log.append(f"node {target_id} not found")

        elif op == "set_label":
            old = flow.get("label", "")
            flow["label"] = op_def["label"]
            log.append(f"label: '{old}' -> '{op_def['label']}'")

        elif op == "set_info":
            flow["info"] = op_def["info"]
            log.append("info updated")

        elif op == "set_disabled":
            flow["disabled"] = op_def["disabled"]
            state = "disabled" if op_def["disabled"] else "enabled"
            log.append(f"flow {state}")

        else:
            raise ValueError(f"Unknown patch op: {op}")

    return flow, log


@mcp.tool()
async def patch_flow(flow_id: str, operations: str) -> str:
    """Apply incremental patch operations to a flow.

    Fetches the current flow, applies operations, and updates it.
    Much more efficient than update_flow for small changes.

    Args:
        flow_id: Flow ID to patch
        operations: JSON array of patch operations. Supported ops:
            - {"op": "remove_nodes", "ids": ["nodeId1", ...]}
            - {"op": "add_nodes", "nodes": [{node}, ...]}
            - {"op": "update_node", "id": "nodeId", "set": {"name": "New", ...}}
            - {"op": "rewire", "id": "nodeId", "output": 0, "targets": ["id1", ...], "mode": "replace|append"}
            - {"op": "set_label", "label": "New Name"}
            - {"op": "set_info", "info": "Description text"}
            - {"op": "set_disabled", "disabled": true}

    Returns:
        Summary of changes applied.
    """
    client = get_client()
    raw_flow = await client.get_flow(flow_id)
    ops = json.loads(operations)
    patched_flow, log = _apply_patch_ops(raw_flow, ops)
    await client.update_flow(flow_id, patched_flow)
    result = f"Flow {flow_id} patched: " + "; ".join(log)

    # Auto-lint: check layout of the patched flow (already in memory)
    from nodered_mcp.tools.layout import _lint_nodes, format_lint_report

    report = _lint_nodes(patched_flow.get("nodes", []))
    result += format_lint_report(report)
    return result

"""Node management tools for Node-RED."""

import json

from nodered_mcp.client import get_client
from nodered_mcp.models.node import NodeModule, NodeSet
from nodered_mcp.models.flow import Node
from nodered_mcp.server import mcp


@mcp.tool()
async def inject(node_id: str) -> str:
    """Trigger an inject node.

    Args:
        node_id: Inject node ID to trigger

    Returns:
        Confirmation message.
    """
    client = get_client()
    await client.inject(node_id)
    return f"Inject node {node_id} triggered"


@mcp.tool()
async def get_nodes() -> list[NodeSet]:
    """Get list of installed node modules.

    Returns:
        List of NodeSet objects with node types and versions.
    """
    client = get_client()
    raw_nodes = await client.get_nodes()
    return [NodeSet.from_api(n) for n in raw_nodes]


@mcp.tool()
async def get_node_info(module: str) -> NodeModule:
    """Get information about a specific node module.

    Args:
        module: Node module name

    Returns:
        NodeModule with version and node sets.
    """
    client = get_client()
    raw_info = await client.get_node_info(module)
    return NodeModule.from_api(raw_info)


@mcp.tool()
async def toggle_node_module(module: str, enabled: bool) -> NodeModule:
    """Enable or disable a node module.

    Args:
        module: Node module name
        enabled: True to enable, False to disable

    Returns:
        Updated NodeModule object.
    """
    client = get_client()
    raw_module = await client.toggle_node_module(module, enabled)
    return NodeModule.from_api(raw_module)


@mcp.tool()
async def find_nodes_by_type(node_type: str) -> list[Node]:
    """Find all nodes of a specific type.

    Args:
        node_type: Node type to search for

    Returns:
        List of matching Node objects.
    """
    client = get_client()
    raw_flows = await client.get_flows()
    matches = [
        f for f in raw_flows
        if f.get("type") == node_type and node_type not in ("tab", "subflow")
    ]
    return [Node.from_api(n) for n in matches]


@mcp.tool()
async def search_nodes(query: str, property: str | None = None) -> list[Node]:
    """Search for nodes by name or properties.

    Args:
        query: String to search for in node properties
        property: Specific property to search (optional, searches all properties if not specified)

    Returns:
        List of matching Node objects.
    """
    client = get_client()
    raw_flows = await client.get_flows()

    matches = []
    for node in raw_flows:
        if property:
            if property in node and query in str(node.get(property, "")):
                matches.append(node)
        else:
            if query in json.dumps(node):
                matches.append(node)

    return [Node.from_api(n) for n in matches]

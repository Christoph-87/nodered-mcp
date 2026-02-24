"""Utility tools for Node-RED MCP server."""

from nodered_mcp.server import mcp


@mcp.tool()
async def api_help() -> str:
    """Get Node-RED API endpoint reference with implementation status.

    Returns:
        Markdown table of API endpoints and their MCP implementation status.
    """
    endpoints = [
        ("GET", "/flows", "Get all flows", True),
        ("POST", "/flows", "Update all flows", True),
        ("GET", "/flow/:id", "Get a specific flow", True),
        ("PUT", "/flow/:id", "Update a specific flow", True),
        ("DELETE", "/flow/:id", "Delete a specific flow", True),
        ("POST", "/flow", "Create a new flow", True),
        ("GET", "/flows/state", "Get the state of flows", True),
        ("POST", "/flows/state", "Set the state of flows", True),
        ("GET", "/nodes", "Get list of installed nodes", True),
        ("POST", "/nodes", "Install a new node module", False),
        ("GET", "/settings", "Get runtime settings", True),
        ("GET", "/diagnostics", "Get diagnostics information", True),
        ("POST", "/inject/:id", "Trigger an inject node", True),
    ]

    output = [
        "# Node-RED API Help",
        "",
        "| Method | Path | Description | Implemented in MCP |",
        "|--------|------|-------------|---------------------|",
    ]

    for method, path, description, implemented in endpoints:
        status = "✅" if implemented else "❌"
        output.append(f"| {method} | {path} | {description} | {status} |")

    return "\n".join(output)

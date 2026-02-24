"""FastMCP server for Node-RED operations."""

import logging

from fastmcp import FastMCP

from nodered_mcp.client import initialize_client
from nodered_mcp.config import get_config

logger = logging.getLogger(__name__)

# Create the MCP server
mcp = FastMCP(
    name="nodered-mcp",
    instructions="""Node-RED MCP server providing comprehensive access to Node-RED flows, nodes, and settings.
    Supports reading/updating flows, managing nodes, runtime control, and diagnostics.
    Responses are optimized for AI consumption with structured data and clear error messages.""",
)

# Load configuration and initialize client
config = get_config()
initialize_client(config)
logger.info(
    "Initialized Node-RED client for %s (API version: %s)",
    config.url,
    config.api_version,
)

# Import all tool modules - tools are registered via @mcp.tool() decorators
from nodered_mcp.tools import flows  # noqa: F401, E402
from nodered_mcp.tools import nodes  # noqa: F401, E402
from nodered_mcp.tools import settings  # noqa: F401, E402
from nodered_mcp.tools import utility  # noqa: F401, E402
from nodered_mcp.tools import layout  # noqa: F401, E402


def main():
    """Run the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()

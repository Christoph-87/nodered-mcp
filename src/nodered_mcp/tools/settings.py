"""Settings and diagnostics tools for Node-RED."""

from nodered_mcp.client import get_client
from nodered_mcp.models.responses import DiagnosticsResult, Settings
from nodered_mcp.server import mcp


@mcp.tool()
async def get_settings() -> Settings:
    """Get Node-RED runtime settings.

    Returns:
        Settings with runtime configuration.
    """
    client = get_client()
    raw_settings = await client.get_settings()
    return Settings.from_api(raw_settings)


@mcp.tool()
async def get_diagnostics() -> DiagnosticsResult:
    """Get Node-RED diagnostics information.

    Returns:
        DiagnosticsResult with system diagnostics data.
    """
    client = get_client()
    raw_diagnostics = await client.get_diagnostics()
    return DiagnosticsResult(data=raw_diagnostics)

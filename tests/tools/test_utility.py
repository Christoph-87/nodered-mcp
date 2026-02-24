"""Tests for utility tools."""

import pytest


@pytest.mark.asyncio
class TestApiHelp:
    async def test_api_help_returns_string(self) -> None:
        from nodered_mcp.tools.utility import api_help

        result = await api_help.fn()

        # Should return markdown/text string
        assert isinstance(result, str)
        assert len(result) > 0

    async def test_api_help_contains_endpoints(self) -> None:
        from nodered_mcp.tools.utility import api_help

        result = await api_help.fn()

        # Should document key API endpoints
        assert "/flows" in result
        assert "/flow" in result
        assert "/nodes" in result
        assert "/settings" in result

    async def test_api_help_contains_http_methods(self) -> None:
        from nodered_mcp.tools.utility import api_help

        result = await api_help.fn()

        # Should mention HTTP methods
        assert "GET" in result
        assert "POST" in result or "PUT" in result or "DELETE" in result

    async def test_api_help_no_client_call(self, mock_client) -> None:
        """Verify api_help doesn't call the client (it's static content)."""
        from nodered_mcp.tools.utility import api_help

        await api_help.fn()

        # Should not have called any client methods
        mock_client.get_flows.assert_not_called()
        mock_client.get_settings.assert_not_called()
        mock_client.get_nodes.assert_not_called()

"""Tests for settings tools."""

import pytest

from nodered_mcp.client import NodeRedClient


@pytest.mark.asyncio
class TestGetSettings:
    async def test_get_settings(self, mock_client: NodeRedClient) -> None:
        from nodered_mcp.tools.settings import get_settings

        result = await get_settings.fn()

        # Should return Settings model
        from nodered_mcp.models.responses import Settings
        assert isinstance(result, Settings)
        assert result.http_node_root != ""
        assert result.version != ""
        mock_client.get_settings.assert_called_once()

    async def test_get_settings_with_user(self, mock_client: NodeRedClient) -> None:
        from nodered_mcp.tools.settings import get_settings

        result = await get_settings.fn()

        # User field should be populated from sample data
        assert result.user is not None
        assert "username" in result.user


@pytest.mark.asyncio
class TestGetDiagnostics:
    async def test_get_diagnostics(self, mock_client: NodeRedClient) -> None:
        from nodered_mcp.tools.settings import get_diagnostics

        result = await get_diagnostics.fn()

        # Should return DiagnosticsResult wrapping data
        from nodered_mcp.models.responses import DiagnosticsResult
        assert isinstance(result, DiagnosticsResult)
        assert isinstance(result.data, dict)
        assert len(result.data) > 0
        mock_client.get_diagnostics.assert_called_once()

    async def test_get_diagnostics_preserves_structure(self, mock_client: NodeRedClient) -> None:
        from nodered_mcp.tools.settings import get_diagnostics

        result = await get_diagnostics.fn()

        # Nested structure from sample_diagnostics_data should be preserved
        assert "report" in result.data
        assert "versions" in result.data["report"]

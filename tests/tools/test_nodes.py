"""Tests for node tools."""

import pytest

from nodered_mcp.client import NodeRedClient


@pytest.mark.asyncio
class TestInject:
    async def test_inject(self, mock_client: NodeRedClient) -> None:
        from nodered_mcp.tools.nodes import inject

        result = await inject.fn("inject1")

        # Should return confirmation string
        assert isinstance(result, str)
        assert "inject" in result.lower() or "triggered" in result.lower()
        mock_client.inject.assert_called_once_with("inject1")


@pytest.mark.asyncio
class TestGetNodes:
    async def test_get_nodes(self, mock_client: NodeRedClient) -> None:
        from nodered_mcp.tools.nodes import get_nodes

        result = await get_nodes.fn()

        # Should return list of NodeSet
        assert isinstance(result, list)
        from nodered_mcp.models.node import NodeSet
        assert all(isinstance(ns, NodeSet) for ns in result)
        assert len(result) > 0
        mock_client.get_nodes.assert_called_once()


@pytest.mark.asyncio
class TestGetNodeInfo:
    async def test_get_node_info(self, mock_client: NodeRedClient) -> None:
        from nodered_mcp.tools.nodes import get_node_info

        result = await get_node_info.fn("node-red-contrib-test")

        # Should return NodeModule
        from nodered_mcp.models.node import NodeModule
        assert isinstance(result, NodeModule)
        assert result.name != ""
        mock_client.get_node_info.assert_called_once_with("node-red-contrib-test")


@pytest.mark.asyncio
class TestToggleNodeModule:
    async def test_toggle_node_module_enable(self, mock_client: NodeRedClient) -> None:
        from nodered_mcp.tools.nodes import toggle_node_module

        result = await toggle_node_module.fn("node-red-contrib-test", enabled=True)

        # Should return NodeModule (actual API response)
        from nodered_mcp.models.node import NodeModule
        assert isinstance(result, NodeModule)
        mock_client.toggle_node_module.assert_called_once_with(
            "node-red-contrib-test", True
        )

    async def test_toggle_node_module_disable(self, mock_client: NodeRedClient) -> None:
        from nodered_mcp.tools.nodes import toggle_node_module

        result = await toggle_node_module.fn("node-red-contrib-test", enabled=False)

        from nodered_mcp.models.node import NodeModule
        assert isinstance(result, NodeModule)
        mock_client.toggle_node_module.assert_called_once_with(
            "node-red-contrib-test", False
        )


@pytest.mark.asyncio
class TestFindNodesByType:
    async def test_find_nodes_by_type(self, mock_client: NodeRedClient) -> None:
        from nodered_mcp.tools.nodes import find_nodes_by_type

        result = await find_nodes_by_type.fn("inject")

        # Should return list of Node (filtered from flow data)
        assert isinstance(result, list)
        from nodered_mcp.models.flow import Node
        assert all(isinstance(n, Node) for n in result)
        # Sample data has 2 inject nodes
        assert len(result) == 2
        assert all(n.type == "inject" for n in result)
        mock_client.get_flows.assert_called_once()

    async def test_find_nodes_by_type_no_matches(self, mock_client: NodeRedClient) -> None:
        from nodered_mcp.tools.nodes import find_nodes_by_type

        result = await find_nodes_by_type.fn("nonexistent-type")

        assert isinstance(result, list)
        assert len(result) == 0


@pytest.mark.asyncio
class TestSearchNodes:
    async def test_search_nodes_by_name(self, mock_client: NodeRedClient) -> None:
        from nodered_mcp.tools.nodes import search_nodes

        result = await search_nodes.fn("Test")

        # Should return list of Node matching query
        assert isinstance(result, list)
        from nodered_mcp.models.flow import Node
        assert all(isinstance(n, Node) for n in result)
        # Should find nodes with "Test" in name
        assert len(result) > 0
        mock_client.get_flows.assert_called_once()

    async def test_search_nodes_by_type(self, mock_client: NodeRedClient) -> None:
        from nodered_mcp.tools.nodes import search_nodes

        result = await search_nodes.fn("inject")

        # Should match nodes with "inject" in type or name
        assert isinstance(result, list)
        assert len(result) > 0

    async def test_search_nodes_no_matches(self, mock_client: NodeRedClient) -> None:
        from nodered_mcp.tools.nodes import search_nodes

        result = await search_nodes.fn("NONEXISTENT_QUERY_STRING")

        assert isinstance(result, list)
        assert len(result) == 0

    async def test_search_nodes_case_insensitive(self, mock_client: NodeRedClient) -> None:
        from nodered_mcp.tools.nodes import search_nodes

        result = await search_nodes.fn("test")

        # Should match regardless of case
        assert isinstance(result, list)
        assert len(result) > 0

"""Tests for flow tools."""

import json

import pytest

from nodered_mcp.client import NodeRedClient


@pytest.mark.asyncio
class TestGetFlows:
    async def test_get_flows(self, mock_client: NodeRedClient) -> None:
        from nodered_mcp.tools.flows import get_flows

        result = await get_flows.fn()

        # Should return FlowList with flows and tabs separated
        from nodered_mcp.models.responses import FlowList
        assert isinstance(result, FlowList)
        assert len(result.flows) > 0
        assert len(result.tabs) > 0
        assert result.summary != ""
        assert "statistics" in result.__dict__
        mock_client.get_flows.assert_called_once()


@pytest.mark.asyncio
class TestUpdateFlows:
    async def test_update_flows_default_deployment(self, mock_client: NodeRedClient) -> None:
        from nodered_mcp.tools.flows import update_flows

        flows_json = json.dumps([{"id": "test", "type": "tab"}])
        result = await update_flows.fn(flows_json)

        assert isinstance(result, str)
        assert "updated" in result.lower() or "success" in result.lower()
        mock_client.update_flows.assert_called_once()
        # Verify default deployment_type is "full"
        call_args = mock_client.update_flows.call_args
        assert call_args[1]["deployment_type"] == "full"

    async def test_update_flows_custom_deployment(self, mock_client: NodeRedClient) -> None:
        from nodered_mcp.tools.flows import update_flows

        flows_json = json.dumps([{"id": "test"}])
        await update_flows.fn(flows_json, deployment_type="nodes")

        call_args = mock_client.update_flows.call_args
        assert call_args[1]["deployment_type"] == "nodes"

    async def test_update_flows_parses_json(self, mock_client: NodeRedClient) -> None:
        from nodered_mcp.tools.flows import update_flows

        flows_json = json.dumps([{"id": "flow1"}, {"id": "flow2"}])
        await update_flows.fn(flows_json)

        # Verify JSON was parsed and passed to client
        call_args = mock_client.update_flows.call_args
        flows_list = call_args[0][0]
        assert isinstance(flows_list, list)
        assert len(flows_list) == 2


@pytest.mark.asyncio
class TestGetFlow:
    async def test_get_flow(self, mock_client: NodeRedClient) -> None:
        from nodered_mcp.tools.flows import get_flow

        result = await get_flow.fn("tab1")

        from nodered_mcp.models.flow import Flow
        assert isinstance(result, Flow)
        assert result.id != ""
        mock_client.get_flow.assert_called_once_with("tab1")


@pytest.mark.asyncio
class TestUpdateFlow:
    async def test_update_flow(self, mock_client: NodeRedClient) -> None:
        from nodered_mcp.tools.flows import update_flow

        flow_json = json.dumps({"id": "tab1", "label": "Updated"})
        result = await update_flow.fn("tab1", flow_json)

        assert isinstance(result, str)
        assert "updated" in result.lower() or "success" in result.lower()
        mock_client.update_flow.assert_called_once()


@pytest.mark.asyncio
class TestListTabs:
    async def test_list_tabs(self, mock_client: NodeRedClient) -> None:
        from nodered_mcp.tools.flows import list_tabs

        result = await list_tabs.fn()

        # Should return list of FlowTab (filtered from heterogeneous array)
        assert isinstance(result, list)
        from nodered_mcp.models.flow import FlowTab
        # All items should be FlowTab instances
        assert all(isinstance(tab, FlowTab) for tab in result)
        # Should have found the tabs from sample data (2 tabs)
        assert len(result) == 2
        mock_client.get_flows.assert_called_once()


@pytest.mark.asyncio
class TestCreateFlow:
    async def test_create_flow(self, mock_client: NodeRedClient) -> None:
        from nodered_mcp.tools.flows import create_flow

        flow_json = json.dumps({"label": "New Flow", "type": "tab"})
        result = await create_flow.fn(flow_json)

        from nodered_mcp.models.responses import FlowCreateResult
        assert isinstance(result, FlowCreateResult)
        assert result.id == "new-flow-id"
        mock_client.create_flow.assert_called_once()


@pytest.mark.asyncio
class TestDeleteFlow:
    async def test_delete_flow(self, mock_client: NodeRedClient) -> None:
        from nodered_mcp.tools.flows import delete_flow

        result = await delete_flow.fn("tab1")

        assert isinstance(result, str)
        assert "deleted" in result.lower() or "success" in result.lower()
        mock_client.delete_flow.assert_called_once_with("tab1")


@pytest.mark.asyncio
class TestGetFlowsState:
    async def test_get_flows_state(self, mock_client: NodeRedClient) -> None:
        from nodered_mcp.tools.flows import get_flows_state

        result = await get_flows_state.fn()

        from nodered_mcp.models.flow import FlowState
        assert isinstance(result, FlowState)
        assert result.state != ""
        mock_client.get_flows_state.assert_called_once()


@pytest.mark.asyncio
class TestSetFlowsState:
    async def test_set_flows_state_start(self, mock_client: NodeRedClient) -> None:
        from nodered_mcp.tools.flows import set_flows_state

        result = await set_flows_state.fn("start")

        from nodered_mcp.models.flow import FlowState
        assert isinstance(result, FlowState)
        mock_client.set_flows_state.assert_called_once_with("start")

    async def test_set_flows_state_stop(self, mock_client: NodeRedClient) -> None:
        from nodered_mcp.tools.flows import set_flows_state

        await set_flows_state.fn("stop")

        mock_client.set_flows_state.assert_called_once_with("stop")


@pytest.mark.asyncio
class TestGetFlowsFormatted:
    async def test_get_flows_formatted(self, mock_client: NodeRedClient) -> None:
        from nodered_mcp.tools.flows import get_flows_formatted

        result = await get_flows_formatted.fn()

        from nodered_mcp.models.responses import FlowSummary
        assert isinstance(result, FlowSummary)
        assert result.summary != ""
        assert "statistics" in result.__dict__
        # Should have grouped data
        assert "data" in result.__dict__
        mock_client.get_flows.assert_called_once()


@pytest.mark.asyncio
class TestVisualizeFlows:
    async def test_visualize_flows(self, mock_client: NodeRedClient) -> None:
        from nodered_mcp.tools.flows import visualize_flows

        result = await visualize_flows.fn()

        # Should return markdown string
        assert isinstance(result, str)
        assert len(result) > 0
        # Should contain tab names from sample data
        assert "Main Flow" in result or "tab" in result.lower()
        mock_client.get_flows.assert_called_once()


@pytest.mark.asyncio
class TestPatchFlow:
    """Tests for patch_flow tool and _apply_patch_ops helper."""

    def _make_flow(self) -> dict:
        """Build a minimal flow dict for patching tests."""
        return {
            "id": "flow1",
            "label": "Test Flow",
            "info": "",
            "disabled": False,
            "nodes": [
                {"id": "n1", "type": "inject", "z": "flow1", "name": "trigger", "wires": [["n2", "n3"]]},
                {"id": "n2", "type": "function", "z": "flow1", "name": "process", "wires": [["n3"]]},
                {"id": "n3", "type": "debug", "z": "flow1", "name": "output", "wires": []},
            ],
            "configs": [],
            "subflows": [],
        }

    async def test_remove_nodes(self, mock_client: NodeRedClient) -> None:
        from nodered_mcp.tools.flows import patch_flow

        flow = self._make_flow()
        mock_client.get_flow.return_value = flow

        ops = json.dumps([{"op": "remove_nodes", "ids": ["n3"]}])
        result = await patch_flow.fn("flow1", ops)

        assert "removed 1 nodes" in result
        call_args = mock_client.update_flow.call_args
        patched = call_args[0][1]
        node_ids = [n["id"] for n in patched["nodes"]]
        assert "n3" not in node_ids
        assert len(patched["nodes"]) == 2

    async def test_remove_nodes_wire_cleanup(self, mock_client: NodeRedClient) -> None:
        from nodered_mcp.tools.flows import patch_flow

        flow = self._make_flow()
        mock_client.get_flow.return_value = flow

        ops = json.dumps([{"op": "remove_nodes", "ids": ["n2"]}])
        await patch_flow.fn("flow1", ops)

        call_args = mock_client.update_flow.call_args
        patched = call_args[0][1]
        # n1 originally wired to ["n2", "n3"] — n2 should be stripped
        n1 = next(n for n in patched["nodes"] if n["id"] == "n1")
        assert n1["wires"] == [["n3"]]

    async def test_add_nodes(self, mock_client: NodeRedClient) -> None:
        from nodered_mcp.tools.flows import patch_flow

        flow = self._make_flow()
        mock_client.get_flow.return_value = flow

        new_node = {"id": "n4", "type": "debug", "name": "new debug", "wires": []}
        ops = json.dumps([{"op": "add_nodes", "nodes": [new_node]}])
        result = await patch_flow.fn("flow1", ops)

        assert "added 1 nodes" in result
        call_args = mock_client.update_flow.call_args
        patched = call_args[0][1]
        n4 = next(n for n in patched["nodes"] if n["id"] == "n4")
        assert n4["z"] == "flow1"
        assert len(patched["nodes"]) == 4

    async def test_update_node(self, mock_client: NodeRedClient) -> None:
        from nodered_mcp.tools.flows import patch_flow

        flow = self._make_flow()
        mock_client.get_flow.return_value = flow

        ops = json.dumps([{"op": "update_node", "id": "n2", "set": {"name": "Renamed", "x": 500}}])
        result = await patch_flow.fn("flow1", ops)

        assert "updated node n2" in result
        call_args = mock_client.update_flow.call_args
        patched = call_args[0][1]
        n2 = next(n for n in patched["nodes"] if n["id"] == "n2")
        assert n2["name"] == "Renamed"
        assert n2["x"] == 500
        assert n2["type"] == "function"  # unchanged

    async def test_update_node_not_found(self, mock_client: NodeRedClient) -> None:
        from nodered_mcp.tools.flows import patch_flow

        flow = self._make_flow()
        mock_client.get_flow.return_value = flow

        ops = json.dumps([{"op": "update_node", "id": "missing", "set": {"name": "X"}}])
        result = await patch_flow.fn("flow1", ops)

        assert "not found" in result

    async def test_rewire(self, mock_client: NodeRedClient) -> None:
        from nodered_mcp.tools.flows import patch_flow

        flow = self._make_flow()
        mock_client.get_flow.return_value = flow

        ops = json.dumps([{"op": "rewire", "id": "n1", "output": 0, "targets": ["n3"]}])
        result = await patch_flow.fn("flow1", ops)

        assert "rewired node n1 output 0" in result
        call_args = mock_client.update_flow.call_args
        patched = call_args[0][1]
        n1 = next(n for n in patched["nodes"] if n["id"] == "n1")
        assert n1["wires"][0] == ["n3"]

    async def test_rewire_append(self, mock_client: NodeRedClient) -> None:
        from nodered_mcp.tools.flows import patch_flow

        flow = self._make_flow()
        mock_client.get_flow.return_value = flow
        # n1 starts with wires [["n2", "n3"]] — append "n4"
        ops = json.dumps([{"op": "rewire", "id": "n1", "output": 0, "targets": ["n4"], "mode": "append"}])
        result = await patch_flow.fn("flow1", ops)

        assert "rewired node n1 output 0" in result
        call_args = mock_client.update_flow.call_args
        patched = call_args[0][1]
        n1 = next(n for n in patched["nodes"] if n["id"] == "n1")
        assert n1["wires"][0] == ["n2", "n3", "n4"]

    async def test_rewire_append_deduplicates(self, mock_client: NodeRedClient) -> None:
        from nodered_mcp.tools.flows import patch_flow

        flow = self._make_flow()
        mock_client.get_flow.return_value = flow
        # n1 starts with wires [["n2", "n3"]] — append "n2" (already present)
        ops = json.dumps([{"op": "rewire", "id": "n1", "output": 0, "targets": ["n2"], "mode": "append"}])
        await patch_flow.fn("flow1", ops)

        call_args = mock_client.update_flow.call_args
        patched = call_args[0][1]
        n1 = next(n for n in patched["nodes"] if n["id"] == "n1")
        assert n1["wires"][0] == ["n3", "n2"]  # n2 moved to end, no duplicate

    async def test_set_label(self, mock_client: NodeRedClient) -> None:
        from nodered_mcp.tools.flows import patch_flow

        flow = self._make_flow()
        mock_client.get_flow.return_value = flow

        ops = json.dumps([{"op": "set_label", "label": "Office Automation"}])
        result = await patch_flow.fn("flow1", ops)

        assert "Office Automation" in result
        call_args = mock_client.update_flow.call_args
        patched = call_args[0][1]
        assert patched["label"] == "Office Automation"

    async def test_set_info(self, mock_client: NodeRedClient) -> None:
        from nodered_mcp.tools.flows import patch_flow

        flow = self._make_flow()
        mock_client.get_flow.return_value = flow

        ops = json.dumps([{"op": "set_info", "info": "Controls lights and fans"}])
        result = await patch_flow.fn("flow1", ops)

        assert "info updated" in result
        call_args = mock_client.update_flow.call_args
        patched = call_args[0][1]
        assert patched["info"] == "Controls lights and fans"

    async def test_set_disabled(self, mock_client: NodeRedClient) -> None:
        from nodered_mcp.tools.flows import patch_flow

        flow = self._make_flow()
        mock_client.get_flow.return_value = flow

        ops = json.dumps([{"op": "set_disabled", "disabled": True}])
        result = await patch_flow.fn("flow1", ops)

        assert "disabled" in result
        call_args = mock_client.update_flow.call_args
        patched = call_args[0][1]
        assert patched["disabled"] is True

    async def test_multiple_ops(self, mock_client: NodeRedClient) -> None:
        from nodered_mcp.tools.flows import patch_flow

        flow = self._make_flow()
        mock_client.get_flow.return_value = flow

        ops = json.dumps([
            {"op": "set_label", "label": "Renamed"},
            {"op": "remove_nodes", "ids": ["n3"]},
            {"op": "update_node", "id": "n1", "set": {"name": "Start"}},
        ])
        result = await patch_flow.fn("flow1", ops)

        assert "Renamed" in result
        assert "removed 1" in result
        assert "updated node n1" in result
        call_args = mock_client.update_flow.call_args
        patched = call_args[0][1]
        assert patched["label"] == "Renamed"
        assert len(patched["nodes"]) == 2
        n1 = next(n for n in patched["nodes"] if n["id"] == "n1")
        assert n1["name"] == "Start"

    async def test_unknown_op(self, mock_client: NodeRedClient) -> None:
        from nodered_mcp.tools.flows import patch_flow

        flow = self._make_flow()
        mock_client.get_flow.return_value = flow

        ops = json.dumps([{"op": "explode"}])
        with pytest.raises(ValueError, match="Unknown patch op: explode"):
            await patch_flow.fn("flow1", ops)

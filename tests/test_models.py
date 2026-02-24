"""Tests for Pydantic data models and their from_api() methods."""

from nodered_mcp.models.flow import Flow, FlowState, FlowTab, Node
from nodered_mcp.models.node import NodeModule, NodeSet
from nodered_mcp.models.responses import (
    DiagnosticsResult,
    FlowCreateResult,
    FlowList,
    FlowSummary,
    Settings,
)


# ── BaseApiModel tests ────────────────────────────────────────────


class TestBaseApiModel:
    def test_from_api_single_dict(self) -> None:
        result = Node.from_api({"id": "test1", "type": "inject"})
        assert isinstance(result, Node)
        assert result.id == "test1"
        assert result.type == "inject"

    def test_from_api_list_of_dicts(self) -> None:
        results = Node.from_api([
            {"id": "n1", "type": "inject"},
            {"id": "n2", "type": "debug"},
        ])
        assert isinstance(results, list)
        assert len(results) == 2
        assert all(isinstance(n, Node) for n in results)


# ── Node model tests ──────────────────────────────────────────────


class TestNode:
    def test_from_api_basic(self) -> None:
        node = Node.from_api({
            "id": "node1",
            "type": "inject",
            "z": "tab1",
            "name": "Test Node",
            "x": 100,
            "y": 200,
            "wires": [["node2"]],
        })
        assert node.id == "node1"
        assert node.type == "inject"
        assert node.z == "tab1"
        assert node.name == "Test Node"
        assert node.x == 100
        assert node.y == 200
        assert node.wires == [["node2"]]

    def test_from_api_preserves_extra_fields(self) -> None:
        """Verify extra='allow' captures type-specific fields."""
        node = Node.from_api({
            "id": "inject1",
            "type": "inject",
            "payload": "test",
            "payloadType": "str",
            "repeat": "",
            "crontab": "",
            "once": False,
            "topic": "test/topic",
        })
        assert node.id == "inject1"
        # Extra fields should be accessible as attributes
        assert hasattr(node, "payload")
        assert node.payload == "test"  # type: ignore[attr-defined]
        assert node.payloadType == "str"  # type: ignore[attr-defined]
        assert node.topic == "test/topic"  # type: ignore[attr-defined]

    def test_from_api_minimal(self) -> None:
        node = Node.from_api({"id": "n1"})
        assert node.id == "n1"
        assert node.type == ""
        assert node.z == ""
        assert node.name == ""
        assert node.wires == []
        assert node.x == 0
        assert node.y == 0

    def test_from_api_list(self) -> None:
        nodes = Node.from_api([
            {"id": "n1", "type": "inject"},
            {"id": "n2", "type": "debug"},
        ])
        assert isinstance(nodes, list)
        assert len(nodes) == 2


# ── FlowTab model tests ───────────────────────────────────────────


class TestFlowTab:
    def test_from_api_complete(self) -> None:
        tab = FlowTab.from_api({
            "id": "tab1",
            "label": "Main Flow",
            "disabled": False,
            "info": "Primary workspace",
        })
        assert tab.id == "tab1"
        assert tab.label == "Main Flow"
        assert tab.disabled is False
        assert tab.info == "Primary workspace"

    def test_from_api_minimal(self) -> None:
        tab = FlowTab.from_api({"id": "tab1"})
        assert tab.id == "tab1"
        assert tab.label == ""
        assert tab.disabled is False
        assert tab.info == ""

    def test_from_api_list(self) -> None:
        tabs = FlowTab.from_api([
            {"id": "tab1", "label": "Flow 1"},
            {"id": "tab2", "label": "Flow 2"},
        ])
        assert isinstance(tabs, list)
        assert len(tabs) == 2


# ── Flow model tests ──────────────────────────────────────────────


class TestFlow:
    def test_from_api_complete(self) -> None:
        flow = Flow.from_api({
            "id": "flow1",
            "label": "Test Flow",
            "nodes": [
                {"id": "n1", "type": "inject"},
                {"id": "n2", "type": "debug"},
            ],
            "configs": [
                {"id": "c1", "type": "mqtt-broker"},
            ],
            "subflows": [],
        })
        assert flow.id == "flow1"
        assert flow.label == "Test Flow"
        assert len(flow.nodes) == 2
        assert isinstance(flow.nodes[0], Node)
        assert len(flow.configs) == 1
        assert isinstance(flow.configs[0], Node)
        assert flow.subflows == []

    def test_from_api_minimal(self) -> None:
        flow = Flow.from_api({"id": "flow1"})
        assert flow.id == "flow1"
        assert flow.label == ""
        assert flow.nodes == []
        assert flow.configs == []
        assert flow.subflows == []

    def test_from_api_with_nested_nodes(self) -> None:
        flow = Flow.from_api({
            "id": "flow1",
            "label": "Test",
            "nodes": [
                {"id": "n1", "type": "inject", "name": "Input"},
            ],
        })
        assert flow.nodes[0].id == "n1"
        assert flow.nodes[0].name == "Input"


# ── FlowState model tests ─────────────────────────────────────────


class TestFlowState:
    def test_from_api_start(self) -> None:
        state = FlowState.from_api({"state": "start"})
        assert state.state == "start"

    def test_from_api_stop(self) -> None:
        state = FlowState.from_api({"state": "stop"})
        assert state.state == "stop"

    def test_from_api_minimal(self) -> None:
        state = FlowState.from_api({})
        assert state.state == ""


# ── NodeSet model tests ───────────────────────────────────────────


class TestNodeSet:
    def test_from_api_complete(self) -> None:
        node_set = NodeSet.from_api({
            "id": "node-red/inject",
            "name": "inject",
            "types": ["inject"],
            "enabled": True,
            "module": "node-red",
            "version": "3.1.0",
        })
        assert node_set.id == "node-red/inject"
        assert node_set.name == "inject"
        assert node_set.types == ["inject"]
        assert node_set.enabled is True
        assert node_set.module == "node-red"
        assert node_set.version == "3.1.0"

    def test_from_api_minimal(self) -> None:
        node_set = NodeSet.from_api({})
        assert node_set.id == ""
        assert node_set.name == ""
        assert node_set.types == []
        assert node_set.enabled is True
        assert node_set.module == ""
        assert node_set.version == ""

    def test_from_api_list(self) -> None:
        node_sets = NodeSet.from_api([
            {"id": "ns1", "name": "test1"},
            {"id": "ns2", "name": "test2"},
        ])
        assert isinstance(node_sets, list)
        assert len(node_sets) == 2


# ── NodeModule model tests ────────────────────────────────────────


class TestNodeModule:
    def test_from_api_complete(self) -> None:
        module = NodeModule.from_api({
            "name": "node-red-contrib-test",
            "version": "1.0.0",
            "nodes": [
                {
                    "id": "test/node1",
                    "name": "node1",
                    "types": ["test-input"],
                    "enabled": True,
                    "module": "node-red-contrib-test",
                    "version": "1.0.0",
                },
            ],
        })
        assert module.name == "node-red-contrib-test"
        assert module.version == "1.0.0"
        assert len(module.nodes) == 1
        assert isinstance(module.nodes[0], NodeSet)
        assert module.nodes[0].name == "node1"

    def test_from_api_with_nested_node_sets(self) -> None:
        module = NodeModule.from_api({
            "name": "test-module",
            "version": "2.0.0",
            "nodes": [
                {"id": "ns1", "name": "set1"},
                {"id": "ns2", "name": "set2"},
            ],
        })
        assert len(module.nodes) == 2
        assert all(isinstance(ns, NodeSet) for ns in module.nodes)

    def test_from_api_minimal(self) -> None:
        module = NodeModule.from_api({})
        assert module.name == ""
        assert module.version == ""
        assert module.nodes == []


# ── Settings model tests ──────────────────────────────────────────


class TestSettings:
    def test_from_api_with_validation_alias(self) -> None:
        """Verify validation_alias converts httpNodeRoot to http_node_root."""
        settings = Settings.from_api({
            "httpNodeRoot": "/api",
            "version": "3.1.0",
            "user": {"username": "admin"},
        })
        assert settings.http_node_root == "/api"
        assert settings.version == "3.1.0"
        assert settings.user == {"username": "admin"}

    def test_from_api_minimal(self) -> None:
        settings = Settings.from_api({})
        assert settings.http_node_root == ""
        assert settings.version == ""
        assert settings.user is None

    def test_from_api_snake_case_direct(self) -> None:
        """Verify snake_case keys also work (populate_by_name=True)."""
        settings = Settings.from_api({
            "http_node_root": "/custom",
            "version": "3.0.0",
        })
        assert settings.http_node_root == "/custom"


# ── DiagnosticsResult model tests ─────────────────────────────────


class TestDiagnosticsResult:
    def test_from_api_with_nested_data(self) -> None:
        diag = DiagnosticsResult.from_api({
            "data": {
                "report": {
                    "versions": {"node-red": "3.1.0"},
                    "platform": {"os": "darwin"},
                },
            }
        })
        assert "report" in diag.data
        assert diag.data["report"]["versions"]["node-red"] == "3.1.0"

    def test_from_api_minimal(self) -> None:
        diag = DiagnosticsResult.from_api({})
        assert diag.data == {}


# ── FlowCreateResult model tests ──────────────────────────────────


class TestFlowCreateResult:
    def test_from_api(self) -> None:
        result = FlowCreateResult.from_api({"id": "new-flow-123"})
        assert result.id == "new-flow-123"

    def test_from_api_minimal(self) -> None:
        result = FlowCreateResult.from_api({})
        assert result.id == ""


# ── FlowList model tests ──────────────────────────────────────────


class TestFlowList:
    def test_from_api_complete(self) -> None:
        flow_list = FlowList.from_api({
            "flows": [{"id": "n1"}, {"id": "n2"}],
            "tabs": [{"id": "tab1"}],
            "summary": "2 flows, 1 tab",
            "statistics": {"total_nodes": 2, "total_tabs": 1},
        })
        assert len(flow_list.flows) == 2
        assert len(flow_list.tabs) == 1
        assert flow_list.summary == "2 flows, 1 tab"
        assert flow_list.statistics["total_nodes"] == 2

    def test_from_api_minimal(self) -> None:
        flow_list = FlowList.from_api({})
        assert flow_list.flows == []
        assert flow_list.tabs == []
        assert flow_list.summary == ""
        assert flow_list.statistics == {}


# ── FlowSummary model tests ───────────────────────────────────────


class TestFlowSummary:
    def test_from_api_complete(self) -> None:
        summary = FlowSummary.from_api({
            "summary": "Total: 5 nodes across 2 tabs",
            "statistics": {"nodes": 5, "tabs": 2},
            "data": {
                "tabs": [{"id": "tab1"}],
                "nodes": [{"id": "n1"}],
            },
        })
        assert summary.summary == "Total: 5 nodes across 2 tabs"
        assert summary.statistics["nodes"] == 5
        assert "tabs" in summary.data

    def test_from_api_minimal(self) -> None:
        summary = FlowSummary.from_api({})
        assert summary.summary == ""
        assert summary.statistics == {}
        assert summary.data == {}

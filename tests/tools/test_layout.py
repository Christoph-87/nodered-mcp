"""Tests for layout linting tools."""

import json

import pytest

from nodered_mcp.client import NodeRedClient
from nodered_mcp.models.layout import LayoutIssue, LayoutReport
from nodered_mcp.tools.layout import _lint_nodes, format_lint_report


class TestLintNodesNoIssues:
    def test_well_spaced_nodes(self) -> None:
        nodes = [
            {"id": "n1", "type": "inject", "name": "A", "x": 100, "y": 100, "wires": [["n2"]]},
            {"id": "n2", "type": "debug", "name": "B", "x": 400, "y": 100, "wires": []},
        ]
        report = _lint_nodes(nodes)

        assert isinstance(report, LayoutReport)
        assert report.issues == []
        assert report.nodes_checked == 2
        assert report.summary == "no issues"


class TestOverlapDetection:
    def test_same_position(self) -> None:
        nodes = [
            {"id": "n1", "type": "inject", "name": "A", "x": 300, "y": 100, "wires": []},
            {"id": "n2", "type": "debug", "name": "B", "x": 300, "y": 100, "wires": []},
        ]
        report = _lint_nodes(nodes)

        assert len(report.issues) == 1
        issue = report.issues[0]
        assert issue.severity == "error"
        assert issue.rule == "overlap"
        assert "n1" in issue.node_ids
        assert "n2" in issue.node_ids
        assert "1 error" in report.summary

    def test_partial_overlap(self) -> None:
        # Nodes 50px apart horizontally (< DEFAULT_NODE_WIDTH=120), same y
        nodes = [
            {"id": "n1", "type": "inject", "name": "A", "x": 100, "y": 100, "wires": []},
            {"id": "n2", "type": "debug", "name": "B", "x": 150, "y": 100, "wires": []},
        ]
        report = _lint_nodes(nodes)

        overlap_issues = [i for i in report.issues if i.rule == "overlap"]
        assert len(overlap_issues) == 1


class TestSpacingDetection:
    def test_nodes_too_close(self) -> None:
        # 130px apart horizontally: > 120 (no overlap) but < 140 (120+20 spacing)
        # Same y so dy=0 < 30+20=50
        nodes = [
            {"id": "n1", "type": "inject", "name": "A", "x": 100, "y": 100, "wires": []},
            {"id": "n2", "type": "debug", "name": "B", "x": 230, "y": 100, "wires": []},
        ]
        report = _lint_nodes(nodes)

        spacing_issues = [i for i in report.issues if i.rule == "spacing"]
        assert len(spacing_issues) == 1
        assert spacing_issues[0].severity == "warning"
        assert "n1" in spacing_issues[0].node_ids
        assert "n2" in spacing_issues[0].node_ids

    def test_no_double_report_with_overlap(self) -> None:
        # Same position: should only get overlap, not also spacing
        nodes = [
            {"id": "n1", "type": "inject", "name": "A", "x": 100, "y": 100, "wires": []},
            {"id": "n2", "type": "debug", "name": "B", "x": 100, "y": 100, "wires": []},
        ]
        report = _lint_nodes(nodes)

        spacing_issues = [i for i in report.issues if i.rule == "spacing"]
        assert len(spacing_issues) == 0


class TestWireCrossing:
    def test_wire_through_node(self) -> None:
        # A at x=100 wires to C at x=500; B sits at x=300 in the middle, same y
        nodes = [
            {"id": "A", "type": "inject", "name": "A", "x": 100, "y": 100, "wires": [["C"]]},
            {"id": "B", "type": "function", "name": "B", "x": 300, "y": 100, "wires": []},
            {"id": "C", "type": "debug", "name": "C", "x": 500, "y": 100, "wires": []},
        ]
        report = _lint_nodes(nodes)

        wire_issues = [i for i in report.issues if i.rule == "wire_crossing"]
        assert len(wire_issues) >= 1
        issue = wire_issues[0]
        assert "B" in issue.node_ids
        assert issue.severity == "warning"

    def test_no_crossing_when_wire_avoids_node(self) -> None:
        # A wires to C; B is far off the path
        nodes = [
            {"id": "A", "type": "inject", "name": "A", "x": 100, "y": 100, "wires": [["C"]]},
            {"id": "B", "type": "function", "name": "B", "x": 300, "y": 500, "wires": []},
            {"id": "C", "type": "debug", "name": "C", "x": 500, "y": 100, "wires": []},
        ]
        report = _lint_nodes(nodes)

        wire_issues = [i for i in report.issues if i.rule == "wire_crossing"]
        assert len(wire_issues) == 0


class TestScopedCheck:
    def test_node_ids_filter(self) -> None:
        # n1 and n2 overlap, n3 is well-separated
        nodes = [
            {"id": "n1", "type": "inject", "name": "A", "x": 100, "y": 100, "wires": []},
            {"id": "n2", "type": "debug", "name": "B", "x": 100, "y": 100, "wires": []},
            {"id": "n3", "type": "function", "name": "C", "x": 500, "y": 500, "wires": []},
        ]
        # Scope to n3 only — should find no issues since n3 doesn't overlap with anyone
        report = _lint_nodes(nodes, node_ids=["n3"])
        assert report.issues == []

    def test_scoped_finds_relevant_issues(self) -> None:
        nodes = [
            {"id": "n1", "type": "inject", "name": "A", "x": 100, "y": 100, "wires": []},
            {"id": "n2", "type": "debug", "name": "B", "x": 100, "y": 100, "wires": []},
        ]
        # Scope to n1 — should still find the overlap with n2
        report = _lint_nodes(nodes, node_ids=["n1"])
        assert len(report.issues) == 1
        assert report.issues[0].rule == "overlap"


class TestSkipsUnplacedNodes:
    def test_nodes_at_origin_skipped(self) -> None:
        nodes = [
            {"id": "n1", "type": "inject", "name": "A", "x": 0, "y": 0, "wires": []},
            {"id": "n2", "type": "debug", "name": "B", "x": 0, "y": 0, "wires": []},
        ]
        report = _lint_nodes(nodes)

        assert report.issues == []
        assert report.nodes_checked == 0

    def test_config_nodes_without_position_skipped(self) -> None:
        nodes = [
            {"id": "n1", "type": "mqtt-broker", "name": "MQTT"},
            {"id": "n2", "type": "inject", "name": "A", "x": 100, "y": 100, "wires": []},
        ]
        report = _lint_nodes(nodes)

        assert report.issues == []
        assert report.nodes_checked == 1


class TestFormatLintReport:
    def test_empty_report(self) -> None:
        report = LayoutReport(issues=[], nodes_checked=5, summary="no issues")
        assert format_lint_report(report) == ""

    def test_report_with_issues(self) -> None:
        report = LayoutReport(
            issues=[
                LayoutIssue(
                    severity="error",
                    rule="overlap",
                    message='"A" and "B" overlap',
                    node_ids=["n1", "n2"],
                ),
            ],
            nodes_checked=2,
            summary="1 error",
        )
        formatted = format_lint_report(report)
        assert "Layout (1 error):" in formatted
        assert "[error] overlap:" in formatted


@pytest.mark.asyncio
class TestLintFlowTool:
    async def test_lint_flow_returns_report(self, mock_client: NodeRedClient) -> None:
        from nodered_mcp.tools.layout import lint_flow

        result = await lint_flow.fn("tab1")

        assert isinstance(result, LayoutReport)
        mock_client.get_flow.assert_called_once_with("tab1")

    async def test_lint_flow_with_node_ids(self, mock_client: NodeRedClient) -> None:
        from nodered_mcp.tools.layout import lint_flow

        mock_client.get_flow.return_value = {
            "id": "tab1",
            "nodes": [
                {"id": "n1", "type": "inject", "name": "A", "x": 100, "y": 100, "wires": []},
                {"id": "n2", "type": "debug", "name": "B", "x": 100, "y": 100, "wires": []},
            ],
            "configs": [],
            "subflows": [],
        }

        # Scoped to n1 — should find overlap
        result = await lint_flow.fn("tab1", node_ids=json.dumps(["n1"]))
        assert len(result.issues) == 1

    async def test_lint_flow_detects_overlap(self, mock_client: NodeRedClient) -> None:
        from nodered_mcp.tools.layout import lint_flow

        mock_client.get_flow.return_value = {
            "id": "flow1",
            "nodes": [
                {"id": "n1", "type": "inject", "name": "A", "x": 200, "y": 200, "wires": []},
                {"id": "n2", "type": "debug", "name": "B", "x": 200, "y": 200, "wires": []},
            ],
            "configs": [],
            "subflows": [],
        }

        result = await lint_flow.fn("flow1")
        assert len(result.issues) == 1
        assert result.issues[0].rule == "overlap"
        assert result.issues[0].severity == "error"

"""Shared test fixtures for nodered_mcp tests."""

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from nodered_mcp.client import NodeRedClient


# ── Sample API data fixtures ──────────────────────────────────────


@pytest.fixture
def sample_flows_data() -> list[dict[str, Any]]:
    """Raw Node-RED flows API response (heterogeneous array of tabs, nodes, subflows)."""
    return [
        # Two tabs
        {
            "id": "tab1",
            "type": "tab",
            "label": "Main Flow",
            "disabled": False,
            "info": "Primary workspace",
        },
        {
            "id": "tab2",
            "type": "tab",
            "label": "Test Flow",
            "disabled": True,
            "info": "",
        },
        # Several nodes of different types
        {
            "id": "inject1",
            "type": "inject",
            "z": "tab1",
            "name": "Test Inject",
            "topic": "",
            "payload": "test",
            "payloadType": "str",
            "repeat": "",
            "crontab": "",
            "once": False,
            "onceDelay": 0.1,
            "x": 100,
            "y": 100,
            "wires": [["function1"]],
        },
        {
            "id": "function1",
            "type": "function",
            "z": "tab1",
            "name": "Process Data",
            "func": "return msg;",
            "outputs": 1,
            "noerr": 0,
            "x": 300,
            "y": 100,
            "wires": [["debug1"]],
        },
        {
            "id": "debug1",
            "type": "debug",
            "z": "tab1",
            "name": "Output",
            "active": True,
            "tosidebar": True,
            "console": False,
            "tostatus": False,
            "complete": "payload",
            "x": 500,
            "y": 100,
            "wires": [],
        },
        {
            "id": "inject2",
            "type": "inject",
            "z": "tab2",
            "name": "Another Inject",
            "payload": "",
            "payloadType": "date",
            "repeat": "",
            "crontab": "",
            "once": False,
            "x": 100,
            "y": 200,
            "wires": [[]],
        },
        # One subflow
        {
            "id": "subflow1",
            "type": "subflow",
            "name": "Test Subflow",
            "info": "",
            "in": [{"x": 50, "y": 50, "wires": [{"id": "sf-node1"}]}],
            "out": [{"x": 250, "y": 50, "wires": [{"id": "sf-node1", "port": 0}]}],
        },
    ]


@pytest.fixture
def sample_flow_data() -> dict[str, Any]:
    """Single flow API response (GET /flow/:id)."""
    return {
        "id": "tab1",
        "label": "Main Flow",
        "nodes": [
            {
                "id": "inject1",
                "type": "inject",
                "name": "Test",
                "x": 100,
                "y": 100,
                "wires": [["debug1"]],
            },
            {
                "id": "debug1",
                "type": "debug",
                "name": "Output",
                "x": 300,
                "y": 100,
                "wires": [],
            },
        ],
        "configs": [],
        "subflows": [],
    }


@pytest.fixture
def sample_node_module_data() -> dict[str, Any]:
    """NodeModule API response (GET /nodes/:module)."""
    return {
        "name": "node-red-contrib-test",
        "version": "1.0.0",
        "nodes": [
            {
                "id": "node-red-contrib-test/test-node",
                "name": "test-node",
                "types": ["test-input", "test-output"],
                "enabled": True,
                "module": "node-red-contrib-test",
                "version": "1.0.0",
            }
        ],
    }


@pytest.fixture
def sample_node_set_data() -> dict[str, Any]:
    """NodeSet API response."""
    return {
        "id": "node-red/inject",
        "name": "inject",
        "types": ["inject"],
        "enabled": True,
        "module": "node-red",
        "version": "3.1.0",
    }


@pytest.fixture
def sample_settings_data() -> dict[str, Any]:
    """Settings API response (GET /settings)."""
    return {
        "httpNodeRoot": "/api",
        "version": "3.1.0",
        "user": {
            "username": "admin",
            "permissions": "*",
        },
        "flowFilePretty": True,
        "editorTheme": {
            "page": {"title": "Node-RED"},
        },
    }


@pytest.fixture
def sample_diagnostics_data() -> dict[str, Any]:
    """Diagnostics API response (GET /diagnostics)."""
    return {
        "report": {
            "versions": {
                "node-red": "3.1.0",
                "nodejs": "18.17.0",
                "npm": "9.6.7",
            },
            "platform": {
                "os": "darwin",
                "arch": "arm64",
                "cpus": 8,
                "mem": 17179869184,
            },
            "modules": {
                "node-red-contrib-test": "1.0.0",
            },
        },
    }


@pytest.fixture
def sample_flows_state_data() -> dict[str, Any]:
    """Flow state API response (GET /flows/state)."""
    return {"state": "start"}


# ── Mock client fixture ───────────────────────────────────────────


@pytest.fixture
def mock_client(
    sample_flows_data: list[dict[str, Any]],
    sample_flow_data: dict[str, Any],
    sample_node_module_data: dict[str, Any],
    sample_node_set_data: dict[str, Any],
    sample_settings_data: dict[str, Any],
    sample_diagnostics_data: dict[str, Any],
    sample_flows_state_data: dict[str, Any],
) -> NodeRedClient:
    """Mock NodeRedClient with all methods stubbed."""
    client = AsyncMock(spec=NodeRedClient)

    # Flow endpoints
    client.get_flows.return_value = sample_flows_data
    client.get_flow.return_value = sample_flow_data
    client.update_flows.return_value = None
    client.update_flow.return_value = None
    client.create_flow.return_value = {"id": "new-flow-id"}
    client.delete_flow.return_value = None
    client.get_flows_state.return_value = sample_flows_state_data
    client.set_flows_state.return_value = sample_flows_state_data

    # Node endpoints
    client.get_nodes.return_value = [sample_node_set_data]
    client.get_node_info.return_value = sample_node_module_data
    client.toggle_node_module.return_value = sample_node_module_data
    client.inject.return_value = None

    # Settings endpoints
    client.get_settings.return_value = sample_settings_data
    client.get_diagnostics.return_value = sample_diagnostics_data

    with (
        patch("nodered_mcp.tools.flows.get_client", return_value=client),
        patch("nodered_mcp.tools.nodes.get_client", return_value=client),
        patch("nodered_mcp.tools.settings.get_client", return_value=client),
        patch("nodered_mcp.tools.layout.get_client", return_value=client),
    ):
        yield client

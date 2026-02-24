"""Flow-related models for Node-RED."""

from pydantic import ConfigDict, Field

from nodered_mcp.models.base import BaseApiModel


class Node(BaseApiModel):
    """Node-RED node.

    Node-RED nodes have many type-specific fields that vary by node type,
    so we use extra="allow" to capture them without strict modeling.
    """

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    id: str = ""
    type: str = ""
    z: str = ""  # parent flow ID
    name: str = ""
    wires: list[list[str]] = Field(default_factory=list)
    x: int = 0
    y: int = 0


class FlowTab(BaseApiModel):
    """Flow tab (workspace) in Node-RED."""

    id: str = ""
    label: str = ""
    disabled: bool = False
    info: str = ""


class Flow(BaseApiModel):
    """Complete flow representation."""

    id: str = ""
    label: str = ""
    nodes: list[Node] = Field(default_factory=list)
    configs: list[Node] = Field(default_factory=list)
    subflows: list[dict] = Field(default_factory=list)


class FlowState(BaseApiModel):
    """Flow state (start/stop)."""

    state: str = ""

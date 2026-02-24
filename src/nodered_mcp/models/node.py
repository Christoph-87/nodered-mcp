"""Node module models for Node-RED."""

from pydantic import Field

from nodered_mcp.models.base import BaseApiModel


class NodeSet(BaseApiModel):
    """Node-RED node set (collection of node types in a module)."""

    id: str = ""
    name: str = ""
    types: list[str] = Field(default_factory=list)
    enabled: bool = True
    module: str = ""
    version: str = ""


class NodeModule(BaseApiModel):
    """Node-RED module containing node sets."""

    name: str = ""
    version: str = ""
    nodes: list[NodeSet] = Field(default_factory=list)

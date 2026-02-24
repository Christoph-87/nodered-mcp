"""Response models for MCP tools.

All MCP tools must return Pydantic models, never dicts.
These models wrap paginated and structured responses.
"""

from typing import Any

from pydantic import Field

from nodered_mcp.models.base import BaseApiModel


class FlowList(BaseApiModel):
    """List of flows with summary statistics."""

    flows: list[Any] = Field(default_factory=list)  # raw flow data (heterogeneous)
    tabs: list[Any] = Field(default_factory=list)  # raw tab data
    summary: str = ""
    statistics: dict = Field(default_factory=dict)


class FlowSummary(BaseApiModel):
    """Formatted flow summary with grouped data."""

    summary: str = ""
    statistics: dict = Field(default_factory=dict)
    data: dict = Field(default_factory=dict)


class FlowCreateResult(BaseApiModel):
    """Result of flow creation."""

    id: str = ""


class Settings(BaseApiModel):
    """Node-RED settings."""

    http_node_root: str = Field("", validation_alias="httpNodeRoot")
    version: str = ""
    user: dict | None = None


class DiagnosticsResult(BaseApiModel):
    """Diagnostics result.

    Thin wrapper - diagnostics response structure is too variable
    for strict modeling.
    """

    data: dict = Field(default_factory=dict)

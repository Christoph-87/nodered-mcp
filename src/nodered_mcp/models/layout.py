"""Layout lint result models for Node-RED flow visualization."""

from nodered_mcp.models.base import BaseApiModel


class LayoutIssue(BaseApiModel):
    """A single layout issue found by the linter."""

    severity: str = ""  # "error" | "warning"
    rule: str = ""  # "overlap" | "spacing" | "wire_crossing"
    message: str = ""
    node_ids: list[str] = []


class LayoutReport(BaseApiModel):
    """Layout lint report for a flow."""

    issues: list[LayoutIssue] = []
    nodes_checked: int = 0
    summary: str = ""

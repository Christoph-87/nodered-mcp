"""Layout linting tools for Node-RED flows."""

import json

from nodered_mcp.client import get_client
from nodered_mcp.models.layout import LayoutIssue, LayoutReport
from nodered_mcp.server import mcp

# Node-RED default node dimensions (px)
DEFAULT_NODE_WIDTH = 120
DEFAULT_NODE_HEIGHT = 30
MIN_SPACING = 20  # minimum gap between nodes (matches Node-RED grid)


def _is_placed(node: dict) -> bool:
    """Check if a node has a meaningful position (not unplaced/config)."""
    x = node.get("x", 0)
    y = node.get("y", 0)
    return not (x == 0 and y == 0)


def _node_label(node: dict) -> str:
    """Get a human-readable label for a node."""
    return node.get("name") or node.get("type") or node.get("id", "?")


def _segment_intersects_aabb(
    x1: float, y1: float, x2: float, y2: float,
    bx: float, by: float, bw: float, bh: float,
) -> bool:
    """Test if line segment (x1,y1)→(x2,y2) intersects axis-aligned bounding box.

    The box is centered at (bx, by) with half-widths bw and bh.
    Uses parametric clipping (Liang-Barsky).
    """
    dx = x2 - x1
    dy = y2 - y1

    # Box edges relative to segment origin
    p = [-dx, dx, -dy, dy]
    q = [
        x1 - (bx - bw),
        (bx + bw) - x1,
        y1 - (by - bh),
        (by + bh) - y1,
    ]

    t_enter = 0.0
    t_exit = 1.0

    for pi, qi in zip(p, q):
        if pi == 0:
            if qi < 0:
                return False
        else:
            t = qi / pi
            if pi < 0:
                t_enter = max(t_enter, t)
            else:
                t_exit = min(t_exit, t)
            if t_enter > t_exit:
                return False

    return True


def _lint_nodes(nodes: list[dict], node_ids: list[str] | None = None) -> LayoutReport:
    """Run layout lint checks on a list of raw node dicts.

    Args:
        nodes: Raw node dicts (from client).
        node_ids: Optional list of node IDs to scope checks to.
            When provided, only pairs involving at least one specified node
            are checked, and only wires from/to specified nodes are checked.

    Returns:
        LayoutReport with any issues found.
    """
    # Filter to placed nodes only
    placed = [n for n in nodes if _is_placed(n)]
    scope = set(node_ids) if node_ids else None
    issues: list[LayoutIssue] = []
    overlap_pairs: set[tuple[str, str]] = set()

    hw = DEFAULT_NODE_WIDTH / 2
    hh = DEFAULT_NODE_HEIGHT / 2

    # Pairwise checks: overlap and spacing
    for i, a in enumerate(placed):
        aid = a.get("id", "")
        ax, ay = a.get("x", 0), a.get("y", 0)

        for b in placed[i + 1:]:
            bid = b.get("id", "")

            # If scoped, at least one node must be in scope
            if scope and aid not in scope and bid not in scope:
                continue

            bx, by = b.get("x", 0), b.get("y", 0)
            dx = abs(ax - bx)
            dy = abs(ay - by)

            # Overlap: bounding boxes intersect
            if dx < DEFAULT_NODE_WIDTH and dy < DEFAULT_NODE_HEIGHT:
                pair = (min(aid, bid), max(aid, bid))
                overlap_pairs.add(pair)
                issues.append(LayoutIssue(
                    severity="error",
                    rule="overlap",
                    message=(
                        f'"{_node_label(a)}" and "{_node_label(b)}" overlap '
                        f"at ({ax}, {ay}) — separate by at least "
                        f"{DEFAULT_NODE_WIDTH}px horizontally or "
                        f"{DEFAULT_NODE_HEIGHT}px vertically"
                    ),
                    node_ids=[aid, bid],
                ))
            # Spacing: too close but not overlapping
            elif dx < DEFAULT_NODE_WIDTH + MIN_SPACING and dy < DEFAULT_NODE_HEIGHT + MIN_SPACING:
                gap = min(
                    max(dx - DEFAULT_NODE_WIDTH, 0),
                    max(dy - DEFAULT_NODE_HEIGHT, 0),
                )
                issues.append(LayoutIssue(
                    severity="warning",
                    rule="spacing",
                    message=(
                        f'"{_node_label(a)}" and "{_node_label(b)}" are only '
                        f"{gap}px apart at ({ax}, {ay})"
                    ),
                    node_ids=[aid, bid],
                ))

    # Wire-through-node check
    node_by_id = {n.get("id", ""): n for n in placed}
    for node in placed:
        nid = node.get("id", "")
        if scope and nid not in scope:
            continue

        for output_wires in node.get("wires", []):
            for target_id in output_wires:
                target = node_by_id.get(target_id)
                if not target:
                    continue

                # Segment from source right edge to target left edge
                sx = node.get("x", 0) + hw
                sy = node.get("y", 0)
                tx = target.get("x", 0) - hw
                ty = target.get("y", 0)

                # Check against all other placed nodes
                for other in placed:
                    oid = other.get("id", "")
                    if oid in (nid, target_id):
                        continue

                    ox = other.get("x", 0)
                    oy = other.get("y", 0)

                    if _segment_intersects_aabb(sx, sy, tx, ty, ox, oy, hw, hh):
                        issues.append(LayoutIssue(
                            severity="warning",
                            rule="wire_crossing",
                            message=(
                                f'Wire from "{_node_label(node)}" to '
                                f'"{_node_label(target)}" passes through '
                                f'"{_node_label(other)}"'
                            ),
                            node_ids=[nid, target_id, oid],
                        ))

    # Build summary
    error_count = sum(1 for i in issues if i.severity == "error")
    warning_count = sum(1 for i in issues if i.severity == "warning")
    parts = []
    if error_count:
        parts.append(f"{error_count} error{'s' if error_count != 1 else ''}")
    if warning_count:
        parts.append(f"{warning_count} warning{'s' if warning_count != 1 else ''}")
    summary = ", ".join(parts) if parts else "no issues"

    return LayoutReport(
        issues=issues,
        nodes_checked=len(placed),
        summary=summary,
    )


def format_lint_report(report: LayoutReport) -> str:
    """Format a LayoutReport as a human-readable string for appending to tool output."""
    if not report.issues:
        return ""
    lines = [f"\nLayout ({report.summary}):"]
    for issue in report.issues:
        lines.append(f"- [{issue.severity}] {issue.rule}: {issue.message}")
    return "\n".join(lines)


@mcp.tool()
async def lint_flow(flow_id: str, node_ids: str | None = None) -> LayoutReport:
    """Lint a flow's node layout for overlaps, spacing, and wire crossings.

    Args:
        flow_id: Flow ID to lint.
        node_ids: Optional JSON array of node IDs to scope the check.

    Returns:
        LayoutReport with issues, nodes checked count, and summary.
    """
    client = get_client()
    raw_flow = await client.get_flow(flow_id)
    nodes = raw_flow.get("nodes", [])
    scoped_ids = json.loads(node_ids) if node_ids else None
    return _lint_nodes(nodes, scoped_ids)

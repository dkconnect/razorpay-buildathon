"""
Renders the actual implicated subgraph for a selected window: transaction
nodes connected to the device/IP/BIN entities they share. This is built
directly from graph_intelligence.top_community in the pipeline's own
output (Day 4's GraphRingDetector) - not a re-derived approximation, so
what the dashboard shows is exactly what the system saw when it made its
decision.

Same two-layer pattern as every other panel:
1. build_graph_data() - pure function, extracts nodes/edges from a
   WindowFrame. No Plotly/Streamlit dependency, fully unit-testable.
2. build_graph_figure() / render_graph_panel() - thin rendering layer.

Layout: a small bipartite-style graph. Transaction nodes (cyan dots, sized
by amount) connect to entity nodes (devices/IPs/BINs, shown as distinct
shapes/colors) they share. A tight cluster of transactions fanning into
just 1-2 devices/IPs is the visual signature of a ring; a diffuse spread
across many distinct entities is the visual signature of organic traffic
(e.g. a flash sale) - the graph is the point, not decoration.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

TX_COLOR = "#00F0FF"
DEVICE_COLOR = "#ff3b3b"
IP_COLOR = "#ffb300"
BIN_COLOR = "#7c4dff"
EDGE_COLOR = "#333333"
BG_COLOR = "#000000"
TEXT_COLOR = "#e0e0e0"
FONT_FAMILY = "JetBrains Mono, Consolas, monospace"


@dataclass
class GraphNode:
    node_id: str
    node_type: str  # "transaction", "device", "ip", "bin"
    label: str
    size: float
    x: float = 0.0
    y: float = 0.0


@dataclass
class GraphEdge:
    source: str
    target: str


@dataclass
class GraphData:
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    ring_score: float
    community_id: Optional[str]
    transaction_count: int
    has_ring: bool  # False when there's no community to show (empty/quiet window)


def build_graph_data(frame) -> GraphData:
    """
    frame: dashboard.replay.WindowFrame

    Extracts the top community from the window's pipeline result and lays
    it out as a small bipartite graph: one node per transaction ID present
    in the community, one node per distinct shared device/IP/BIN, with an
    edge between a transaction and an entity node whenever that
    transaction's own record shares that entity (looked up from the raw
    transactions in the frame, since top_community only stores the
    aggregate shared-entity SETS, not the per-transaction assignment).
    """
    top_community = (
        frame.pipeline_result.get("graph_intelligence", {}).get("top_community") or {}
    )
    tx_ids = top_community.get("transaction_ids", [])
    ring_score = float(top_community.get("ring_score", 0.0))
    community_id = top_community.get("community_id")

    if not tx_ids:
        return GraphData(
            nodes=[], edges=[], ring_score=0.0, community_id=None,
            transaction_count=0, has_ring=False,
        )

    tx_by_id = {t.get("transaction_id"): t for t in frame.transactions}

    nodes: List[GraphNode] = []
    edges: List[GraphEdge] = []
    seen_entities: Dict[str, str] = {}  # entity value -> node_id

    def entity_node_id(entity_type: str, value: str) -> str:
        key = f"{entity_type}:{value}"
        if key not in seen_entities:
            seen_entities[key] = key
            color_type = {"device": "device", "ip": "ip", "bin": "bin"}[entity_type]
            nodes.append(
                GraphNode(node_id=key, node_type=color_type, label=value, size=10.0)
            )
        return seen_entities[key]

    for tx_id in tx_ids:
        tx = tx_by_id.get(tx_id)
        if tx is None:
            continue
        amount = float(tx.get("amount", 0.0))
        nodes.append(
            GraphNode(
                node_id=tx_id,
                node_type="transaction",
                label=f"₹{amount:,.0f}",
                size=6.0 + min(amount / 2000.0, 14.0),
            )
        )
        if tx.get("device_id"):
            eid = entity_node_id("device", tx["device_id"])
            edges.append(GraphEdge(source=tx_id, target=eid))
        if tx.get("ip_subnet"):
            eid = entity_node_id("ip", tx["ip_subnet"])
            edges.append(GraphEdge(source=tx_id, target=eid))
        if tx.get("card_bin"):
            eid = entity_node_id("bin", tx["card_bin"])
            edges.append(GraphEdge(source=tx_id, target=eid))

    _layout_bipartite(nodes)

    return GraphData(
        nodes=nodes,
        edges=edges,
        ring_score=ring_score,
        community_id=community_id,
        transaction_count=len(tx_ids),
        has_ring=True,
    )


def _layout_bipartite(nodes: List[GraphNode]) -> None:
    """Simple, deterministic circular layout: entity nodes on an outer
    ring, transaction nodes on an inner ring. No physics simulation needed
    for graphs this small (a few dozen nodes at most)."""
    tx_nodes = [n for n in nodes if n.node_type == "transaction"]
    entity_nodes = [n for n in nodes if n.node_type != "transaction"]

    for i, n in enumerate(tx_nodes):
        angle = 2 * math.pi * i / max(1, len(tx_nodes))
        n.x = 1.0 * math.cos(angle)
        n.y = 1.0 * math.sin(angle)

    for i, n in enumerate(entity_nodes):
        angle = 2 * math.pi * i / max(1, len(entity_nodes))
        n.x = 2.2 * math.cos(angle)
        n.y = 2.2 * math.sin(angle)


_NODE_COLORS = {
    "transaction": TX_COLOR,
    "device": DEVICE_COLOR,
    "ip": IP_COLOR,
    "bin": BIN_COLOR,
}


def build_graph_figure(data: GraphData):
    import plotly.graph_objects as go

    fig = go.Figure()

    if not data.has_ring:
        fig.update_layout(
            plot_bgcolor=BG_COLOR, paper_bgcolor=BG_COLOR,
            font=dict(family=FONT_FAMILY, color=TEXT_COLOR, size=11),
            height=380,
            annotations=[
                dict(
                    text="No suspicious cluster in this window",
                    showarrow=False, font=dict(size=13, color="#555555"),
                    xref="paper", yref="paper", x=0.5, y=0.5,
                )
            ],
            xaxis=dict(visible=False), yaxis=dict(visible=False),
        )
        return fig

    node_by_id = {n.node_id: n for n in data.nodes}

    edge_x, edge_y = [], []
    for e in data.edges:
        src, tgt = node_by_id.get(e.source), node_by_id.get(e.target)
        if src is None or tgt is None:
            continue
        edge_x += [src.x, tgt.x, None]
        edge_y += [src.y, tgt.y, None]

    fig.add_trace(
        go.Scatter(
            x=edge_x, y=edge_y, mode="lines",
            line=dict(color=EDGE_COLOR, width=1),
            hoverinfo="skip", showlegend=False,
        )
    )

    for node_type, color in _NODE_COLORS.items():
        group = [n for n in data.nodes if n.node_type == node_type]
        if not group:
            continue
        fig.add_trace(
            go.Scatter(
                x=[n.x for n in group],
                y=[n.y for n in group],
                mode="markers",
                marker=dict(size=[n.size for n in group], color=color, line=dict(width=0)),
                text=[n.label for n in group],
                hoverinfo="text",
                name=node_type.capitalize(),
            )
        )

    fig.update_layout(
        plot_bgcolor=BG_COLOR, paper_bgcolor=BG_COLOR,
        font=dict(family=FONT_FAMILY, color=TEXT_COLOR, size=11),
        legend=dict(orientation="h", y=1.1, bgcolor="rgba(0,0,0,0)"),
        margin=dict(l=10, r=10, t=30, b=10),
        height=380,
        xaxis=dict(visible=False, scaleanchor="y", scaleratio=1),
        yaxis=dict(visible=False),
    )
    return fig


def render_graph_panel(frame, st_module=None) -> None:
    if st_module is None:
        import streamlit as st_module

    data = build_graph_data(frame)
    fig = build_graph_figure(data)

    st_module.markdown("#### RING GRAPH")
    st_module.plotly_chart(fig, use_container_width=True)

    if data.has_ring:
        st_module.caption(
            f"community {data.community_id} — {data.transaction_count} transactions — "
            f"ring_score {data.ring_score:.2f}"
        )
    else:
        st_module.caption("—")
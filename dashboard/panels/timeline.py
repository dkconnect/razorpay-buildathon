"""
Two layers, same pattern as every other module this project:

1. build_timeline_data() - pure function, no Streamlit/Plotly dependency.
   Takes the replay's WindowFrame list and extracts exactly the arrays a
   chart needs. Fully unit-testable without a browser or a running app.

2. render_timeline_panel() - thin Streamlit+Plotly layer that just draws
   what layer 1 already computed. Kept intentionally dumb: if a number on
   the chart looks wrong, the bug is almost certainly in layer 1, where
   it's actually testable.

Design choice: this shows COUNT and MEAN AMOUNT as two lines (not one
combined "volume" number), because that's the actual distinction the
detector is built to notice - Phase 1 (card-testing) is a count spike with
amount flat-or-down, a flash sale is a count spike with amount flat, and
Phase 2 (bust-out) is an amount spike with count flat-or-down. Collapsing
these into one series would hide the exact signal the system is designed
to separate.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

FLAGGED_DECISIONS = ("FLAG_FOR_REVIEW", "HOLD_FOR_REVIEW")

# Terminal theme constants, shared across all dashboard panels.
BG_COLOR = "#000000"
GRID_COLOR = "#1a1a1a"
TEXT_COLOR = "#e0e0e0"
ACCENT_CYAN = "#00F0FF"
COLOR_COUNT = "#e0e0e0"
COLOR_AMOUNT = "#888888"
COLOR_REGIME = "#00F0FF"
COLOR_FLAG = "#ff3b3b"
FONT_FAMILY = "JetBrains Mono, Consolas, monospace"


@dataclass
class TimelineData:
    window_indices: List[int]
    window_labels: List[str]
    transaction_counts: List[int]
    mean_amounts: List[float]
    regime_scores: List[float]
    decisions: List[str]
    changepoint_indices: List[int]  # positions where a real regime shift was flagged


def build_timeline_data(frames: List) -> TimelineData:
    """
    frames: List[dashboard.replay.WindowFrame]

    Extracts one point per window for each series. changepoint_indices
    marks windows where the temporal layer itself flagged a suspicious
    regime (not just where the final decision was non-MONITOR - those can
    differ, since a window might have a live regime alert that the graph
    layer/fusion later downgrades).
    """
    window_indices: List[int] = []
    window_labels: List[str] = []
    transaction_counts: List[int] = []
    mean_amounts: List[float] = []
    regime_scores: List[float] = []
    decisions: List[str] = []
    changepoint_indices: List[int] = []

    for i, frame in enumerate(frames):
        txs = frame.transactions
        result = frame.pipeline_result

        window_indices.append(frame.window_index)
        window_labels.append(frame.window_label)
        transaction_counts.append(len(txs))
        mean_amounts.append(
            round(sum(t["amount"] for t in txs) / len(txs), 2) if txs else 0.0
        )

        temporal = result.get("temporal_regime") or {}
        regime_score = float(temporal.get("regime_score", 0.0))
        regime_scores.append(regime_score)

        decision = result.get("decision", "MONITOR")
        decisions.append(decision)

        if temporal.get("is_suspicious_regime"):
            changepoint_indices.append(i)

    return TimelineData(
        window_indices=window_indices,
        window_labels=window_labels,
        transaction_counts=transaction_counts,
        mean_amounts=mean_amounts,
        regime_scores=regime_scores,
        decisions=decisions,
        changepoint_indices=changepoint_indices,
    )


def build_timeline_figure(data: TimelineData):
    """
    Builds (but does not render) a Plotly figure: dual-axis chart with
    transaction count + mean amount on the left axis pair, regime_score on
    a secondary axis, and vertical markers at every detected changepoint.
    Returns the figure object so it's independently testable (assert on
    figure.data, trace names, etc.) without a running Streamlit app.
    """
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(
        go.Scatter(
            x=data.window_labels,
            y=data.transaction_counts,
            name="Transaction Count",
            line=dict(color=COLOR_COUNT, width=1.5),
            mode="lines",
        ),
        secondary_y=False,
    )

    fig.add_trace(
        go.Scatter(
            x=data.window_labels,
            y=data.mean_amounts,
            name="Mean Amount (₹)",
            line=dict(color=COLOR_AMOUNT, width=1.5, dash="dot"),
            mode="lines",
        ),
        secondary_y=False,
    )

    fig.add_trace(
        go.Scatter(
            x=data.window_labels,
            y=data.regime_scores,
            name="Regime Score",
            line=dict(color=COLOR_REGIME, width=2),
            mode="lines",
            fill="tozeroy",
            fillcolor="rgba(0, 240, 255, 0.08)",
        ),
        secondary_y=True,
    )

    for idx in data.changepoint_indices:
        fig.add_vline(
            x=data.window_labels[idx],
            line=dict(color=COLOR_FLAG, width=1, dash="dash"),
        )

    fig.update_layout(
        plot_bgcolor=BG_COLOR,
        paper_bgcolor=BG_COLOR,
        font=dict(family=FONT_FAMILY, color=TEXT_COLOR, size=11),
        legend=dict(orientation="h", y=1.12, bgcolor="rgba(0,0,0,0)"),
        margin=dict(l=40, r=40, t=40, b=40),
        height=340,
        hovermode="x unified",
    )
    fig.update_xaxes(showgrid=True, gridcolor=GRID_COLOR, tickangle=-45)
    fig.update_yaxes(
        title_text="Count / Amount", showgrid=True, gridcolor=GRID_COLOR,
        secondary_y=False,
    )
    fig.update_yaxes(
        title_text="Regime Score", range=[0, 1], showgrid=False,
        secondary_y=True,
    )

    return fig


def render_timeline_panel(frames: List, st_module=None) -> None:
    """
    Renders the panel into the current Streamlit app. st_module is
    injectable for testing (pass a fake with a no-op plotly_chart) without
    needing a running Streamlit server.
    """
    if st_module is None:
        import streamlit as st_module

    data = build_timeline_data(frames)
    fig = build_timeline_figure(data)

    st_module.markdown("#### TRANSACTION TIMELINE")
    st_module.plotly_chart(fig, use_container_width=True)

    if data.changepoint_indices:
        n = len(data.changepoint_indices)
        st_module.caption(
            f"{n} regime shift{'s' if n != 1 else ''} detected "
            f"(marked in red) — window-level resolution, 30 min each."
        )
    else:
        st_module.caption("No regime shifts detected in this window range.")
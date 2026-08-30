"""
The closing beat: detection-rate-by-volume curve, confusion matrix, and the
₹ P&L statement, pulled from the real numbers Day 6 computed - not
recomputed fresh on every page load (a full sweep takes minutes; nobody
should wait that long just to view a dashboard tab).

Reuses evaluation/generate_report.py's load_or_regenerate() directly rather
than duplicating its file-reading/regeneration logic - this panel is a
thin viewer over what evaluation/ already produces, same as every other
panel is a thin viewer over what detection/ already produces.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

BG_COLOR = "#000000"
GRID_COLOR = "#1a1a1a"
TEXT_COLOR = "#e0e0e0"
ACCENT_CYAN = "#00F0FF"
BAR_LOW = "#ff3b3b"
BAR_HIGH = "#00ff88"
FONT_FAMILY = "JetBrains Mono, Consolas, monospace"


@dataclass
class EvalSummaryData:
    n_scenarios_detection: int
    overall_detection_rate: float
    overall_detected: int
    overall_n: int
    volume_buckets: List[Dict[str, Any]]

    true_positives: int
    false_positives: int
    false_negatives: int
    true_negatives: int

    fraud_saved: float
    false_positive_cost: float
    fraud_missed: float
    net_impact: float

    false_positive_reports: List[Dict[str, Any]] = field(default_factory=list)


def build_eval_summary_data(detection: Dict[str, Any], pnl: Dict[str, Any]) -> EvalSummaryData:
    overall = detection.get("overall_detection_rate", {})
    outcome = pnl.get("outcome", {})
    pnl_result = pnl.get("pnl", {})

    return EvalSummaryData(
        n_scenarios_detection=detection.get("n_scenarios", 0),
        overall_detection_rate=float(overall.get("detection_rate", 0.0)),
        overall_detected=int(overall.get("detected", 0)),
        overall_n=int(overall.get("n", 0)),
        volume_buckets=detection.get("detection_by_phase1_volume", []),
        true_positives=int(outcome.get("true_positives", 0)),
        false_positives=int(outcome.get("false_positives", 0)),
        false_negatives=int(outcome.get("false_negatives", 0)),
        true_negatives=int(outcome.get("true_negatives", 0)),
        fraud_saved=float(pnl_result.get("fraud_saved", 0.0)),
        false_positive_cost=float(pnl_result.get("false_positive_cost", 0.0)),
        fraud_missed=float(pnl_result.get("fraud_missed", 0.0)),
        net_impact=float(pnl_result.get("net_impact", 0.0)),
        false_positive_reports=pnl.get("false_positive_reports", []),
    )


def build_volume_curve_figure(data: EvalSummaryData):
    import plotly.graph_objects as go

    volumes = [b["phase1_volume"] for b in data.volume_buckets]
    rates = [b["detection_rate"] for b in data.volume_buckets]
    ns = [b["n"] for b in data.volume_buckets]

    colors = [
        BAR_LOW if r < 0.6 else ("#ffb300" if r < 0.9 else BAR_HIGH) for r in rates
    ]

    fig = go.Figure(
        go.Bar(
            x=[str(v) for v in volumes],
            y=rates,
            marker_color=colors,
            text=[f"{r:.0%}<br>n={n}" for r, n in zip(rates, ns)],
            textposition="outside",
            textfont=dict(size=10, color=TEXT_COLOR),
        )
    )
    fig.update_layout(
        plot_bgcolor=BG_COLOR, paper_bgcolor=BG_COLOR,
        font=dict(family=FONT_FAMILY, color=TEXT_COLOR, size=11),
        margin=dict(l=40, r=20, t=20, b=40),
        height=300,
        yaxis=dict(range=[0, 1.15], tickformat=".0%", gridcolor=GRID_COLOR,
                   title="Detection Rate"),
        xaxis=dict(title="Phase 1 Transaction Volume", gridcolor=GRID_COLOR),
    )
    return fig


def render_eval_summary_panel(st_module=None, regenerate: bool = False) -> None:
    if st_module is None:
        import streamlit as st_module

    from evaluation.generate_report import load_or_regenerate

    st_module.markdown("#### EVALUATION SUMMARY")

    if st_module.button("Regenerate eval numbers (takes ~2-3 min)"):
        with st_module.spinner("Running fresh sweeps..."):
            detection, pnl = load_or_regenerate(regenerate=True)
        st_module.session_state["eval_detection"] = detection
        st_module.session_state["eval_pnl"] = pnl
    elif "eval_detection" in st_module.session_state:
        detection = st_module.session_state["eval_detection"]
        pnl = st_module.session_state["eval_pnl"]
    else:
        detection, pnl = load_or_regenerate(regenerate=False)
        st_module.session_state["eval_detection"] = detection
        st_module.session_state["eval_pnl"] = pnl

    data = build_eval_summary_data(detection, pnl)

    c1, c2, c3, c4 = st_module.columns(4)
    c1.metric("Detection Rate", f"{data.overall_detection_rate:.0%}",
              f"{data.overall_detected}/{data.overall_n}")
    c2.metric("Fraud Saved", f"₹{data.fraud_saved/1e6:.2f}M")
    c3.metric("FP Cost", f"₹{data.false_positive_cost:,.0f}")
    c4.metric("Net Impact", f"₹{data.net_impact/1e6:.2f}M")

    st_module.markdown("**Detection rate by Phase 1 transaction volume**")
    st_module.caption(
        "The real difficulty axis — ring size alone doesn't control "
        "detection difficulty in this generator (see Day 6 Step 3)."
    )
    fig = build_volume_curve_figure(data)
    st_module.plotly_chart(fig, width="stretch")

    st_module.markdown("**Confusion matrix**")
    st_module.table(
        {
            "Predicted Fraud": [data.true_positives, data.false_positives],
            "Predicted Legitimate": [data.false_negatives, data.true_negatives],
        }
    )
    st_module.caption("Rows: Actually Fraud, Actually Legitimate")

    with st_module.expander("False-positive cost breakdown"):
        for r in data.false_positive_reports:
            st_module.write(
                f"{r['scenario_name']}: {r['flagged_windows']}/{r['total_windows']} "
                f"windows flagged ({r['false_positive_rate']:.1%}) "
                f"→ ₹{r['total_false_positive_cost']:,.2f}"
            )
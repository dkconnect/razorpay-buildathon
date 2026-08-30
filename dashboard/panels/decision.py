"""
Shows the risk-desk numbers (VaR/CVaR), the decision with its full cost
breakdown, reason codes from both the temporal and fusion layers, and a
live audit-trail integrity check against the real hash-chained log Step 1
just wrote (not a mock) - calling AuditTrailLogger.verify_integrity()
directly, so a "Verify Integrity" click in the UI is a real cryptographic
check, not a decorative button.

Same two-layer pattern as every other panel: pure data-prep
(build_decision_data, build_audit_summary), thin Streamlit rendering
(render_decision_panel, render_audit_panel).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

BADGE_COLORS = {
    "MONITOR": "#00ff88",
    "FLAG_FOR_REVIEW": "#ffb300",
    "HOLD_FOR_REVIEW": "#ff3b3b",
}
BG_COLOR = "#000000"
TEXT_COLOR = "#e0e0e0"
MUTED_COLOR = "#888888"
ACCENT_CYAN = "#00F0FF"
FONT_FAMILY = "JetBrains Mono, Consolas, monospace"


@dataclass
class DecisionData:
    decision: str
    badge_color: str
    overall_risk_score: float
    components: Dict[str, float]
    reason_codes: List[str]
    total_window_volume: float
    var_95: float
    cvar_95: float
    implicated_volume: float
    expected_fraud_exposure: float
    expected_costs: Dict[str, float]
    net_savings_vs_monitor: float
    justification: str


def build_decision_data(frame) -> DecisionData:
    """frame: dashboard.replay.WindowFrame"""
    result = frame.pipeline_result

    risk = result.get("risk_assessment", {}) or {}
    temporal = result.get("temporal_regime", {}) or {}
    exposure = result.get("exposure_metrics", {}) or {}
    tail = exposure.get("tail_metrics", {}) or {}
    econ = result.get("decision_economics", {}) or {}

    decision = result.get("decision", "MONITOR")

    # Merge reason codes from both layers, de-duplicated, order-preserving.
    reason_codes: List[str] = []
    for code in list(risk.get("reason_codes", [])) + list(temporal.get("reason_codes", [])):
        if code not in reason_codes:
            reason_codes.append(code)

    return DecisionData(
        decision=decision,
        badge_color=BADGE_COLORS.get(decision, MUTED_COLOR),
        overall_risk_score=float(risk.get("overall_risk_score", 0.0)),
        components=dict(risk.get("components", {})),
        reason_codes=reason_codes,
        total_window_volume=float(exposure.get("total_window_volume", 0.0)),
        var_95=float(tail.get("var_95", 0.0)),
        cvar_95=float(tail.get("cvar_95", 0.0)),
        implicated_volume=float(exposure.get("implicated_volume", 0.0)),
        expected_fraud_exposure=float(exposure.get("expected_fraud_exposure", 0.0)),
        expected_costs=dict(econ.get("expected_costs", {})),
        net_savings_vs_monitor=float(econ.get("net_savings_vs_monitor", 0.0)),
        justification=str(econ.get("justification", "")),
    )


@dataclass
class AuditSummary:
    record_count: int
    integrity_ok: Optional[bool]  # None until checked
    integrity_reason: Optional[str]
    latest_decision: Optional[str]


def build_audit_summary(logger, checked: bool = False) -> AuditSummary:
    """
    logger: dashboard.replay's AuditTrailLogger instance.
    checked: if True, actually runs verify_integrity() (a real, possibly
    non-trivial scan of the whole chain). If False, just reports the record
    count without running the check yet - lets the UI show "N records
    logged" immediately and defer the actual verification to a button
    click, matching a real audit workflow (the log exists whether or not
    anyone has audited it yet).
    """
    record_count = len(logger)
    latest_decision = None
    if record_count > 0:
        records = logger.read_all()
        latest_decision = records[-1]["payload"].get("decision")

    if not checked:
        return AuditSummary(
            record_count=record_count, integrity_ok=None,
            integrity_reason=None, latest_decision=latest_decision,
        )

    report = logger.verify_integrity()
    return AuditSummary(
        record_count=record_count,
        integrity_ok=report.ok,
        integrity_reason=report.reason,
        latest_decision=latest_decision,
    )


def render_decision_panel(frame, st_module=None) -> None:
    if st_module is None:
        import streamlit as st_module

    data = build_decision_data(frame)

    st_module.markdown("#### RISK & DECISION")

    st_module.markdown(
        f"<span style='background-color:{data.badge_color};color:#000;"
        f"padding:3px 10px;border-radius:3px;font-family:{FONT_FAMILY};"
        f"font-weight:bold;font-size:13px'>{data.decision}</span>",
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st_module.columns(3)
    c1.metric("Overall Risk", f"{data.overall_risk_score:.2f}")
    c2.metric("VaR (95%)", f"₹{data.var_95:,.0f}")
    c3.metric("CVaR (95%)", f"₹{data.cvar_95:,.0f}")

    st_module.caption(
        f"regime {data.components.get('regime_score', 0):.2f} · "
        f"ring {data.components.get('ring_score', 0):.2f} · "
        f"escalation {data.components.get('escalation_score', 0):.2f}"
    )

    if data.reason_codes:
        tags = " ".join(
            f"<span style='background:#1a1a1a;color:{ACCENT_CYAN};padding:2px 8px;"
            f"border-radius:10px;font-size:11px;margin-right:4px;font-family:{FONT_FAMILY}'>"
            f"{code}</span>"
            for code in data.reason_codes
        )
        st_module.markdown(tags, unsafe_allow_html=True)

    with st_module.expander("Decision economics"):
        st_module.write(f"Expected fraud exposure: ₹{data.expected_fraud_exposure:,.2f}")
        st_module.write(f"Implicated volume: ₹{data.implicated_volume:,.2f}")
        for action, cost in data.expected_costs.items():
            marker = " ← chosen" if action == data.decision else ""
            st_module.write(f"  {action}: ₹{cost:,.2f}{marker}")
        st_module.write(f"Net savings vs. MONITOR: ₹{data.net_savings_vs_monitor:,.2f}")
        if data.justification:
            st_module.caption(data.justification)


def render_audit_panel(logger, st_module=None) -> None:
    if st_module is None:
        import streamlit as st_module

    st_module.markdown("#### AUDIT TRAIL")

    summary = build_audit_summary(logger, checked=False)
    st_module.write(f"{summary.record_count} records logged (hash-chained)")
    if summary.latest_decision:
        st_module.caption(f"Latest: {summary.latest_decision}")

    if st_module.button("Verify Integrity"):
        checked_summary = build_audit_summary(logger, checked=True)
        if checked_summary.integrity_ok:
            st_module.success(f"Chain verified — {checked_summary.record_count} records, no tampering detected.")
        else:
            st_module.error(f"INTEGRITY FAILURE: {checked_summary.integrity_reason}")
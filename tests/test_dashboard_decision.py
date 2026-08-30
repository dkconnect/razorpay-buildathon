import json

from dashboard.panels.decision import (
    DecisionData,
    build_audit_summary,
    build_decision_data,
)
from dashboard.replay import WindowFrame, get_audit_logger, load_scenario, replay_scenario


def test_build_decision_data_on_flagged_window(tmp_path):
    txs = load_scenario("mixed_fraud")
    frames = replay_scenario(txs, audit_log_path=str(tmp_path / "a.jsonl"))
    flagged = [f for f in frames if f.pipeline_result["decision"] != "MONITOR"]
    assert flagged

    data = build_decision_data(flagged[0])
    assert isinstance(data, DecisionData)
    assert data.decision in ("FLAG_FOR_REVIEW", "HOLD_FOR_REVIEW")
    assert data.badge_color != "#888888"  # a real mapped color, not the fallback
    assert 0.0 <= data.overall_risk_score <= 1.0
    assert data.cvar_95 >= data.var_95 >= 0.0  # CVaR is always >= VaR by definition
    assert data.decision in data.expected_costs


def test_build_decision_data_monitor_window_uses_monitor_badge(tmp_path):
    txs = load_scenario("normal_day")
    frames = replay_scenario(txs, audit_log_path=str(tmp_path / "a.jsonl"))
    quiet = [f for f in frames if f.pipeline_result["decision"] == "MONITOR"]
    assert quiet

    data = build_decision_data(quiet[0])
    assert data.decision == "MONITOR"
    assert data.badge_color == "#00ff88"


def test_build_decision_data_reason_codes_deduplicated(tmp_path):
    """If the same code appears in both risk_assessment and temporal_regime,
    it should only show up once."""
    frame = WindowFrame(
        window_index=0, window_label="00:00 - 00:30", transactions=[],
        pipeline_result={
            "decision": "MONITOR",
            "risk_assessment": {"overall_risk_score": 0.1, "components": {}, "reason_codes": ["A", "B"]},
            "temporal_regime": {"reason_codes": ["B", "C"]},
            "exposure_metrics": {"tail_metrics": {}},
            "decision_economics": {"expected_costs": {}},
        },
        audit_record={},
    )
    data = build_decision_data(frame)
    assert data.reason_codes == ["A", "B", "C"]


def test_build_decision_data_handles_missing_fields_gracefully():
    """A minimal/empty pipeline result shouldn't crash the panel."""
    frame = WindowFrame(
        window_index=0, window_label="00:00 - 00:30", transactions=[],
        pipeline_result={"decision": "MONITOR"},
        audit_record={},
    )
    data = build_decision_data(frame)
    assert data.decision == "MONITOR"
    assert data.overall_risk_score == 0.0
    assert data.cvar_95 == 0.0
    assert data.reason_codes == []


def test_build_audit_summary_unchecked_does_not_run_verification(tmp_path):
    audit_path = str(tmp_path / "a.jsonl")
    txs = load_scenario("normal_day")
    replay_scenario(txs, audit_log_path=audit_path)

    logger = get_audit_logger(audit_log_path=audit_path)
    summary = build_audit_summary(logger, checked=False)
    assert summary.record_count > 0
    assert summary.integrity_ok is None  # not checked yet
    assert summary.latest_decision is not None


def test_build_audit_summary_checked_confirms_clean_chain(tmp_path):
    audit_path = str(tmp_path / "a.jsonl")
    txs = load_scenario("normal_day")
    replay_scenario(txs, audit_log_path=audit_path)

    logger = get_audit_logger(audit_log_path=audit_path)
    summary = build_audit_summary(logger, checked=True)
    assert summary.integrity_ok is True
    assert summary.integrity_reason is None


def test_build_audit_summary_detects_real_tampering(tmp_path):
    """This exercises the actual dashboard code path (not just
    AuditTrailLogger in isolation) against a real tamper attempt."""
    audit_path = tmp_path / "a.jsonl"
    txs = load_scenario("mixed_fraud")
    replay_scenario(txs, audit_log_path=str(audit_path))

    lines = audit_path.read_text().splitlines()
    tampered = json.loads(lines[2])
    tampered["payload"]["decision"] = "TAMPERED"
    lines[2] = json.dumps(tampered)
    audit_path.write_text("\n".join(lines) + "\n")

    logger = get_audit_logger(audit_log_path=str(audit_path))
    summary = build_audit_summary(logger, checked=True)
    assert summary.integrity_ok is False
    assert "sequence 2" in summary.integrity_reason


def test_render_decision_panel_with_fake_streamlit(tmp_path):
    class FakeSt:
        def __init__(self):
            self.calls = []

        def markdown(self, *a, **k):
            self.calls.append("markdown")

        def columns(self, n):
            return [FakeColumn(self) for _ in range(n)]

        def caption(self, *a, **k):
            self.calls.append("caption")

        def write(self, *a, **k):
            self.calls.append("write")

        def expander(self, *a, **k):
            return FakeExpander(self)

    class FakeColumn:
        def __init__(self, parent):
            self.parent = parent

        def metric(self, *a, **k):
            self.parent.calls.append("metric")

    class FakeExpander:
        def __init__(self, parent):
            self.parent = parent

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def write(self, *a, **k):
            self.parent.calls.append("write")

        def caption(self, *a, **k):
            self.parent.calls.append("caption")

    from dashboard.panels.decision import render_decision_panel

    txs = load_scenario("mixed_fraud")
    frames = replay_scenario(txs, audit_log_path=str(tmp_path / "a.jsonl"))
    flagged = [f for f in frames if f.pipeline_result["decision"] != "MONITOR"]

    fake_st = FakeSt()
    render_decision_panel(flagged[0], st_module=fake_st)
    assert "metric" in fake_st.calls
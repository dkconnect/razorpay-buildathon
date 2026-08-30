from dashboard.panels.timeline import (
    TimelineData,
    build_timeline_data,
    build_timeline_figure,
)
from dashboard.replay import load_scenario, replay_scenario


def test_build_timeline_data_on_normal_day(tmp_path):
    txs = load_scenario("normal_day")
    frames = replay_scenario(txs, audit_log_path=str(tmp_path / "a.jsonl"))
    data = build_timeline_data(frames)

    assert isinstance(data, TimelineData)
    assert len(data.window_indices) == len(frames)
    assert len(data.window_labels) == len(frames)
    assert len(data.transaction_counts) == len(frames)
    assert len(data.mean_amounts) == len(frames)
    assert len(data.regime_scores) == len(frames)
    assert all(0.0 <= s <= 1.0 for s in data.regime_scores)


def test_build_timeline_data_on_mixed_fraud_has_changepoints(tmp_path):
    txs = load_scenario("mixed_fraud")
    frames = replay_scenario(txs, audit_log_path=str(tmp_path / "a.jsonl"))
    data = build_timeline_data(frames)

    # mixed_fraud.json contains a real, injected ring - the temporal layer
    # should flag at least one genuine regime shift.
    assert len(data.changepoint_indices) > 0
    assert all(0 <= i < len(frames) for i in data.changepoint_indices)


def test_build_timeline_data_empty_frames():
    data = build_timeline_data([])
    assert data.window_indices == []
    assert data.changepoint_indices == []


def test_mean_amount_zero_for_empty_window():
    """A WindowFrame with no transactions shouldn't raise a division error."""
    from dashboard.replay import WindowFrame

    empty_frame = WindowFrame(
        window_index=0,
        window_label="00:00 - 00:30",
        transactions=[],
        pipeline_result={"decision": "MONITOR", "temporal_regime": {"regime_score": 0.0}},
        audit_record={},
    )
    data = build_timeline_data([empty_frame])
    assert data.mean_amounts == [0.0]
    assert data.transaction_counts == [0]


def test_build_timeline_figure_has_expected_traces(tmp_path):
    txs = load_scenario("mixed_fraud")
    frames = replay_scenario(txs, audit_log_path=str(tmp_path / "a.jsonl"))
    data = build_timeline_data(frames)
    fig = build_timeline_figure(data)

    trace_names = [t.name for t in fig.data]
    assert "Transaction Count" in trace_names
    assert "Mean Amount (₹)" in trace_names
    assert "Regime Score" in trace_names


def test_build_timeline_figure_x_axis_matches_window_labels(tmp_path):
    txs = load_scenario("normal_day")
    frames = replay_scenario(txs, audit_log_path=str(tmp_path / "a.jsonl"))
    data = build_timeline_data(frames)
    fig = build_timeline_figure(data)

    assert list(fig.data[0].x) == data.window_labels


def test_render_timeline_panel_with_fake_streamlit(tmp_path):
    """Exercises render_timeline_panel end to end without a real Streamlit
    server, using a minimal fake that just records calls."""

    class FakeSt:
        def __init__(self):
            self.calls = []

        def markdown(self, text):
            self.calls.append(("markdown", text))

        def plotly_chart(self, fig, **kwargs):
            self.calls.append(("plotly_chart", fig))

        def caption(self, text):
            self.calls.append(("caption", text))

    from dashboard.panels.timeline import render_timeline_panel

    txs = load_scenario("mixed_fraud")
    frames = replay_scenario(txs, audit_log_path=str(tmp_path / "a.jsonl"))

    fake_st = FakeSt()
    render_timeline_panel(frames, st_module=fake_st)

    call_types = [c[0] for c in fake_st.calls]
    assert "plotly_chart" in call_types
    assert "caption" in call_types
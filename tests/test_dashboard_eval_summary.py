import json

from dashboard.panels.eval_summary import (
    EvalSummaryData,
    build_eval_summary_data,
    build_volume_curve_figure,
)


def _load_real_cached_data():
    with open("evaluation/detection_curve.json") as f:
        detection = json.load(f)
    with open("evaluation/pnl_summary.json") as f:
        pnl = json.load(f)
    return detection, pnl


def test_build_eval_summary_data_from_real_cached_files():
    detection, pnl = _load_real_cached_data()
    data = build_eval_summary_data(detection, pnl)

    assert isinstance(data, EvalSummaryData)
    assert data.overall_n > 0
    assert 0.0 <= data.overall_detection_rate <= 1.0
    # detection_curve.json and pnl_summary.json are two SEPARATE sweeps
    # with independently-sized samples (60 vs 30 scenarios) - their counts
    # are not expected to match each other. The P&L side's own confusion
    # matrix must be internally consistent, though.
    assert data.true_positives + data.false_negatives == pnl["n_scenarios"]
    assert len(data.volume_buckets) > 0


def test_pnl_net_impact_matches_components():
    detection, pnl = _load_real_cached_data()
    data = build_eval_summary_data(detection, pnl)

    expected_net = data.fraud_saved - data.false_positive_cost - data.fraud_missed
    assert abs(data.net_impact - round(expected_net, 2)) < 0.01


def test_build_eval_summary_data_handles_missing_keys():
    """A malformed/partial JSON shouldn't crash the panel - degrade
    gracefully to zeros instead."""
    data = build_eval_summary_data({}, {})
    assert data.overall_n == 0
    assert data.overall_detection_rate == 0.0
    assert data.volume_buckets == []
    assert data.net_impact == 0.0


def test_build_volume_curve_figure_bar_count_matches_buckets():
    detection, pnl = _load_real_cached_data()
    data = build_eval_summary_data(detection, pnl)
    fig = build_volume_curve_figure(data)

    assert len(fig.data[0].x) == len(data.volume_buckets)
    assert len(fig.data[0].y) == len(data.volume_buckets)


def test_build_volume_curve_figure_colors_reflect_detection_rate():
    """Low detection-rate buckets should be colored differently from high
    ones - this is the visual point of the chart."""
    detection, pnl = _load_real_cached_data()
    data = build_eval_summary_data(detection, pnl)
    fig = build_volume_curve_figure(data)

    colors = fig.data[0].marker.color
    rates = [b["detection_rate"] for b in data.volume_buckets]
    for color, rate in zip(colors, rates):
        if rate < 0.6:
            assert color == "#ff3b3b"
        elif rate >= 0.9:
            assert color == "#00ff88"


def test_render_eval_summary_panel_with_fake_streamlit(monkeypatch):
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

    class FakeSt:
        def __init__(self):
            self.calls = []
            self.session_state = {}

        def markdown(self, *a, **k):
            self.calls.append("markdown")

        def caption(self, *a, **k):
            self.calls.append("caption")

        def button(self, *a, **k):
            return False  # simulate "not clicked" for this test

        def columns(self, n):
            return [FakeColumn(self) for _ in range(n)]

        def plotly_chart(self, *a, **k):
            self.calls.append("plotly_chart")

        def table(self, *a, **k):
            self.calls.append("table")

        def expander(self, *a, **k):
            return FakeExpander(self)

        def write(self, *a, **k):
            self.calls.append("write")

    from dashboard.panels import eval_summary

    fake_st = FakeSt()
    eval_summary.render_eval_summary_panel(st_module=fake_st)

    assert "plotly_chart" in fake_st.calls
    assert "table" in fake_st.calls
    assert "eval_detection" in fake_st.session_state
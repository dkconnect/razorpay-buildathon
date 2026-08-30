from dashboard.panels.graph_view import (
    GraphData,
    build_graph_data,
    build_graph_figure,
)
from dashboard.replay import WindowFrame, load_scenario, replay_scenario


def test_build_graph_data_on_flagged_window_has_nodes_and_edges(tmp_path):
    txs = load_scenario("mixed_fraud")
    frames = replay_scenario(txs, audit_log_path=str(tmp_path / "a.jsonl"))
    flagged = [f for f in frames if f.pipeline_result["decision"] != "MONITOR"]
    assert flagged, "expected at least one flagged window in mixed_fraud.json"

    data = build_graph_data(flagged[0])
    assert isinstance(data, GraphData)
    assert data.has_ring
    assert len(data.nodes) > 0
    assert len(data.edges) > 0
    assert 0.0 <= data.ring_score <= 1.0

    tx_nodes = [n for n in data.nodes if n.node_type == "transaction"]
    entity_nodes = [n for n in data.nodes if n.node_type != "transaction"]
    assert len(tx_nodes) == data.transaction_count
    assert len(entity_nodes) > 0  # a ring implies shared devices/IPs/BINs


def test_build_graph_data_edges_only_connect_tx_to_entities(tmp_path):
    """Every edge must connect a transaction node to an entity node - never
    two transactions directly, and never two entities directly (this would
    misrepresent a bipartite structure as something else)."""
    txs = load_scenario("mixed_fraud")
    frames = replay_scenario(txs, audit_log_path=str(tmp_path / "a.jsonl"))
    flagged = [f for f in frames if f.pipeline_result["decision"] != "MONITOR"]
    data = build_graph_data(flagged[0])

    node_type_by_id = {n.node_id: n.node_type for n in data.nodes}
    for e in data.edges:
        src_type = node_type_by_id.get(e.source)
        tgt_type = node_type_by_id.get(e.target)
        assert src_type == "transaction"
        assert tgt_type in ("device", "ip", "bin")


def test_build_graph_data_empty_community_returns_no_ring():
    frame = WindowFrame(
        window_index=0,
        window_label="00:00 - 00:30",
        transactions=[],
        pipeline_result={
            "decision": "MONITOR",
            "graph_intelligence": {"top_community": {}},
        },
        audit_record={},
    )
    data = build_graph_data(frame)
    assert data.has_ring is False
    assert data.nodes == []
    assert data.edges == []


def test_build_graph_data_missing_graph_intelligence_key_handled():
    """Older/malformed pipeline results without graph_intelligence at all
    should degrade gracefully, not crash the dashboard."""
    frame = WindowFrame(
        window_index=0,
        window_label="00:00 - 00:30",
        transactions=[],
        pipeline_result={"decision": "MONITOR"},
        audit_record={},
    )
    data = build_graph_data(frame)
    assert data.has_ring is False


def test_build_graph_figure_no_ring_case_still_builds():
    frame = WindowFrame(
        window_index=0,
        window_label="00:00 - 00:30",
        transactions=[],
        pipeline_result={"decision": "MONITOR", "graph_intelligence": {"top_community": {}}},
        audit_record={},
    )
    data = build_graph_data(frame)
    fig = build_graph_figure(data)
    assert fig is not None


def test_build_graph_figure_ring_case_has_node_traces(tmp_path):
    txs = load_scenario("mixed_fraud")
    frames = replay_scenario(txs, audit_log_path=str(tmp_path / "a.jsonl"))
    flagged = [f for f in frames if f.pipeline_result["decision"] != "MONITOR"]
    data = build_graph_data(flagged[0])
    fig = build_graph_figure(data)

    trace_names = [t.name for t in fig.data if t.name]
    assert "Transaction" in trace_names


def test_render_graph_panel_with_fake_streamlit(tmp_path):
    class FakeSt:
        def __init__(self):
            self.calls = []

        def markdown(self, text):
            self.calls.append(("markdown", text))

        def plotly_chart(self, fig, use_container_width=True):
            self.calls.append(("plotly_chart", fig))

        def caption(self, text):
            self.calls.append(("caption", text))

    from dashboard.panels.graph_view import render_graph_panel

    txs = load_scenario("mixed_fraud")
    frames = replay_scenario(txs, audit_log_path=str(tmp_path / "a.jsonl"))
    flagged = [f for f in frames if f.pipeline_result["decision"] != "MONITOR"]

    fake_st = FakeSt()
    render_graph_panel(flagged[0], st_module=fake_st)

    call_types = [c[0] for c in fake_st.calls]
    assert "plotly_chart" in call_types
    assert "caption" in call_types
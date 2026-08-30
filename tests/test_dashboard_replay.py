import pytest

from dashboard.replay import (
    WindowFrame,
    get_audit_logger,
    load_scenario,
    replay_scenario,
)


def test_load_scenario_normal_day():
    txs = load_scenario("normal_day")
    assert len(txs) > 0
    assert all("amount" in t and "timestamp" in t for t in txs[:5])


def test_load_scenario_unknown_name_raises():
    with pytest.raises(ValueError):
        load_scenario("not_a_real_scenario")


def test_load_scenario_random_requires_seed():
    with pytest.raises(ValueError):
        load_scenario("random")


def test_load_scenario_random_is_reproducible():
    txs1 = load_scenario("random", seed=555)
    txs2 = load_scenario("random", seed=555)
    assert len(txs1) == len(txs2)
    assert [t["amount"] for t in txs1] == [t["amount"] for t in txs2]


def test_load_scenario_random_different_seeds_differ():
    txs1 = load_scenario("random", seed=1)
    txs2 = load_scenario("random", seed=2)
    assert len(txs1) != len(txs2) or [t["amount"] for t in txs1] != [t["amount"] for t in txs2]


def test_replay_scenario_produces_valid_frames(tmp_path):
    txs = load_scenario("normal_day")
    frames = replay_scenario(txs, audit_log_path=str(tmp_path / "audit.jsonl"))

    assert len(frames) > 0
    assert all(isinstance(f, WindowFrame) for f in frames)

    first = frames[0]
    assert "decision" in first.pipeline_result
    assert "risk_assessment" in first.pipeline_result
    assert first.window_label  # non-empty string like "00:00 - 00:30"
    assert isinstance(first.transactions, list)


def test_replay_scenario_windows_are_chronological(tmp_path):
    txs = load_scenario("normal_day")
    frames = replay_scenario(txs, audit_log_path=str(tmp_path / "audit.jsonl"))
    indices = [f.window_index for f in frames]
    assert indices == sorted(indices)


def test_replay_scenario_empty_input_returns_empty_list(tmp_path):
    frames = replay_scenario([], audit_log_path=str(tmp_path / "audit.jsonl"))
    assert frames == []


def test_replay_scenario_writes_valid_audit_chain(tmp_path):
    audit_path = str(tmp_path / "audit.jsonl")
    txs = load_scenario("normal_day")
    frames = replay_scenario(txs, audit_log_path=audit_path)

    logger = get_audit_logger(audit_log_path=audit_path)
    assert len(logger) == len(frames)

    report = logger.verify_integrity()
    assert report.ok


def test_replay_scenario_fresh_run_does_not_append_to_stale_log(tmp_path):
    """A second replay to the same path should start a fresh chain, not
    silently accumulate onto a previous run's records."""
    audit_path = str(tmp_path / "audit.jsonl")
    txs = load_scenario("normal_day")

    frames1 = replay_scenario(txs, audit_log_path=audit_path)
    frames2 = replay_scenario(txs, audit_log_path=audit_path)

    logger = get_audit_logger(audit_log_path=audit_path)
    assert len(logger) == len(frames2)  # not len(frames1) + len(frames2)


def test_replay_mixed_fraud_flags_more_than_pure_monitor(tmp_path):
    """Sanity check against known Day 6 numbers: mixed_fraud.json should
    produce at least one non-MONITOR decision (it contains a real ring)."""
    txs = load_scenario("mixed_fraud")
    frames = replay_scenario(txs, audit_log_path=str(tmp_path / "audit.jsonl"))
    decisions = [f.pipeline_result["decision"] for f in frames]
    assert any(d != "MONITOR" for d in decisions)
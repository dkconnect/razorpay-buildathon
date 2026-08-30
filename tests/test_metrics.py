from evaluation.eval_harness import ScenarioResult, run_stealth_volume_sweep
from evaluation.metrics import (
    detection_rate_by_ring_size,
    detection_rate_by_volume,
    latency_stats,
    overall_detection_rate,
)


def _fake_result(
    identity_count=8, detected=True, missed_phase=None, latency=0
):
    return ScenarioResult(
        seed=1,
        ring_id="r",
        identity_count=identity_count,
        phase1_transaction_count=50,
        phase2_transaction_count=10,
        injected_start_offset_minutes=100,
        detected=detected,
        missed_phase=missed_phase,
        first_detection_window_index=1 if detected else None,
        time_to_detection_minutes=latency if detected else None,
        windows_with_ring_activity=1,
        windows_flagged_among_ring_activity=1 if detected else 0,
        max_overall_risk_score_on_ring_windows=0.8,
    )


def test_detection_rate_by_ring_size_buckets_correctly():
    results = [
        _fake_result(identity_count=4, detected=True),
        _fake_result(identity_count=4, detected=False, missed_phase="both"),
        _fake_result(identity_count=10, detected=True),
    ]
    buckets = detection_rate_by_ring_size(results)
    sizes = {b.ring_size: b for b in buckets}

    assert sizes[4].n == 2
    assert sizes[4].detected == 1
    assert sizes[4].detection_rate == 0.5
    assert sizes[10].detection_rate == 1.0


def test_overall_detection_rate():
    results = [_fake_result(detected=True) for _ in range(3)] + [
        _fake_result(detected=False, missed_phase="both") for _ in range(1)
    ]
    rate = overall_detection_rate(results)
    assert rate["n"] == 4
    assert rate["detected"] == 3
    assert rate["detection_rate"] == 0.75


def test_latency_stats_handles_no_detections():
    results = [_fake_result(detected=False, missed_phase="both") for _ in range(3)]
    stats = latency_stats(results)
    assert stats.n_detected == 0
    assert stats.mean_minutes is None
    assert stats.missed_entirely == 3


def test_latency_stats_computes_correctly():
    results = [
        _fake_result(detected=True, latency=0),
        _fake_result(detected=True, latency=30),
        _fake_result(detected=True, latency=30),
    ]
    stats = latency_stats(results)
    assert stats.n_detected == 3
    assert stats.mean_minutes == 20.0
    assert stats.median_minutes == 30.0
    assert stats.caught_before_bustout == 3


def test_latency_never_negative_by_construction():
    """Regression guard for the window-alignment bug found during Step 3
    (raw datetime subtraction could go negative; window-count-based latency
    cannot)."""
    from evaluation.eval_harness import run_single_scenario

    for seed in [100, 101, 102]:
        result = run_single_scenario(seed=seed, window_minutes=30)
        if result.detected:
            assert result.time_to_detection_minutes >= 0


def test_stealth_volume_sweep_shows_low_volume_is_harder():
    """This is the actual finding from Step 3: identity_count doesn't
    control difficulty, phase1_transaction_count does. A very low volume
    (3 transactions total) should detect notably less reliably than a
    moderate volume (30 transactions), holding identity_count fixed."""
    results_by_volume = run_stealth_volume_sweep(
        volumes=[3, 30], samples_per_volume=3, identity_count=8
    )
    buckets = {b["phase1_volume"]: b for b in detection_rate_by_volume(results_by_volume)}

    assert buckets[3]["detection_rate"] <= buckets[30]["detection_rate"]
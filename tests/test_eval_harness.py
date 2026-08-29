from evaluation.eval_harness import (
    ScenarioResult,
    bucket_into_windows,
    run_eval_sweep,
    run_single_scenario,
)


def test_single_scenario_returns_valid_result():
    result = run_single_scenario(seed=2000, window_minutes=30)
    assert isinstance(result, ScenarioResult)
    assert result.identity_count >= 4
    assert result.windows_with_ring_activity > 0
    if result.detected:
        assert result.time_to_detection_minutes is not None
        assert result.time_to_detection_minutes >= 0  # never negative


def test_reproducibility_same_seed_same_result():
    """The whole point of a seeded eval harness: identical input -> identical
    output, every time. If this ever fails, something introduced
    nondeterminism (unseeded randomness, set iteration order, etc.)."""
    r1 = run_single_scenario(seed=3000, window_minutes=30)
    r2 = run_single_scenario(seed=3000, window_minutes=30)
    assert r1.to_dict() == r2.to_dict()


def test_different_seeds_produce_different_configs():
    r1 = run_single_scenario(seed=4000, window_minutes=30)
    r2 = run_single_scenario(seed=4001, window_minutes=30)
    # Not a strict requirement that they differ in every field, but the
    # random config draw should not degenerate to the same ring every time.
    assert (
        r1.identity_count != r2.identity_count
        or r1.phase1_transaction_count != r2.phase1_transaction_count
        or r1.injected_start_offset_minutes != r2.injected_start_offset_minutes
    )


def test_eval_sweep_matches_individual_calls():
    seeds = [5000, 5001, 5002]
    sweep_results = run_eval_sweep(seeds, window_minutes=30)
    individual_results = [run_single_scenario(seed=s, window_minutes=30) for s in seeds]

    assert [r.to_dict() for r in sweep_results] == [r.to_dict() for r in individual_results]


def test_bucket_into_windows_groups_correctly():
    from datetime import datetime, timedelta

    epoch = datetime(2026, 1, 1)
    txs = [
        {"timestamp": epoch + timedelta(minutes=5)},
        {"timestamp": epoch + timedelta(minutes=29)},
        {"timestamp": epoch + timedelta(minutes=31)},
        {"timestamp": epoch + timedelta(minutes=65)},
    ]
    windows = bucket_into_windows(txs, epoch, window_minutes=30)
    assert len(windows[0]) == 2  # minutes 5 and 29
    assert len(windows[1]) == 1  # minute 31
    assert len(windows[2]) == 1  # minute 65
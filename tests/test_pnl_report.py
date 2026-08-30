from evaluation.pnl_report import (
    EvaluationOutcome,
    aggregate_outcomes,
    calculate_pnl,
    classify_evaluation,
    compute_false_positive_cost,
    run_fraud_evaluation,
    scenario_to_outcome,
)


# ---------------------------------------------------------------------------
# Original pure-function tests
# ---------------------------------------------------------------------------

def test_pnl_calculation():
    result = calculate_pnl(
        fraud_saved=10000,
        false_positive_cost=500,
        fraud_missed=2000,
    )

    assert result.fraud_saved == 10000
    assert result.false_positive_cost == 500
    assert result.fraud_missed == 2000
    assert result.net_impact == 7500


def test_pnl_never_accepts_negative_components():
    result = calculate_pnl(
        fraud_saved=-100,
        false_positive_cost=-50,
        fraud_missed=-25,
    )

    assert result.fraud_saved == 0
    assert result.false_positive_cost == 0
    assert result.fraud_missed == 0
    assert result.net_impact == 0


def test_negative_net_impact_is_allowed():
    result = calculate_pnl(
        fraud_saved=1000,
        false_positive_cost=300,
        fraud_missed=2000,
    )

    assert result.net_impact == -1300


def test_pnl_result_is_serializable():
    result = calculate_pnl(
        fraud_saved=5000,
        false_positive_cost=100,
        fraud_missed=500,
    )

    assert result.to_dict() == {
        "fraud_saved": 5000.0,
        "false_positive_cost": 100.0,
        "fraud_missed": 500.0,
        "net_impact": 4400.0,
    }


def test_detected_fraud_is_true_positive():
    result = classify_evaluation(
        fraud_detected=True,
        fraud_exposure=40000,
        legitimate_alerts=2,
        total_legitimate=100,
    )

    assert result.true_positives == 1
    assert result.false_negatives == 0
    assert result.fraud_exposure_caught == 40000
    assert result.fraud_exposure_missed == 0
    assert result.false_positives == 2
    assert result.true_negatives == 98


def test_missed_fraud_is_false_negative():
    result = classify_evaluation(
        fraud_detected=False,
        fraud_exposure=40000,
        legitimate_alerts=0,
        total_legitimate=100,
    )

    assert result.true_positives == 0
    assert result.false_negatives == 1
    assert result.fraud_exposure_caught == 0
    assert result.fraud_exposure_missed == 40000


def test_legitimate_alerts_are_false_positives():
    result = classify_evaluation(
        fraud_detected=True,
        fraud_exposure=10000,
        legitimate_alerts=5,
        total_legitimate=100,
    )

    assert result.false_positives == 5
    assert result.true_negatives == 95


# ---------------------------------------------------------------------------
# New: aggregation + real data-gathering layer
# ---------------------------------------------------------------------------

def test_aggregate_outcomes_sums_all_fields():
    outcomes = [
        EvaluationOutcome(1, 2, 0, 98, 40000.0, 0.0),
        EvaluationOutcome(0, 1, 1, 99, 0.0, 15000.0),
    ]
    total = aggregate_outcomes(outcomes)
    assert total.true_positives == 1
    assert total.false_positives == 3
    assert total.false_negatives == 1
    assert total.true_negatives == 197
    assert total.fraud_exposure_caught == 40000.0
    assert total.fraud_exposure_missed == 15000.0


def test_aggregate_outcomes_empty_list():
    total = aggregate_outcomes([])
    assert total.true_positives == 0
    assert total.fraud_exposure_caught == 0.0


def test_scenario_to_outcome_caught_before_bustout():
    from evaluation.eval_harness import ScenarioResult

    r = ScenarioResult(
        seed=1, ring_id="r", identity_count=8,
        phase1_transaction_count=50, phase2_transaction_count=10,
        injected_start_offset_minutes=100,
        detected=True, missed_phase=None,
        first_detection_window_index=2, time_to_detection_minutes=0,
        windows_with_ring_activity=1, windows_flagged_among_ring_activity=1,
        max_overall_risk_score_on_ring_windows=0.8,
        phase2_amount_total=25000.0,
        background_windows_flagged=1, background_windows_total=47,
    )
    outcome = scenario_to_outcome(r)
    assert outcome.true_positives == 1
    assert outcome.fraud_exposure_caught == 25000.0
    assert outcome.false_positives == 1
    assert outcome.true_negatives == 46


def test_scenario_to_outcome_caught_late_counts_as_missed():
    """A ring only caught after Phase 2 already started is conservatively
    treated as a miss for exposure-accounting purposes (window-level
    granularity can't prove partial recovery)."""
    from evaluation.eval_harness import ScenarioResult

    r = ScenarioResult(
        seed=1, ring_id="r", identity_count=8,
        phase1_transaction_count=50, phase2_transaction_count=10,
        injected_start_offset_minutes=100,
        detected=True, missed_phase="phase1",
        first_detection_window_index=3, time_to_detection_minutes=30,
        windows_with_ring_activity=2, windows_flagged_among_ring_activity=1,
        max_overall_risk_score_on_ring_windows=0.8,
        phase2_amount_total=25000.0,
        background_windows_flagged=0, background_windows_total=47,
    )
    outcome = scenario_to_outcome(r)
    assert outcome.true_positives == 0
    assert outcome.false_negatives == 1
    assert outcome.fraud_exposure_missed == 25000.0
    assert outcome.fraud_exposure_caught == 0.0


def test_compute_false_positive_cost_on_normal_day():
    """Real, deterministic run against normal_day.json - 100% ground-truth
    legitimate traffic, so every flagged window is by definition a false
    positive."""
    report = compute_false_positive_cost("normal_day.json", "normal_day")
    assert report.total_windows > 0
    assert report.flagged_windows <= report.total_windows
    assert report.total_false_positive_cost >= 0.0
    assert 0.0 <= report.false_positive_rate <= 1.0


def test_run_fraud_evaluation_reproducible():
    """Same seeds in, same outcomes out."""
    seeds = [1000, 1001, 1002]
    o1 = run_fraud_evaluation(seeds)
    o2 = run_fraud_evaluation(seeds)
    assert [o.to_dict() for o in o1] == [o.to_dict() for o in o2]
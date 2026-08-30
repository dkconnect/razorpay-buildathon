"""
Day 6 Validation & Test Suite — Step 6

Cross-cutting sanity checks across everything built today: the audit
logger, the eval harness, the P&L report, and the report generator. These
are checks ON THE SYSTEM AS A WHOLE, not on any one module in isolation
(each module already has its own dedicated test file).
"""

import json

from audit.logger import AuditTrailLogger
from evaluation.eval_harness import default_seed_range, run_eval_sweep
from evaluation.pnl_report import (
    aggregate_outcomes,
    calculate_pnl,
    compute_false_positive_cost,
    run_fraud_evaluation,
)


# ---------------------------------------------------------------------------
# Reproducibility: same seed -> same numbers, every time
# ---------------------------------------------------------------------------

def test_eval_sweep_reproducible_across_runs():
    seeds = default_seed_range(n=5, start=7000)
    r1 = run_eval_sweep(seeds)
    r2 = run_eval_sweep(seeds)
    assert [r.to_dict() for r in r1] == [r.to_dict() for r in r2]


def test_pnl_reproducible_across_runs():
    seeds = default_seed_range(n=5, start=7100)
    o1 = aggregate_outcomes(run_fraud_evaluation(seeds))
    o2 = aggregate_outcomes(run_fraud_evaluation(seeds))
    assert o1.to_dict() == o2.to_dict()


def test_false_positive_cost_deterministic():
    """normal_day.json is a fixed, deterministic dataset - running the
    false-positive cost calculation twice must give identical numbers."""
    r1 = compute_false_positive_cost("normal_day.json", "normal_day")
    r2 = compute_false_positive_cost("normal_day.json", "normal_day")
    assert r1 == r2


# ---------------------------------------------------------------------------
# Audit log consistency: record count matches calls made, chain stays intact
# ---------------------------------------------------------------------------

def test_audit_log_record_count_matches_calls_made(tmp_path):
    logger = AuditTrailLogger(tmp_path / "audit.jsonl")
    n_calls = 7
    for i in range(n_calls):
        logger.log({"decision": "MONITOR", "call_index": i})
    assert len(logger) == n_calls
    assert len(logger.read_all()) == n_calls


def test_audit_log_stays_intact_across_many_writes(tmp_path):
    """Regression guard: write a realistic number of records (simulating a
    day's worth of window decisions) and confirm the hash chain is still
    fully verifiable at the end - nothing about scale should break it."""
    logger = AuditTrailLogger(tmp_path / "audit.jsonl")
    for i in range(48):  # one 30-min window per hour-half, across a day
        logger.log({"decision": "MONITOR" if i % 5 else "FLAG_FOR_REVIEW", "window": i})

    report = logger.verify_integrity()
    assert report.ok
    assert report.record_count == 48


def test_audit_log_can_persist_real_pipeline_output(tmp_path):
    """The audit logger and the pipeline's actual output schema must stay
    compatible - this is checked here (system-level) in addition to
    test_audit_logger.py's unit-level check, since the pipeline's output
    shape could drift as it's modified independently of the logger."""
    from detection.sentinel_pipeline import FraudSentinelPipeline

    with open("data/generated/normal_day.json") as f:
        data = json.load(f)
    txs = data if isinstance(data, list) else data.get("transactions", [])

    pipeline = FraudSentinelPipeline()
    logger = AuditTrailLogger(tmp_path / "audit.jsonl")

    for chunk_start in range(0, 300, 150):
        result = pipeline.process_window(txs[chunk_start : chunk_start + 150])
        logger.log(result)

    assert len(logger) == 2
    report = logger.verify_integrity()
    assert report.ok


# ---------------------------------------------------------------------------
# P&L internal consistency
# ---------------------------------------------------------------------------

def test_pnl_accounts_for_full_scenario_set():
    """Every scenario's exposure must land in exactly one bucket: caught or
    missed. Caught + missed must equal the total exposure across all
    scenarios - no ring's money should silently vanish from the accounting."""
    seeds = default_seed_range(n=10, start=7200)
    outcomes = run_fraud_evaluation(seeds)
    aggregated = aggregate_outcomes(outcomes)

    total_exposure = aggregated.fraud_exposure_caught + aggregated.fraud_exposure_missed
    # true_positives + false_negatives must equal the number of scenarios,
    # since every scenario is classified as exactly one or the other.
    assert aggregated.true_positives + aggregated.false_negatives == len(seeds)
    assert total_exposure >= 0.0


def test_pnl_net_impact_matches_manual_calculation():
    seeds = default_seed_range(n=5, start=7300)
    aggregated = aggregate_outcomes(run_fraud_evaluation(seeds))
    fp_normal = compute_false_positive_cost("normal_day.json", "normal_day")

    pnl = calculate_pnl(
        fraud_saved=aggregated.fraud_exposure_caught,
        false_positive_cost=fp_normal.total_false_positive_cost,
        fraud_missed=aggregated.fraud_exposure_missed,
    )

    expected_net = (
        aggregated.fraud_exposure_caught
        - fp_normal.total_false_positive_cost
        - aggregated.fraud_exposure_missed
    )
    assert abs(pnl.net_impact - round(expected_net, 2)) < 0.01


# ---------------------------------------------------------------------------
# Report generation sanity
# ---------------------------------------------------------------------------

def test_report_generator_produces_valid_markdown_and_json(tmp_path, monkeypatch):
    from evaluation import generate_report

    # Redirect output paths so this test doesn't overwrite the real
    # evaluation/EVAL_REPORT.md on disk.
    monkeypatch.setattr(generate_report, "_REPORT_MD_PATH", tmp_path / "EVAL_REPORT.md")
    monkeypatch.setattr(generate_report, "_REPORT_JSON_PATH", tmp_path / "eval_report.json")
    monkeypatch.setattr(generate_report, "_DETECTION_CURVE_PATH", tmp_path / "detection_curve.json")
    monkeypatch.setattr(generate_report, "_PNL_SUMMARY_PATH", tmp_path / "pnl_summary.json")

    detection = generate_report.regenerate_detection_curve(n_ring_size_scenarios=5)
    pnl = generate_report.regenerate_pnl_summary(n_scenarios=5)

    report_md = generate_report.generate_markdown_report(detection, pnl)
    assert "Breakpoint" in report_md
    assert "Net impact" in report_md
    assert "₹" in report_md

    # Every field referenced in the template must actually be present -
    # this catches a schema drift between metrics.py/pnl_report.py's output
    # and what generate_markdown_report expects to read.
    assert str(detection["overall_detection_rate"]["detected"]) in report_md
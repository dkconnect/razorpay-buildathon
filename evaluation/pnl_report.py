"""
P&L / False-Positive-Cost Report — Day 6 Step 4

Two layers, deliberately kept separate:

1. Pure calculation layer (PnLResult, EvaluationOutcome, calculate_pnl,
   classify_evaluation) - takes numbers in, does arithmetic, has no
   knowledge of the pipeline, JSON files, or the eval harness. Fully unit
   testable in isolation.

2. Data-gathering layer (everything below aggregate_outcomes) - runs the
   real pipeline against real generated scenarios and feeds the results
   into layer 1. This is where the actual ₹ numbers come from.

False-positive cost is read directly from the pipeline's own
decision_economics output for each flagged window, not a second,
separately-invented cost formula - this report's job is to correctly
ATTRIBUTE the system's own cost figures against ground truth, not to
re-derive them.

Honesty note: because the pipeline scores whole windows in one shot, a ring
caught in the same window Phase 2 already started in can't be resolved into
"how much of Phase 2 happened before vs after the alert." Such scenarios are
conservatively counted as a full Phase 2 loss (fraud_detected=False for the
purposes of exposure accounting is too harsh, so we instead route them
through fraud_exposure_missed directly rather than exposure_caught - see
run_fraud_evaluation).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List

from data.generator.scenario import DEFAULT_START_TIME
from detection.sentinel_pipeline import FraudSentinelPipeline
from evaluation.eval_harness import ScenarioResult, bucket_into_windows

FLAGGED_DECISIONS = ("FLAG_FOR_REVIEW", "HOLD_FOR_REVIEW")


# ---------------------------------------------------------------------------
# Layer 1: pure calculation (unchanged from the initial draft)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PnLResult:
    """Financial outcome of a fraud-detection evaluation run."""

    fraud_saved: float
    false_positive_cost: float
    fraud_missed: float
    net_impact: float

    def to_dict(self) -> dict:
        return {
            "fraud_saved": self.fraud_saved,
            "false_positive_cost": self.false_positive_cost,
            "fraud_missed": self.fraud_missed,
            "net_impact": self.net_impact,
        }


@dataclass(frozen=True)
class EvaluationOutcome:
    """Classification counts and exposure from one evaluation run."""

    true_positives: int
    false_positives: int
    false_negatives: int
    true_negatives: int

    fraud_exposure_caught: float
    fraud_exposure_missed: float

    def to_dict(self) -> dict:
        return {
            "true_positives": self.true_positives,
            "false_positives": self.false_positives,
            "false_negatives": self.false_negatives,
            "true_negatives": self.true_negatives,
            "fraud_exposure_caught": self.fraud_exposure_caught,
            "fraud_exposure_missed": self.fraud_exposure_missed,
        }


def calculate_pnl(
    fraud_saved: float,
    false_positive_cost: float,
    fraud_missed: float,
) -> PnLResult:
    """
    Calculate the net financial impact of BreakPoint's decisions.

    Positive net_impact means the system prevented more fraud loss
    than it incurred through false-positive friction.

    Negative net_impact means operational friction and missed fraud
    outweighed the fraud value successfully caught.
    """
    fraud_saved = max(0.0, float(fraud_saved))
    false_positive_cost = max(0.0, float(false_positive_cost))
    fraud_missed = max(0.0, float(fraud_missed))

    net_impact = (
        fraud_saved
        - false_positive_cost
        - fraud_missed
    )

    return PnLResult(
        fraud_saved=round(fraud_saved, 2),
        false_positive_cost=round(false_positive_cost, 2),
        fraud_missed=round(fraud_missed, 2),
        net_impact=round(net_impact, 2),
    )


def classify_evaluation(
    *,
    fraud_detected: bool,
    fraud_exposure: float,
    legitimate_alerts: int,
    total_legitimate: int,
) -> EvaluationOutcome:
    """
    Convert a single scenario's ground truth and pipeline outcome
    into TP/FP/FN/TN counts plus fraud exposure accounting.
    """
    fraud_exposure = max(0.0, float(fraud_exposure))
    legitimate_alerts = max(0, int(legitimate_alerts))
    total_legitimate = max(0, int(total_legitimate))

    if fraud_detected:
        true_positives = 1
        false_negatives = 0
        fraud_exposure_caught = fraud_exposure
        fraud_exposure_missed = 0.0
    else:
        true_positives = 0
        false_negatives = 1
        fraud_exposure_caught = 0.0
        fraud_exposure_missed = fraud_exposure

    false_positives = legitimate_alerts
    true_negatives = max(
        0,
        total_legitimate - legitimate_alerts,
    )

    return EvaluationOutcome(
        true_positives=true_positives,
        false_positives=false_positives,
        false_negatives=false_negatives,
        true_negatives=true_negatives,
        fraud_exposure_caught=round(fraud_exposure_caught, 2),
        fraud_exposure_missed=round(fraud_exposure_missed, 2),
    )


def aggregate_outcomes(outcomes: List[EvaluationOutcome]) -> EvaluationOutcome:
    """Element-wise sum across many scenarios' outcomes into one grand total."""
    if not outcomes:
        return EvaluationOutcome(0, 0, 0, 0, 0.0, 0.0)
    return EvaluationOutcome(
        true_positives=sum(o.true_positives for o in outcomes),
        false_positives=sum(o.false_positives for o in outcomes),
        false_negatives=sum(o.false_negatives for o in outcomes),
        true_negatives=sum(o.true_negatives for o in outcomes),
        fraud_exposure_caught=round(sum(o.fraud_exposure_caught for o in outcomes), 2),
        fraud_exposure_missed=round(sum(o.fraud_exposure_missed for o in outcomes), 2),
    )


# ---------------------------------------------------------------------------
# Layer 2: data gathering - real pipeline runs feeding layer 1
# ---------------------------------------------------------------------------

def _elapsed_minutes(ts: datetime, epoch: datetime) -> float:
    return (ts - epoch).total_seconds() / 60.0


def _load_scenario_dicts(filename: str) -> List[Dict[str, Any]]:
    """Loads a pre-generated scenario JSON file and parses timestamps into
    real datetime objects, matching what bucket_into_windows expects."""
    with open(f"data/generated/{filename}") as f:
        data = json.load(f)
    txs = data.get("transactions", data) if isinstance(data, dict) else data

    def parse(ts):
        try:
            return float(ts)
        except (TypeError, ValueError):
            return datetime.fromisoformat(ts.replace("Z", "+00:00"))

    parsed = [{**t, "timestamp": parse(t["timestamp"])} for t in txs]
    parsed.sort(key=lambda t: t["timestamp"])
    return parsed


@dataclass
class FalsePositiveCostReport:
    scenario_name: str
    total_windows: int
    flagged_windows: int
    false_positive_rate: float
    total_false_positive_cost: float
    total_legitimate_volume: float


def compute_false_positive_cost(
    filename: str, scenario_name: str, window_minutes: int = 30
) -> FalsePositiveCostReport:
    """
    Replays an entirely-legitimate scenario (normal_day.json or
    flash_sale.json - both 100% ground-truth non-fraud) through ONE live
    pipeline instance, window by window. Any FLAG/HOLD decision on these
    files is, by definition, a false positive. Its ₹ cost is read directly
    from the pipeline's own decision_economics for that window.
    """
    txs = _load_scenario_dicts(filename)
    windows = bucket_into_windows(txs, DEFAULT_START_TIME, window_minutes)

    pipeline = FraudSentinelPipeline(window_minutes=window_minutes)

    total_windows = 0
    flagged_windows = 0
    total_fp_cost = 0.0
    total_volume = 0.0

    for window_idx in sorted(windows.keys()):
        window_txs = windows[window_idx]
        pipeline_txs = [
            {**t, "timestamp": _elapsed_minutes(t["timestamp"], DEFAULT_START_TIME) * 60.0}
            for t in window_txs
        ]
        result = pipeline.process_window(pipeline_txs)
        total_windows += 1
        total_volume += sum(t["amount"] for t in window_txs)

        decision = result["decision"]
        if decision in FLAGGED_DECISIONS:
            flagged_windows += 1
            total_fp_cost += result["decision_economics"]["expected_costs"][decision]

    return FalsePositiveCostReport(
        scenario_name=scenario_name,
        total_windows=total_windows,
        flagged_windows=flagged_windows,
        false_positive_rate=round(flagged_windows / total_windows, 4) if total_windows else 0.0,
        total_false_positive_cost=round(total_fp_cost, 2),
        total_legitimate_volume=round(total_volume, 2),
    )


def scenario_to_outcome(result: ScenarioResult) -> EvaluationOutcome:
    """
    Converts one fraud-ring ScenarioResult into an EvaluationOutcome via
    classify_evaluation.

    A ring caught only AFTER Phase 2 (bust-out) had already started
    (missed_phase == "phase1") is treated as fraud_detected=False for
    exposure-accounting purposes: window-level granularity can't prove how
    much of Phase 2 happened before vs after the alert within that window,
    so we conservatively count the full Phase 2 amount as missed rather
    than guessing a partial recovery (see module docstring).
    """
    fraud_detected = result.detected and result.missed_phase is None
    return classify_evaluation(
        fraud_detected=fraud_detected,
        fraud_exposure=result.phase2_amount_total,
        legitimate_alerts=result.background_windows_flagged,
        total_legitimate=result.background_windows_total,
    )


def run_fraud_evaluation(seeds: List[int], window_minutes: int = 30) -> List[EvaluationOutcome]:
    from evaluation.eval_harness import run_eval_sweep

    results = run_eval_sweep(seeds, window_minutes=window_minutes)
    return [scenario_to_outcome(r) for r in results]


def format_pnl_statement(
    pnl: PnLResult, outcome: EvaluationOutcome, fp_reports: List[FalsePositiveCostReport]
) -> str:
    lines = []
    lines.append("=" * 60)
    lines.append("BREAKPOINT -- P&L STATEMENT")
    lines.append("=" * 60)

    lines.append(f"\nConfusion matrix (fraud scenarios + background windows):")
    lines.append(f"  True Positives (rings caught):     {outcome.true_positives}")
    lines.append(f"  False Negatives (rings missed):    {outcome.false_negatives}")
    lines.append(f"  False Positives (legit flagged):   {outcome.false_positives}")
    lines.append(f"  True Negatives (legit correct):    {outcome.true_negatives}")

    lines.append(f"\nFraud exposure:")
    lines.append(f"  Caught: Rs.{outcome.fraud_exposure_caught:>14,.2f}")
    lines.append(f"  Missed: Rs.{outcome.fraud_exposure_missed:>14,.2f}")

    total_fp_cost = sum(r.total_false_positive_cost for r in fp_reports)
    lines.append(f"\nFalse-positive cost (dedicated normal_day/flash_sale sweeps):")
    for r in fp_reports:
        lines.append(
            f"  {r.scenario_name:<15} {r.flagged_windows}/{r.total_windows} windows flagged "
            f"({r.false_positive_rate:.2%})  ->  Rs.{r.total_false_positive_cost:,.2f}"
        )
    lines.append(f"  Total: Rs.{total_fp_cost:,.2f}")

    lines.append(f"\nFinal P&L:")
    lines.append(f"  Fraud saved:          Rs.{pnl.fraud_saved:>14,.2f}")
    lines.append(f"  False-positive cost:  Rs.{pnl.false_positive_cost:>14,.2f}")
    lines.append(f"  Fraud missed:         Rs.{pnl.fraud_missed:>14,.2f}")
    lines.append(f"  NET IMPACT:           Rs.{pnl.net_impact:>14,.2f}")
    return "\n".join(lines)


if __name__ == "__main__":
    from evaluation.eval_harness import default_seed_range

    print("Running fraud-scenario sweep (60 scenarios)...")
    seeds = default_seed_range(n=60, start=1000)
    outcomes = run_fraud_evaluation(seeds)
    aggregated = aggregate_outcomes(outcomes)

    print("Computing false-positive cost on normal_day.json...")
    fp_normal = compute_false_positive_cost("normal_day.json", "normal_day")
    print("Computing false-positive cost on flash_sale.json...")
    fp_flash = compute_false_positive_cost("flash_sale.json", "flash_sale")
    total_fp_cost = fp_normal.total_false_positive_cost + fp_flash.total_false_positive_cost

    pnl = calculate_pnl(
        fraud_saved=aggregated.fraud_exposure_caught,
        false_positive_cost=total_fp_cost,
        fraud_missed=aggregated.fraud_exposure_missed,
    )

    print()
    print(format_pnl_statement(pnl, aggregated, [fp_normal, fp_flash]))

    summary = {
        "pnl": pnl.to_dict(),
        "outcome": aggregated.to_dict(),
        "false_positive_reports": [r.__dict__ for r in [fp_normal, fp_flash]],
    }
    with open("evaluation/pnl_summary.json", "w") as f:
        json.dump(summary, f, indent=2)
    print("\nSaved summary to evaluation/pnl_summary.json")
"""
Runs the full FraudSentinelPipeline against many independently randomized
fraud-ring scenarios (varying ring size, phase durations, and injection time
of day), replaying each scenario window-by-window in chronological order so
Day 4's cross-phase escalation linkage gets the same live conditions it would
in production. Records whether/when each ring was caught.

Reproducibility: every random draw in this file is seeded (the fraud config,
the fraud ring's internal identity/amount sampling, and the injection start
time all derive from the scenario's seed). The same seed list produces the
same results every run - this is checked explicitly in
tests/test_eval_harness.py.

Honesty note on baseline_stats: FraudSentinelPipeline.process_window() takes
a baseline_stats["mean_velocity"] argument that it uses as the "expected"
transaction rate for that window. The pipeline does NOT currently reach
Day 3's calibrated, hour-aware CUSUM baseline (see the dead
self.cusum_detector in sentinel_pipeline.py - it's instantiated but never
called). Rather than pass a single guessed constant for every window
regardless of time of day (which Day 3's investigation showed produces
exactly the kind of nighttime-vs-daytime false positives we spent that day
fixing), this harness computes each window's expected rate from the ACTUAL
background-only transaction count in that same time slot. It's a partial,
honest workaround - not a substitute for actually wiring Day 3's CUSUM into
the pipeline, which is flagged as follow-up work.
"""

from __future__ import annotations

import random
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from data.generator.fraud_config import generate_random_fraud_config
from data.generator.scenario import DEFAULT_START_TIME
from data.schema import Transaction
from detection.sentinel_pipeline import FraudSentinelPipeline
from scenarios.fraud_ring import generate_fraud_ring
from scenarios.normal_day import generate_normal_day

FLAGGED_DECISIONS = ("FLAG_FOR_REVIEW", "HOLD_FOR_REVIEW")


def _tx_to_dict(tx: Transaction) -> Dict[str, Any]:
    return {
        "transaction_id": tx.transaction_id,
        "timestamp": tx.timestamp,
        "amount": tx.amount,
        "customer_id": tx.customer_id,
        "device_id": tx.device_id,
        "ip_subnet": tx.ip_subnet,
        "card_bin": tx.card_bin,
        "is_fraud": tx.is_fraud,
        "ring_id": tx.ring_id,
        "phase": tx.phase,
    }


def _elapsed_minutes(ts: datetime, epoch: datetime) -> float:
    return (ts - epoch).total_seconds() / 60.0


def bucket_into_windows(
    txs: List[Dict[str, Any]], epoch: datetime, window_minutes: int
) -> Dict[int, List[Dict[str, Any]]]:
    """
    Buckets transactions (dicts with a datetime 'timestamp') into consecutive
    window_minutes-wide windows indexed from epoch. Returns a dict keyed by
    window index so empty/overnight windows are simply absent rather than
    materialized as empty lists.
    """
    windows: Dict[int, List[Dict[str, Any]]] = {}
    for tx in txs:
        idx = int(_elapsed_minutes(tx["timestamp"], epoch) // window_minutes)
        windows.setdefault(idx, []).append(tx)
    return windows


@dataclass
class ScenarioResult:
    seed: int
    ring_id: str
    identity_count: int
    phase1_transaction_count: int
    phase2_transaction_count: int
    injected_start_offset_minutes: int
    detected: bool
    missed_phase: Optional[str]  # "phase1" (caught late), "both" (never caught), or None
    first_detection_window_index: Optional[int]
    time_to_detection_minutes: Optional[float]
    windows_with_ring_activity: int
    windows_flagged_among_ring_activity: int
    max_overall_risk_score_on_ring_windows: float
    decisions_on_ring_windows: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# Background traffic (generate_normal_day) is deterministic - fixed seed=42
# baked into NORMAL_DAY_CONFIG - so it's generated once and reused across an
# entire sweep rather than regenerated (~11.9k transactions) per scenario.
_background_cache: Dict[int, tuple] = {}


def _get_background(window_minutes: int):
    if window_minutes not in _background_cache:
        raw = generate_normal_day()
        background = [_tx_to_dict(t) for t in raw]
        window_map = bucket_into_windows(background, DEFAULT_START_TIME, window_minutes)
        window_counts = {idx: len(v) for idx, v in window_map.items()}
        _background_cache[window_minutes] = (background, window_counts)
    return _background_cache[window_minutes]


def run_single_scenario(
    seed: int, window_minutes: int = 30, config_override=None
) -> ScenarioResult:
    """
    Injects one randomized fraud ring into the standard background day,
    replays the merged stream through ONE FraudSentinelPipeline instance
    window-by-window in chronological order, and records whether/when the
    ring was caught.

    config_override: if provided, use this FraudRingConfig instead of
    generating one from `seed` via generate_random_fraud_config. Used by
    run_stealth_volume_sweep to probe transaction-volume as an axis
    independent of the seed-driven random config.
    """
    background, background_window_counts = _get_background(window_minutes)

    rng = random.Random(seed)
    # Randomize WHEN in the day the ring starts, not just its size. Always
    # injecting at midnight (as the original mixed_fraud.json does) would
    # bias every eval run toward one specific hour's traffic conditions -
    # see Day 3's nighttime-vs-daytime false-positive investigation.
    start_offset_minutes = rng.randint(60, 23 * 60)
    injected_start = DEFAULT_START_TIME + timedelta(minutes=start_offset_minutes)

    config = config_override or generate_random_fraud_config(
        seed=seed, ring_id=f"eval_ring_{seed:04d}"
    )
    fraud_txs_raw = generate_fraud_ring(config=config, start_time=injected_start, seed=seed)
    fraud_txs = [_tx_to_dict(t) for t in fraud_txs_raw]

    if not fraud_txs:
        raise ValueError(f"seed={seed} produced an empty fraud ring - check config bounds")

    all_txs = background + fraud_txs
    all_txs.sort(key=lambda t: t["timestamp"])
    windows = bucket_into_windows(all_txs, DEFAULT_START_TIME, window_minutes)

    ring_window_indices = sorted(
        {
            int(_elapsed_minutes(t["timestamp"], DEFAULT_START_TIME) // window_minutes)
            for t in fraud_txs
        }
    )

    pipeline = FraudSentinelPipeline(window_minutes=window_minutes)

    first_detection_window_index: Optional[int] = None
    ring_activity_flagged = 0
    max_risk_on_ring_windows = 0.0
    decisions_on_ring_windows: List[str] = []
    ring_start_ts = min(t["timestamp"] for t in fraud_txs)

    for window_idx in sorted(windows.keys()):
        window_txs = windows[window_idx]
        expected_rate = background_window_counts.get(window_idx, 1) / max(1, window_minutes)

        # Convert datetime timestamps to elapsed-seconds floats, matching
        # what the rest of the pipeline (temporal/graph layers) expects.
        pipeline_txs = [
            {**t, "timestamp": _elapsed_minutes(t["timestamp"], DEFAULT_START_TIME) * 60.0}
            for t in window_txs
        ]

        result = pipeline.process_window(
            pipeline_txs, baseline_stats={"mean_velocity": max(expected_rate, 0.1)}
        )
        decision = result["decision"]

        if window_idx in ring_window_indices:
            decisions_on_ring_windows.append(decision)
            max_risk_on_ring_windows = max(
                max_risk_on_ring_windows, result["risk_assessment"]["overall_risk_score"]
            )
            if decision in FLAGGED_DECISIONS:
                ring_activity_flagged += 1
                if first_detection_window_index is None:
                    first_detection_window_index = window_idx

    detected = first_detection_window_index is not None
    time_to_detection: Optional[float] = None
    if detected:
        # Measured in windows-since-onset, not raw datetime subtraction.
        # Window boundaries are aligned to the day's epoch, not to when the
        # ring itself starts, so "window_start - ring_start_ts" can go
        # negative purely from that phase misalignment even when detection
        # correctly fired in the very first window touching the ring. This
        # also reflects the pipeline's actual resolution honestly: it scores
        # a whole window in one shot, so sub-window timing isn't resolvable
        # with this architecture - reporting a false precise minute figure
        # would overstate what we can actually measure.
        ring_start_window_index = min(ring_window_indices)
        detection_latency_windows = first_detection_window_index - ring_start_window_index
        time_to_detection = detection_latency_windows * window_minutes

    # Did we catch it during Phase 1 (testing), or only after Phase 2
    # (bust-out) had already started extracting money?
    phase2_txs = [t for t in fraud_txs if t.get("phase") == "bust_out"]
    phase2_start_window = None
    if phase2_txs:
        phase2_start_ts = min(t["timestamp"] for t in phase2_txs)
        phase2_start_window = int(
            _elapsed_minutes(phase2_start_ts, DEFAULT_START_TIME) // window_minutes
        )

    missed_phase: Optional[str] = None
    if not detected:
        missed_phase = "both"
    elif phase2_start_window is not None and first_detection_window_index > phase2_start_window:
        missed_phase = "phase1"  # caught only after bust-out had already begun

    return ScenarioResult(
        seed=seed,
        ring_id=config.ring_id,
        identity_count=config.identity_count,
        phase1_transaction_count=config.phase1_transaction_count,
        phase2_transaction_count=config.phase2_transaction_count,
        injected_start_offset_minutes=start_offset_minutes,
        detected=detected,
        missed_phase=missed_phase,
        first_detection_window_index=first_detection_window_index,
        time_to_detection_minutes=time_to_detection,
        windows_with_ring_activity=len(ring_window_indices),
        windows_flagged_among_ring_activity=ring_activity_flagged,
        max_overall_risk_score_on_ring_windows=round(max_risk_on_ring_windows, 4),
        decisions_on_ring_windows=decisions_on_ring_windows,
    )


def run_eval_sweep(seeds: List[int], window_minutes: int = 30) -> List[ScenarioResult]:
    """Runs run_single_scenario for every seed, in order. Deterministic:
    the same seed list always produces the same results."""
    return [run_single_scenario(seed=s, window_minutes=window_minutes) for s in seeds]


def default_seed_range(n: int = 30, start: int = 1000) -> List[int]:
    """A stable, arbitrary-but-fixed seed range for reproducible sweeps.
    Starts at 1000 to avoid colliding with the low seeds (0-5ish) already
    used by hand-authored fixtures elsewhere in the codebase."""
    return list(range(start, start + n))


def run_stealth_volume_sweep(
    volumes: List[int],
    samples_per_volume: int = 5,
    identity_count: int = 8,
    window_minutes: int = 30,
    seed_base: int = 9000,
) -> Dict[int, List[ScenarioResult]]:
    """
    identity_count (ring size) turns out NOT to control detection difficulty
    in this generator, because phase1_transaction_count is randomized
    independently of it (see Day 6 Step 3 findings) - a 4-identity ring can
    still produce 140+ test transactions, which is a loud, dense, easily
    detected signal regardless of how few identities share it.

    The axis that actually should control difficulty is transaction VOLUME:
    a genuinely stealthy ring keeps its total transaction count low. This
    sweep holds identity_count fixed and varies phase1_transaction_count
    (and proportionally, phase2_transaction_count) down into a low range,
    to find where detection actually starts to break down.
    """
    from config.fraud import FraudRingConfig

    results_by_volume: Dict[int, List[ScenarioResult]] = {}

    for volume in volumes:
        # phase2 is always a smaller fraction of phase1 in the original
        # random generator (roughly 1:5 to 1:7 ratio) - keep that shape.
        phase2_count = max(2, volume // 6)
        bucket_results = []
        for i in range(samples_per_volume):
            seed = seed_base + volume * 100 + i
            config = FraudRingConfig(
                ring_id=f"stealth_v{volume}_{i}",
                identity_count=identity_count,
                phase1_duration_minutes=max(5, min(20, volume // 3)),
                phase1_transaction_count=volume,
                phase2_gap_minutes=5,
                phase2_duration_minutes=8,
                phase2_transaction_count=phase2_count,
            )
            result = run_single_scenario(
                seed=seed, window_minutes=window_minutes, config_override=config
            )
            bucket_results.append(result)
        results_by_volume[volume] = bucket_results

    return results_by_volume


if __name__ == "__main__":
    import json

    seeds = default_seed_range(n=20)
    results = run_eval_sweep(seeds)

    detected_count = sum(1 for r in results if r.detected)
    print(f"Ran {len(results)} scenarios, detected {detected_count}/{len(results)}")
    for r in results:
        status = "DETECTED" if r.detected else "MISSED"
        ttd = f"{r.time_to_detection_minutes:.1f}min" if r.time_to_detection_minutes is not None else "-"
        print(
            f"  seed={r.seed} ring_size={r.identity_count:2d} "
            f"start_offset={r.injected_start_offset_minutes:4d}min "
            f"-> {status:8s} ttd={ttd:>8s} missed_phase={r.missed_phase}"
        )

    with open("evaluation/eval_sweep_raw.json", "w") as f:
        json.dump([r.to_dict() for r in results], f, indent=2)
    print("\nSaved raw results to evaluation/eval_sweep_raw.json")
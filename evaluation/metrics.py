"""
Aggregates a list of evaluation.eval_harness.ScenarioResult into the two
numbers §7 of the project plan actually asks for:

1. Detection rate as a function of ring size — a CURVE, not one number.
   Where does the system reliably catch rings, and where does it start to
   miss small ones?

2. Detection latency — how many minutes after a ring's first transaction
   does the system flag it, and critically: was it caught during the cheap
   Phase 1 (testing) window, or only after Phase 2 (bust-out) had already
   started extracting money?

Both are reported with sample counts alongside every rate, since a rate
computed from 2 scenarios and a rate computed from 40 scenarios are not the
same kind of claim, and presenting them identically would be dishonest.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from typing import Dict, List, Optional

from evaluation.eval_harness import ScenarioResult


@dataclass
class RingSizeBucket:
    ring_size: int
    n: int
    detected: int
    detection_rate: float
    caught_before_bustout: int  # flagged during/before Phase 2 onset
    caught_late: int  # flagged only after Phase 2 had already begun
    missed: int  # never flagged at all


def detection_rate_by_ring_size(results: List[ScenarioResult]) -> List[RingSizeBucket]:
    """
    Buckets scenarios by ring size (identity_count) and computes detection
    rate per bucket. Returns buckets sorted by ring_size ascending, so the
    output can be plotted directly as a curve.
    """
    by_size: Dict[int, List[ScenarioResult]] = {}
    for r in results:
        by_size.setdefault(r.identity_count, []).append(r)

    buckets = []
    for size in sorted(by_size.keys()):
        group = by_size[size]
        n = len(group)
        detected = sum(1 for r in group if r.detected)
        caught_before = sum(1 for r in group if r.detected and r.missed_phase is None)
        caught_late = sum(1 for r in group if r.missed_phase == "phase1")
        missed = sum(1 for r in group if not r.detected)

        buckets.append(
            RingSizeBucket(
                ring_size=size,
                n=n,
                detected=detected,
                detection_rate=round(detected / n, 4) if n else 0.0,
                caught_before_bustout=caught_before,
                caught_late=caught_late,
                missed=missed,
            )
        )
    return buckets


def overall_detection_rate(results: List[ScenarioResult]) -> Dict[str, float]:
    n = len(results)
    detected = sum(1 for r in results if r.detected)
    return {
        "n": n,
        "detected": detected,
        "detection_rate": round(detected / n, 4) if n else 0.0,
    }


@dataclass
class LatencyStats:
    n_detected: int
    mean_minutes: Optional[float]
    median_minutes: Optional[float]
    p90_minutes: Optional[float]
    max_minutes: Optional[float]
    caught_before_bustout: int
    caught_late: int
    missed_entirely: int


def latency_stats(results: List[ScenarioResult]) -> LatencyStats:
    """
    Latency is reported in whole windows (see eval_harness.py's docstring on
    why sub-window timing isn't resolvable with this architecture) - so
    these numbers will cluster at multiples of window_minutes, not form a
    smooth distribution. That's an honest reflection of the pipeline's
    actual resolution, not a rounding artifact to explain away.
    """
    detected_latencies = [
        r.time_to_detection_minutes for r in results
        if r.detected and r.time_to_detection_minutes is not None
    ]
    caught_before = sum(1 for r in results if r.detected and r.missed_phase is None)
    caught_late = sum(1 for r in results if r.missed_phase == "phase1")
    missed = sum(1 for r in results if not r.detected)

    if not detected_latencies:
        return LatencyStats(
            n_detected=0, mean_minutes=None, median_minutes=None,
            p90_minutes=None, max_minutes=None,
            caught_before_bustout=caught_before, caught_late=caught_late,
            missed_entirely=missed,
        )

    sorted_lat = sorted(detected_latencies)
    p90_idx = min(len(sorted_lat) - 1, int(0.9 * len(sorted_lat)))

    return LatencyStats(
        n_detected=len(detected_latencies),
        mean_minutes=round(statistics.mean(sorted_lat), 2),
        median_minutes=round(statistics.median(sorted_lat), 2),
        p90_minutes=round(sorted_lat[p90_idx], 2),
        max_minutes=round(max(sorted_lat), 2),
        caught_before_bustout=caught_before,
        caught_late=caught_late,
        missed_entirely=missed,
    )


def format_curve_table(buckets: List[RingSizeBucket]) -> str:
    lines = [
        f"{'ring_size':>9} | {'n':>4} | {'detected':>8} | {'rate':>6} | "
        f"{'before_bustout':>14} | {'caught_late':>11} | {'missed':>6}"
    ]
    lines.append("-" * len(lines[0]))
    for b in buckets:
        lines.append(
            f"{b.ring_size:>9} | {b.n:>4} | {b.detected:>8} | {b.detection_rate:>6.2%} | "
            f"{b.caught_before_bustout:>14} | {b.caught_late:>11} | {b.missed:>6}"
        )
    return "\n".join(lines)


def detection_rate_by_volume(
    results_by_volume: Dict[int, List[ScenarioResult]]
) -> List[Dict]:
    """
    Same idea as detection_rate_by_ring_size, but bucketed by Phase 1
    transaction volume instead of identity count - this is the axis that
    Day 6 Step 3 found actually controls detection difficulty (see
    eval_harness.run_stealth_volume_sweep's docstring for why identity_count
    alone does not).
    """
    buckets = []
    for volume in sorted(results_by_volume.keys()):
        group = results_by_volume[volume]
        n = len(group)
        detected = sum(1 for r in group if r.detected)
        caught_before = sum(1 for r in group if r.detected and r.missed_phase is None)
        caught_late = sum(1 for r in group if r.missed_phase == "phase1")
        missed = sum(1 for r in group if not r.detected)
        buckets.append(
            {
                "phase1_volume": volume,
                "n": n,
                "detected": detected,
                "detection_rate": round(detected / n, 4) if n else 0.0,
                "caught_before_bustout": caught_before,
                "caught_late": caught_late,
                "missed": missed,
            }
        )
    return buckets


def format_volume_curve_table(buckets: List[Dict]) -> str:
    lines = [
        f"{'phase1_volume':>13} | {'n':>4} | {'detected':>8} | {'rate':>6} | "
        f"{'before_bustout':>14} | {'caught_late':>11} | {'missed':>6}"
    ]
    lines.append("-" * len(lines[0]))
    for b in buckets:
        lines.append(
            f"{b['phase1_volume']:>13} | {b['n']:>4} | {b['detected']:>8} | "
            f"{b['detection_rate']:>6.2%} | {b['caught_before_bustout']:>14} | "
            f"{b['caught_late']:>11} | {b['missed']:>6}"
        )
    return "\n".join(lines)


if __name__ == "__main__":
    import json
    import time

    from evaluation.eval_harness import (
        default_seed_range,
        run_eval_sweep,
        run_stealth_volume_sweep,
    )

    N_SCENARIOS = 100
    print(f"Running {N_SCENARIOS} random-config scenarios (~{N_SCENARIOS * 1.9 / 60:.1f} min)...")
    t0 = time.time()
    seeds = default_seed_range(n=N_SCENARIOS, start=1000)
    results = run_eval_sweep(seeds)
    t1 = time.time()
    print(f"Done in {t1 - t0:.1f}s\n")

    overall = overall_detection_rate(results)
    print(f"Overall detection rate: {overall['detected']}/{overall['n']} = {overall['detection_rate']:.2%}\n")

    buckets = detection_rate_by_ring_size(results)
    print("Detection rate by ring size (identity_count):")
    print(format_curve_table(buckets))
    print(
        "\nNOTE: this curve is flat because phase1_transaction_count is randomized\n"
        "independently of identity_count in generate_random_fraud_config - a small\n"
        "ring can still produce 140+ transactions, which is loud and easily detected\n"
        "regardless of how few identities share it. See the volume sweep below for\n"
        "the axis that actually controls detection difficulty.\n"
    )

    lat = latency_stats(results)
    print(f"Latency (minutes, among {lat.n_detected} detected):")
    print(f"  mean={lat.mean_minutes}  median={lat.median_minutes}  p90={lat.p90_minutes}  max={lat.max_minutes}")
    print(f"  caught before bust-out started: {lat.caught_before_bustout}")
    print(f"  caught only after bust-out started: {lat.caught_late}")
    print(f"  missed entirely: {lat.missed_entirely}")

    print("\n" + "=" * 70)
    volumes = [3, 5, 8, 12, 20, 30, 50, 80]
    print(f"Running stealth-volume sweep ({len(volumes)} volumes x 5 samples)...")
    t0 = time.time()
    results_by_volume = run_stealth_volume_sweep(volumes, samples_per_volume=5)
    t1 = time.time()
    print(f"Done in {t1 - t0:.1f}s\n")

    volume_buckets = detection_rate_by_volume(results_by_volume)
    print("Detection rate by Phase 1 transaction volume (identity_count fixed at 8):")
    print(format_volume_curve_table(volume_buckets))

    summary = {
        "n_scenarios": N_SCENARIOS,
        "overall_detection_rate": overall,
        "detection_by_ring_size": [b.__dict__ for b in buckets],
        "latency_stats": lat.__dict__,
        "detection_by_phase1_volume": volume_buckets,
    }
    with open("evaluation/detection_curve.json", "w") as f:
        json.dump(summary, f, indent=2)
    print("\nSaved summary to evaluation/detection_curve.json")
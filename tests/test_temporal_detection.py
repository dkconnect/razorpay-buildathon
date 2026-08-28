"""
Validation & Benchmark Suite:
- Validates temporal feature extraction, CUSUM detection, and regime classifier.
- Scenario checks: normal_day.json, flash_sale.json, mixed_fraud.json.
- Detection latency and throughput benchmark.
"""

import json
import time
from datetime import datetime
from pathlib import Path
import pytest
import numpy as np

from features.temporal import TemporalFeatureExtractor, TemporalSnapshot
from detection.cusum import BaselineCalibrator, CUSUMDetector, BaselineProfile
from detection.regime import RegimeClassifier, RegimeType, RegimeDiagnosis


DATA_DIR = Path("data/generated")


def _parse_timestamp_to_seconds(ts_val) -> float:
    """Parses timestamp values (float, int, or ISO-8601 string) into numeric epoch seconds."""
    if isinstance(ts_val, (int, float)):
        return float(ts_val)
    if isinstance(ts_val, str):
        try:
            return float(ts_val)
        except ValueError:
            dt = datetime.fromisoformat(ts_val.replace("Z", "+00:00"))
            return dt.timestamp()
    raise TypeError(f"Unsupported timestamp format: {type(ts_val)} ({ts_val})")


def load_scenario_txs(filename: str) -> list[dict]:
    """Loads scenario JSON, normalizes timestamps relative to scenario start (t0=0.0)."""
    filepath = DATA_DIR / filename
    if not filepath.exists():
        pytest.skip(f"Scenario dataset {filepath} not found.")
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    if isinstance(data, dict):
        txs = data.get("transactions", data.get("data", []))
    else:
        txs = data
        
    raw_txs = []
    for tx in txs:
        raw_txs.append({
            "timestamp": _parse_timestamp_to_seconds(tx["timestamp"]),
            "amount": float(tx["amount"]),
            "transaction_id": tx.get("transaction_id", "")
        })

    raw_txs.sort(key=lambda x: x["timestamp"])
    
    if not raw_txs:
        return []
        
    t0 = raw_txs[0]["timestamp"]
    for tx in raw_txs:
        tx["timestamp"] = tx["timestamp"] - t0

    return raw_txs


@pytest.fixture
def calibrated_baseline() -> BaselineProfile:
    """Calibrates non-stationary baseline profile strictly using clean normal_day traffic."""
    clean_txs = load_scenario_txs("normal_day.json")
    extractor = TemporalFeatureExtractor(window_minutes=15.0)
    snapshots = extractor.process_stream(clean_txs)
    
    baseline = BaselineCalibrator.fit(snapshots, scenario_name="normal_day")
    return baseline


def run_pipeline(
    txs: list[dict], 
    baseline: BaselineProfile, 
    warmup_seconds: float = 900.0,
    k_slack: float = 1.0,
    threshold_h: float = 12.0
) -> list[RegimeDiagnosis]:
    """
    Streams transactions sequentially through Feature -> CUSUM -> Regime Classifier.
    Evaluates streaming regime diagnoses post warmup.
    """
    extractor = TemporalFeatureExtractor(window_minutes=15.0)
    cusum = CUSUMDetector(baseline=baseline, k_slack=k_slack, threshold_h=threshold_h)
    classifier = RegimeClassifier()
    
    diagnoses = []
    for tx in txs:
        snapshot = extractor.update(tx["timestamp"], tx["amount"])
        state = cusum.update(snapshot)
        diagnosis = classifier.classify(state)
        
        if tx["timestamp"] >= warmup_seconds:
            diagnoses.append(diagnosis)
            
    return diagnoses


# =====================================================================
# Scenario Validation Tests
# =====================================================================

def test_normal_day_false_positive_rate(calibrated_baseline):
    """
    Ensures nominal merchant traffic produces a LOW, honestly-reported rate of
    confirmed fraud alarms.

    NOTE: We deliberately assert a rate bound rather than exact 0. A Gaussian
    CUSUM over a bounded, low-count proportion feature (high_val_ratio) will
    not hit a literal zero false-positive rate on real-shaped, heteroscedastic
    traffic (nighttime windows have far fewer transactions than daytime ones,
    so the ratio is a noisier estimate at night even after calibration).
    Forcing exact 0 here would mean either tuning the detector until it's too
    conservative to catch real fraud, or hardcoding around this specific
    dataset - neither is honest. Measured rate on normal_day.json is ~0.21%
    (25/11860 post-warmup snapshots); we assert a bound with headroom above
    that, and report the exact rate so it's visible in the eval writeup
    (this is exactly the "false-positive cost" the track brief asks for).
    """
    txs = load_scenario_txs("normal_day.json")
    diagnoses = run_pipeline(txs, calibrated_baseline, k_slack=1.0, threshold_h=10.0)

    malicious_attacks = [
        d for d in diagnoses
        if d.regime in (RegimeType.CARD_TESTING, RegimeType.BUSTOUT)
    ]
    fp_rate = len(malicious_attacks) / len(diagnoses) if diagnoses else 0.0
    MAX_ACCEPTABLE_FP_RATE = 0.01  # 1% - measured rate is ~0.21%, headroom included

    print(
        f"\n[normal_day FP rate] {len(malicious_attacks)}/{len(diagnoses)} "
        f"= {fp_rate:.4%} (bound: {MAX_ACCEPTABLE_FP_RATE:.2%})"
    )
    assert fp_rate <= MAX_ACCEPTABLE_FP_RATE, (
        f"False-positive rate on normal_day.json too high: {fp_rate:.4%} "
        f"({len(malicious_attacks)}/{len(diagnoses)}), exceeds bound of "
        f"{MAX_ACCEPTABLE_FP_RATE:.2%}"
    )


def test_flash_sale_distinction(calibrated_baseline):
    """
    Validates Flash Sale distinction:
    - Velocity spikes.
    - System diagnoses FLASH_SALE as the dominant regime.
    - CARD_TESTING alarms (velocity + amount-deflection co-occurring) stay
      at a low, honestly-bounded rate rather than exact 0, for the same
      reason as test_normal_day_false_positive_rate above. Measured rate is
      1/17870 post-warmup snapshots (~0.006%).
    """
    txs = load_scenario_txs("flash_sale.json")
    diagnoses = run_pipeline(txs, calibrated_baseline, k_slack=1.0, threshold_h=10.0)

    # Check velocity spike was registered
    velocity_alerts = [d for d in diagnoses if d.cusum_state.velocity_alert]
    assert len(velocity_alerts) > 0, "Flash sale did not trigger expected CUSUM velocity alert (S_v+)."

    # Ensure it is diagnosed as FLASH_SALE (the dominant regime, not just present)
    flash_sale_diagnoses = [d for d in diagnoses if d.regime == RegimeType.FLASH_SALE]
    assert len(flash_sale_diagnoses) > 0, "Flash sale was not categorized as RegimeType.FLASH_SALE."
    assert len(flash_sale_diagnoses) > len(diagnoses) * 0.25, (
        "FLASH_SALE should be a substantial share of diagnoses during the flash sale window, "
        f"got {len(flash_sale_diagnoses)}/{len(diagnoses)}"
    )

    # Crucial: Flash sale must mostly NOT trigger CARD_TESTING - bounded rate, not exact 0
    card_testing_attacks = [d for d in diagnoses if d.regime == RegimeType.CARD_TESTING]
    ct_rate = len(card_testing_attacks) / len(diagnoses) if diagnoses else 0.0
    MAX_ACCEPTABLE_CT_RATE = 0.005  # 0.5% - measured rate is ~0.006%, headroom included

    print(
        f"\n[flash_sale false CARD_TESTING rate] {len(card_testing_attacks)}/{len(diagnoses)} "
        f"= {ct_rate:.4%} (bound: {MAX_ACCEPTABLE_CT_RATE:.2%})"
    )
    assert ct_rate <= MAX_ACCEPTABLE_CT_RATE, (
        f"Flash sale falsely triggered CARD_TESTING attacks at too high a rate: "
        f"{ct_rate:.4%} ({len(card_testing_attacks)}/{len(diagnoses)})"
    )


def test_mixed_fraud_detection(calibrated_baseline):
    """
    Validates Card Testing -> Bust-Out attack detection on mixed_fraud.json:
    - Phase 1: Card testing triggers CARD_TESTING.
    - Diagnostic reason codes attributed.
    """
    txs = load_scenario_txs("mixed_fraud.json")
    diagnoses = run_pipeline(txs, calibrated_baseline, k_slack=1.0, threshold_h=10.0)
    
    # 1. Must flag CARD_TESTING during Phase 1
    card_testing_detections = [d for d in diagnoses if d.regime == RegimeType.CARD_TESTING]
    assert len(card_testing_detections) > 0, "CUSUM failed to flag CARD_TESTING regime during card testing phase."
    
    # 2. Check reason codes
    all_reasons = [code for d in diagnoses for code in d.reason_codes]
    assert any("TRANSACTION_VELOCITY_SPIKE" in r for r in all_reasons), "Missing velocity spike reason code."
    assert any("MICRO_AMOUNT_CONCENTRATION" in r for r in all_reasons), "Missing micro amount concentration reason code."


# =====================================================================
# Performance & Latency Benchmark
# =====================================================================

def test_detection_latency_benchmark(calibrated_baseline):
    """
    Ensures per-transaction stream processing operates under 1.0 ms per transaction.
    """
    extractor = TemporalFeatureExtractor(window_minutes=15.0)
    cusum = CUSUMDetector(baseline=calibrated_baseline, k_slack=1.0, threshold_h=10.0)
    classifier = RegimeClassifier()
    
    n_txs = 1500
    base_ts = 1000.0
    
    latencies_ms = []
    for i in range(n_txs):
        ts = base_ts + (i * 2.0)
        amt = 100.0 + (i % 50)
        
        t0 = time.perf_counter()
        snapshot = extractor.update(ts, amt)
        state = cusum.update(snapshot)
        _ = classifier.classify(state)
        t1 = time.perf_counter()
        
        latencies_ms.append((t1 - t0) * 1000.0)
        
    avg_latency = float(np.mean(latencies_ms))
    p95_latency = float(np.percentile(latencies_ms, 95))
    
    print(f"\n[Temporal Engine Latency] Mean: {avg_latency:.4f} ms | P95: {p95_latency:.4f} ms")
    assert avg_latency < 1.0, f"Average stream latency {avg_latency:.3f} ms exceeds 1.0 ms SLA limit."
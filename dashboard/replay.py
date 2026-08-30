"""
Replays a full scenario (normal_day, flash_sale, mixed_fraud, or a freshly
generated randomized fraud-ring scenario) through ONE live
FraudSentinelPipeline instance, window by window, capturing every window's
complete result into a list the dashboard can step through.

This deliberately replays the SAME way evaluation/eval_harness.py does
(same window bucketing, same chronological single-pipeline-instance
replay) so the dashboard shows exactly what the eval numbers measure, not
a second, parallel path that could silently drift from it.

Every window's result is also written to a real, hash-chained audit log
(audit/logger.py) as it's produced - the dashboard's "verify integrity"
control (Step 4) checks this same log, not a mock.
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from audit.logger import AuditTrailLogger
from data.generator.fraud_config import generate_random_fraud_config
from data.generator.scenario import DEFAULT_START_TIME
from data.schema import Transaction
from detection.sentinel_pipeline import FraudSentinelPipeline
from evaluation.eval_harness import bucket_into_windows
from scenarios.fraud_ring import generate_fraud_ring
from scenarios.normal_day import generate_normal_day

_DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "generated"

SCENARIO_FILES = {
    "normal_day": "normal_day.json",
    "flash_sale": "flash_sale.json",
    "mixed_fraud": "mixed_fraud.json",
}


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


def _load_scenario_dicts(filename: str) -> List[Dict[str, Any]]:
    with open(_DATA_DIR / filename) as f:
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


def load_scenario(name: str, seed: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    name: one of "normal_day", "flash_sale", "mixed_fraud", or "random".
    seed: required when name == "random" - injects a freshly randomized
    fraud ring (varying size, phase durations, and time of day) into the
    standard background day, using the same mechanism as
    evaluation/eval_harness.py.run_single_scenario.
    """
    if name in SCENARIO_FILES:
        return _load_scenario_dicts(SCENARIO_FILES[name])

    if name == "random":
        if seed is None:
            raise ValueError("seed is required for a random scenario")

        rng = random.Random(seed)
        start_offset_minutes = rng.randint(60, 23 * 60)
        injected_start = DEFAULT_START_TIME + timedelta(minutes=start_offset_minutes)

        config = generate_random_fraud_config(seed=seed, ring_id=f"dashboard_ring_{seed:04d}")
        fraud_txs_raw = generate_fraud_ring(config=config, start_time=injected_start, seed=seed)
        fraud_txs = [_tx_to_dict(t) for t in fraud_txs_raw]

        background_raw = generate_normal_day()
        background = [_tx_to_dict(t) for t in background_raw]

        all_txs = background + fraud_txs
        all_txs.sort(key=lambda t: t["timestamp"])
        return all_txs

    raise ValueError(
        f"Unknown scenario name: {name!r}. Expected one of "
        f"{list(SCENARIO_FILES.keys()) + ['random']}"
    )


@dataclass
class WindowFrame:
    """Everything the dashboard needs to render one window's state."""

    window_index: int
    window_label: str  # e.g. "08:30 - 09:00"
    transactions: List[Dict[str, Any]]  # raw transactions in this window
    pipeline_result: Dict[str, Any]  # full FraudSentinelPipeline.process_window() output
    audit_record: Dict[str, Any]  # the hash-chained audit record for this window


def replay_scenario(
    transactions: List[Dict[str, Any]],
    window_minutes: int = 30,
    audit_log_path: Optional[str] = None,
) -> List[WindowFrame]:
    """
    Replays transactions through ONE live pipeline instance, window by
    window, in chronological order. Every window's result is logged to the
    audit trail and captured into the returned list.

    audit_log_path: if None, uses a fresh in-memory-equivalent temp file
    per call (dashboard/.replay_audit.jsonl) so repeated dashboard replays
    don't append to one another's chains indefinitely.
    """
    if not transactions:
        return []

    windows = bucket_into_windows(transactions, DEFAULT_START_TIME, window_minutes)
    pipeline = FraudSentinelPipeline(window_minutes=window_minutes)

    log_path = audit_log_path or str(
        Path(__file__).resolve().parent / ".replay_audit.jsonl"
    )
    # A fresh replay should start a fresh chain, not append onto a stale one
    # from a previous dashboard session.
    log_file = Path(log_path)
    if log_file.exists():
        log_file.unlink()
    logger = AuditTrailLogger(log_path)

    frames: List[WindowFrame] = []
    for window_idx in sorted(windows.keys()):
        window_txs = windows[window_idx]
        pipeline_txs = [
            {**t, "timestamp": _elapsed_minutes(t["timestamp"], DEFAULT_START_TIME) * 60.0}
            for t in window_txs
        ]
        result = pipeline.process_window(pipeline_txs)
        audit_record = logger.log(result)

        window_start = DEFAULT_START_TIME + timedelta(minutes=window_idx * window_minutes)
        window_end = window_start + timedelta(minutes=window_minutes)
        label = f"{window_start.strftime('%H:%M')} - {window_end.strftime('%H:%M')}"

        frames.append(
            WindowFrame(
                window_index=window_idx,
                window_label=label,
                transactions=window_txs,
                pipeline_result=result,
                audit_record=audit_record,
            )
        )

    return frames


def get_audit_logger(audit_log_path: Optional[str] = None) -> AuditTrailLogger:
    """Returns a logger pointed at the same file replay_scenario just wrote,
    so the dashboard's integrity-check control reads the real, just-produced
    chain rather than a separate instance."""
    log_path = audit_log_path or str(
        Path(__file__).resolve().parent / ".replay_audit.jsonl"
    )
    return AuditTrailLogger(log_path)
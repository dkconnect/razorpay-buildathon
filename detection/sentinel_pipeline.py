from typing import Any, Dict, List, Optional
import json
import uuid
from datetime import datetime
from pathlib import Path

import numpy as np

from features.temporal import TemporalFeatureExtractor
from detection.cusum import BaselineCalibrator, BaselineProfile, CUSUMDetector
from detection.regime import RegimeClassifier, RegimeDiagnosis

from detection.graph_detector import GraphRingDetector, PhaseLinker
from detection.fusion import RiskFusionEngine
from exposure.evt import TailExposureEstimator
from decision.cost_engine import CostSensitiveDecisionEngine


_DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "generated"
_cached_default_baseline: Optional[BaselineProfile] = None


def _parse_timestamp_to_seconds(ts_val) -> float:
    if isinstance(ts_val, (int, float)):
        return float(ts_val)
    if isinstance(ts_val, str):
        try:
            return float(ts_val)
        except ValueError:
            return datetime.fromisoformat(ts_val.replace("Z", "+00:00")).timestamp()
    raise TypeError(f"Unsupported timestamp format: {type(ts_val)} ({ts_val})")


def get_default_baseline(temporal_window_minutes: float = 15.0) -> BaselineProfile:
    """
    Calibrates (once per process, then cached) the same hour-aware CUSUM
    baseline that Day 3's own validation suite uses - fit strictly from
    data/generated/normal_day.json, mirroring
    tests/test_temporal_detection.py's `calibrated_baseline` fixture exactly
    so the production pipeline and the Day 3 validation suite are backed by
    the identical calibration, not two independently-drifting copies.
    """
    global _cached_default_baseline
    if _cached_default_baseline is not None:
        return _cached_default_baseline

    with open(_DATA_DIR / "normal_day.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    txs = data.get("transactions", data) if isinstance(data, dict) else data

    raw_txs = [
        {"timestamp": _parse_timestamp_to_seconds(t["timestamp"]), "amount": float(t["amount"])}
        for t in txs
    ]
    raw_txs.sort(key=lambda x: x["timestamp"])
    t0 = raw_txs[0]["timestamp"]
    for t in raw_txs:
        t["timestamp"] -= t0

    extractor = TemporalFeatureExtractor(window_minutes=temporal_window_minutes)
    snapshots = extractor.process_stream(raw_txs)
    _cached_default_baseline = BaselineCalibrator.fit(snapshots, scenario_name="normal_day")
    return _cached_default_baseline


def _to_seconds_since_midnight(ts_val) -> float:
    """
    Converts a transaction timestamp into seconds-since-midnight, matching
    the semantics get_default_baseline's calibration was fit against (the
    calibrated baseline's hour-of-day lookup assumes timestamp // 3600 % 24
    gives the TRUE hour of day).

    Two calling conventions are supported:
    - float/int: assumed to already be elapsed-seconds-since-midnight (this
      is what evaluation/eval_harness.py passes).
    - ISO-8601 string: hour/minute/second are read directly off the parsed
      datetime's own fields, NOT via datetime.timestamp(). Using
      .timestamp() on a naive datetime silently depends on the server's
      local timezone to convert to epoch seconds, which can shift the
      computed hour-of-day by several hours depending on where this runs -
      reading the calendar fields directly sidesteps that entirely.
    """
    if isinstance(ts_val, (int, float)):
        return float(ts_val)
    if isinstance(ts_val, str):
        try:
            return float(ts_val)
        except ValueError:
            dt = datetime.fromisoformat(ts_val.replace("Z", "+00:00"))
            return dt.hour * 3600.0 + dt.minute * 60.0 + dt.second + dt.microsecond / 1e6
    raise TypeError(f"Unsupported timestamp format: {type(ts_val)} ({ts_val})")


class FraudSentinelPipeline:
    """Integrated Risk Management Sentinel for Coordinated Attacks & Flash Sales."""

    def __init__(
        self,
        window_minutes: int = 30,
        min_cluster_size: int = 2,
        baseline_profile: Optional[BaselineProfile] = None,
        temporal_window_minutes: float = 15.0,
        cusum_k_slack: float = 1.0,
        cusum_threshold_h: float = 12.0,
    ):
        self.window_minutes = window_minutes

        self.baseline_profile = baseline_profile or get_default_baseline(temporal_window_minutes)
        self.temporal_extractor = TemporalFeatureExtractor(window_minutes=temporal_window_minutes)
        self.cusum_detector = CUSUMDetector(
            baseline=self.baseline_profile,
            k_slack=cusum_k_slack,
            threshold_h=cusum_threshold_h,
        )
        self.regime_classifier = RegimeClassifier()

        self.graph_detector = GraphRingDetector(min_cluster_size=min_cluster_size)
        self.phase_linker = PhaseLinker()
        self.fusion_engine = RiskFusionEngine()
        self.exposure_estimator = TailExposureEstimator()
        self.decision_engine = CostSensitiveDecisionEngine()

        # Historical memory for cross-phase tracking
        self.historical_phase1_communities: List[Dict[str, Any]] = []

    def process_window(
        self,
        transactions: List[Dict[str, Any]],
        baseline_stats: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """
        Processes a sliding window of transactions and generates an auditable risk report.

        NOTE on baseline_stats: this parameter is accepted for backward API
        compatibility only and is no longer used to compute regime_score.
        It previously fed a caller-supplied guess into a simple velocity-
        ratio heuristic; regime_score is now produced by the actual
        calibrated, hour-aware CUSUM detector from Day 3 (see
        get_default_baseline), which reads each transaction's own timestamp
        to look up the correct diurnal baseline rather than relying on the
        caller to estimate one.

        Transactions within (and across) calls must be fed in chronological
        order - the temporal extractor and CUSUM detector are stateful and
        persist across process_window calls on the same pipeline instance,
        by design (this is what lets Day 4's cross-phase escalation and the
        CUSUM's rolling baseline both work correctly on a continuous stream).
        """
        if not transactions:
            return self._empty_response()

        # 1. Temporal Detection - real calibrated CUSUM, not a heuristic ratio.
        # Fed per-transaction (not as a batch aggregate) because the CUSUM's
        # state (and its reset-on-alarm behavior) is inherently sequential.
        regime_score = 0.0
        last_diagnosis: Optional[RegimeDiagnosis] = None
        for tx in transactions:
            ts = _to_seconds_since_midnight(tx.get("timestamp", 0.0))
            amt = float(tx.get("amount", 0.0))
            snapshot = self.temporal_extractor.update(ts, amt)
            state = self.cusum_detector.update(snapshot)
            diagnosis = self.regime_classifier.classify(state)
            # Max, not last: reset-on-alarm zeroes the CUSUM sum the instant
            # it fires, so the LAST transaction's score in a window can read
            # near-zero even though the window clearly contained an alarm.
            regime_score = max(regime_score, diagnosis.regime_score)
            last_diagnosis = diagnosis

        regime_score = round(float(np.clip(regime_score, 0.0, 1.0)), 4)

        # 2. Graph Intelligence: Communities & Rings
        communities = self.graph_detector.detect_communities(transactions)
        
        top_community = communities[0] if communities else {}
        ring_score = float(top_community.get("ring_score", 0.0))
        implicated_tx_ids = top_community.get("transaction_ids", [])

        # Store Phase 1 candidates if low-to-medium amount and suspicious ring
        if ring_score >= 0.50 and top_community.get("mean_amount", 0.0) < 500.0:
            self.historical_phase1_communities.append(top_community)

        # 3. Cross-Phase Escalation Linkage
        escalated_events = self.phase_linker.link_phases(
            self.historical_phase1_communities,
            transactions,
            high_value_threshold=1000.0
        )
        escalation_score = 0.0
        if escalated_events:
            escalation_score = max(e.get("escalation_score", 0.0) for e in escalated_events)

        # 4. Risk Fusion
        fusion_result = self.fusion_engine.fuse_signals(
            regime_score=regime_score,
            ring_score=ring_score,
            escalation_score=escalation_score,
            context={"community_count": len(communities)}
        )
        overall_risk_score = fusion_result["overall_risk_score"]

        # 5. Tail Exposure & Expected Loss
        exposure_result = self.exposure_estimator.compute_exposure_metrics(
            window_transactions=transactions,
            implicated_tx_ids=implicated_tx_ids,
            ring_risk_score=ring_score
        )

        # 6. Cost-Sensitive Decision
        decision_result = self.decision_engine.evaluate_action(
            overall_risk_score=overall_risk_score,
            expected_fraud_exposure=exposure_result["expected_fraud_exposure"],
            implicated_volume=exposure_result["implicated_volume"],
            ring_score=ring_score,
            escalation_score=escalation_score
        )

        # Construct Full Audit Record
        alert_id = f"ALT_{uuid.uuid4().hex[:8].upper()}"
        return {
            "alert_id": alert_id,
            "timestamp": transactions[-1].get("timestamp", 0),
            "window_size": len(transactions),
            "decision": decision_result["recommended_action"],
            "risk_assessment": {
                "overall_risk_score": overall_risk_score,
                "components": fusion_result["component_scores"],
                "reason_codes": fusion_result["reason_codes"]
            },
            "temporal_regime": {
                "regime": last_diagnosis.regime.value if last_diagnosis else None,
                "regime_score": regime_score,
                "is_suspicious_regime": last_diagnosis.is_suspicious_regime if last_diagnosis else None,
                "reason_codes": last_diagnosis.reason_codes if last_diagnosis else [],
            },
            "exposure_metrics": exposure_result,
            "decision_economics": decision_result,
            "graph_intelligence": {
                "detected_communities_count": len(communities),
                "top_community": top_community,
                "escalated_events": escalated_events
            }
        }

    def _empty_response(self) -> Dict[str, Any]:
        return {
            "alert_id": "NONE",
            "decision": "MONITOR",
            "risk_assessment": {
                "overall_risk_score": 0.0,
                "components": {"regime_score": 0.0, "ring_score": 0.0, "escalation_score": 0.0},
                "reason_codes": []
            },
            "exposure_metrics": {},
            "decision_economics": {"recommended_action": "MONITOR"}
        }
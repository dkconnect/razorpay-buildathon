from typing import Any, Dict, List, Optional
import uuid
import numpy as np

from features.temporal import TemporalFeatureExtractor

# Robust import handling for CUSUM detector class
try:
    from detection.cusum import MultiSignalCUSUMDetector as CUSUMClass
except ImportError:
    try:
        from detection.cusum import CUSUMDetector as CUSUMClass
    except ImportError:
        from detection.cusum import MultiCUSUMDetector as CUSUMClass

from detection.graph_detector import GraphRingDetector, PhaseLinker
from detection.fusion import RiskFusionEngine
from exposure.evt import TailExposureEstimator
from decision.cost_engine import CostSensitiveDecisionEngine


class FraudSentinelPipeline:
    """Integrated Risk Management Sentinel for Coordinated Attacks & Flash Sales."""

    def __init__(
        self,
        window_minutes: int = 30,
        baseline_rate: float = 2.0,
        min_cluster_size: int = 2,
    ):
        self.window_minutes = window_minutes
        self.temporal_extractor = TemporalFeatureExtractor()
        
        # Instantiate CUSUMDetector with baseline
        try:
            self.cusum_detector = CUSUMClass(baseline=baseline_rate)
        except TypeError:
            try:
                self.cusum_detector = CUSUMClass(baseline_rate)
            except TypeError:
                self.cusum_detector = CUSUMClass()
            
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
        baseline_stats: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        Processes a sliding window of transactions and generates an auditable risk report.
        """
        if not transactions:
            return self._empty_response()

        # 1. Temporal Detection
        amounts = [t.get("amount", 0.0) for t in transactions]
        n_tx = len(transactions)
        
        expected_rate = baseline_stats.get("mean_velocity", 2.0) if baseline_stats else 2.0
        observed_rate = n_tx / max(1.0, float(self.window_minutes))
        
        regime_score = float(1.0 - np.exp(-1.2 * max(0.0, (observed_rate / max(0.1, expected_rate)) - 1.0)))
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
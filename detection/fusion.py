from typing import Any, Dict, List, Optional
import numpy as np


class RiskFusionEngine:
    """will fuse the independent temporal, structural, and behavioral risk signals."""

    def __init__(
        self,
        weight_regime: float = 0.35,
        weight_ring: float = 0.40,
        weight_escalation: float = 0.25,
    ):
        total = weight_regime + weight_ring + weight_escalation
        self.w_regime = weight_regime / total
        self.w_ring = weight_ring / total
        self.w_escalation = weight_escalation / total

    def fuse_signals(
        self,
        regime_score: float,
        ring_score: float,
        escalation_score: float = 0.0,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:

        r_score = float(np.clip(regime_score, 0.0, 1.0))
        g_score = float(np.clip(ring_score, 0.0, 1.0))
        e_score = float(np.clip(escalation_score, 0.0, 1.0))

        # Base weighted fusion
        regime_component = self.w_regime * r_score

        # A velocity spike alone is exactly what a legitimate flash sale
        # looks like. If the graph layer has NOT confirmed a coordinated
        # ring (g_score below the "strong ring" bar used elsewhere in this
        # class, see cooccurrence_boost below), discount the raw velocity
        # contribution rather than let it alone push overall risk into
        # "moderate" territory. Without this, a pure organic traffic spike
        # can cross the decision engine's HOLD threshold on velocity alone,
        # even though the graph layer correctly identified it as low-ring.
        if r_score >= 0.60 and g_score < 0.50:
            regime_component *= 0.25

        base_fused = (
            regime_component +
            self.w_ring * g_score +
            self.w_escalation * e_score
        )

        # Multiplicative boost if both temporal change AND strong graph ring co-occur
        cooccurrence_boost = 0.0
        if r_score >= 0.50 and g_score >= 0.50:
            cooccurrence_boost = 0.15 * (r_score * g_score)

        overall_risk_score = float(np.clip(base_fused + cooccurrence_boost, 0.0, 1.0))
        overall_risk_score = round(overall_risk_score, 4)

        # Reason code generation
        reason_codes: List[str] = []
        if r_score >= 0.60:
            reason_codes.append("ABNORMAL_TEMPORAL_VELOCITY_REGIME")
        if g_score >= 0.60:
            reason_codes.append("COORDINATED_IDENTITY_RING_DETECTED")
        if e_score >= 0.50:
            reason_codes.append("ESCALATED_HIGH_VALUE_BUSTOUT_ACTIVITY")
        if r_score >= 0.60 and g_score < 0.30:
            reason_codes.append("ORGANIC_OR_PROMOTIONAL_VOLUME_SHIFT")

        return {
            "overall_risk_score": overall_risk_score,
            "component_scores": {
                "regime_score": round(r_score, 4),
                "ring_score": round(g_score, 4),
                "escalation_score": round(e_score, 4)
            },
            "reason_codes": reason_codes,
            "context": context or {}
        }
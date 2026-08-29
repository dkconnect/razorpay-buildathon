from typing import Any, Dict, List
import numpy as np


class CostSensitiveDecisionEngine:
    """Evaluates expected financial costs across defensive intervention policies."""

    def __init__(
        self,
        cost_investigation_review: float = 50.0,    # Flat operational review cost
        cost_hold_friction: float = 150.0,          # Merchant settlement delay friction
        fp_friction_rate: float = 0.05,             # 5% customer churn penalty on false positive holds
    ):
        self.c_review = cost_investigation_review
        self.c_hold = cost_hold_friction
        self.fp_rate = fp_friction_rate

    def evaluate_action(
        self,
        overall_risk_score: float,
        expected_fraud_exposure: float,
        implicated_volume: float,
        ring_score: float = 0.0,
        escalation_score: float = 0.0
    ) -> Dict[str, Any]:
        """
        Computes the expected cost of:
          - MONITOR:
              ExpectedCost = expected_fraud_exposure (100% loss unmitigated)
          - FLAG_FOR_REVIEW:
              Investigator catches fraud with prob 0.85 -> saves 85% of loss
              ExpectedCost = (1 - 0.85)*exposure + c_review
          - HOLD_FOR_REVIEW:
              Immediately secures 100% of exposure
              ExpectedCost = c_review + c_hold + (1 - risk_score)*(fp_rate * implicated_volume)
        """
        p_risk = float(np.clip(overall_risk_score, 0.0, 1.0))
        exposure = max(0.0, float(expected_fraud_exposure))
        volume = max(0.0, float(implicated_volume))

        # Expected cost formulations
        cost_monitor = exposure

        # FLAG review: Investigator catches 85% of fraud asynchronously
        cost_flag = 0.15 * exposure + self.c_review

        # HOLD review: 100% loss prevented immediately, with friction if FP
        false_positive_prob = max(0.0, 1.0 - p_risk)
        cost_hold = (
            self.c_review +
            self.c_hold +
            false_positive_prob * (self.fp_rate * volume)
        )

        costs = {
            "MONITOR": round(cost_monitor, 2),
            "FLAG_FOR_REVIEW": round(cost_flag, 2),
            "HOLD_FOR_REVIEW": round(cost_hold, 2)
        }

        # Select action with minimal expected cost
        best_action = min(costs, key=costs.get)

        # Safety Guardrails:
        # If risk is minimal (< 0.25) or exposure is zero, default to MONITOR
        if p_risk < 0.25 and exposure < 100.0:
            best_action = "MONITOR"
        # If escalation is confirmed and ring_score >= 0.70 with substantial exposure, HOLD
        elif escalation_score >= 0.60 and ring_score >= 0.70 and exposure >= 500.0:
            best_action = "HOLD_FOR_REVIEW"

        # Construct justification narrative
        if best_action == "HOLD_FOR_REVIEW":
            justification = (
                f"High risk ({p_risk:.2f}) and significant expected exposure (₹{exposure:,.2f}) "
                f"warrant immediate hold to minimize total loss."
            )
        elif best_action == "FLAG_FOR_REVIEW":
            justification = (
                f"Moderate risk ({p_risk:.2f}) warrants asynchronous investigation "
                f"(expected cost ₹{costs['FLAG_FOR_REVIEW']:,.2f} vs monitor ₹{costs['MONITOR']:,.2f})."
            )
        else:
            justification = f"Low risk ({p_risk:.2f}) and negligible exposure; monitor passively."

        return {
            "recommended_action": best_action,
            "expected_costs": costs,
            "net_savings_vs_monitor": round(max(0.0, cost_monitor - costs[best_action]), 2),
            "justification": justification
        }
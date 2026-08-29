import pytest
from decision.cost_engine import CostSensitiveDecisionEngine


def test_cost_engine_decision_boundaries():
    engine = CostSensitiveDecisionEngine()

    # 1. Low risk / small volume -> MONITOR
    dec_low = engine.evaluate_action(
        overall_risk_score=0.10,
        expected_fraud_exposure=20.0,
        implicated_volume=20.0
    )
    assert dec_low["recommended_action"] == "MONITOR"

    # 2. Moderate risk / medium exposure -> FLAG_FOR_REVIEW
    dec_mod = engine.evaluate_action(
        overall_risk_score=0.60,
        expected_fraud_exposure=800.0,
        implicated_volume=1300.0
    )
    assert dec_mod["recommended_action"] == "FLAG_FOR_REVIEW"
    assert dec_mod["net_savings_vs_monitor"] > 0

    # 3. High risk + high exposure + bustout escalation -> HOLD_FOR_REVIEW
    dec_high = engine.evaluate_action(
        overall_risk_score=0.92,
        expected_fraud_exposure=60000.0,
        implicated_volume=65000.0,
        ring_score=0.90,
        escalation_score=0.85
    )
    assert dec_high["recommended_action"] == "HOLD_FOR_REVIEW"
    assert dec_high["expected_costs"]["HOLD_FOR_REVIEW"] < dec_high["expected_costs"]["MONITOR"]
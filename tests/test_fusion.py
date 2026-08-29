import pytest
from detection.fusion import RiskFusionEngine


def test_fusion_weights_and_bounds():
    engine = RiskFusionEngine(weight_regime=0.35, weight_ring=0.40, weight_escalation=0.25)

    # 1. Clean traffic
    res_clean = engine.fuse_signals(regime_score=0.05, ring_score=0.0, escalation_score=0.0)
    assert res_clean["overall_risk_score"] < 0.10
    assert len(res_clean["reason_codes"]) == 0

    # 2. Flash sale / Legitimate surge: High temporal spike, zero graph ring
    res_flash = engine.fuse_signals(regime_score=0.95, ring_score=0.05, escalation_score=0.0)
    assert res_flash["overall_risk_score"] < 0.45
    assert "ORGANIC_OR_PROMOTIONAL_VOLUME_SHIFT" in res_flash["reason_codes"]

    # 3. Card testing + Bust out coordinated attack
    res_attack = engine.fuse_signals(regime_score=0.85, ring_score=0.90, escalation_score=0.80)
    assert res_attack["overall_risk_score"] >= 0.85
    assert "COORDINATED_IDENTITY_RING_DETECTED" in res_attack["reason_codes"]
    assert "ESCALATED_HIGH_VALUE_BUSTOUT_ACTIVITY" in res_attack["reason_codes"]
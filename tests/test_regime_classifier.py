"""
tests/test_regime_classifier.py
Verifies baseline integrity guards and gated anti-flash-sale fusion.
"""

import pytest
from detection.cusum import BaselineCalibrator, CUSUMState
from detection.regime import RegimeClassifier, RegimeType
from features.temporal import TemporalSnapshot


def test_baseline_contamination_guard():
    dummy_snap = [
        TemporalSnapshot(
            timestamp=0.0,
            window_minutes=15.0,
            tx_count=10,
            velocity_per_min=1.0,
            mean_amount=100.0,
            mean_log_amount=4.6,
            std_log_amount=0.1,
            low_val_ratio=0.0,
            high_val_ratio=0.0,
        )
    ]
    # Attempting to fit on contaminated scenario names MUST raise ValueError
    with pytest.raises(ValueError, match="Data contamination guard triggered"):
        BaselineCalibrator.fit(dummy_snap, scenario_name="mixed_fraud_run1")

    with pytest.raises(ValueError, match="Data contamination guard triggered"):
        BaselineCalibrator.fit(dummy_snap, scenario_name="flash_sale_data")

    # Clean normal scenario succeeds
    profile = BaselineCalibrator.fit(dummy_snap, scenario_name="normal_day_clean")
    assert profile.source_scenario == "normal_day_clean"


def test_flash_sale_zero_fraud_score():
    """Velocity spike alone (S_v+ high) MUST evaluate to regime_score ~ 0."""
    classifier = RegimeClassifier()
    state = CUSUMState(
        timestamp=200.0,
        s_velocity_pos=15.0,        # Massive velocity surge
        s_amount_neg=0.0,           # No micro-transaction drift
        s_high_val_pos=0.0,
        velocity_alert=True,
        amount_alert=False,
        high_val_alert=False,
        normalized_velocity_score=0.99,
        normalized_amount_score=0.0,
        normalized_high_val_score=0.0,
    )
    diag = classifier.classify(state)
    assert diag.regime == RegimeType.FLASH_SALE
    assert not diag.is_suspicious_regime
    assert diag.regime_score == 0.0  # 0.99 * 0.0 = 0.0


def test_card_testing_high_fraud_score():
    """Card testing (S_v+ AND S_a- high) activates Phase 1 risk."""
    classifier = RegimeClassifier()
    state = CUSUMState(
        timestamp=300.0,
        s_velocity_pos=10.0,
        s_amount_neg=8.0,
        s_high_val_pos=0.0,
        velocity_alert=True,
        amount_alert=True,
        high_val_alert=False,
        normalized_velocity_score=0.95,
        normalized_amount_score=0.90,
        normalized_high_val_score=0.0,
    )
    diag = classifier.classify(state)
    assert diag.regime == RegimeType.CARD_TESTING
    assert diag.is_suspicious_regime
    assert diag.regime_score == pytest.approx(0.95 * 0.90, 1e-3)
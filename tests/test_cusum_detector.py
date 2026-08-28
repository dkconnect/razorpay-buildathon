"""
tests/test_cusum_detector.py
Verifies CUSUM behavior under flash sale, card testing, and normal traffic.
"""

import numpy as np
import pytest
from features.temporal import TemporalSnapshot
from detection.cusum import BaselineCalibrator, CUSUMDetector


@pytest.fixture
def baseline():
    snapshots = [
        TemporalSnapshot(
            timestamp=float(h * 3600),
            window_minutes=15.0,
            tx_count=30,
            velocity_per_min=2.0,
            mean_amount=100.0,
            mean_log_amount=float(np.log(100.0)),
            std_log_amount=0.1,
            low_val_ratio=0.02,
            high_val_ratio=0.01,
        )
        for h in range(24)
    ]
    return BaselineCalibrator.fit(snapshots)


def test_cusum_normal_steady_state(baseline):
    detector = CUSUMDetector(baseline=baseline, k_slack=0.5, threshold_h=5.0)
    
    # Ingest 10 normal snapshots
    for i in range(10):
        snap = TemporalSnapshot(
            timestamp=float(i * 60),
            window_minutes=15.0,
            tx_count=30,
            velocity_per_min=2.0,
            mean_amount=100.0,
            mean_log_amount=float(np.log(100.0)),
            std_log_amount=0.1,
            low_val_ratio=0.02,
            high_val_ratio=0.01,
        )
        state = detector.update(snap)

    assert not state.velocity_alert
    assert not state.amount_alert
    assert state.s_velocity_pos == 0.0
    assert state.s_amount_neg == 0.0


def test_cusum_flash_sale_distinction(baseline):
    """Flash sale has high velocity but normal/higher amount distribution."""
    detector = CUSUMDetector(baseline=baseline, k_slack=0.5, threshold_h=5.0)
    
    for i in range(15):
        snap = TemporalSnapshot(
            timestamp=float(i * 60),
            window_minutes=15.0,
            tx_count=150,
            velocity_per_min=10.0,  # 5x volume spike
            mean_amount=120.0,      # amount remains normal/high
            mean_log_amount=float(np.log(120.0)),
            std_log_amount=0.1,
            low_val_ratio=0.02,
            high_val_ratio=0.02,
        )
        state = detector.update(snap)

    # Velocity alert triggers, but Amount Neg (micro-testing) remains 0
    assert state.velocity_alert
    assert not state.amount_alert
    assert state.s_amount_neg == 0.0


def test_cusum_card_testing_detection(baseline):
    """Card testing has high velocity AND significant downward amount drift."""
    detector = CUSUMDetector(baseline=baseline, k_slack=0.5, threshold_h=5.0)
    
    for i in range(15):
        snap = TemporalSnapshot(
            timestamp=float(i * 60),
            window_minutes=15.0,
            tx_count=150,
            velocity_per_min=10.0,  # Velocity spike
            mean_amount=2.0,        # Micro-transaction ($2)
            mean_log_amount=float(np.log(2.0)),
            std_log_amount=0.05,
            low_val_ratio=0.98,
            high_val_ratio=0.0,
        )
        state = detector.update(snap)

    # Both Velocity and Micro-Amount alerts trigger
    assert state.velocity_alert
    assert state.amount_alert
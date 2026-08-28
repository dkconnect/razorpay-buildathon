import numpy as np
import pytest
from features.temporal import TemporalSnapshot
from detection.cusum import BaselineCalibrator


def test_baseline_calibrator_fitting():
    snapshots = []
    
    for t_hour in range(48):
        hour_of_day = t_hour % 24
        ts = t_hour * 3600.0

        vel = 2.0 + 0.5 * hour_of_day
        log_amt = float(np.log(100.0))
        
        snapshots.append(
            TemporalSnapshot(
                timestamp=ts,
                window_minutes=15.0,
                tx_count=int(vel * 15),
                velocity_per_min=vel,
                mean_amount=100.0,
                mean_log_amount=log_amt,
                std_log_amount=0.1,
                low_val_ratio=0.02,
                high_val_ratio=0.01,
            )
        )

    profile = BaselineCalibrator.fit(snapshots)

    assert len(profile.hourly_velocity_mean) == 24
    assert profile.hourly_velocity_mean[0] == pytest.approx(2.0, 1e-3)
    assert profile.hourly_velocity_mean[10] == pytest.approx(7.0, 1e-3)
    assert profile.hourly_log_amt_mean[0] == pytest.approx(np.log(100.0), 1e-3)
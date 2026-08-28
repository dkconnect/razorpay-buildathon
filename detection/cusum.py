#Baseline Calibration and Online CUSUM Regime Detectors.


from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import numpy as np

from features.temporal import TemporalSnapshot


@dataclass
class BaselineProfile:
# expected values and SD for temporal metrics.
    hourly_velocity_mean: np.ndarray      
    hourly_velocity_std: np.ndarray      
    hourly_log_amt_mean: np.ndarray      
    hourly_log_amt_std: np.ndarray       
    hourly_low_ratio_mean: np.ndarray     
    hourly_low_ratio_std: np.ndarray    
    hourly_high_ratio_mean: np.ndarray   
    hourly_high_ratio_std: np.ndarray   


class BaselineCalibrator:

    @staticmethod
    def fit(snapshots: List[TemporalSnapshot]) -> BaselineProfile:
        # first 24 hrs
        hours = np.array([int((s.timestamp // 3600) % 24) for s in snapshots])
        velocities = np.array([s.velocity_per_min for s in snapshots])
        log_amts = np.array([s.mean_log_amount for s in snapshots])
        low_ratios = np.array([s.low_val_ratio for s in snapshots])
        high_ratios = np.array([s.high_val_ratio for s in snapshots])

        h_vel_mean = np.zeros(24)
        h_vel_std = np.zeros(24)
        h_log_mean = np.zeros(24)
        h_log_std = np.zeros(24)
        h_low_mean = np.zeros(24)
        h_low_std = np.zeros(24)
        h_high_mean = np.zeros(24)
        h_high_std = np.zeros(24)

        for h in range(24):
            mask = (hours == h)
            if np.any(mask):
                h_vel_mean[h] = np.mean(velocities[mask])
                h_vel_std[h] = max(float(np.std(velocities[mask])), 0.1)
                
                h_log_mean[h] = np.mean(log_amts[mask])
                h_log_std[h] = max(float(np.std(log_amts[mask])), 0.05)

                h_low_mean[h] = np.mean(low_ratios[mask])
                h_low_std[h] = max(float(np.std(low_ratios[mask])), 0.01)

                h_high_mean[h] = np.mean(high_ratios[mask])
                h_high_std[h] = max(float(np.std(high_ratios[mask])), 0.01)
                
            else:
                h_vel_mean[h] = np.mean(velocities) if len(velocities) > 0 else 1.0
                h_vel_std[h] = np.std(velocities) if len(velocities) > 0 else 0.5
                h_log_mean[h] = np.mean(log_amts) if len(log_amts) > 0 else 4.0
                h_log_std[h] = np.std(log_amts) if len(log_amts) > 0 else 0.5
                h_low_mean[h] = 0.05
                h_low_std[h] = 0.02
                h_high_mean[h] = 0.02
                h_high_std[h] = 0.01

        return BaselineProfile(
            hourly_velocity_mean=h_vel_mean,
            hourly_velocity_std=h_vel_std,
            hourly_log_amt_mean=h_log_mean,
            hourly_log_amt_std=h_log_std,
            hourly_low_ratio_mean=h_low_mean,
            hourly_low_ratio_std=h_low_std,
            hourly_high_ratio_mean=h_high_mean,
            hourly_high_ratio_std=h_high_std,
        )
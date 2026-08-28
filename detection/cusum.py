"""
detection/cusum.py
Baseline Calibration and Multi-Signal Online CUSUM Regime Detectors.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import numpy as np

from features.temporal import TemporalSnapshot


@dataclass
class BaselineProfile:
    """Hourly expected values and standard deviations for temporal metrics."""
    hourly_velocity_mean: np.ndarray      # Shape: (24,)
    hourly_velocity_std: np.ndarray       # Shape: (24,)
    hourly_log_amt_mean: np.ndarray       # Shape: (24,)
    hourly_log_amt_std: np.ndarray        # Shape: (24,)
    hourly_low_ratio_mean: np.ndarray     # Shape: (24,)
    hourly_low_ratio_std: np.ndarray      # Shape: (24,)
    hourly_high_ratio_mean: np.ndarray    # Shape: (24,)
    hourly_high_ratio_std: np.ndarray     # Shape: (24,)


class BaselineCalibrator:
    """
    Fits non-stationary diurnal baseline parameters using historical clean/normal traffic.
    """

    @staticmethod
    def fit(snapshots: List[TemporalSnapshot]) -> BaselineProfile:
        """
        Fits 24-hour profiles from a list of snapshots generated from normal training data.
        """
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


@dataclass
class CUSUMState:
    """Tracks state and changepoint flags across all three temporal signals."""
    timestamp: float
    s_velocity_pos: float
    s_amount_neg: float
    s_high_val_pos: float
    velocity_alert: bool
    amount_alert: bool
    high_val_alert: bool
    normalized_velocity_score: float   # in [0, 1]
    normalized_amount_score: float     # in [0, 1]
    normalized_high_val_score: float   # in [0, 1]


class CUSUMDetector:
    """
    Multi-Signal Online CUSUM detector tracking:
    1. Upward velocity drift (S_v^+)
    2. Downward log-amount drift (S_a^-)
    3. Upward high-value transaction rate (S_bust^+)
    """

    def __init__(
        self,
        baseline: BaselineProfile,
        k_slack: float = 0.5,
        threshold_h: float = 5.0,
    ):
        self.baseline = baseline
        self.k = k_slack
        self.h = threshold_h

        # Accumulator states
        self.s_velocity: float = 0.0
        self.s_amount: float = 0.0
        self.s_high_val: float = 0.0

    def reset(self) -> None:
        """Resets all accumulators to zero."""
        self.s_velocity = 0.0
        self.s_amount = 0.0
        self.s_high_val = 0.0

    def update(self, snapshot: TemporalSnapshot) -> CUSUMState:
        """
        Updates CUSUM accumulators with the latest sliding window snapshot.
        """
        hour = int((snapshot.timestamp // 3600) % 24)

        # 1. Standardize inputs against diurnal baselines
        z_vel = (
            snapshot.velocity_per_min - self.baseline.hourly_velocity_mean[hour]
        ) / self.baseline.hourly_velocity_std[hour]

        z_amt = (
            snapshot.mean_log_amount - self.baseline.hourly_log_amt_mean[hour]
        ) / self.baseline.hourly_log_amt_std[hour]

        z_high = (
            snapshot.high_val_ratio - self.baseline.hourly_high_ratio_mean[hour]
        ) / self.baseline.hourly_high_ratio_std[hour]

        # 2. Update CUSUM accumulators
        # Upward velocity shift
        self.s_velocity = max(0.0, self.s_velocity + z_vel - self.k)

        # Downward log amount shift (Negative drift indicates micro-testing)
        self.s_amount = max(0.0, self.s_amount - z_amt - self.k)

        # Upward high-value breakout (Bust-out)
        self.s_high_val = max(0.0, self.s_high_val + z_high - self.k)

        # 3. Check threshold exceedance
        vel_alert = bool(self.s_velocity >= self.h)
        amt_alert = bool(self.s_amount >= self.h)
        high_alert = bool(self.s_high_val >= self.h)

        # 4. Normalize accumulators to [0, 1] scores using sigmoid saturation
        norm_vel = float(np.tanh(self.s_velocity / self.h))
        norm_amt = float(np.tanh(self.s_amount / self.h))
        norm_high = float(np.tanh(self.s_high_val / self.h))

        return CUSUMState(
            timestamp=snapshot.timestamp,
            s_velocity_pos=self.s_velocity,
            s_amount_neg=self.s_amount,
            s_high_val_pos=self.s_high_val,
            velocity_alert=vel_alert,
            amount_alert=amt_alert,
            high_val_alert=high_alert,
            normalized_velocity_score=norm_vel,
            normalized_amount_score=norm_amt,
            normalized_high_val_score=norm_high,
        )
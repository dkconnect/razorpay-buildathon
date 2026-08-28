"""
detection/cusum.py
Baseline Calibration and Multi-Signal Online CUSUM Regime Detectors.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional
import numpy as np

from features.temporal import TemporalSnapshot


@dataclass
class BaselineProfile:
    """Hourly expected values and standard deviations for temporal metrics."""
    source_scenario: str
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
    Fits non-stationary diurnal baseline parameters strictly from clean normal traffic.
    """

    @staticmethod
    def fit(snapshots: List[TemporalSnapshot], scenario_name: str = "normal_day") -> BaselineProfile:
        # Strict enforcement against baseline contamination
        if "normal" not in scenario_name.lower() or "fraud" in scenario_name.lower() or "flash" in scenario_name.lower():
            raise ValueError(
                f"Data contamination guard triggered! Baseline calibration can only run on clean normal traffic. "
                f"Attempted to calibrate on: '{scenario_name}'"
            )

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
            source_scenario=scenario_name,
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
    def __init__(
        self,
        baseline: BaselineProfile,
        k_slack: float = 0.5,
        threshold_h: float = 5.0,
        min_window_count: int = 50,
    ):
        self.baseline = baseline
        self.k = k_slack
        self.h = threshold_h
        # high_val_ratio is a proportion estimated from the window's tx count.
        # Below this sample size the proportion is too noisy to trust as
        # evidence (nighttime/low-traffic windows can have n~30 vs n~165
        # in the day) - the CUSUM simply holds rather than accumulating
        # on an unreliable small-sample estimate.
        self.min_window_count = min_window_count
        self.s_velocity: float = 0.0
        self.s_amount: float = 0.0
        self.s_high_val: float = 0.0

    def reset(self) -> None:
        self.s_velocity = 0.0
        self.s_amount = 0.0
        self.s_high_val = 0.0

    def update(self, snapshot: TemporalSnapshot) -> CUSUMState:
        hour = int((snapshot.timestamp // 3600) % 24)

        z_vel = (
            snapshot.velocity_per_min - self.baseline.hourly_velocity_mean[hour]
        ) / self.baseline.hourly_velocity_std[hour]

        z_amt = (
            snapshot.mean_log_amount - self.baseline.hourly_log_amt_mean[hour]
        ) / self.baseline.hourly_log_amt_std[hour]

        z_high = (
            snapshot.high_val_ratio - self.baseline.hourly_high_ratio_mean[hour]
        ) / self.baseline.hourly_high_ratio_std[hour]

        self.s_velocity = max(0.0, self.s_velocity + z_vel - self.k)
        self.s_amount = max(0.0, self.s_amount - z_amt - self.k)
        if snapshot.tx_count >= self.min_window_count:
            self.s_high_val = max(0.0, self.s_high_val + z_high - self.k)
        # else: hold s_high_val unchanged - window too small to trust the ratio

        vel_alert = bool(self.s_velocity >= self.h)
        amt_alert = bool(self.s_amount >= self.h)
        high_alert = bool(self.s_high_val >= self.h)

        # Capture magnitudes BEFORE reset, so a snapshot that just fired an
        # alert still reports the score that caused it (not 0). Downstream
        # regime_score fusion depends on this being non-zero at the moment
        # of alarm.
        s_velocity_report = self.s_velocity
        s_amount_report = self.s_amount
        s_high_val_report = self.s_high_val

        norm_vel = float(np.tanh(s_velocity_report / self.h))
        norm_amt = float(np.tanh(s_amount_report / self.h))
        norm_high = float(np.tanh(s_high_val_report / self.h))

        # Classical CUSUM reset-on-alarm: once a sum crosses h, the alarm is
        # logged for THIS snapshot, then the sum resets to 0 so the detector
        # can find the next changepoint instead of staying pinned above
        # threshold indefinitely.
        if vel_alert:
            self.s_velocity = 0.0
        if amt_alert:
            self.s_amount = 0.0
        if high_alert:
            self.s_high_val = 0.0

        return CUSUMState(
            timestamp=snapshot.timestamp,
            s_velocity_pos=s_velocity_report,
            s_amount_neg=s_amount_report,
            s_high_val_pos=s_high_val_report,
            velocity_alert=vel_alert,
            amount_alert=amt_alert,
            high_val_alert=high_alert,
            normalized_velocity_score=norm_vel,
            normalized_amount_score=norm_amt,
            normalized_high_val_score=norm_high,
        )
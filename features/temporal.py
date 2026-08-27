"""
Online streaming temporal feature extractor across sliding time windows.
"""

from collections import deque
from dataclasses import dataclass
from typing import Dict, List, Optional
import numpy as np


@dataclass
class TemporalSnapshot:
    timestamp: float
    window_minutes: float
    tx_count: int
    velocity_per_min: float
    mean_amount: float
    mean_log_amount: float
    std_log_amount: float
    # <= threshold_low (e.g. 50.0)
    low_val_ratio: float      
    # >= threshold_high (e.g. 5000.0)
    high_val_ratio: float     


class TemporalFeatureExtractor:
# to maintain online sliding windows of transactions to compute temporal & distributional shift metrics at transaction arrival time.

    def __init__(
        self,
        window_minutes: float = 15.0,
        threshold_low: float = 50.0,
        threshold_high: float = 5000.0,
    ):
        self.window_seconds = window_minutes * 60.0
        self.window_minutes = window_minutes
        self.threshold_low = threshold_low
        self.threshold_high = threshold_high
        self.buffer: deque = deque()
        self._sum_amount: float = 0.0
        self._sum_log_amount: float = 0.0
        self._sum_sq_log_amount: float = 0.0
        self._count_low: int = 0
        self._count_high: int = 0

    def _evict_stale(self, current_time: float) -> None:
        cutoff = current_time - self.window_seconds
        while self.buffer and self.buffer[0][0] < cutoff:
            _, amt, log_amt = self.buffer.popleft()
            self._sum_amount -= amt
            self._sum_log_amount -= log_amt
            self._sum_sq_log_amount -= (log_amt ** 2)
            if amt <= self.threshold_low:
                self._count_low -= 1
            if amt >= self.threshold_high:
                self._count_high -= 1

    def update(self, timestamp: float, amount: float) -> TemporalSnapshot:
        # returns the current window snapshot.

        log_amt = float(np.log(max(amount, 0.01)))
        
        self._evict_stale(timestamp)
        
        self.buffer.append((timestamp, amount, log_amt))
        self._sum_amount += amount
        self._sum_log_amount += log_amt
        self._sum_sq_log_amount += (log_amt ** 2)
        if amount <= self.threshold_low:
            self._count_low += 1
        if amount >= self.threshold_high:
            self._count_high += 1

        n = len(self.buffer)
        velocity = n / self.window_minutes
        mean_amt = self._sum_amount / n
        mean_log_amt = self._sum_log_amount / n
        
        variance_log = max(0.0, (self._sum_sq_log_amount / n) - (mean_log_amt ** 2))
        std_log_amt = float(np.sqrt(variance_log))
        
        low_ratio = self._count_low / n
        high_ratio = self._count_high / n

        return TemporalSnapshot(
            timestamp=timestamp,
            window_minutes=self.window_minutes,
            tx_count=n,
            velocity_per_min=velocity,
            mean_amount=mean_amt,
            mean_log_amount=mean_log_amt,
            std_log_amount=std_log_amt,
            low_val_ratio=low_ratio,
            high_val_ratio=high_ratio,
        )

    def process_stream(self, transactions: List[Dict]) -> List[TemporalSnapshot]:
        snapshots = []
        for tx in transactions:
            ts = float(tx["timestamp"])
            amt = float(tx["amount"])
            snapshots.append(self.update(ts, amt))
        return snapshots
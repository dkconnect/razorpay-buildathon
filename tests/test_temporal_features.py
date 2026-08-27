import numpy as np
import pytest
from features.temporal import TemporalFeatureExtractor


def test_temporal_extractor_eviction():
    extractor = TemporalFeatureExtractor(window_minutes=1.0, threshold_low=50.0, threshold_high=5000.0)
    
    # Tx 1 at t=0, $10 (low value)
    snap1 = extractor.update(timestamp=0.0, amount=10.0)
    assert snap1.tx_count == 1
    assert snap1.velocity_per_min == 1.0
    assert snap1.low_val_ratio == 1.0
    
    # Tx 2 at t=30, $6000 (high value)
    snap2 = extractor.update(timestamp=30.0, amount=6000.0)
    assert snap2.tx_count == 2
    assert snap2.velocity_per_min == 2.0
    assert snap2.low_val_ratio == 0.5
    assert snap2.high_val_ratio == 0.5
    
    # Tx 3 at t=70 (Tx 1 at t=0 evicted since window is 60s)
    snap3 = extractor.update(timestamp=70.0, amount=200.0)
    assert snap3.tx_count == 2  # contains Tx 2 (t=30) and Tx 3 (t=70)
    assert snap3.low_val_ratio == 0.0
    assert snap3.high_val_ratio == 0.5


def test_distribution_moments():
    extractor = TemporalFeatureExtractor(window_minutes=5.0)
    amounts = [100.0, 100.0, 100.0]
    
    for i, amt in enumerate(amounts):
        snap = extractor.update(timestamp=float(i * 10), amount=amt)
        
    assert snap.mean_amount == 100.0
    assert pytest.approx(snap.mean_log_amount, 1e-4) == np.log(100.0)
    assert pytest.approx(snap.std_log_amount, 1e-4) == 0.0
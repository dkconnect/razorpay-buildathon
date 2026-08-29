import pytest
import numpy as np
from exposure.evt import TailExposureEstimator


def test_tail_exposure_metrics_computation():
    estimator = TailExposureEstimator(tail_percentile=90.0, alpha=0.95)

    # 100 transactions with lognormal tail
    np.random.seed(42)
    sample_amounts = list(np.random.lognormal(mean=4.0, sigma=1.2, size=150))
    transactions = [
        {"transaction_id": f"tx_{i}", "amount": amt}
        for i, amt in enumerate(sample_amounts)
    ]

    implicated_ids = ["tx_0", "tx_1", "tx_2"]
    res = estimator.compute_exposure_metrics(
        window_transactions=transactions,
        implicated_tx_ids=implicated_ids,
        ring_risk_score=0.85
    )

    assert res["total_window_volume"] > 0
    assert res["tail_metrics"]["var_95"] > res["tail_metrics"]["threshold_u"]
    assert res["tail_metrics"]["cvar_95"] >= res["tail_metrics"]["var_95"]
    assert res["implicated_volume"] > 0
    assert res["expected_fraud_exposure"] == round(0.85 * res["implicated_volume"], 2)


def test_small_sample_edge_case():
    estimator = TailExposureEstimator()
    transactions = [
        {"transaction_id": "tx_1", "amount": 10.0},
        {"transaction_id": "tx_2", "amount": 20.0},
    ]

    res = estimator.compute_exposure_metrics(transactions)
    assert res["total_window_volume"] == 30.0
    assert res["tail_metrics"]["var_95"] >= 0.0
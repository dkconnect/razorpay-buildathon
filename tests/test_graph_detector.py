import pytest
from detection.graph_detector import GraphRingDetector


def test_community_detection_separates_independent_rings():
    detector = GraphRingDetector(min_cluster_size=2)

    # Ring 1: 3 transactions sharing dev_1 and ip_1
    ring1 = [
        {"transaction_id": "tx_1", "amount": 10.0, "timestamp": 10, "device_id": "dev_1", "ip_subnet": "1.1.1.0", "card_bin": "411111", "customer_id": "c1"},
        {"transaction_id": "tx_2", "amount": 15.0, "timestamp": 11, "device_id": "dev_1", "ip_subnet": "1.1.1.0", "card_bin": "411111", "customer_id": "c2"},
        {"transaction_id": "tx_3", "amount": 12.0, "timestamp": 12, "device_id": "dev_1", "ip_subnet": "1.1.1.0", "card_bin": "411111", "customer_id": "c3"},
    ]

    # Ring 2: 2 transactions sharing dev_2
    ring2 = [
        {"transaction_id": "tx_4", "amount": 50.0, "timestamp": 20, "device_id": "dev_2", "ip_subnet": "2.2.2.0", "card_bin": "510000", "customer_id": "c4"},
        {"transaction_id": "tx_5", "amount": 55.0, "timestamp": 21, "device_id": "dev_2", "ip_subnet": "2.2.2.0", "card_bin": "510000", "customer_id": "c5"},
    ]

    # Legitimate isolated transaction
    isolated = [
        {"transaction_id": "tx_6", "amount": 100.0, "timestamp": 30, "device_id": "dev_3", "ip_subnet": "3.3.3.0", "card_bin": "601100", "customer_id": "c6"},
    ]

    transactions = ring1 + ring2 + isolated
    communities = detector.detect_communities(transactions)

    # Should detect 2 communities (isolated single tx is excluded by min_cluster_size=2)
    assert len(communities) == 2

    # Ring 1 verification
    comm1 = next(c for c in communities if "tx_1" in c["transaction_ids"])
    assert comm1["transaction_count"] == 3
    assert "dev_1" in comm1["shared_devices"]
    assert "1.1.1.0" in comm1["shared_ips"]
    assert comm1["features"]["device_reuse_ratio"] == 3.0

    # Ring 2 verification
    comm2 = next(c for c in communities if "tx_4" in c["transaction_ids"])
    assert comm2["transaction_count"] == 2
    assert "dev_2" in comm2["shared_devices"]
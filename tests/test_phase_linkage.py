import pytest
from detection.graph_detector import GraphRingDetector, PhaseLinker


def test_phase_linkage_detects_bustout_escalation():
    detector = GraphRingDetector()

    # Phase 1: Small card-testing attempts sharing device_test_1
    phase1_txs = [
        {"transaction_id": "tx_p1_1", "amount": 10.0, "timestamp": 10, "device_id": "dev_test_1", "ip_subnet": "192.168.1.0", "card_bin": "411111", "customer_id": "c1"},
        {"transaction_id": "tx_p1_2", "amount": 15.0, "timestamp": 11, "device_id": "dev_test_1", "ip_subnet": "192.168.1.0", "card_bin": "411111", "customer_id": "c2"},
        {"transaction_id": "tx_p1_3", "amount": 12.0, "timestamp": 12, "device_id": "dev_test_1", "ip_subnet": "192.168.1.0", "card_bin": "411111", "customer_id": "c3"},
    ]

    p1_comms = detector.detect_communities(phase1_txs)
    assert len(p1_comms) == 1
    assert p1_comms[0]["ring_score"] >= 0.65

    # Phase 2: High-value bust-out attempt with same device
    phase2_txs = [
        {"transaction_id": "tx_p2_bustout", "amount": 45000.0, "timestamp": 500, "device_id": "dev_test_1", "ip_subnet": "192.168.1.0", "card_bin": "411111", "customer_id": "c1"},
        {"transaction_id": "tx_p2_legit", "amount": 15000.0, "timestamp": 510, "device_id": "dev_clean_9", "ip_subnet": "10.0.0.0", "card_bin": "510000", "customer_id": "c9"},
    ]

    escalated = PhaseLinker.link_phases(p1_comms, phase2_txs, high_value_threshold=1000.0)

    # Only the first tx should be linked as an escalated bust-out
    assert len(escalated) == 1
    assert escalated[0]["transaction_id"] == "tx_p2_bustout"
    assert escalated[0]["is_escalated_bustout"] is True
    assert escalated[0]["linked_community_id"] == p1_comms[0]["community_id"]
    assert "device:dev_test_1" in escalated[0]["shared_entities"]
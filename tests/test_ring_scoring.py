import json
import pytest
from detection.graph_detector import GraphRingDetector


def test_ring_score_bounds_and_ordering():
    detector = GraphRingDetector()

    # Highly suspicious cluster: 10 transactions sharing 1 device, 1 IP, 1 BIN, 10 distinct customers
    coordinated_ring = [
        {
            "transaction_id": f"tx_{i}",
            "amount": 10.0,
            "timestamp": 100 + i,
            "device_id": "bot_device_1",
            "ip_subnet": "192.168.100.0",
            "card_bin": "411111",
            "customer_id": f"fake_cust_{i}"
        }
        for i in range(10)
    ]

    comm = detector.detect_communities(coordinated_ring)
    assert len(comm) == 1
    assert comm[0]["ring_score"] >= 0.75

    # Organic traffic: 10 transactions with completely independent entities
    organic_traffic = [
        {
            "transaction_id": f"tx_org_{i}",
            "amount": 100.0 + i,
            "timestamp": 200 + i,
            "device_id": f"dev_{i}",
            "ip_subnet": f"10.0.{i}.0",
            "card_bin": f"40000{i}",
            "customer_id": f"cust_{i}"
        }
        for i in range(10)
    ]
    # In organic traffic without shared entities, projection has no edges, no communities >= min_cluster_size
    comm_org = detector.detect_communities(organic_traffic)
    assert len(comm_org) == 0


def test_flash_sale_vs_fraud_generated_dataset():
    detector = GraphRingDetector(min_cluster_size=3)

    # 1. Load flash sale dataset - should have minimal or low-scoring rings
    with open("data/generated/flash_sale.json", "r") as f:
        flash_data = json.load(f)
    
    flash_txs = flash_data if isinstance(flash_data, list) else flash_data.get("transactions", [])
    flash_comms = detector.detect_communities(flash_txs[:200])
    
    # In flash sales, organic traffic has low reuse across distinct customers
    for c in flash_comms:
        assert c["ring_score"] < 0.65

    # 2. Load mixed fraud dataset - must detect high-confidence fraud rings
    with open("data/generated/mixed_fraud.json", "r") as f:
        mixed_data = json.load(f)
        
    mixed_txs = mixed_data if isinstance(mixed_data, list) else mixed_data.get("transactions", [])
    mixed_comms = detector.detect_communities(mixed_txs)
    
    assert len(mixed_comms) > 0
    top_ring = mixed_comms[0]
    assert top_ring["ring_score"] >= 0.70
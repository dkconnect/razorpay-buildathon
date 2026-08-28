import pytest
from features.graph_features import TransactionGraphBuilder, GraphFeatureExtractor


def test_heterogeneous_graph_construction():
    builder = TransactionGraphBuilder()
    transactions = [
        {"transaction_id": "tx_1", "amount": 10.0, "timestamp": 100, "device_id": "dev_A", "ip_subnet": "192.168.1.0", "card_bin": "411111", "customer_id": "cust_1"},
        {"transaction_id": "tx_2", "amount": 12.0, "timestamp": 105, "device_id": "dev_A", "ip_subnet": "192.168.1.0", "card_bin": "411111", "customer_id": "cust_2"},
        {"transaction_id": "tx_3", "amount": 250.0, "timestamp": 110, "device_id": "dev_B", "ip_subnet": "10.0.0.0", "card_bin": "550000", "customer_id": "cust_3"},
    ]

    G = builder.build_window_graph(transactions)
    assert G.number_of_nodes() == 3 + 2 + 2 + 2 + 3  # 3 tx + 2 dev + 2 ip + 2 bin + 3 cust = 12 nodes
    assert G.has_edge("tx_tx_1", "dev_dev_A")
    assert G.has_edge("tx_tx_2", "dev_dev_A")

    proj_G = builder.build_transaction_projection(G)
    assert proj_G.has_edge("tx_tx_1", "tx_tx_2")
    assert proj_G["tx_tx_1"]["tx_tx_2"]["weight"] == 3  # Shared dev, ip, bin
    assert not proj_G.has_edge("tx_tx_1", "tx_tx_3")


def test_feature_extractor_metrics():
    builder = TransactionGraphBuilder()
    extractor = GraphFeatureExtractor()
    transactions = [
        {"transaction_id": "tx_1", "amount": 5.0, "timestamp": 10, "device_id": "d1", "ip_subnet": "ip1", "card_bin": "bin1", "customer_id": "c1"},
        {"transaction_id": "tx_2", "amount": 5.0, "timestamp": 12, "device_id": "d1", "ip_subnet": "ip1", "card_bin": "bin1", "customer_id": "c2"},
    ]

    G = builder.build_window_graph(transactions)
    feats = extractor.extract_subgraph_features(G, {"tx_tx_1", "tx_tx_2"})

    assert feats["tx_count"] == 2.0
    assert feats["device_reuse_ratio"] == 2.0  # 2 tx / 1 dev
    assert feats["ip_reuse_ratio"] == 2.0      # 2 tx / 1 ip
    assert feats["bin_concentration"] == 1.0   # 100% same BIN
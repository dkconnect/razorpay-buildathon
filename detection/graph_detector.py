from typing import Any, Dict, List, Set
import networkx as nx
from networkx.algorithms.community import louvain_communities

from features.graph_features import TransactionGraphBuilder, GraphFeatureExtractor


class GraphRingDetector:
    """Detects coordinated fraud rings and communities from transaction streams."""

    def __init__(self, resolution: float = 1.0, min_cluster_size: int = 2):
        self.builder = TransactionGraphBuilder()
        self.extractor = GraphFeatureExtractor()
        self.resolution = resolution
        self.min_cluster_size = min_cluster_size

    def detect_communities(self, transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not transactions:
            return []

        # 1. Build heterogeneous and projected transaction graphs
        hetero_G = self.builder.build_window_graph(transactions)
        proj_G = self.builder.build_transaction_projection(hetero_G)

        if proj_G.number_of_nodes() == 0:
            return []

        # 2. Partition into Louvain communities on the projected graph
        # For disconnected components, louvain_communities handles them per component
        try:
            communities: List[Set[str]] = louvain_communities(
                proj_G,
                weight="weight",
                resolution=self.resolution,
                seed=42
            )
        except Exception:
            # Fallback to connected components if modularity fails on degenerate graphs
            communities = list(nx.connected_components(proj_G))

        results: List[Dict[str, Any]] = []

        for idx, comm in enumerate(communities):
            tx_nodes = set(comm)
            if len(tx_nodes) < self.min_cluster_size:
                continue

            # Extract raw transaction IDs and amounts
            tx_ids = [hetero_G.nodes[n].get("raw_id") for n in tx_nodes if "raw_id" in hetero_G.nodes[n]]
            amounts = [hetero_G.nodes[n].get("amount", 0.0) for n in tx_nodes]

            # Extract structural subgraph features
            features = self.extractor.extract_subgraph_features(hetero_G, tx_nodes)

            # Discover implicated shared entities
            devices: Set[str] = set()
            ips: Set[str] = set()
            bins: Set[str] = set()
            customers: Set[str] = set()

            for tx_node in tx_nodes:
                for neighbor in hetero_G.neighbors(tx_node):
                    node_type = hetero_G.nodes[neighbor].get("node_type")
                    if node_type == "device":
                        devices.add(neighbor.replace("dev_", "", 1))
                    elif node_type == "ip":
                        ips.add(neighbor.replace("ip_", "", 1))
                    elif node_type == "bin":
                        bins.add(neighbor.replace("bin_", "", 1))
                    elif node_type == "customer":
                        customers.add(neighbor.replace("cust_", "", 1))

            results.append({
                "community_id": f"comm_{idx:03d}",
                "transaction_ids": tx_ids,
                "transaction_count": len(tx_nodes),
                "total_amount": float(sum(amounts)),
                "mean_amount": float(sum(amounts) / len(amounts)) if amounts else 0.0,
                "shared_devices": sorted(list(devices)),
                "shared_ips": sorted(list(ips)),
                "shared_bins": sorted(list(bins)),
                "shared_customers": sorted(list(customers)),
                "features": features
            })

        return sorted(results, key=lambda x: x["transaction_count"], reverse=True)
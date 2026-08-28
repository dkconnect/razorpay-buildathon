"""
Graph feature extraction for transaction windows.
"""

from typing import Any, Dict, List, Set
import networkx as nx
import numpy as np


class TransactionGraphBuilder:
    """Constructs heterogeneous entity graphs from transaction streams."""

    def __init__(self):
        pass

    def build_window_graph(self, transactions: List[Dict[str, Any]]) -> nx.Graph:
        """
        Builds a NetworkX graph connecting transactions to their shared attributes.
        
        Node format:
          - (f"tx_{tx_id}", {"node_type": "transaction", "amount": amount, "timestamp": ts})
          - (f"dev_{device_id}", {"node_type": "device"})
          - (f"ip_{ip_subnet}", {"node_type": "ip"})
          - (f"bin_{card_bin}", {"node_type": "bin"})
          - (f"cust_{customer_id}", {"node_type": "customer"})
        """
        G = nx.Graph()

        for tx in transactions:
            tx_node = f"tx_{tx['transaction_id']}"
            G.add_node(
                tx_node,
                node_type="transaction",
                amount=tx.get("amount", 0.0),
                timestamp=tx.get("timestamp", 0),
                raw_id=tx["transaction_id"]
            )

            # Entity mappings
            entities = [
                (f"dev_{tx['device_id']}", "device"),
                (f"ip_{tx['ip_subnet']}", "ip"),
                (f"bin_{tx['card_bin']}", "bin"),
                (f"cust_{tx['customer_id']}", "customer"),
            ]

            for entity_node, entity_type in entities:
                if not G.has_node(entity_node):
                    G.add_node(entity_node, node_type=entity_type)
                G.add_edge(tx_node, entity_node)

        return G

    def build_transaction_projection(self, G: nx.Graph) -> nx.Graph:
            """
            Projects heterogeneous graph to an undirected transaction-only graph.
            An edge exists between tx_A and tx_B if they share >= 1 entity.
            Edge weight = number of shared entities.
            """
            tx_nodes = [n for n, d in G.nodes(data=True) if d.get("node_type") == "transaction"]
            proj_G = nx.Graph()
            proj_G.add_nodes_from((n, G.nodes[n]) for n in tx_nodes)

            tx_set = set(tx_nodes)
            for tx_node in tx_nodes:
                entity_neighbors = list(G.neighbors(tx_node))
                for entity in entity_neighbors:
                    for peer_tx in G.neighbors(entity):
                        # Only process ordered pair to avoid double counting undirected weights
                        if peer_tx in tx_set and tx_node < peer_tx:
                            if proj_G.has_edge(tx_node, peer_tx):
                                proj_G[tx_node][peer_tx]["weight"] += 1
                            else:
                                proj_G.add_edge(tx_node, peer_tx, weight=1)

            return proj_G

class GraphFeatureExtractor:
    """Computes topological, entity reuse, and concentration metrics."""

    @staticmethod
    def calculate_herfindahl_index(counts: List[int]) -> float:
        """Computes Herfindahl-Hirschman Index (HHI) for concentration in [0, 1]."""
        total = sum(counts)
        if total == 0:
            return 0.0
        shares = [c / total for c in counts]
        return float(np.sum(np.square(shares)))

    def extract_subgraph_features(self, G: nx.Graph, tx_nodes: Set[str]) -> Dict[str, float]:
        """
        Extracts structural features for a subset of transactions in the heterogeneous graph.
        """
        if not tx_nodes:
            return {
                "tx_count": 0.0,
                "device_reuse_ratio": 0.0,
                "ip_reuse_ratio": 0.0,
                "bin_concentration": 0.0,
                "customer_diversity": 0.0,
                "mean_degree": 0.0,
                "edge_density": 0.0,
            }

        devices: Set[str] = set()
        ips: Set[str] = set()
        bins: Dict[str, int] = {}
        customers: Set[str] = set()

        for tx in tx_nodes:
            for neighbor in G.neighbors(tx):
                node_type = G.nodes[neighbor].get("node_type")
                if node_type == "device":
                    devices.add(neighbor)
                elif node_type == "ip":
                    ips.add(neighbor)
                elif node_type == "bin":
                    bins[neighbor] = bins.get(neighbor, 0) + 1
                elif node_type == "customer":
                    customers.add(neighbor)

        n_tx = len(tx_nodes)
        n_dev = len(devices) if devices else 1
        n_ip = len(ips) if ips else 1
        n_cust = len(customers) if customers else 1

        # Higher ratio = higher reuse per entity (suspicious)
        device_reuse_ratio = n_tx / n_dev
        ip_reuse_ratio = n_tx / n_ip
        bin_concentration = self.calculate_herfindahl_index(list(bins.values()))
        customer_diversity = n_cust / n_tx

        subgraph = G.subgraph(list(tx_nodes) + list(devices) + list(ips) + list(bins.keys()) + list(customers))
        degrees = [d for _, d in subgraph.degree()]
        mean_degree = float(np.mean(degrees)) if degrees else 0.0
        density = float(nx.density(subgraph)) if len(subgraph) > 1 else 0.0

        return {
            "tx_count": float(n_tx),
            "device_reuse_ratio": float(device_reuse_ratio),
            "ip_reuse_ratio": float(ip_reuse_ratio),
            "bin_concentration": float(bin_concentration),
            "customer_diversity": float(customer_diversity),
            "mean_degree": mean_degree,
            "edge_density": density,
        }
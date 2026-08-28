from typing import Any, Dict, List, Set
import networkx as nx
from networkx.algorithms.community import louvain_communities
import numpy as np

from features.graph_features import TransactionGraphBuilder, GraphFeatureExtractor


class GraphRingDetector:
# Detects coordinated fraud rings and communities from transaction streams.

    def __init__(self, resolution: float = 1.0, min_cluster_size: int = 2):
        self.builder = TransactionGraphBuilder()
        self.extractor = GraphFeatureExtractor()
        self.resolution = resolution
        self.min_cluster_size = min_cluster_size

    @staticmethod
    def calculate_ring_score(features: Dict[str, float]) -> float:
        """
        Calculates a calibrated ring score in [0.0, 1.0] from extracted subgraph features.
        
        Flash-sale / organic spikes:
          - High transaction count, but device_reuse ~ 1.0, ip_reuse ~ 1.0, low bin concentration -> ring_score ~ 0.0
        
        Card testing / Coordinated Ring:
          - High device reuse, high IP reuse, high BIN concentration -> ring_score >= 0.85
        """
        tx_count = features.get("tx_count", 0.0)
        if tx_count < 2.0:
            return 0.0

        dev_reuse = features.get("device_reuse_ratio", 1.0)
        ip_reuse = features.get("ip_reuse_ratio", 1.0)
        bin_conc = features.get("bin_concentration", 0.0)
        cust_div = features.get("customer_diversity", 1.0)

        # Entity sharing signal (normalized via soft-saturation)
        dev_signal = float(1.0 - np.exp(-0.7 * max(0.0, dev_reuse - 1.0)))
        ip_signal = float(1.0 - np.exp(-0.7 * max(0.0, ip_reuse - 1.0)))
        bin_signal = float(bin_conc)

        # Dispersed identities on shared infrastructure:
        # High customer diversity + high device/IP reuse is a classic synthetic/bot hallmark
        identity_mismatch = cust_div if (dev_reuse > 1.2 or ip_reuse > 1.2) else 0.0

        # Weighted combination of structural signals
        composite = (
            0.35 * dev_signal +
            0.30 * ip_signal +
            0.20 * bin_signal +
            0.15 * identity_mismatch
        )

        # Size scaling multiplier: small clusters (2 txs) need stronger signals than larger clusters (10+ txs)
        size_factor = float(1.0 / (1.0 + np.exp(-0.5 * (tx_count - 3.0))))
        
        ring_score = float(np.clip(composite * (0.6 + 0.4 * size_factor), 0.0, 1.0))
        return round(ring_score, 4)

    def detect_communities(self, transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Builds the window graph, projects to transaction space, partitions communities via Louvain,
        and extracts structural features + ring score for each detected cluster.
        """
        if not transactions:
            return []

        hetero_G = self.builder.build_window_graph(transactions)
        proj_G = self.builder.build_transaction_projection(hetero_G)

        if proj_G.number_of_nodes() == 0:
            return []

        try:
            communities: List[Set[str]] = louvain_communities(
                proj_G,
                weight="weight",
                resolution=self.resolution,
                seed=42
            )
        except Exception:
            communities = list(nx.connected_components(proj_G))

        results: List[Dict[str, Any]] = []

        for idx, comm in enumerate(communities):
            tx_nodes = set(comm)
            if len(tx_nodes) < self.min_cluster_size:
                continue

            tx_ids = [hetero_G.nodes[n].get("raw_id") for n in tx_nodes if "raw_id" in hetero_G.nodes[n]]
            amounts = [hetero_G.nodes[n].get("amount", 0.0) for n in tx_nodes]
            features = self.extractor.extract_subgraph_features(hetero_G, tx_nodes)
            ring_score = self.calculate_ring_score(features)

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
                "features": features,
                "ring_score": ring_score
            })

        return sorted(results, key=lambda x: (x["ring_score"], x["transaction_count"]), reverse=True)

class PhaseLinker:
    """Links Phase 1 (card testing) clusters to Phase 2 (bust-out) transaction attempts."""

    @staticmethod
    def link_phases(
        phase1_communities: List[Dict[str, Any]],
        phase2_transactions: List[Dict[str, Any]],
        high_value_threshold: float = 1000.0
    ) -> List[Dict[str, Any]]:
        """
        Scans Phase 2 transactions against known Phase 1 suspicious communities.
        If a high-value transaction shares device_id, ip_subnet, or card_bin with a Phase 1 community,
        it is flagged as an Escalated Bust-Out event.
        """
        escalated_events: List[Dict[str, Any]] = []

        # Index Phase 1 communities by entity
        dev_to_comm: Dict[str, Dict[str, Any]] = {}
        ip_to_comm: Dict[str, Dict[str, Any]] = {}
        bin_to_comm: Dict[str, Dict[str, Any]] = {}

        for comm in phase1_communities:
            if comm.get("ring_score", 0.0) < 0.5:
                continue  # Only link against suspicious communities

            for dev in comm.get("shared_devices", []):
                dev_to_comm[dev] = comm
            for ip in comm.get("shared_ips", []):
                ip_to_comm[ip] = comm
            for card_bin in comm.get("shared_bins", []):
                bin_to_comm[card_bin] = comm

        for tx in phase2_transactions:
            amount = tx.get("amount", 0.0)
            dev = tx.get("device_id")
            ip = tx.get("ip_subnet")
            card_bin = tx.get("card_bin")

            matched_comm = dev_to_comm.get(dev) or ip_to_comm.get(ip) or bin_to_comm.get(card_bin)

            if matched_comm and amount >= high_value_threshold:
                shared_links = []
                if dev in matched_comm.get("shared_devices", []):
                    shared_links.append(f"device:{dev}")
                if ip in matched_comm.get("shared_ips", []):
                    shared_links.append(f"ip:{ip}")
                if card_bin in matched_comm.get("shared_bins", []):
                    shared_links.append(f"bin:{card_bin}")

                escalated_events.append({
                    "transaction_id": tx["transaction_id"],
                    "amount": amount,
                    "timestamp": tx.get("timestamp"),
                    "linked_community_id": matched_comm["community_id"],
                    "phase1_ring_score": matched_comm["ring_score"],
                    "shared_entities": shared_links,
                    "is_escalated_bustout": True,
                    "escalation_score": min(1.0, round(matched_comm["ring_score"] * 1.2, 4))
                })

        return escalated_events
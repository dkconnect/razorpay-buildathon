import matplotlib.pyplot as plt
import numpy as np
import networkx as nx

# Set styling
plt.style.use('dark_background')
plt.rcParams['font.sans-serif'] = 'DejaVu Sans'

# -------------------------------------------------------------
# 1. CUSUM Flash Sale vs. Fraud Ring Velocity Anomaly Plot
# -------------------------------------------------------------
fig, ax = plt.subplots(figsize=(10, 4.5), dpi=300)
time = np.arange(0, 100)
np.random.seed(42)

# Baseline + Flash Sale (smooth broad surge) vs Fraud (sharp anomalous spikes)
baseline = np.random.poisson(lam=10, size=100)
flash_sale = baseline + np.exp(-((time - 35)**2)/100) * 45
fraud_spike = flash_sale.copy()
fraud_spike[70:78] += np.random.poisson(lam=60, size=8)

# CUSUM statistic calculation
k = 5
h = 40
mu0 = 10
s_n = np.zeros(100)
for t in range(1, 100):
    s_n[t] = max(0, s_n[t-1] + (fraud_spike[t] - mu0 - k))

ax.plot(time, fraud_spike, color='#89B4FA', label='Transaction Rate (TPS)', alpha=0.6, lw=1.5)
ax.plot(time, s_n, color='#F38BA8', label="CUSUM Statistic ($S_n$)", lw=2.5)
ax.axhline(h, color='#FAB387', linestyle='--', label='Detection Threshold ($h$)', lw=1.8)

ax.set_title("BREAKPOINT: Statistical Temporal Anomaly Detection (CUSUM)", fontsize=13, pad=12, color='#CDD6F4')
ax.set_xlabel("Time Step (Window Index)", color='#CDD6F4')
ax.set_ylabel("Rate / Anomaly Score", color='#CDD6F4')
ax.legend(frameon=True, facecolor='#1E1E2E', edgecolor='#313244')
plt.tight_layout()
plt.savefig("cusum_anomaly_plot.png")
plt.close()

# -------------------------------------------------------------
# 2. Fraud Ring Subgraph Topology Plot
# -------------------------------------------------------------
fig, ax = plt.subplots(figsize=(7, 6), dpi=300)
G = nx.DiGraph()

# Synthetic Ring: 5 users cycling funds across 3 intermediary merchants
users = [f"U_{i}" for i in range(1, 6)]
merchants = [f"M_{j}" for j in range(1, 4)]

for u in users:
    G.add_node(u, node_type='user')
for m in merchants:
    G.add_node(m, node_type='merchant')

edges = [
    ("U_1", "M_1"), ("M_1", "U_2"), ("U_2", "M_2"),
    ("M_2", "U_3"), ("U_3", "M_3"), ("M_3", "U_1"),
    ("U_4", "M_1"), ("U_5", "M_2"), ("M_3", "U_4")
]
G.add_edges_from(edges)

pos = nx.spring_layout(G, seed=42)
user_nodes = [n for n, d in G.nodes(data=True) if d['node_type'] == 'user']
merchant_nodes = [n for n, d in G.nodes(data=True) if d['node_type'] == 'merchant']

nx.draw_networkx_nodes(G, pos, nodelist=user_nodes, node_color='#89B4FA', node_size=600, label='User Identities (Mules)', ax=ax)
nx.draw_networkx_nodes(G, pos, nodelist=merchant_nodes, node_color='#F38BA8', node_size=800, node_shape='s', label='Merchants (Nodes)', ax=ax)
nx.draw_networkx_edges(G, pos, edge_color='#CDD6F4', arrows=True, arrowsize=15, width=1.6, ax=ax)
nx.draw_networkx_labels(G, pos, font_color='#11111B', font_size=9, font_weight='bold', ax=ax)

ax.set_title("BREAKPOINT: Collusive Bipartite Fraud Ring Topology", fontsize=12, pad=12, color='#CDD6F4')
ax.axis('off')
ax.legend(frameon=True, facecolor='#1E1E2E', edgecolor='#313244', loc='lower right')
plt.tight_layout()
plt.savefig("fraud_ring_topology.png")
plt.close()

print("Generated: 'cusum_anomaly_plot.png' and 'fraud_ring_topology.png'")
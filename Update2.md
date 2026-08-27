# Day 2 — Report
### Fraud Ring & Evaluation Data

---

**27 Aug 2026 · 00:00 AM – 9 PM**

---

### **Fraud archetype**

Defined the core attack pattern:

**Coordinated Card-Testing Ring → Bust-Out**

### **Fraud configuration**

Created configurable fraud-ring parameters:

- Number of synthetic identities
- Phase 1 duration & transaction count
- Phase 2 duration & transaction count
- Gap between phases
- Fraud phase labels

### **Fraud identities**

Built reusable synthetic identities using:

```
customer_id
device_id
ip_subnet
card_bin
```

### **Phase 1 — Card Testing**

Implemented low-value/high-velocity transactions:

```
₹1 – ₹50
```

Ground truth:

```
is_fraud = True
phase = "testing"
ring_id = known ring
```

---

### **Phase 2 — Bust-Out**

Implemented the escalation phase:

```text
₹5,000 – ₹50,000
```

with fewer but substantially higher-value transactions.

Ground truth:

```text
is_fraud = True
phase = "bust_out"
ring_id = same ring
```

---

### **Randomized fraud scenarios**

Moved from one deterministic fraud example to randomized configurations.

Different seeds produce different:

```
ring sizes
testing durations
testing volumes
phase gaps
bust-out durations
bust-out volumes
```

### **Multiple-scenario generation**

Built the ability to generate multiple independent fraud scenarios:

**Detection Rate vs Ring Size** evaluation.

---

#### **Mixed legitimate + fraud stream**

#### **Ground-truth validation**

Added explicit validation. This protects the integrity of our future precision/recall measurements.

---

### **Final Day-2 dataset**

```
Total:       11,944
Legitimate:  11,899
Fraud:           45

Testing:         33
Bust-out:        12

Start: 2026-01-05 00:00:57
End:   2026-01-05 23:59:58
Seed:  42
```
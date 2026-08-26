# Day 1 — Report

**26 Aug 2026 · 9 AM–6 PM**

*Day 1: Complete*

### Points

* **Transaction schema + generator** — structured legitimate transactions with reproducible generation.
* **Poisson arrivals** — replaced unrealistic fixed intervals with stochastic transaction arrivals.
* **Inhomogeneous Poisson process** — transaction rate varies over time through `λ(t)`.
* **Hourly seasonality** — modeled realistic merchant traffic patterns across the day.
* **Day-of-week seasonality** — added weekday/weekend traffic variation.
* **Lognormal transaction amounts** — modeled realistic right-skewed purchase values.
* **Merchant stream generator** — combined arrivals, seasonality, amounts, and transaction metadata.
* **Scenario configuration** — introduced reproducible scenario definitions.
* **Normal-day scenario** — generated a complete 24-hour legitimate merchant day.
* **Flash-sale scenario** — created a legitimate 2-hour high-volume event (~8× traffic) with **zero fraud**.
* **Dataset persistence** — added JSON save/load functionality and generated the baseline datasets.
* **Testing** — built the test suite incrementally; all tests passing.

### Final datasets

```text
normal_day.json
├── 11,899 transactions
├── fraud: 0
├── median amount: ₹1,825.23
└── max amount: ₹50,060.78

flash_sale.json
├── 17,904 transactions
├── fraud: 0
└── median amount: ₹1,816.09
```

### Key validation

**Flash sale volume:**

```text
Before: 914
Sale:   7,305
Ratio:  7.99×
```

The important property is that **volume changes dramatically while transaction-value distribution remains broadly similar**. This gives us a legitimate anomaly against which Day 3's regime detector can be tested for false positives.

### Final Day 1 outcome

> **A reproducible synthetic merchant environment with realistic time-varying traffic, transaction values, a normal baseline, and a legitimate high-volume flash-sale stress scenario.**



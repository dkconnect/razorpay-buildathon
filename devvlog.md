### 26 Aug Morning - 9 AM

Transaction schema --> Single legitimate transaction generator --> 2 passing tests

### 26 Aug Morning - 10 AM

----------------------
*Poisson transaction*
----------------------
current stream is obv not realistic.
```
12:00:00
12:00:10
12:00:20
12:00:30
```

A merchant's transactions will be randomly around an underlying rate.

modelling arrivals using a Poisson process.

### 26 Aug - 11:30 AM

```
night       → low λ
morning     → medium λ
afternoon   → high λ
evening     → very high λ
night       → low λ
```

this will give the inhomogeneous Poisson process required for the merchant baseline.

### 26 Aug - 11:45 AN
#### Model transaction amounts

*X ∼ LogNormal(mu,sigma)*

mu = 7.5 | sigma = 0.8


### 26 Aug - 12:50 PM
#### Define merchant traffic seasonality

right now the arrival rate is constant:
λ = 10 transactions/minute
but real merchants wont behave like that.

rough
```
Time        Relative traffic
00–06       very low
06–09       low
09–12       medium
12–16       high
16–20       very high
20–23       high
23–00       medium
```

so I kinda need seasonality module

Seasonality Module:

*λ(t) = λ_base X M_hour(t) X M_day(t)*

### 26 Aug - 1:15 PM
#### day-of-week seasonality

currently hourly behavior, gonna add a second dim. - day of week.

assuming
```
Monday–Thursday: normal
Friday: slightly busier
Saturday: busy
Sunday: moderately busy
```
Seasonality Module: *λ(t) = λ_base X M_hour(t) X M_day(t)*

so, if base = 10 tx/min | hour = 18:00 → 1.5 | Saturday → 1.3

then: 10 × 1.5 × 1.3 = 19.5

### 26 Aug - 2 PM
#### Build the inhomogeneous arrival process

timestamp --> expected λ(t)

needed

time --> expected rate λ(t) --> random arrival --> next timestamp --> recalculate λ(t)

This will give a time-varying Poisson


DAY 1 MID HOLDING 
1. Poisson arrivals --> Time-varying λ(t) --> Merchant stream
2. Lognormal amounts --> Time-varying λ(t) --> Merchant stream  
      

### Introducing scenario configuration

creating
- normal_day
- flash_sale
- fraud_ring

### 26 Aug - 4 PM
#### Normal-day dataset

*Scenario Result*
```
transactions: 11899
first: 2026-01-05 00:00:57.701006
last: 2026-01-05 23:59:58.743260
median amount: 1825.23
mean amount: 2510.431872426254
max amount: 50060.78
```

---

### 26 Aug - 5 PM
#### Finallllyyy 
#### Flash-sale scenario

The legitimate flash-sale scenario exists, is labeled legitimate, is reproducible, and has a defined two-hour event window.

*Quant Test*
*Actual Ratio*

```
before: 914
sale: 7305
ratio: 7.99
```

### 26 Aug - 6 PM
### Last Sprint of Day
*Saving scenarios as datasets*

```
NORMAL DAY
transactions: 11899
fraud: 0
FLASH SALE
transactions: 17904
fraud: 0
amount median normal: 1825.23
amount median flash: 1816.09
```
### 26 Aug - 10 PM

### 27 Aug - 00:05 AM
Generate ring identities

Each ring will have:

ring
── device fingerprints
── IP subnet
── card BINs

Transaction A
 ├─ device: fraud_device_ring_001_3
 ├─ IP:     10.250.3.0/24
 └─ BIN:    4000003

Transaction B
 ├─ device: fraud_device_ring_001_3
 ├─ IP:     10.250.3.0/24
 └─ BIN:    4000003


### 27 Aug - 7 AM
#### Card Testing

*many tiny payments in a short period, using the same coordinated identity pool*
```
Phase 1

Duration:       configurable
Transactions:   configurable
Amount:         ₹1–₹50
Identity pool:  fraud ring identities
is_fraud:       True
phase:          "testing"
ring_id:        ring_001
```

```Phase 1 | ₹1–₹50 | many transactions``` --> ```Phase 2 | ₹5,000–₹50,000 | fewer transactions```


### 27 Aug - 9 AM
#### Combine Phase 1 + Phase 2

creating one function that will:
- Generate Phase 1.
- Determine its actual end timestamp.
- Apply the configured gap.
- Generate Phase 2.
- Combine them.
- Sort everything chronologically.

#### Random Fraud-Ring Configurations

```
small ring - 4 identities
medium ring - 8 identities
large ring - 14 identities

short test - 5 min
long test - 20 min

small burst - 30 testing tx
large burst - 150 testing tx

short gap - 2 min
long gap - 15 min
```

*Manual Check*

```
FraudRingConfig(ring_id='ring_000', identity_count=10, phase1_duration_minutes=18, phase1_transaction_count=35, phase2_gap_minutes=6, phase2_duration_minutes=13, phase2_transaction_count=20, phase1_min_amount=1.0, phase1_max_amount=50.0, phase2_min_amount=5000.0, phase2_max_amount=50000.0)
```
```
FraudRingConfig(ring_id='ring_001', identity_count=6, phase1_duration_minutes=7, phase1_transaction_count=62, phase2_gap_minutes=3, phase2_duration_minutes=12, phase2_transaction_count=29, phase1_min_amount=1.0, phase1_max_amount=50.0, phase2_min_amount=5000.0, phase2_max_amount=50000.0)
```
```
FraudRingConfig(ring_id='ring_002', identity_count=4, phase1_duration_minutes=7, phase1_transaction_count=40, phase2_gap_minutes=7, phase2_duration_minutes=7, phase2_transaction_count=28, phase1_min_amount=1.0, phase1_max_amount=50.0, phase2_min_amount=5000.0, phase2_max_amount=50000.0)
```
```
FraudRingConfig(ring_id='ring_003', identity_count=7, phase1_duration_minutes=9, phase1_transaction_count=77, phase2_gap_minutes=11, phase2_duration_minutes=12, phase2_transaction_count=25, phase1_min_amount=1.0, phase1_max_amount=50.0, phase2_min_amount=5000.0, phase2_max_amount=50000.0)
```
```
FraudRingConfig(ring_id='ring_004', identity_count=7, phase1_duration_minutes=14, phase1_transaction_count=43, phase2_gap_minutes=13, phase2_duration_minutes=11, phase2_transaction_count=20, phase1_min_amount=1.0, phase1_max_amount=50.0, phase2_min_amount=5000.0, phase2_max_amount=50000.0)
```

### 27 Aug - 11 AM
#### Multiple Fraud Scenarios
```
seed 0 → ring_000 → transactions
seed 1 → ring_001 → transactions
seed 2 → ring_002 → transactions
```

*Manual Check*
```
scenarios: 10
transactions: [45, 138, 66, 106, 47, 108, 60, 111, 103, 83]
total: 867
```

#### Mix Legitimacy and Fraud Traffic
*check*
```
total: 11944
legitimate: 11899
fraud: 45
testing: 33
bust_out: 12
```

*current line*
```
LEGITIMATE DAY + FRAUD RING --> MIXED STREAM --> known ground truth
```
### 27 Aug - 1 PM
#### Ground Truth Validation

I need one small data-integrity checkpoint so that wil guarantee that the fraud injector is not producing nonsense.

```
Every fraud transaction has is_fraud=True.
Every fraud transaction has a valid phase.
Testing transactions are actually low-value.
Bust-out transactions are actually high-value.
```
### 27 Aug - Final Data
*Day 2 dataset*
```
generated                                                                                               
-----------------------                                                                                               
total:     11944                                                                                                      
legitimate: 11899                                                                                                     
fraud:     45          
testing:   33
bust_out:  12
seed:      42
output:    data\generated\mixed_fraud.json
```
```
loaded: 11944
fraud: 45
testing: 33
bust_out: 12
first: 2026-01-05 00:00:57.701006
last: 2026-01-05 23:59:58.743260
```

### 27 Aug (Day 3 Starting)
#### Rolling Feature Window Engine

```
to process an online stream of transaction events and maintain rolling statis over config time windows
```

The key signals:

```
​```
mean_amount & mean_log_amount: Tracks nominal vs. exponential deflection  
```
```
low_val_ratio: Ratio of transactions where amount≤$50 (card testing signature)  
```
```
high_val_ratio: Ratio of transactions where amount≥$5000 (bust-out signature)  
```

```velocity: tx count / t (minutes)```

​```mean_amount & mean_log_amount: Tracks nominal vs. exponential deflection  ```

```low_val_ratio: Ratio of transactions where amount≤$50 (card testing signature)  ```

```high_val_ratio: Ratio of transactions where amount≥$5000 (bust-out signature)  ```


### 28 Aug : 7 AM
#### Baseline Profiler & Diurnal Calibration 

- To run CUSUM effectively without false alarms, static global thresholds will be kinda eww.

- I will calibrate an hourly baseline profile ```mu, sigma``` directly from clean/normal transaction windows.

### 28 Aug : 9 AM
#### Step 3: Multi-Signal Dual-Sided CUSUM Core 

- Implementing the online CUSUM detector. 

*Maths*

For each time step and observation with hourly baseline mean and SD.

1. **Standardized Score ($Z$):**
   $$z_t = \frac{x_t - \mu_0(h)}{\sigma_0(h)}$$

2. **One-Sided Positive CUSUM ($S^+$):** 
   $$S_t^+ = \max\left(0,\, S_{t-1}^+ + z_t - k\right)$$

3. **One-Sided Negative CUSUM ($S^-$):** 
   $$S_t^- = \max\left(0,\, S_{t-1}^- - z_t - k\right)$$

* $k$ is the reference allowance (typically $k = 0.5$).
* $h_{\text{thresh}}$ is the decision threshold (typically $h = 5.0$).
* $S_0^+ = 0$ and $S_0^- = 0$ are the initial conditions.


### 28 Aug - 10 AM

#### 1. The Fusion Function: Multiplicative Gate 

A naive linear combination ($\sum w_i S_i$) or maximum ($\max S_i$) fails the **Flash-Sale False-Positive Test** because a $5\times$ velocity spike produces a massive $S_v^+ \approx 1.0$, pushing a weighted sum into alert territory even when basket sizes are completely healthy.

*Mathematical Formulation for Fusion*

We decompose the temporal risk into two independent threat channels and take their safe bounded union:

$$\text{Risk}_{\text{Phase 1 (Card Testing)}} = S_{\text{velocity\_norm}} \times S_{\text{amount\_neg\_norm}}$$

$$\text{Risk}_{\text{Phase 2 (Bust-Out)}} = S_{\text{high\_val\_norm}}$$

1. **Multiplicative Conjunction (Fuzzy-AND) for Phase 1:**

$$\text{score}_{\text{testing}} = \sigma\left(\frac{S_v^+}{h}\right) \times \sigma\left(\frac{S_a^-}{h}\right)$$


* **During Flash Sale:** $S_v^+ \gg h \implies \sigma \approx 1.0$, but $S_a^- = 0 \implies \sigma = 0.0$.

$$\text{score}_{\text{testing}} = 1.0 \times 0.0 = \mathbf{0.0}$$


* **During Card Testing:** $S_v^+ \gg h$ AND $S_a^- \gg h \implies \sigma(S_v^+) \approx 1.0 \text{ and } \sigma(S_a^-) \approx 1.0$.

$$\text{score}_{\text{testing}} = 1.0 \times 1.0 = \mathbf{1.0}$$


2. **Decoupled Activation for Phase 2 (Bust-Out):**

$$\text{score}_{\text{bust}} = \sigma\left(\frac{S_{\text{high}}^+}{h}\right)$$


Bust-outs often occur with normal or moderate velocity, so $S_{\text{high}}^+$ does not require high transaction volume to assert risk.


3. **Combined Unified Regime Score:**

$$\text{regime\_score} = 1 - (1 - \text{score}_{\text{testing}}) \times (1 - \text{score}_{\text{bust}}) \in [0, 1]$$


---

#### 2. Strict Baseline Source Guarantee (Preventing Data Leakage)

To guarantee that the baseline parameter profile $\mu_0(h), \sigma_0(h)$ is exclusively fitted on clean, unpolluted data:

1. **Tag Metadata on Dataset Generation / Serialization:**
Every dataset JSON carries a top-level `"scenario_type"` metadata field (`"normal_day"`, `"flash_sale"`, `"mixed_fraud"`).


2. **Hard Assertion in `BaselineCalibrator.fit()`:**
Enforce strict metadata validation so fitting will throw a `ValueError` if executed on anything other than clean baseline data.


### 28 Aug - 9 PM
#### Day 4 - Graph Builder & Feature Extraction 

Building the heterogeneous transaction graph constructor and feature extractor.

### 28 Aug - 10 PM
#### Community Detection & Graph Detector

Building the detector layer. takes the transaction window, partitions connected transaction clusters using NetworkX's Louvain community detection, extracts per-cluster structural features and maps each cluster into an identified community structure.  

### 29 Aug 
#### Ring Scoring Model (ring_score $\in [0, 1]$)   

- Build the calibrated scoring engine.
- The ring_score maps multi-dimensional topological features into $[0, 1]$ using a non-linear sigmoid formulation based on:


Device Reuse Ratio ($\ge 2.0$ transactions/device is suspicious)  

IP Reuse Ratio ($\ge 2.0$ transactions/IP is suspicious)  

BIN Concentration (HHI index $\to 1.0$ indicates focused card-testing across specific target BINs)

Customer Dispersal with Shared Infrastructure  

Cluster Size Scaling

#### Cross-Phase Identity Linkage & End-to-End Validation  

Implement the cross-phase linkage engine. 
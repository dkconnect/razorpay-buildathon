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

### 27 Aug - 00:05
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
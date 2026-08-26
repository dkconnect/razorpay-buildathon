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

### 26 Aug - 11: 45
#### Model transaction amounts

*X ∼ LogNormal(mu,sigma)*

mu = 7.5 | sigma = 0.8


### 26 Aug - 12:50
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


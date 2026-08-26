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

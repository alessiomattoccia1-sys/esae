<!-- SPDX-License-Identifier: Apache-2.0 -->

# FSIE-001 — quantitative methodology

Retrospective latest-acquired-vintage research, not a predictive trading backtest.

Configuration:
```json
{
  "start": "2000-01-01",
  "end": "2026-11-06",
  "bootstrap_replicates": 999,
  "block_weeks": 13,
  "seed": 20261106,
  "anomaly_window": 104,
  "anomaly_min_history": 52,
  "anomaly_z": 4.0
}
```

Observation dates and current snapshot acquisition times do not prove original historical publication availability. Unknown publication timestamps remain null. NFCI/ANFCI can revise their histories. Never forward-fill a Friday index into earlier trading dates. Weekly alignment selects the last Treasury session in the same Monday-Friday week, preserving original dates and missingness. No interpolation.

Spread basis points =100*(10Y yield - short yield), input rates in percentage points. Volatility is ddof1 standard deviation of changes in yield/spread basis points per observed session/week, not bond-price volatility or annualized investment risk.

Strict negative spread defines inversion. Episodes count observed inverted sessions and inclusive calendar span separately. Missing required yields and sample end censor episodes; unknown intervals do not prove termination.

Pearson/Spearman are descriptive; no IID correlation p-values. Joint moving-block bootstrap:13 weeks, 999 replicates, seed 20261106, 95% percentile intervals. Calendar alignment and paired missingness retained. These intervals require temporal-dependence/stability assumptions.

Lags:-26,-13,-4,0,4,13,26weeks. corr(delta_spread[t],delta_index[t+k]):positive k means spread observation leads index reference week, not publication availability or causality. All 28 predeclared first-difference tests use OLS/HAC(Newey-West, 13 lags) and Holm correction across the full 28-test family, including unestimable tests as conservative p=1. Rolling windows 26/52/104 weeks and all predefined historical subperiods are reported. No favorable-window selection.

Anomalies:past-only 104-week median/MAD, minimum 52 prior observations,scale 1.4826, |z| >= 4. ZeroMAD is not determinable, never an infinite surprise. Volatility exceedances use only preceding104weekly estimates,p95,min52. Two-sided CUSUM/Page-Hinkley-style accumulation of standardized changes has drift 0.5, threshold 8 and resets on an event; these are heuristic candidates, not formal break proofs. NFCI>0 and>1 are declared relative-condition thresholds; persistence4weeks is an overlapping-window count.

No-follow-through proxy:inversion onset not followed by index threshold0/1/2 within 13/26/52 weeks, excluding incomplete follow-up. These are retrospective threshold sensitivity counts, not true/false crisis forecasts. NFCI already combines financial-market information; sources and indicators are not independent.

Original-code Apache 2.0 is separate from source-data terms. Raw institutional archives/full series remain local. Public artifacts contain original computed findings/aggregates and source references. No trading, broker integration, money management, personalized advice or return promise.

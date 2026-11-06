<!-- SPDX-License-Identifier: Apache-2.0 -->

# Scope and limitations

FSIE is a computational research prototype, not a financial adviser or trading
system. It implements no order execution, broker connection, leverage, money
management, price-prediction guarantee or personalized recommendation.

The actual study is retrospective using acquired current-vintage observations.
Unknown historical publication dates remain null. NFCI revisions and overlapping
market inputs prevent claims of a look-ahead-free predictive backtest or source
independence. An inversion is not a certain crisis; NFCI thresholds measure
relative conditions. Correlation and lag association do not establish causality.

HAC/Newey-West and block-bootstrap uncertainty require assumptions about temporal
dependence and stability. No method is claimed valid under arbitrary structural
nonstationarity. All declared windows and lags are shown, including null outcomes.
CUSUM-style candidates and robust anomalies are heuristic flags, not proven
structural breaks or acquisition errors. The no-follow-through proxy uses declared
thresholds, not an independently validated crisis label or measured forecast skill.

Volatility refers to changes in yields/spreads per observed session/week, not
bond-price volatility. Missing observations remain missing. Financial data use
upstream terms, not Apache. Public reports omit full raw institutional archives;
exact old-vintage replay requires the corresponding frozen cache.

The quantitative stage uses a bounded in-memory DataFrame for this actual study.
DuckDB/Parquet scalability is tested separately on 20 million synthetic rows.
This does not qualify arbitrary-size financial analysis. Only macOS Apple Silicon
Python 3.12 is qualified; Windows/Linux are not yet tested. Optional local AI can
be unavailable/rejected and has no role in numeric results. FRED/ALFRED and SEC
are not implemented. ECB is a separate tested supplement, not a new main finding.

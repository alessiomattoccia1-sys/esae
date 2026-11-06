<!-- SPDX-License-Identifier: Apache-2.0 -->

# Measured results

| Quantity | Computed result | Denominator / scope |
|---|---:|---|
| Source observations acquired | 139,903 | Long-format values/nulls across all 13 source files, not 139,903 trading dates |
| Stored target-period observations | 98,286 | 21 series; null fields retained |
| Common Treasury sessions | 6,711 | 2000-01-03–2026-10-30 |
| Complete primary reference weeks | 1,400 | 2000-01-07–2026-10-30; zero missing primary week slots |
| 10Y–2Y inverted sessions | 1,009 | 6,711 known sessions; 20 observed episodes |
| 10Y–3M inverted sessions | 1,117 | 6,708 known sessions; 38 observed episodes |
| 10Y–2Y spread range | −108 to +291 bp | Acquired common daily sample |
| 10Y–3M spread range | −189 to +385 bp | Acquired common daily sample |
| HAC/Holm lag tests significant at 5% | 0 | All 28 predeclared tests were estimable |
| Past-normalized anomaly flags | 115 | Two spread changes plus NFCI/ANFCI changes; flags are not necessarily unique dates |

Contemporaneous 10Y–2Y/NFCI level Pearson correlation is 0.093241701577
with 13-week moving-block 95% interval [−0.101448814492, 0.222914134873]
(1,400 paired weeks). Its first-difference correlation is 0.031412177228
(1,399 pairs), interval [−0.096233066592, 0.147955415658]. All eight
contemporaneous bootstrap intervals include zero. This is an inconclusive/null
association outcome under the declared method, not a claim of universal absence.

Examples: ANFCI changed +0.260 in the 2020-03-13 reference week, past-normalized
z = 16.003826202126. NFCI changed +0.164 in the same week, z = 13.827060569270.
SOFR increased 282 bp on 2019-09-17 and decreased 270 bp on 2019-09-18.
These are calculations from the acquired vintage, not asserted causes or
verified crisis probabilities. Full cases and formulas are in the generated report.

The separate ECB connector acquired 22 USD/EUR daily observations in October
2026. They do not enter these findings. The synthetic 20-million-row benchmark
also does not contribute any financial observations or statistical result.

All numbers above are checked against the generated JSON rather than supplied by
an LLM or borrowed from literature. See the full report/manifest for subperiods,
rolling windows, threshold sensitivity, censored follow-up, source overlap,
uncertainty and limitations. Analysis SHA-256: `2b6702e018e1b92aa0973b936457d7f77698c2b52ac514320cc0e8fe406efac4`.

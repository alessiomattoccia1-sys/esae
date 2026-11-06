<!-- SPDX-License-Identifier: Apache-2.0 -->

# FSIE-001 — Treasury Yield Curve & Financial Stress

A historical analysis of market regimes. Configuration was fixed before bulk
acquisition and analysis: study from 2000-01-01, end 2026-11-06; 13-week joint
moving blocks, 999 replicates, seed 20261106; full 28-test HAC/Holm lag family;
past-only 104-week median/MAD anomalies with minimum 52 prior observations,
scale 1.4826 and threshold |z| >= 4. All windows and subperiods are retained.

The actual study was completed at 2026-11-06T06:47:59.825384+00:00 using 13 real HTTPS files.
Source acquisition covers the Treasury historical archive and later annual XML,
current Chicago indices, and SOFR annual JSON. Raw files include observations
outside the target period; exclusions are explicit rather than fabricated fills.
There are 139,903 acquired long-format observations,
98,286 stored in the target period and
41,617 outside-period exclusions. Zero invalid records and duplicates.

The common comparison is 1,400 weeks from 2000-01-07 through 2026-10-30.
Treasury data in the archive extend through 2026-11-05 and SOFR through
2026-11-04; later dates are not paired with nonexistent weekly financial indices.
The study therefore stops at the actual common coverage, not the request date.

All three required analytical results exist: curve regimes/inversion episodes,
financial-condition relationships including a null corrected result, and dated
statistical anomalies. The complete raw sources were rehashed/reparsed and the
analysis reproduced without network. Independent SQL and direct NumPy matrix
calculations confirmed counts/spreads, Pearson and all 28 HAC/Holm results.

Analysis SHA-256: `2b6702e018e1b92aa0973b936457d7f77698c2b52ac514320cc0e8fe406efac4`.
No prediction, trading strategy or causal effect is claimed. Missing original
publication times and revised histories preclude a qualified real-time backtest.

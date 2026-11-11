<!-- SPDX-License-Identifier: Apache-2.0 -->

# Financial Systems Intelligence Engine — FSIE 0.1.0

A project by **Alessio Mattoccia**.

ENGINE 04 / MARKETS in Research Engines, alongside CODE, LIFE and MATTER.
A local computational research application for institutional time series,
yield-curve regimes, financial conditions and dependence-aware statistics.
Original code: Apache License 2.0. Institutional data retain separate terms.

## Run on the qualified environment

Python 3.12 on macOS Apple Silicon was tested on the Mac mini M1 with 16 GiB RAM.
Other platforms are not qualified. FSIE needs no C++ analyzer, broker or cloud key.
From the existing source repository root:

```sh
python3.12 scripts/setup_financial.py
.venv-fsie/bin/python -m financial.cli serve
```

Open http://127.0.0.1:4204/ . Opening the dashboard does not acquire data.
Press **Start research** to explicitly download official data and run the
analysis. An unchecked refresh box uses the hash-verified cache. Refresh records
a new acquisition and changes against previously seen source values.
No persistent service is installed. Ctrl-C stops the local server.

Equivalent command-line study:

```sh
.venv-fsie/bin/python -m financial.cli run --data .local/financial --start 2000-01-01 --end 2026-11-06
.venv-fsie/bin/python -m financial.cli verify --data .local/financial --job JOB_ID
```

The end date defaults to the current UTC date. Jobs and frozen response snapshots
persist locally. An interrupted job can be resumed with `--resume JOB_ID` or the
dashboard. No personal financial records are accepted by the v0.1 workflow.

## Demonstrated real experiment

FSIE-001 acquired **139,903 long-format observations**
from 13 official response files; **98,286** fall in the requested
period, with 0 invalid observations and 0 duplicate identities. There are 21 series:
14 Treasury maturities, six Chicago Fed indices/subindices and SOFR.
The common study covers **2000-01-07–2026-10-30**:
6,711 Treasury sessions and 1,400 complete reference weeks.
The exact source hashes, acquisition timestamps and versions are in the manifest.

* 10Y–2Y: 1,009 inverted of 6,711 known sessions; 20 observed inversion episodes.
* 10Y–3M: 1,117 inverted of 6,708 known sessions; 38 episodes.
* **0 of 28** predeclared first-difference lag tests pass HAC/Holm at 5%.
  The null outcome is reported, rather than selecting favorable unadjusted tests.
* 115 past-normalized extreme-change flags are computed with declared thresholds.

This is a retrospective current-vintage study. NFCI histories can revise;
original historical publication timestamps are unknown. It is not a verified
real-time predictive backtest, investment recommendation or crisis forecast.

## Dashboard and API

Overview, Market Explorer, Yield Curve Analysis, Correlation Lab, Systemic Risk,
Research Findings and AI Insights use the completed local database. Filters,
selected-date curves, pagination, lag/rolling controls and exports are functional.
Dates without observations show an explicit empty state, not a filled curve.
API access is loopback-only, protected by Host/Origin checks and a same-origin
mutation header. There is no public scientific backend.

## Optional local AI

```sh
.venv-fsie/bin/python -m financial.cli serve --ollama-url http://127.0.0.1:11434 --ollama-model YOUR_EXISTING_LOCAL_MODEL
```

No model is downloaded by setup or automatically contacted. The optional local
model receives a bounded finding/evidence subset. Observed data and computed
numbers remain outside generated prose. Unknown references and generated numeric
claims are rejected. An unavailable model leaves quantitative analysis intact.

## Additional source support

A second-phase ECB SDMX connector was tested on 22 USD/EUR observations in
October 2026, separate from FSIE-001. Run `financial.cli ecb --start 2026-10-01
--end 2026-10-30`. FRED/ALFRED and SEC are future interfaces, not operational
connectors in this release; no credentials are invented.

An explicit official-file fallback is available for inaccessible downloads:
`financial.cli import-file --file OFFICIAL_FILE --source-url ALLOWLISTED_URL
--parser nfci_csv --data .local/financial`. It records manually asserted origin,
not authenticated HTTP. Such input is rejected by the public-study export gate.

## Reports, benchmark and license

See `reports/financial/`, the source manifest and the documents below. The separate
20-million-row benchmark is **synthetic technical data**, never a scientific
market finding. Exact historical numerical replay requires the manifest-matching
original raw cache; the public source release does not redistribute full
institutional time-series archives. New downloads may have different vintages.

Read ARCHITECTURE.md, ARCHITECTURE_REUSE.md, DATA_SOURCES.md, DATA_GOVERNANCE.md,
QUANTITATIVE_METHODOLOGY.md, EXPERIMENT_FSIE-001.md, RESULTS.md,
REPRODUCIBILITY.md, BENCHMARK.md, LIMITATIONS.md and THIRD_PARTY_NOTICES.md.
The included LICENSE is the complete official Apache License 2.0 for original code.

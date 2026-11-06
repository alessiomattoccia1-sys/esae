<!-- SPDX-License-Identifier: Apache-2.0 -->
# FSIE assessment and architecture reuse

Creator: Codex per Alessio / Mattoccia Labs,6November2026. PROJECT/EVIDENCE;
retain until explicit retirement. Prepared after actual source inspection and
baseline testing, before implementation. Existing repository `esae`, commit
0981207102312180c406eb63d0234904bf9a12cb. No clone or replacement repository.

ESAE0.1.1, GEE0.1.0 and MDE0.1.0 are implemented. Initial regression:
**169passed,0failed/errors/skipped**, one preexisting Starlette HTTPX warning.
ESAE uses native sandboxed C++ analyzers; GEE uses ClinVar/Ensembl deterministic
identity/evidence logic; MDE has completed93902-material JARVIS screening.
Runtime, API and UI hashes of all three are frozen as baseline evidence.

| Component | Classification | Intervention |
|---|---|---|
| Shared PublicCache | Direct reuse | FSIE-specific strict official URL policy/organization/parser injected through existing compatible hooks; immutable content-addressed vintage wrapper |
| Shared JobStore / OperationLock | Direct reuse | Separate financial SQLite job/metadata archive and domain orchestration; no earlier database migration |
| Domain normalization | New financial module | Percent points vs basis points, dates/frequencies/publication/vintage semantics; no genomic/material concepts reused |
| Existing SQLite | Adaptable | Job/source/series/revision/finding metadata; DuckDB/partitioned Parquet added for actual analytical query layer |
| Statistical algorithms | New financial module | Explicit yield spreads, trailing volatility/regimes/anomalies, lag convention, block bootstrap and HAC/Holm |
| Shared local AI | Direct reuse | Existing bounded loopback hypothesis helper, exact evidence IDs, deterministic facts separate, optional/no cloud |
| Dashboard | Adaptable | Existing original ESAE CSS, safe DOM/SVG and FastAPI boundary; seven financial areas, no new frontend framework |
| Report/export | Adaptable pattern | Original financial HTML/JSON/CSV, source/config/version manifest, offline raw replay and derived-only public output |
| Website | Adaptable existing master | React/esbuild source83 overlay; extend CODE/LIFE/MATTER to MARKETS, retain earlier page bodies and results |
| Prior scientific/C++ analyzers | Domain-specific | Preserve unchanged; not reused as finance classifications or confidence scores |
| Analytical scalability | New | Bounded DuckDB/Parquet benchmark on clearly synthetic data, separate from scientific findings |

## Source assessment

Live limited probes succeeded for official Treasury2026 XML (OData/Atom), Chicago
Fed NFCI/ANFCI CSV and New York Fed SOFR JSON. Treasury provides a historical
1990–2024 CSV and annual XML for later years. CSV schema is checked before parsing.
Chicago CSV has Friday_of_Week,NFCI,ANFCI,Risk,Credit,Leverage,Nonfinancial_Leverage.
The source describes weekly Wednesday publication and revisions; observation
Friday is not original publication time. The study will use acquired latest
vintages retrospectively, not a real-time predictive backtest.

Source rights are distinct from Apache2.0 original code. Raw response archives and
full institution time series remain local. Public output prioritizes original
computed aggregates, methods and source links; no blanket source-data relicensing,
Fed endorsement, copied institutional charts or indiscriminate archive publication.
Chicago terms are recorded and full index redistribution is excluded. New York
reference-rate terms/disclaimers are checked before public output.

## Architecture decisions

A separate `.venv-fsie` preserves earlier environments. NumPy/SciPy/Pandas/
Statsmodels provide explicit math; DuckDB/PyArrow provide partitioned columnar
storage and actual query/benchmark operations. No new JS framework or Plotly/CDN
is needed; original local SVG charts remain sufficient. The optional AI reuses
existing local code and the already present model only when explicitly enabled.

No changes to ATENA, Appunti, mail, firewall or persistent services. FSIE will
bind only to loopback. The website remains static and uses only authorized
TCP2223, a fresh status/baseline, hash allowlist and real post-deploy verification.
Canonical Apps background and ESAE serious-benchmark hierarchy remain required.

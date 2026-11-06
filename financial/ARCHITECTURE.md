<!-- SPDX-License-Identifier: Apache-2.0 -->

# Architecture

The existing repository remains the source of truth. FSIE adds the `financial`
Python package and a separate local archive/environment. Existing ESAE, GEE,
MDE algorithms, APIs, UI files and shared runtime files remain byte-identical.

```text
Official Treasury CSV/XML + Chicago CSV + New York SOFR JSON
    -> strict institution URL policies + shared bounded HTTP cache
    -> immutable SHA-256 response snapshots + acquisition metadata
    -> domain parsers / date, unit, missingness and identity checks
    -> SQLite jobs, sources, releases, series, revisions, experiments, findings
    -> year-partitioned Parquet + bounded DuckDB analytical database
    -> deterministic financial analysis
    -> original HTML/JSON/CSV findings and optional local hypotheses
    -> loopback FastAPI / original ESAE CSS and safe DOM/SVG dashboard
    -> validated derived-only static website export
```

Reused code is imported from `research_core`: PublicCache, JobStore,
OperationLock, local_boundary, hypothesis and loopback URL validation. No common
module is rewritten. Domain-specific parsers, financial rules and statistics
remain in FSIE. `connectors.py`, `parsers.py`, `storage.py`, `analysis.py`,
`service.py`, `api.py`, `report.py`, `export.py`, `benchmark.py` and `ecb.py` each
have a defined responsibility. The website reuses React/esbuild and the existing
Research Engines shell; it does not expose the local database/API.

Analytical connections are limited to 512 MB and two DuckDB threads. Arrow
inserts use batches of 5,000; Parquet partitions by year. The real v0.1 experiment
is bounded to about 100,000 in-period observations and uses Pandas for statistics.
The separate 20-million-row SQL/Parquet benchmark demonstrates the warehouse
path only; it does not qualify statistical analysis of arbitrary-size panels.

Source acquisition is explicit, allowlisted HTTPS with response/cache limits,
validated redirects, retry/backoff and immutable vintage snapshots. Imports
never execute source text. Mutations use the existing local-only request boundary.
There is no trading, authentication-secret input, external SQL, arbitrary URL API,
cloud fallback or public scientific service.

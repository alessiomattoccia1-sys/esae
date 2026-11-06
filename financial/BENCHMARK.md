<!-- SPDX-License-Identifier: Apache-2.0 -->

# FSIE-BIGDATA-001 — synthetic infrastructure benchmark

**SYNTHETIC TECHNICAL DATA. NOT FINANCIAL RESEARCH.**
20,000,000 generated rows, 10,000 series, dates derived from a deterministic
integer sequence, and `sin(i*.001)+cos((i%10000)*.1)` values. No market data.
The SQL generator streams into partitioned Parquet, then actually loads that
Parquet into a DuckDB table and runs analytical queries against Parquet.

Machine: None, arm64,
Darwin 27.0.0,
0 GiB physical memory.
DuckDB 2.0.0; 512 MB memory setting, two threads, ZSTD,
122,880-row groups, yearly partitions. No exclusive machine or forced cold-cache
condition is claimed. Whole fresh-process peak RSS includes Python/imports.

| Measurement | Actual value |
|---|---:|
| Generated / counted rows | 20,000,000 |
| Parquet files / year partitions | 6 / 6 |
| Parquet size | 163,232,364 bytes |
| Loaded database size | 152,842,240 bytes |
| Generation + Parquet write | 1.667033 s |
| Actual Parquet-to-DuckDB load | 0.903476 s |
| Whole-process peak RSS | 517.28 MiB |
| Metadata count query median | 0.005568 s |
| Time + series filter median | 0.004648 s |
| 10,000-group aggregation median | 0.161466 s |
| Full value scan median | 0.127424 s |

Each query ran three times. All timings, SQL, output hashes and samples, machine,
file hashes and source-code hash are in FSIE-BENCHMARK.json. Count=20,000,000 and
filter count=3,100 are independently checked against integer generator arithmetic.
Parallel floating-point reductions can differ in low-order bits; actual hashes
are retained rather than claiming bitwise arithmetic associativity. Metadata
COUNT alone does not exercise value decoding, so a full scan and aggregation
are included. This benchmark qualifies this tested workload, not arbitrary big
data sizes, remote markets, statistical accuracy or performance on other hardware.

Reproduce in a fresh CLI process:

```sh
.venv-fsie/bin/python -m financial.cli benchmark --data .local/financial --benchmark-rows 20000000
```

Requires at least 5 GB free disk. The configured safety bound is 50 million rows;
only the actual 20-million-row workload is qualified. Source hash for this run:
`16b2d24062c03a5a071b7884d48699b67bc9ab0a5aae9b57d347c41566688461`. Completed 2026-11-06T06:15:59.723358+00:00.

# Measured benchmark

Native Apple M1; 17179869184bytes physical RAM; macOS-27.0-arm64-arm-64bit, Python3.12.14; external SviluppoAppSSD. Values describe this measured environment only.

Original XES 728,558,522bytes; compressed 16,901,365bytes; 160Parquet partitions, 65,520,493bytes. Qualified full current-parser streaming import 43.060689s. Initial full import+discovery recorded 51.377356s, process RSS high-water 954,826,752bytes. This includes Python/Arrow/DuckDB; the SQL memory setting512MB is not total-process memory.

| Experiment | Measured wall s incl exports | Lifetime process RSS bytes |
|---|---:|---:|
| OTE-001 | 9.786274 | 876167168 |
| OTE-002 | 30.157354 | 1024278528 |
| OTE-003 | 47.515896 | 1024278528 |

These experiment timings reuse verified original/cache/Parquet data; they are not acquisition times. OTE-002includes120full model/cohort simulations plus4096semi-Markov interval draws per category. OTE-003includes350main and45sensitivity simulations;975maximum agents. Event records are bounded and display only20case agents plus queue/resource telemetry.

Process RSS is a lifetime high-water mark, not incremental per-job allocation. Parallel browser checks or later cached repeats are not misreported as first-acquisition benchmarks. Individual job stages and exact dependency versions are in the experiment manifests.

No throughput claim beyond this measured log, cohort, hardware or configuration.

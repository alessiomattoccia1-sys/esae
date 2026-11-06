# Performance and resource bounds

Measured on the physical Mac mini M1, 16 GiB RAM, macOS arm64, Python 3.12.14. Other workloads may be present; this is not a dedicated-machine or arbitrary-scale claim.

The benchmark reuses the actual frozen experimental data. Runs are separate Python processes and use a warm verified disk cache, with zero network bytes during the measured reruns. It includes selected-data parsing, analysis and scientific figure generation. No synthetic record is counted as experimental data.

| Study | Source objects | Source response bytes | Selected-read / s | Analysis / s | Plots / s | Total before final report write / s | Process peak / MiB | Child peak / MiB |
|---|---|---|---|---|---|---|---|---|
| FPE-001 | 80 | 25549783 | 0.386045 | 1.159301 | 2.467026 | 6.225489 | 412.766 | 4.078 |
| FPE-002 | 2 | 64974349 | 0.106369 | 8.071111 | 0.716439 | 10.940019 | 462.969 | 41.328 |

The legacy manifest child field is named native_reader_child_peak_rss_bytes; the operating-system RUSAGE_CHILDREN measurement includes all child processes, including Git metadata queries. It is not a summed concurrent RSS peak. Total is captured before final JSON/HTML serialization and SQLite persistence; those last writes are excluded. No unmeasured hard RSS guarantee is asserted.

Cold acquisition evidence is retained separately from these warm runs. HTTP source records retain individual acquisition timestamps, source hashes and response byte counts. The complete STFC archive is 64,965,109 bytes and expands to 81,949,600 bytes. MAST reads 80 metadata/coordinate/selected chunk objects totaling 25,549,783 response bytes, rather than all diagnostics of all shots. Slow remote-object latency is not presented as numerical processing time.

Bounds: public cache 512,000,000 bytes, one response at most 80,000,000 bytes; selected array/chunk and file-count limits; at most two independent chunk downloads; single-threaded Dask selection; ZIP at most 2048 members, 200,000,000 expanded bytes and 32,000,000 bytes per member; HDF helper CPU/time/output bounds inherited unchanged. Raw detector output uses row chunks below the existing per-file bound. Cancellation is checked between bounded stages.

Reproduction: run each known experiment in a new Python process with --offline and its existing source cache. Manifests record exact dependency versions, source/algorithm versions and process/environment details. Both complete acquired-source replays passed without network; no OS cache flush is claimed.

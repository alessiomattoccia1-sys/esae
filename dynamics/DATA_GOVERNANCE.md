# Data governance

Only historical civil research datasets and explicitly synthetic states. Original acquired bytes stay in local content-addressed cache, with URL, version, acquisition time, response validators and SHA256. Original selected CSV files stay separate from normalized Parquet and results. Exclusions/deduplication/transforms are recorded. No silent zero fill, source sorting or synthetic fallback; MILUV stable time sorting is explicit.

Public source distribution excludes raw archives, images, sensor IPs, absolute GNSS origins, private paths, model weights, credentials and local SQLite. Public normalized relative flight displays, range residual statistics and generated synthetic replay data carry source attribution. Derived IDF/MILUV material remains CC BY4.0 with modifications identified; Apache2.0 applies to original code only. Source calibration/reference are not independent truth. Public website uses static results; analysis backend remains loopback.

Dataset updates are new acquisitions; pinned replay never substitutes a newer source vintage. Cache symlinks/invalid digests are rejected. Resume retains completed bytes and checks archive validators before adding ranges. Fixed limits are not advertised as an OS-level hard memory guarantee. Cancellation and errors preserve completed evidence.

Creator: Codex per Alessio, 6 November2026. PROJECT; retain until explicit retirement. Original software SPDX-License-Identifier: Apache-2.0.

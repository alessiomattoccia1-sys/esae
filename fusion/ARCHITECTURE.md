# Architecture

The existing repository and four engines remain in place. FPRE imports shared PublicCache, JobStore, OperationLock, strict loopback web boundary, local hypothesis helper and the existing bounded sandbox runner. No shared algorithm or database migration is required.

- acquisition.py: exact official-source policy, immutable SHA-256 blobs, bounded HTTP cache and source journal.
- mast.py: actual catalog selection, safe metadata/codec/shape checks, selected Zarr2/3 chunk mirror, Xarray/Dask lazy reads.
- physics.py: Pint unit compatibility and explicitly independent uncertainty propagation.
- signals.py: magnetic numerical algorithms, finite-segment gates, separate original/transformed displays.
- inertial.py / hdf_worker.py: bounded ZIP inventory and isolated native HDF4 reader, generic detector metrics.
- experiments.py: independent FPE-001 and FPE-002 orchestrators, deterministic scientific fingerprints.
- storage.py / service.py: separate SQLite registry and job directories, cancellation/resume, full raw replay.
- report.py: standalone reports and scientific figures with source-specific licenses.
- api.py / static/: local FastAPI and eight-area native-style dashboard.

SQLite distinguishes experiments, shots, diagnostics, measurements, analyses and findings. Raw response bytes, selected normalized arrays and generated outputs are separate. Replays write a new owned folder and never alter originals.

The website publishes selected static reports and screenshots; it does not expose this local backend or database. See ARCHITECTURE_REUSE.md for the pre-development assessment.


Original software © 2026 Mattoccia Labs, Apache License 2.0. Scientific data and derived artifacts retain the separate source licenses.

# Dynamics Lab — Drone Dynamics Engine

**English source distribution · v0.1.1**

A project by **Alessio Mattoccia**.

A separate family from Research Engines. Historical civil flight observations, transparent mathematical models and explicitly synthetic multi-agent experiments.

## Run on the qualified platform

Python3.12 / macOS Apple Silicon. Existing development environment is reused read-only on the Mini. A source distribution creates its own .venv-dynamics; it does not migrate or replace the five Research Engines.

    python3.12 dynamics/setup.py
    .venv-dynamics/bin/python -m dynamics.cli serve --data .local/dynamics-data

Open http://127.0.0.1:4206/. Research Results → Run DME-001 / DME-002 / DME-003. Initial acquisition uses bounded official HTTPS ranges; no full multi-GB archives or model downloads. Running all studies retrieves30IDF GPS CSVs and six MILUV CSVs plus pinned calibration documents. Cache and results persist; refreshing the page retains the jobs. For an exploratory simulation choose Simulation Lab → agents/scenario/seed → Compute simulation → replay/agent/zoom/time controls.

    .venv-dynamics/bin/python -m dynamics.cli run DME-001
    .venv-dynamics/bin/python -m dynamics.cli run DME-002
    .venv-dynamics/bin/python -m dynamics.cli run DME-003
    .venv-dynamics/bin/python -m dynamics.cli reproduce JOB_UUID

DME-002 explicitly substitutes MILUV for inaccessible AERPAW with owner authorization. It measures scalar range residuals, not3D position errors. DME-001 uses noisy GNSS reference, not known truth. DME-003 is wholly synthetic.

## Implemented

Random Walk, correlated Random Walk, CV, CA, OU, linear Kalman, EKF, particle filter, Gaussian HMM, Monte Carlo. Numerical integration via SciPy. Six individual flight models plus a validation-fitted simplex ensemble. Generic2D/3D abstract simulation, five scenarios, synchronous velocity-consensus interactions, partial observations, separate random streams, checkpoint/replay. Two-dimensional UI only; simulator models CV/CRW are a subset of the mathematical registry. SQLite job/model/source metadata and per-flight Parquet. Loopback FastAPI,7dashboard areas, report JSON/HTML/CSV/manifests, original scientific figures. Optional loopback Ollama; no cloud required.

## Licence

Original code Apache License2.0, complete text in LICENSE. Shared Research Core and minimal ESAE filesystem/time/loopback helpers retain original attribution. IDF_DS and MILUV data are CC BY4.0, separate from code. No raw datasets, hardware control, live tracking or tactical functions are distributed. See THIRD_PARTY_NOTICES.md and DATA_GOVERNANCE.md.

Creator: Codex per Alessio, 6 November2026. PROJECT; retain until explicit retirement. Original software SPDX-License-Identifier: Apache-2.0.

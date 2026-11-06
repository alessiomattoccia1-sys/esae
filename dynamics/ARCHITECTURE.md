# Architecture

Mathematical Core(mathematical.py) has no UAV-specific parameters. Simulation Core(simulation.py) operates on abstract states, a common clock and local synchronous interactions. Flight normalization(flights.py), model evaluation(validation.py) and MILUV diagnostics(miluv.py) are application layers. experiments.py orchestrates three independent study paths.

service.py uses unchanged Shared Research Core JobStore/OperationLock. Dynamics has a separate SQLite database and raw-content-addressed cache. Metadata tables cover jobs, datasets, models and result hashes; normalized observations remain Parquet per source flight. Acquisition bounds compressed member sizes, expanded bytes, archive entry counts and total downloads. No automatic archive script execution.

FastAPI binds literal127.0.0.1; shared middleware checks Host/Origin, mutation header,16KB request limit and strict self-only CSP. UI scripts/styles are local. Reports are static; public website has no analysis API. Jobs compute in one background thread with an interprocess lease; cancellation is checked between bounded source/model/simulation stages. A stopped process marks active jobs interrupted when the next exclusive engine starts. Resume retains acquired source identities; full offline reproduce pins all original bytes.

Models are first-party registered classes, not arbitrary uploaded plugins or deserialized callables. EKF callbacks are trusted application code, never dataset scripts. No changes to previous engine algorithms or endpoints.

Creator: Codex per Alessio, 6 November2026. PROJECT; retain until explicit retirement. Original software SPDX-License-Identifier: Apache-2.0.

# Architecture assessment — Operations Twin Engine

Creator: Codex per Alessio, 6 November 2026. PROJECT; retain until explicit retirement.

The operational repository is the existing `esae` repository, commit `58e96aab10ca5e9bca5d0b902260919dd0adda94`. No new repository or clone. Research Engines has five domain engines; Dynamics Lab has Drone Dynamics in `dynamics/`. Baseline executed on the verified Mini M1 and SviluppoApp: 284 passed, two preexisting Starlette/Zarr warnings. 101 Python/API/UI/shared source files frozen by SHA-256 before implementation.

The mathematical core actually implements Gaussian motion processes, estimators, HMM and Monte Carlo for state trajectories. Generic numeric serialization/fingerprints and NumPy/SciPy dependencies are reusable; motion/aircraft dataset models are not business process models. The existing simulator uses fixed timesteps and records synthetic states. It has no discrete-event scheduler, queues, finite resource model or process-mining parser. Claiming these were already implemented would be incorrect.

Shared Research Core supplies official-source cache, resumable downloads, JobStore/OperationLock, literal-loopback API boundary and optional referenced local Ollama hypotheses. Dynamics uses separate SQLite job metadata, Parquet observations, asynchronous local jobs, reports and a seven-area HTML/CSS/DOM/canvas interface. Existing environments remain unchanged.

Website: existing React/esbuild static overlay, IT/EN/DE, light/dark; canonical builder `site-integration/dynamics-20261106/build.mjs`, current source87. General site build contains unqualified changes and is excluded. Publication uses the installed Mini→VPS TCP2223 channel only, fresh baseline and explicit SHA allowlist; no backend or service changes.

Necessary extensions: a generic SimPy-backed discrete-event adapter inside the existing Dynamics shared-core namespace, generic seeded experiment/statistical helpers, Operations-specific ingestion/discovery/calibration/scenario modules, separate local registry and dashboard. SimPy is absent initially. An isolated OTE environment is justified to install only the required compatible dependencies, rather than changing the qualified six engines. PM4Py is not used or copied.

Scientific boundary: BPI timestamps describe observed elapsed intervals. Resource capacity, service times and individual productivity are not identified from completion-only logs. Empirical and resource-constrained twins must stay separate. Resource identifiers are used locally as aggregate metadata, never person rankings; public projections exclude case/resource/vendor identifiers and anonymized monetary amounts.

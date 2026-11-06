# Architecture

One operational repository; two independent product families. Operations Twin is Dynamics Lab Engine02. No ERP integration, database migration or replacement engine is needed.

`ingestion.py` acquires the official source through the unchanged strict-policy PublicCache, verifies source version/licence/size/MD5/SHA256, and normalizes streams into Zstd Parquet partitions. `discovery.py` creates an isolated DuckDB analytical store with512MB query-memory configuration and one deterministic query thread. Metadata, jobs, evidence and results use the unchanged JobStore/OperationLock contracts in a separate directory. Temporal means sum integer microsecond differences before a single floating-point division, avoiding reduction-order drift. The512MB DuckDB limit does not bound total Python/Arrow process memory; measured whole-process RSS is reported separately.

`dynamics/events.py` adds a generic SimPy adapter because the existing fixed-step motion simulator has no queue/resource scheduler. Existing motion algorithms, APIs, UI and simulator are unchanged. `dynamics/experiment_core.py` provides domain-independent seeded streams, distribution draws and uncertainty helpers. `twin.py` applies these interfaces to case/task/resource agents and workflow events. Motion coordinates are not reinterpreted as business states.

`experiments.py` evaluates three elapsed-time models with chronological/document-disjoint cohorts and separates hypothetical resource scenarios. `process_models.py` implements optional arrival/interval assumptions; empirical schedules and gaps remain the published defaults. `reporting.py` generates standalone artifacts. `service.py`, `api.py` and the local dashboard expose bounded loopback-only jobs. The public React page publishes generated static evidence and replays computed events; it never exposes the analytical API.

Local original XES, normalized events, analytical tables, job metadata, fitted parameters and exports remain distinct. The source distribution contains no original event logs or private import keys. See ARCHITECTURE_REUSE.md for component-by-component decisions.
